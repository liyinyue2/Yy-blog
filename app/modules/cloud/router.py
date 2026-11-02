"""网盘模块：文件上传/下载/管理（最高风险面，全部走强校验）。

关于 safeuploads：文档指定的 `safeuploads` 库在 PyPI 不存在（2026-11 检索确认），
按文档"安全硬约束"以同等强度内置实现：文件名净化 + 扩展名白名单 + ZIP 炸弹检测
+ MIME 签名校验 + 流式落盘（UUID 命名）+ 路径穿越防护 + 下载强制鉴权。
"""
import uuid
import zipfile
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse

from app.core.audit import audit_log
from app.core.config import settings
from app.core.database import db
from app.core.ratelimit import client_ip
from app.core.security import require_admin

router = APIRouter(prefix="/api", tags=["cloud"])

MAX_FILE_SIZE = 20 * 1024 * 1024          # 20MB（与 Nginx client_max_body_size 对齐）
MAX_ZIP_UNCOMPRESSED = 256 * 1024 * 1024  # ZIP 解压后总量上限（炸弹检测）

# 扩展名白名单 → (允许的文件头魔数, 校验偏移)；None 表示不做签名校验（纯文本类）
EXT_WHITELIST = {
    "pdf": [(b"%PDF", 0)],
    "docx": [(b"PK", 0)],
    "doc": [(b"\xd0\xcf\x11\xe0", 0)],
    "xlsx": [(b"PK", 0)],
    "pptx": [(b"PK", 0)],
    "txt": None,
    "md": None,
    "png": [(b"\x89PNG", 0)],
    "jpg": [(b"\xff\xd8\xff", 0)],
    "jpeg": [(b"\xff\xd8\xff", 0)],
    "webp": [(b"RIFF", 0)],
    "gif": [(b"GIF8", 0)],
    "zip": [(b"PK", 0)],
}

MIME_BY_EXT = {
    "pdf": "application/pdf", "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "doc": "application/msword", "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "txt": "text/plain", "md": "text/markdown", "png": "image/png", "jpg": "image/jpeg",
    "jpeg": "image/jpeg", "webp": "image/webp", "gif": "image/gif", "zip": "application/zip",
}


def _sanitize_name(name: str) -> str:
    """文件名净化：含路径成分/穿越模式直接拒绝；去危险字符，保留可读名。"""
    name = name.replace("\\", "/")
    if "/" in name or ".." in name:      # 任何路径成分（含 ../ 穿越）一律 400
        raise HTTPException(status_code=400, detail="文件名不得包含路径分隔符或 ..")
    name = name.replace("\x00", "").strip()
    if not name or name == ".":
        raise HTTPException(status_code=400, detail="非法文件名")
    if any(c in name for c in "<>:\"|?*"):
        raise HTTPException(status_code=400, detail="文件名包含非法字符")
    return name[:200]


def _check_signature(ext: str, head: bytes) -> None:
    rules = EXT_WHITELIST.get(ext)
    if not rules:
        return
    for sig, offset in rules:
        if head[offset:offset + len(sig)] == sig:
            return
    raise HTTPException(status_code=400, detail="文件内容与扩展名不符（MIME 签名校验失败）")


