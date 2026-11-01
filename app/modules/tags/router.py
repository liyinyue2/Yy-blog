"""统一标签模块：横切 blog/note/file/track 四类实体。"""
from fastapi import APIRouter, Body, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from app.core.audit import audit_log
from app.core.database import db
from app.core.ratelimit import client_ip
from app.core.security import require_admin

router = APIRouter(prefix="/api", tags=["tags"])

# 实体类型白名单
ENTITY_TYPES = {"article", "note", "file", "track"}

# 标签名白名单正则：禁止 <>&"' 等字符；1-32 个可见字符
import re

TAG_NAME_RE = re.compile(r"^[^<>&\"'\\]{1,32}$", re.UNICODE)


class TagAssignBody(BaseModel):
    name: str = Field(min_length=1, max_length=32)
    entity_type: str = Field(min_length=1, max_length=16)
    entity_id: int = Field(ge=1)


class TagCreateBody(BaseModel):
    name: str = Field(min_length=1, max_length=32)


def _validate_name(name: str) -> str:
    name = name.strip()
    if not name or not TAG_NAME_RE.match(name):
        raise HTTPException(status_code=400, detail="标签名不合法：1-32 字符，且不得包含 < > & \" ' \\")
    return name


def _validate_entity_type(entity_type: str) -> str:
    if entity_type not in ENTITY_TYPES:
        raise HTTPException(status_code=400, detail=f"entity_type 只能是：{'/'.join(sorted(ENTITY_TYPES))}")
    return entity_type


@router.get("/tags")
def list_tags(entity_type: str = ""):
    """全部标签；可选按实体类型过滤并附计数。"""
    conn = db.conn()
    if entity_type:
        _validate_entity_type(entity_type)
        rows = conn.execute(
            """SELECT t.id, t.name,
                      (SELECT COUNT(*) FROM taggables g WHERE g.tag_id = t.id AND g.entity_type = ?) AS count
               FROM tags t
               WHERE (SELECT COUNT(*) FROM taggables g WHERE g.tag_id = t.id AND g.entity_type = ?) > 0
               ORDER BY count DESC, t.name""",
            (entity_type, entity_type)).fetchall()
        return [dict(r) for r in rows]
    rows = conn.execute(
        """SELECT t.id, t.name,
                  (SELECT COUNT(*) FROM taggables g WHERE g.tag_id = t.id) AS count
           FROM tags t ORDER BY count DESC, t.name""").fetchall()
    return [dict(r) for r in rows]


@router.get("/tags/{name}/{entity_type}")
def entities_by_tag(name: str, entity_type: str):
    """按标签名 + 实体类型取关联实体 id 列表。"""
    _validate_entity_type(entity_type)
    conn = db.conn()
    row = conn.execute("SELECT id FROM tags WHERE name = ?", (name,)).fetchone()
    if not row:
        return []
    ids = [r["entity_id"] for r in conn.execute(
        "SELECT entity_id FROM taggables WHERE tag_id = ? AND entity_type = ? ORDER BY entity_id DESC",
        (row["id"], entity_type))]
    return ids


@router.post("/admin/tags")
def create_tag(body: TagCreateBody, request: Request, user: dict = Depends(require_admin)):
    name = _validate_name(body.name)
    conn = db.conn()
    if conn.execute("SELECT id FROM tags WHERE name = ?", (name,)).fetchone():
        raise HTTPException(status_code=400, detail=f"标签已存在：{name}")
    cur = conn.execute("INSERT INTO tags (name) VALUES (?)", (name,))
    conn.commit()
    audit_log("tag-create", name, client_ip(request), user=user["username"])
    return {"ok": True, "id": cur.lastrowid, "name": name}


@router.post("/admin/tags/assign")
def assign_tag(body: TagAssignBody, request: Request, user: dict = Depends(require_admin)):
    """给实体打标签：标签不存在则自动创建。"""
    name = _validate_name(body.name)
    _validate_entity_type(body.entity_type)
    conn = db.conn()
    row = conn.execute("SELECT id FROM tags WHERE name = ?", (name,)).fetchone()
    tag_id = row["id"] if row else conn.execute("INSERT INTO tags (name) VALUES (?)", (name,)).lastrowid
    conn.execute("INSERT OR IGNORE INTO taggables (tag_id, entity_type, entity_id) VALUES (?,?,?)",
                 (tag_id, body.entity_type, body.entity_id))
    conn.commit()
    audit_log("tag-assign", f"{body.entity_type}#{body.entity_id} <- {name}",
              client_ip(request), user=user["username"])
    return {"ok": True, "tag": name, "entity_type": body.entity_type, "entity_id": body.entity_id}


@router.delete("/admin/tags/{tag_id}")
def delete_tag(tag_id: int, request: Request, user: dict = Depends(require_admin)):
    conn = db.conn()
    row = conn.execute("SELECT name FROM tags WHERE id = ?", (tag_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="标签不存在")
    conn.execute("DELETE FROM taggables WHERE tag_id = ?", (tag_id,))
    conn.execute("DELETE FROM tags WHERE id = ?", (tag_id,))
    conn.commit()
    audit_log("tag-delete", row["name"], client_ip(request), user=user["username"])
    return {"ok": True, "deleted": row["name"]}
