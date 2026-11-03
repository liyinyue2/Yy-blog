"""音乐模块：曲目元数据 + 流式上传 + HTTP Range 流媒体（music.db）。

v2.1 起接口拆分为公开/管理两套：
- /api/public/music/*  匿名只读，仅暴露 visibility='public' 的曲目
- /api/admin/music/*   require_admin，含上传/可见性切换/删除
v2.0 旧公开接口 /api/music/* 已删除（无法按 visibility 过滤，存在越权读取风险）。

关于 safeuploads：文档指定的 `safeuploads` 库在 PyPI 不存在（2026-11 检索确认），
按文档"安全硬约束"条款以同等强度的内置校验实现：扩展名白名单 + MIME 签名校验 + 拒绝用户原始文件名。
"""
import re
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile
from fastapi.responses import StreamingResponse
from mutagen import File as MutagenFile
from pydantic import BaseModel

from app.core.audit import audit_log
from app.core.config import settings
from app.core.database import db
from app.core.ratelimit import client_ip
from app.core.security import require_admin

router = APIRouter(prefix="/api", tags=["music"])

# 音频扩展名白名单 → 允许的 MIME 签名（文件头魔数）
AUDIO_WHITELIST = {
    "mp3": [b"ID3", b"\xff\xfb", b"\xff\xf3", b"\xff\xf2"],
    "flac": [b"fLaC"],
    "ogg": [b"OggS"],
    "m4a": [b"ftyp"],       # M4A 魔数位于偏移 4
    "wav": [b"RIFF"],
}
MAX_AUDIO_SIZE = 100 * 1024 * 1024  # 100MB（音频文件通常较大，Nginx 层对 /api/ 上限单独放宽）

VISIBILITY_VALUES = {"public", "private"}

# 列表对外字段：不含 file_path / cover_path（磁盘绝对路径不外泄；封面暂无服务接口，前端回退站点图标）
_TRACK_COLS = "id, title, artist, album, duration, created_at"


class VisibilityBody(BaseModel):
    visibility: str = ""


def _sniff_ok(ext: str, head: bytes) -> bool:
    sigs = AUDIO_WHITELIST.get(ext, [])
    for sig in sigs:
        if ext == "m4a":
            if head[4:8] == sig:
                return True
        elif head.startswith(sig):
            return True
    return False


def _range_header(range_header: str, size: int) -> tuple[int, int]:
    """解析 Range: bytes=start-end；返回 (start, end)，不合法抛 416。"""
    m = re.fullmatch(r"bytes=(\d*)-(\d*)", range_header.strip())
    if not m or (not m.group(1) and not m.group(2)):
        raise HTTPException(status_code=416, detail="Range 不合法")
    start_s, end_s = m.groups()
    if start_s == "":
        # 后缀形式：bytes=-N → 最后 N 字节
        length = int(end_s)
        if length == 0 or length > size:
            raise HTTPException(status_code=416, detail="Range 超出范围")
        return size - length, size - 1
    start = int(start_s)
    end = int(end_s) if end_s else size - 1
    if start >= size or end < start:
        raise HTTPException(status_code=416, detail="Range 超出范围")
    return start, min(end, size - 1)


def _resolve_track_file(file_path: str) -> Path:
    """路径穿越防护：解析后必须仍位于 uploads/music 内。"""
    try:
        resolved = Path(file_path).resolve()
        resolved.relative_to((settings.UPLOAD_DIR / "music").resolve())
    except (ValueError, OSError):
        raise HTTPException(status_code=400, detail="非法文件路径")
    if not resolved.exists():
        raise HTTPException(status_code=404, detail="音频文件缺失")
    return resolved


def _stream_file(resolved: Path, request: Request) -> StreamingResponse:
    """HTTP Range 流媒体：按分块响应，禁止一次性读全文件。"""
    size = resolved.stat().st_size
    range_header = request.headers.get("Range")
    chunk_size = 256 * 1024
    media_type = {
        "mp3": "audio/mpeg", "flac": "audio/flac", "ogg": "audio/ogg",
        "m4a": "audio/mp4", "wav": "audio/wav",
    }.get(resolved.suffix.lower().lstrip("."), "audio/mpeg")

    def file_iter(start: int, end: int):
        with open(resolved, "rb") as f:
            f.seek(start)
            remaining = end - start + 1
            while remaining > 0:
                data = f.read(min(chunk_size, remaining))
                if not data:
                    break
                remaining -= len(data)
                yield data

    if range_header:
        start, end = _range_header(range_header, size)
        headers = {
            "Content-Range": f"bytes {start}-{end}/{size}",
            "Accept-Ranges": "bytes",
            "Content-Length": str(end - start + 1),
            "Cache-Control": "no-store",
        }
        return StreamingResponse(file_iter(start, end), status_code=206,
                                 media_type=media_type, headers=headers)
    headers = {"Accept-Ranges": "bytes", "Content-Length": str(size), "Cache-Control": "no-store"}
    return StreamingResponse(file_iter(0, size - 1), media_type=media_type, headers=headers)