@router.post("/admin/cloud/upload")
async def cloud_upload(request: Request, file: UploadFile, user: dict = Depends(require_admin)):
    ip = client_ip(request)
    original = _sanitize_name(file.filename or "")
    ext = original.lower().rsplit(".", 1)[-1] if "." in original else ""
    if ext not in EXT_WHITELIST:
        raise HTTPException(status_code=400, detail=f"不支持的文件类型，仅允许：{'/'.join(EXT_WHITELIST)}")

    dest_dir = settings.UPLOAD_DIR / "cloud"
    dest_dir.mkdir(parents=True, exist_ok=True)
    uuid_name = uuid.uuid4().hex          # 无扩展名落盘，防止被当脚本执行
    dest = dest_dir / uuid_name

    size = 0
    head = b""
    try:
        with open(dest, "wb") as out:
            while chunk := await file.read(512 * 1024):
                size += len(chunk)
                if size > MAX_FILE_SIZE:
                    raise HTTPException(status_code=400, detail="文件超过 20MB 限制")
                if len(head) < 1024 * 1024:
                    head += chunk
                out.write(chunk)
    except HTTPException:
        dest.unlink(missing_ok=True)
        raise
    except OSError:
        dest.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail="服务器写入失败")

    try:
        _check_signature(ext, head[:16])
        # ZIP 中央目录在文件尾，必须用完整落盘文件预检，不能只看文件头
        if ext in ("zip", "docx", "xlsx", "pptx"):
            try:
                with zipfile.ZipFile(dest) as zf:
                    total = sum(info.file_size for info in zf.infolist())
                    if total > MAX_ZIP_UNCOMPRESSED:
                        raise HTTPException(
                            status_code=400,
                            detail=f"压缩包解压后过大（{total // 1048576}MB），疑似炸弹构造",
                        )
            except zipfile.BadZipFile:
                raise HTTPException(status_code=400, detail="压缩包损坏或不是合法 ZIP")
    except Exception:
        dest.unlink(missing_ok=True)
        raise

    conn = db.conn()
    cur = conn.execute(
        "INSERT INTO files (uuid_name, original_name, size, mime, uploader_id, created_at) "
        "VALUES (?,?,?,?,?,datetime('now','localtime'))",
        (uuid_name, original, size, MIME_BY_EXT[ext], user["id"]))
    conn.commit()
    audit_log("cloud-upload", f"{original} ({size}B)", ip, user=user["username"])
    return {"ok": True, "id": cur.lastrowid, "name": original, "size": size}


@router.get("/cloud/files")
def list_files(limit: int = 50, offset: int = 0, user: dict = Depends(require_admin)):
    limit = max(1, min(limit, 100))
    rows = [dict(r) for r in db.conn().execute(
        "SELECT id, original_name, size, mime, created_at FROM files ORDER BY id DESC LIMIT ? OFFSET ?",
        (limit, max(0, offset)))]
    return rows


@router.get("/cloud/download/{fid}")
def cloud_download(fid: int, user: dict = Depends(require_admin)):
    """下载必须鉴权；FileResponse 流式返回，强制 attachment。"""
    conn = db.conn()
    row = conn.execute("SELECT uuid_name, original_name, mime FROM files WHERE id = ?", (fid,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="文件不存在")
    dest = (settings.UPLOAD_DIR / "cloud" / row["uuid_name"]).resolve()
    # 路径穿越防护：解析后必须仍位于 uploads/cloud 内
    if not dest.is_relative_to((settings.UPLOAD_DIR / "cloud").resolve()):
        raise HTTPException(status_code=400, detail="非法文件路径")
    if not dest.exists():
        raise HTTPException(status_code=404, detail="文件已丢失")
    # Content-Disposition：ASCII 回退名 + RFC 5987 UTF-8 编码名（中文文件名兼容）
    from urllib.parse import quote
    raw_name = row["original_name"].replace('"', "")
    ascii_fallback = raw_name.encode("ascii", "ignore").decode() or "download"
    encoded_name = quote(raw_name)
    return FileResponse(
        dest,
        media_type=row["mime"] or "application/octet-stream",
        headers={"Content-Disposition":
                 f'attachment; filename="{ascii_fallback}"; filename*=UTF-8\'\'{encoded_name}',
                 "Cache-Control": "no-store"},
    )


@router.delete("/admin/cloud/files/{fid}")
def cloud_delete(fid: int, request: Request, user: dict = Depends(require_admin)):
    conn = db.conn()
    row = conn.execute("SELECT uuid_name, original_name FROM files WHERE id = ?", (fid,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="文件不存在")
    dest = (settings.UPLOAD_DIR / "cloud" / row["uuid_name"]).resolve()
    if dest.is_relative_to((settings.UPLOAD_DIR / "cloud").resolve()):
        dest.unlink(missing_ok=True)
    conn.execute("DELETE FROM taggables WHERE entity_type='file' AND entity_id=?", (fid,))
    conn.execute("DELETE FROM files WHERE id = ?", (fid,))
    conn.commit()
    audit_log("cloud-delete", row["original_name"], client_ip(request), user=user["username"])
    return {"ok": True, "deleted": row["original_name"]}
