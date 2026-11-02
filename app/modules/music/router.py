"""音乐模块：曲目元数据 + 流式上传 + HTTP Range 流媒体（music.db）。

关于 safeuploads：文档指定的 `safeuploads` 库在 PyPI 不存在（2026-11 检索确认），
按文档"安全硬约束"条款以同等强度的内置校验实现：扩展名白名单 + MIME 签名校验 + 拒绝用户原始文件名。
"""
import re
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile
from fastapi.responses import StreamingResponse
from mutagen import File as MutagenFile

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


@router.get("/music/tracks")
def list_tracks(q: str = "", artist: str = "", tag: str = "", limit: int = 50, offset: int = 0):
    """曲目列表/搜索（公开只读）；tag 走统一标签体系。"""
    conn = db.conn()
    limit = max(1, min(limit, 100))
    sql = "SELECT id, title, artist, album, duration, cover_path, created_at FROM music.tracks WHERE 1=1"
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


@router.get("/music/stream/{tid}")
def stream_track(tid: int, request: Request):
    """HTTP Range 流媒体：按分块响应，禁止一次性读全文件。"""
    conn = db.conn()
    row = conn.execute("SELECT file_path, title FROM music.tracks WHERE id = ?", (tid,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="曲目不存在")
    file_path = Path(row["file_path"])
    # 路径穿越防护：解析后必须仍位于 uploads/music 内
    try:
        resolved = file_path.resolve()
        resolved.relative_to((settings.UPLOAD_DIR / "music").resolve())
    except (ValueError, OSError):
        raise HTTPException(status_code=400, detail="非法文件路径")
    if not resolved.exists():
        raise HTTPException(status_code=404, detail="音频文件缺失")

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


@router.post("/admin/music/upload")
async def upload_track(request: Request, file: UploadFile,
                       user: dict = Depends(require_admin)):
    """流式上传音频：扩展名白名单 + MIME 签名校验 + UUID 落盘（禁用原始文件名）。"""
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
            "INSERT INTO music.tracks (title, duration, file_path, created_at) VALUES (?,?,?,datetime('now','localtime'))",
            (title, duration, str(dest)))
        conn.commit()
    except Exception:
        conn.rollback()
        dest.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail="保存曲目失败，请稍后再试")
    audit_log("music-upload", f"{uuid_name} ({size}B, {duration}s)", ip, user=user["username"])
    return {"ok": True, "id": cur.lastrowid, "title": title, "duration": duration, "size": size}


@router.delete("/admin/music/tracks/{tid}")
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
    conn.execute("DELETE FROM music.tracks WHERE id = ?", (tid,))
    conn.commit()
    audit_log("music-delete", f"id={tid}", client_ip(request), user=user["username"])
    return {"ok": True, "deleted": tid}
