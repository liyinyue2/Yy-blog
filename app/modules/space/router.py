"""个人空间模块：全局聚合搜索 / 番茄钟记录 / 网络信息（全部 require_admin）。

聚合搜索只查标题/摘要类短字段（LIKE），返回分类分组的轻量结果；
番茄钟仅落库记录（前端 localStorage 保活，完成后上报）。
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from app.core.audit import audit_log
from app.core.database import db
from app.core.ratelimit import client_ip
from app.core.security import require_admin

router = APIRouter(prefix="/api/space", tags=["space"])


class PomodoroBody(BaseModel):
    label: str = Field(default="", max_length=120)
    minutes: int = Field(default=25, ge=1, le=180)
    completed: bool = True


@router.get("/search")
def space_search(q: str = "", user: dict = Depends(require_admin)):
    q = (q or "").strip()[:80]
    if not q:
        return {"q": "", "groups": []}
    like = f"%{q}%"
    conn = db.conn()
    groups: list[dict] = []

    articles = conn.execute(
        "SELECT slug, title, summary, kind FROM articles"
        " WHERE title LIKE ? OR summary LIKE ? ORDER BY published_at DESC LIMIT 6",
        (like, like)).fetchall()
    if articles:
        groups.append({"type": "article", "label": "文章 / 笔记",
                       "items": [{"title": r["title"], "kind": r["kind"],
                                  "url": f"/post-{r['slug']}.html"} for r in articles]})

    notes = conn.execute(
        "SELECT id, title, substr(content, 1, 80) AS excerpt, updated_at FROM workspace.notes"
        " WHERE title LIKE ? OR content LIKE ? ORDER BY updated_at DESC LIMIT 6",
        (like, like)).fetchall()
    if notes:
        groups.append({"type": "note", "label": "私人笔记",
                       "items": [{"id": r["id"], "title": r["title"] or "(无标题)",
                                  "excerpt": r["excerpt"]} for r in notes]})

    projects = conn.execute(
        "SELECT slug, name, summary, status FROM projects"
        " WHERE name LIKE ? OR summary LIKE ? ORDER BY sort ASC LIMIT 6",
        (like, like)).fetchall()
    if projects:
        groups.append({"type": "project", "label": "项目",
                       "items": [{"name": r["name"], "status": r["status"],
                                  "url": f"/projects/{r['slug']}.html"} for r in projects]})

    files = conn.execute(
        "SELECT id, original_name, size, created_at FROM files"
        " WHERE original_name LIKE ? ORDER BY id DESC LIMIT 6",
        (like,)).fetchall()
    if files:
        groups.append({"type": "file", "label": "网盘文件",
                       "items": [{"id": r["id"], "name": r["original_name"],
                                  "size": r["size"]} for r in files]})

    tracks = conn.execute(
        "SELECT id, title, artist FROM music.tracks"
        " WHERE title LIKE ? OR artist LIKE ? ORDER BY id DESC LIMIT 6",
        (like, like)).fetchall()
    if tracks:
        groups.append({"type": "track", "label": "音乐",
                       "items": [{"id": r["id"], "title": r["title"],
                                  "artist": r["artist"]} for r in tracks]})

    todos = conn.execute(
        "SELECT id, content, done, due FROM workspace.todos"
        " WHERE content LIKE ? ORDER BY id DESC LIMIT 6",
        (like,)).fetchall()
    if todos:
        groups.append({"type": "todo", "label": "待办",
                       "items": [{"id": r["id"], "content": r["content"],
                                  "done": bool(r["done"])} for r in todos]})

    return {"q": q, "groups": groups}


@router.get("/pomodoro")
def list_pomodoro(limit: int = 20, offset: int = 0, user: dict = Depends(require_admin)):
    limit = max(1, min(limit, 100))
    conn = db.conn()
    rows = [dict(r) for r in conn.execute(
        "SELECT id, label, minutes, completed, started_at FROM pomodoro_sessions"
        " ORDER BY id DESC LIMIT ? OFFSET ?", (limit, max(0, offset)))]
    total = conn.execute("SELECT COUNT(*) n FROM pomodoro_sessions").fetchone()["n"]
    today = conn.execute(
        "SELECT COUNT(*) n FROM pomodoro_sessions WHERE completed=1 AND started_at LIKE ?",
        (db.conn().execute("SELECT date('now','localtime') d").fetchone()["d"] + "%",)).fetchone()["n"]
    return {"items": rows, "total": total, "today": today}


@router.post("/pomodoro")
def create_pomodoro(body: PomodoroBody, request: Request, user: dict = Depends(require_admin)):
    conn = db.conn()
    from datetime import datetime
    cur = conn.execute(
        "INSERT INTO pomodoro_sessions (label, minutes, completed, started_at) VALUES (?,?,?,?)",
        (body.label.strip()[:120], body.minutes, 1 if body.completed else 0,
         datetime.now().isoformat(timespec="seconds")))
    conn.commit()
    audit_log("pomodoro-create", f"min={body.minutes} completed={body.completed}",
              client_ip(request), user=user["username"])
    return {"ok": True, "id": cur.lastrowid}


@router.get("/netinfo")
def net_info(request: Request, user: dict = Depends(require_admin)):
    """本机连接信息：出口 IP / UA / 请求头快照（网络工具用，无外部请求，规避 SSRF）。"""
    from app.core.ratelimit import client_ip
    from datetime import datetime
    headers = {k.lower(): v for k, v in request.headers.items()
               if k.lower() in ("user-agent", "accept-language", "host")}
    return {"ip": client_ip(request), "time": datetime.now().isoformat(timespec="seconds"),
            "headers": headers}
