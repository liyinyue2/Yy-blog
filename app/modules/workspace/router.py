"""工作台模块：笔记 / 待办 / 书签（workspace.db），全部 admin 鉴权。"""
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from app.core.audit import audit_log
from app.core.database import db
from app.core.ratelimit import client_ip
from app.core.sanitize import sanitize_html
from app.core.security import require_admin

router = APIRouter(prefix="/api/workspace", tags=["workspace"])

TABLES = {"note": ("notes", ("title", "content")),
          "todo": ("todos", ("content",)),
          "bookmark": ("bookmarks", ("title", "url"))}


class NoteBody(BaseModel):
    title: str = Field(default="", max_length=200)
    content: str = Field(default="", max_length=100000)   # 富文本，入库前清洗


class TodoBody(BaseModel):
    content: str = Field(min_length=1, max_length=500)
    done: bool = False
    due: str = Field(default="", max_length=10)          # YYYY-MM-DD 或空
    priority: int = Field(default=0, ge=0, le=2)          # 0 普通 / 1 重要 / 2 紧急


class BookmarkBody(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    url: str = Field(min_length=1, max_length=2048)


def _validate_table(kind: str) -> str:
    if kind not in TABLES:
        raise HTTPException(status_code=404, detail="未知资源类型")
    return TABLES[kind][0]


def _check_url(url: str) -> str:
    from urllib.parse import urlparse
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise HTTPException(status_code=400, detail="书签 URL 仅支持 http/https")
    return url


def _validate_due(due: str) -> str:
    from datetime import datetime
    due = (due or "").strip()
    if not due:
        return ""
    try:
        datetime.strptime(due, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="due 需为 YYYY-MM-DD 格式或留空")
    return due


def _paginate(limit: int, offset: int) -> tuple[int, int]:
    limit = max(1, min(int(limit), 100))   # 上限 100
    offset = max(0, int(offset))
    return limit, offset


# ---------- 笔记 ----------
@router.get("/notes")
def list_notes(limit: int = 20, offset: int = 0, user: dict = Depends(require_admin)):
    limit, offset = _paginate(limit, offset)
    conn = db.conn()
    rows = [dict(r) for r in conn.execute(
        "SELECT id, title, content, created_at, updated_at FROM workspace.notes ORDER BY id DESC LIMIT ? OFFSET ?",
        (limit, offset))]
    total = conn.execute("SELECT COUNT(*) n FROM workspace.notes").fetchone()["n"]
    return {"items": rows, "total": total, "limit": limit, "offset": offset}


@router.post("/notes")
def create_note(body: NoteBody, request: Request, user: dict = Depends(require_admin)):
    conn = db.conn()
    now = _now()
    title = body.title.strip()[:200]
    content = sanitize_html(body.content)   # 富文本白名单清洗
    cur = conn.execute(
        "INSERT INTO workspace.notes (title, content, created_at, updated_at) VALUES (?,?,?,?)",
        (title, content, now, now))
    conn.commit()
    audit_log("note-create", f"id={cur.lastrowid}", client_ip(request), user=user["username"])
    return {"ok": True, "id": cur.lastrowid}


@router.put("/notes/{nid}")
def update_note(nid: int, body: NoteBody, request: Request, user: dict = Depends(require_admin)):
    conn = db.conn()
    cur = conn.execute(
        "UPDATE workspace.notes SET title=?, content=?, updated_at=? WHERE id=?",
        (body.title.strip()[:200], sanitize_html(body.content), _now(), nid))
    conn.commit()
    if cur.rowcount == 0:
        raise HTTPException(status_code=404, detail="笔记不存在")
    audit_log("note-update", f"id={nid}", client_ip(request), user=user["username"])
    return {"ok": True}


@router.delete("/notes/{nid}")
def delete_note(nid: int, request: Request, user: dict = Depends(require_admin)):
    conn = db.conn()
    cur = conn.execute("DELETE FROM workspace.notes WHERE id=?", (nid,))
    conn.commit()
    if cur.rowcount == 0:
        raise HTTPException(status_code=404, detail="笔记不存在")
    audit_log("note-delete", f"id={nid}", client_ip(request), user=user["username"])
    return {"ok": True, "deleted": nid}


# ---------- 待办 ----------
@router.get("/todos")
def list_todos(limit: int = 20, offset: int = 0, user: dict = Depends(require_admin)):
    limit, offset = _paginate(limit, offset)
    conn = db.conn()
    rows = [dict(r) for r in conn.execute(
        "SELECT id, content, done, due, priority, created_at FROM workspace.todos ORDER BY done ASC, priority DESC, id DESC LIMIT ? OFFSET ?",
        (limit, offset))]
    total = conn.execute("SELECT COUNT(*) n FROM workspace.todos").fetchone()["n"]
    return {"items": rows, "total": total, "limit": limit, "offset": offset}


@router.post("/todos")
def create_todo(body: TodoBody, request: Request, user: dict = Depends(require_admin)):
    conn = db.conn()
    due = _validate_due(body.due)
    cur = conn.execute(
        "INSERT INTO workspace.todos (content, done, due, priority, created_at) VALUES (?,?,?,?,?)",
        (body.content.strip()[:500], 1 if body.done else 0, due, body.priority, _now()))
    conn.commit()
    audit_log("todo-create", f"id={cur.lastrowid}", client_ip(request), user=user["username"])
    return {"ok": True, "id": cur.lastrowid}


@router.put("/todos/{tid}")
def toggle_todo(tid: int, body: TodoBody, request: Request, user: dict = Depends(require_admin)):
    conn = db.conn()
    due = _validate_due(body.due)
    cur = conn.execute("UPDATE workspace.todos SET content=?, done=?, due=?, priority=? WHERE id=?",
                       (body.content.strip()[:500], 1 if body.done else 0, due, body.priority, tid))
    conn.commit()
    if cur.rowcount == 0:
        raise HTTPException(status_code=404, detail="待办不存在")
    audit_log("todo-update", f"id={tid}", client_ip(request), user=user["username"])
    return {"ok": True}


@router.delete("/todos/{tid}")
def delete_todo(tid: int, request: Request, user: dict = Depends(require_admin)):
    conn = db.conn()
    cur = conn.execute("DELETE FROM workspace.todos WHERE id=?", (tid,))
    conn.commit()
    if cur.rowcount == 0:
        raise HTTPException(status_code=404, detail="待办不存在")
    audit_log("todo-delete", f"id={tid}", client_ip(request), user=user["username"])
    return {"ok": True, "deleted": tid}


# ---------- 书签 ----------
@router.get("/bookmarks")
def list_bookmarks(limit: int = 20, offset: int = 0, user: dict = Depends(require_admin)):
    limit, offset = _paginate(limit, offset)
    conn = db.conn()
    rows = [dict(r) for r in conn.execute(
        "SELECT id, title, url, created_at FROM workspace.bookmarks ORDER BY id DESC LIMIT ? OFFSET ?",
        (limit, offset))]
    total = conn.execute("SELECT COUNT(*) n FROM workspace.bookmarks").fetchone()["n"]
    return {"items": rows, "total": total, "limit": limit, "offset": offset}


@router.post("/bookmarks")
def create_bookmark(body: BookmarkBody, request: Request, user: dict = Depends(require_admin)):
    conn = db.conn()
    cur = conn.execute(
        "INSERT INTO workspace.bookmarks (title, url, created_at) VALUES (?,?,?)",
        (body.title.strip()[:200], _check_url(body.url.strip()), _now()))
    conn.commit()
    audit_log("bookmark-create", f"id={cur.lastrowid}", client_ip(request), user=user["username"])
    return {"ok": True, "id": cur.lastrowid}


@router.delete("/bookmarks/{bid}")
def delete_bookmark(bid: int, request: Request, user: dict = Depends(require_admin)):
    conn = db.conn()
    cur = conn.execute("DELETE FROM workspace.bookmarks WHERE id=?", (bid,))
    conn.commit()
    if cur.rowcount == 0:
        raise HTTPException(status_code=404, detail="书签不存在")
    audit_log("bookmark-delete", f"id={bid}", client_ip(request), user=user["username"])
    return {"ok": True, "deleted": bid}


def _now() -> str:
    from datetime import datetime
    return datetime.now().isoformat(timespec="seconds")