# ---------- 公开接口（匿名只读） ----------

@router.get("/public/music/tracks")
def list_public_tracks(q: str = "", artist: str = "", tag: str = "",
                       limit: int = 50, offset: int = 0):
    """公开曲目列表/搜索：仅 visibility='public'；tag 走统一标签体系。"""
    conn = db.conn()
    limit = max(1, min(limit, 100))
    sql = f"SELECT {_TRACK_COLS} FROM music.tracks WHERE visibility = 'public'"
    params: list = []
    if q:
        sql += " AND (title LIKE ? OR artist LIKE ? OR album LIKE ?)"
        params += [f"%{q}%"] * 3
    if artist:
        sql += " AND artist = ?"
        params.append(artist)
    if tag:
        sql += """ AND id IN (SELECT g.entity_id FROM taggables g JOIN tags t ON t.id = g.tag_id
                   WHERE g.entity_type = 'track' AND (t.name = ?))"""
        params.append(tag)
    sql += " ORDER BY id DESC LIMIT ? OFFSET ?"
    params += [limit, max(0, offset)]
    return [dict(r) for r in conn.execute(sql, params)]


@router.get("/public/music/now")
def public_now_playing():
    """公开「正在听」：只给最近一次播放的公开曲目，不暴露播放历史。"""
    row = db.conn().execute(
        "SELECT t.id, t.title, t.artist, t.album, t.duration, h.played_at"
        " FROM music.play_history h JOIN music.tracks t ON t.id = h.track_id"
        " WHERE t.visibility = 'public' ORDER BY h.id DESC LIMIT 1").fetchone()
    return dict(row) if row else None


@router.get("/public/music/stream/{tid}")
def stream_public_track(tid: int, request: Request):
    """公开流媒体：private 曲目 403，不存在 404。"""
    conn = db.conn()
    row = conn.execute(
        "SELECT file_path, visibility FROM music.tracks WHERE id = ?", (tid,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="曲目不存在")
    if row["visibility"] != "public":
        raise HTTPException(status_code=403, detail="该曲目未公开")
    return _stream_file(_resolve_track_file(row["file_path"]), request)


# ---------- 管理接口（require_admin） ----------

@router.get("/admin/music/tracks")
def list_all_tracks(limit: int = 100, offset: int = 0, user: dict = Depends(require_admin)):
    """全部曲目（含 private），带 visibility 字段。"""
    conn = db.conn()
    limit = max(1, min(limit, 500))
    sql = (f"SELECT {_TRACK_COLS}, visibility FROM music.tracks"
           " ORDER BY id DESC LIMIT ? OFFSET ?")
    return [dict(r) for r in conn.execute(sql, (limit, max(0, offset)))]


@router.post("/admin/music/upload")
async def upload_track(request: Request, file: UploadFile,
                       user: dict = Depends(require_admin)):
    """流式上传音频：扩展名白名单 + MIME 签名校验 + UUID 落盘（禁用原始文件名）。新曲目默认 public。"""
    ip = client_ip(request)
    ext = (file.filename or "").lower().rsplit(".", 1)[-1]
    if ext not in AUDIO_WHITELIST:
        raise HTTPException(status_code=400, detail=f"仅支持 {'/'.join(AUDIO_WHITELIST)} 格式")

    dest_dir = settings.UPLOAD_DIR / "music"
    dest_dir.mkdir(parents=True, exist_ok=True)
    uuid_name = f"{uuid.uuid4().hex}.{ext}"
    dest = dest_dir / uuid_name

    size = 0
    head = b""
    with open(dest, "wb") as out:
        while chunk := await file.read(1024 * 512):
            size += len(chunk)
            if size > MAX_AUDIO_SIZE:
                out.close()
                dest.unlink(missing_ok=True)
                raise HTTPException(status_code=400, detail="文件超过 100MB 限制")
            if len(head) < 16:
                head += chunk
            out.write(chunk)

    if not _sniff_ok(ext, head[:16]):
        dest.unlink(missing_ok=True)
        audit_log("music-reject", f"{file.filename}: MIME 签名不符", ip, user=user["username"])
        raise HTTPException(status_code=400, detail="文件内容与音频格式不符（MIME 签名校验失败）")

    # mutagen 解析元数据
    duration = 0.0
    try:
        meta = MutagenFile(str(dest))
        if meta is not None and meta.info:
            duration = round(float(meta.info.length), 2)
    except Exception:
        pass  # 元数据解析失败不阻断上传

    title = (file.filename or "").rsplit(".", 1)[0][:200]
    conn = db.conn()
    try:
        cur = conn.execute(
            "INSERT INTO music.tracks (title, duration, file_path, visibility, created_at)"
            " VALUES (?,?,?,'public',datetime('now','localtime'))",
            (title, duration, str(dest)))
        conn.commit()
    except Exception:
        conn.rollback()
        dest.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail="保存曲目失败，请稍后再试")
    audit_log("music-upload", f"{uuid_name} ({size}B, {duration}s)", ip, user=user["username"])
    return {"ok": True, "id": cur.lastrowid, "title": title, "duration": duration, "size": size}


@router.patch("/admin/music/{tid}")
def update_track_visibility(tid: int, body: VisibilityBody, request: Request,
                            user: dict = Depends(require_admin)):
    """切换曲目可见性：白名单校验，非法值 400。"""
    if body.visibility not in VISIBILITY_VALUES:
        raise HTTPException(status_code=400, detail="visibility 仅允许 public / private")
    conn = db.conn()
    row = conn.execute("SELECT visibility FROM music.tracks WHERE id = ?", (tid,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="曲目不存在")
    old = row["visibility"]
    conn.execute("UPDATE music.tracks SET visibility = ? WHERE id = ?", (body.visibility, tid))
    conn.commit()
    audit_log("music-visibility", f"id={tid} {old}->{body.visibility}",
              client_ip(request), user=user["username"])
    return {"ok": True, "id": tid, "visibility": body.visibility}


@router.delete("/admin/music/{tid}")
def delete_track(tid: int, request: Request, user: dict = Depends(require_admin)):
    conn = db.conn()
    row = conn.execute("SELECT file_path FROM music.tracks WHERE id = ?", (tid,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="曲目不存在")
    dest = Path(row["file_path"])
    try:
        dest.resolve().relative_to((settings.UPLOAD_DIR / "music").resolve())
        dest.unlink(missing_ok=True)
    except (ValueError, OSError):
        pass  # 路径异常时只删记录，不动文件系统
    conn.execute("DELETE FROM taggables WHERE entity_type='track' AND entity_id=?", (tid,))
    conn.execute("DELETE FROM music.track_favorites WHERE track_id=?", (tid,))
    conn.execute("DELETE FROM music.play_history WHERE track_id=?", (tid,))
    conn.execute("DELETE FROM music.tracks WHERE id = ?", (tid,))
    conn.commit()
    audit_log("music-delete", f"id={tid}", client_ip(request), user=user["username"])
    return {"ok": True, "deleted": tid}


# ---------- 收藏与播放记录（v2.3 P5，require_admin） ----------

class FavoriteBody(BaseModel):
    favorite: bool


@router.get("/admin/music/favorites")
def list_favorites(user: dict = Depends(require_admin)):
    """收藏曲目列表（按收藏时间倒序）。"""
    rows = db.conn().execute(
        f"""SELECT t.id, t.title, t.artist, t.album, t.duration, t.created_at
            FROM music.track_favorites f JOIN music.tracks t ON t.id = f.track_id
            ORDER BY f.created_at DESC, f.track_id DESC""").fetchall()
    return [dict(r) for r in rows]


@router.put("/admin/music/{tid}/favorite")
def toggle_favorite(tid: int, body: FavoriteBody, request: Request,
                    user: dict = Depends(require_admin)):
    conn = db.conn()
    if not conn.execute("SELECT id FROM music.tracks WHERE id = ?", (tid,)).fetchone():
        raise HTTPException(status_code=404, detail="曲目不存在")
    if body.favorite:
        conn.execute("INSERT OR IGNORE INTO music.track_favorites (track_id) VALUES (?)", (tid,))
    else:
        conn.execute("DELETE FROM music.track_favorites WHERE track_id = ?", (tid,))
    conn.commit()
    audit_log("music-favorite", f"id={tid} favorite={body.favorite}",
              client_ip(request), user=user["username"])
    return {"ok": True, "id": tid, "favorite": body.favorite}


@router.post("/admin/music/{tid}/play")
def record_play(tid: int, request: Request, user: dict = Depends(require_admin)):
    """记录一次播放（播放历史）。"""
    conn = db.conn()
    if not conn.execute("SELECT id FROM music.tracks WHERE id = ?", (tid,)).fetchone():
        raise HTTPException(status_code=404, detail="曲目不存在")
    cur = conn.execute("INSERT INTO music.play_history (track_id) VALUES (?)", (tid,))
    conn.commit()
    return {"ok": True, "id": cur.lastrowid}


@router.get("/admin/music/history")
def play_history(limit: int = 10, user: dict = Depends(require_admin)):
    """最近播放（去重到曲目粒度，按最近一次播放时间倒序）。"""
    limit = max(1, min(limit, 50))
    rows = db.conn().execute(
        f"""SELECT t.id, t.title, t.artist, t.album, t.duration, MAX(h.played_at) AS last_played
            FROM music.play_history h JOIN music.tracks t ON t.id = h.track_id
            GROUP BY h.track_id ORDER BY last_played DESC LIMIT ?""", (limit,)).fetchall()
    return [dict(r) for r in rows]
