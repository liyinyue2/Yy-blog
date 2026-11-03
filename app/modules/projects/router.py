"""项目中心：公开项目展示 + 后台管理（projects / project_logs，主库 blog.db）。

接口分组：
- /api/public/projects/*   匿名只读，仅 visibility='public'
- /api/admin/projects/*    require_admin，含 CRUD 与开发日志
- /projects/{slug}.html    动态渲染项目详情页（沿用文章 post 模式）
"""
import json
import re
import unicodedata
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse

from app.core.audit import audit_log
from app.core.database import db
from app.core.ratelimit import client_ip
from app.core.sanitize import sanitize_html
from app.core.security import require_admin
from app.modules.blog.templates import NAV_HTML
from app.modules.projects.models import ProjectBody, ProjectLogBody

router = APIRouter(tags=["projects"])

SLUG_RE = re.compile(r"^[\w][\w-]{0,63}$", re.UNICODE)
STATUSES = ("idea", "building", "maintained", "archived")

_PROJECT_COLS = ("id, slug, name, summary, tech_stack, status, repo_url, demo_url,"
                 " progress, sort, visibility, created_at, updated_at")


def _slugify(name: str, fallback_prefix: str = "project") -> str:
    """从名称生成 URL slug；中文等非 ASCII 字符按 URL 安全方式编码缩写。"""
    text = unicodedata.normalize("NFKC", name).strip().lower()
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"[^\w-]", "", text, flags=re.UNICODE).strip("-")
    return (text[:64] or fallback_prefix) if text else fallback_prefix


def _resolve_slug(body: ProjectBody, conn, current_id: int | None) -> str:
    slug = (body.slug or _slugify(body.name)).strip()
    if not SLUG_RE.fullmatch(slug):
        raise HTTPException(status_code=400,
                            detail="slug 只能包含字母、数字、下划线和中划线（1-64 位，字母开头）")
    row = conn.execute("SELECT id FROM projects WHERE slug = ?", (slug,)).fetchone()
    if row and row["id"] != current_id:
        raise HTTPException(status_code=400, detail=f"slug 已被占用：{slug}")
    return slug


def _check_url(url: str, label: str) -> str:
    url = (url or "").strip()
    if url and not url.lower().startswith(("http://", "https://")):
        raise HTTPException(status_code=400, detail=f"{label} 必须以 http(s):// 开头")
    return url


def _clean_tech(items: list[str]) -> str:
    cleaned = [t.strip()[:32] for t in items if t and t.strip()]
    return json.dumps(cleaned[:12], ensure_ascii=False)


def _row_out(row) -> dict:
    out = dict(row)
    try:
        out["tech_stack"] = json.loads(out.get("tech_stack") or "[]")
    except (TypeError, ValueError):
        out["tech_stack"] = []
    return out


def _get_project(pid: int):
    row = db.conn().execute("SELECT * FROM projects WHERE id = ?", (pid,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="项目不存在")
    return row


# ---------- 公开只读 ----------

@router.get("/api/public/projects")
def public_projects(status: str = "", q: str = ""):
    if status and status not in STATUSES:
        raise HTTPException(status_code=400, detail="status 取值不合法")
    conn = db.conn()
    sql = f"SELECT {_PROJECT_COLS} FROM projects WHERE visibility = 'public'"
    params: list = []
    if status:
        sql += " AND status = ?"
        params.append(status)
    if q:
        sql += " AND (name LIKE ? OR summary LIKE ?)"
        params += [f"%{q}%", f"%{q}%"]
    sql += " ORDER BY sort ASC, id DESC"
    return [_row_out(r) for r in conn.execute(sql, params)]


@router.get("/api/public/projects/{slug}")
def public_project_detail(slug: str):
    conn = db.conn()
    row = conn.execute(
        f"SELECT {_PROJECT_COLS}, description FROM projects WHERE slug = ? AND visibility = 'public'",
        (slug,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="项目不存在或未公开")
    logs = [dict(r) for r in conn.execute(
        "SELECT id, title, content, log_date FROM project_logs WHERE project_id = ?"
        " ORDER BY log_date DESC, id DESC", (row["id"],))]
    out = _row_out(row)
    out["logs"] = logs
    return out


# ---------- 管理接口 ----------

@router.get("/api/admin/projects")
def admin_projects(user: dict = Depends(require_admin)):
    rows = db.conn().execute(
        f"SELECT {_PROJECT_COLS} FROM projects ORDER BY sort ASC, id DESC").fetchall()
    return [_row_out(r) for r in rows]


@router.post("/api/admin/projects")
def admin_create_project(body: ProjectBody, request: Request,
                         user: dict = Depends(require_admin)):
    conn = db.conn()
    slug = _resolve_slug(body, conn, None)
    cur = conn.execute(
        """INSERT INTO projects
           (slug, name, summary, description, tech_stack, status, repo_url, demo_url,
            progress, sort, visibility, updated_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,datetime('now','localtime'))""",
        (slug, body.name.strip()[:120], body.summary.strip()[:500],
         sanitize_html(body.description), _clean_tech(body.tech_stack), body.status,
         _check_url(body.repo_url, "仓库链接"), _check_url(body.demo_url, "演示链接"),
         body.progress, body.sort, body.visibility))
    conn.commit()
    audit_log("project-create", f"{slug} (id={cur.lastrowid})",
              client_ip(request), user=user["username"])
    return {"ok": True, "id": cur.lastrowid, "slug": slug}


@router.put("/api/admin/projects/{pid}")
def admin_update_project(pid: int, body: ProjectBody, request: Request,
                         user: dict = Depends(require_admin)):
    _get_project(pid)
    conn = db.conn()
    slug = _resolve_slug(body, conn, pid)
    conn.execute(
        """UPDATE projects SET slug=?, name=?, summary=?, description=?, tech_stack=?,
           status=?, repo_url=?, demo_url=?, progress=?, sort=?, visibility=?,
           updated_at=datetime('now','localtime') WHERE id=?""",
        (slug, body.name.strip()[:120], body.summary.strip()[:500],
         sanitize_html(body.description), _clean_tech(body.tech_stack), body.status,
         _check_url(body.repo_url, "仓库链接"), _check_url(body.demo_url, "演示链接"),
         body.progress, body.sort, body.visibility, pid))
    conn.commit()
    audit_log("project-update", f"{slug} (id={pid})",
              client_ip(request), user=user["username"])
    return {"ok": True, "id": pid, "slug": slug}


@router.delete("/api/admin/projects/{pid}")
def admin_delete_project(pid: int, request: Request, user: dict = Depends(require_admin)):
    row = _get_project(pid)
    conn = db.conn()
    conn.execute("DELETE FROM projects WHERE id = ?", (pid,))  # 日志随 ON DELETE CASCADE
    conn.commit()
    audit_log("project-delete", f"{row['slug']} (id={pid})",
              client_ip(request), user=user["username"])
    return {"ok": True, "deleted": pid}


@router.get("/api/admin/projects/{pid}/logs")
def admin_project_logs(pid: int, user: dict = Depends(require_admin)):
    _get_project(pid)
    rows = db.conn().execute(
        "SELECT id, title, content, log_date, created_at FROM project_logs"
        " WHERE project_id = ? ORDER BY log_date DESC, id DESC", (pid,)).fetchall()
    return [dict(r) for r in rows]


@router.post("/api/admin/projects/{pid}/logs")
def admin_create_project_log(pid: int, body: ProjectLogBody, request: Request,
                             user: dict = Depends(require_admin)):
    _get_project(pid)
    conn = db.conn()
    cur = conn.execute(
        "INSERT INTO project_logs (project_id, title, content, log_date) VALUES (?,?,?,?)",
        (pid, body.title.strip()[:200], sanitize_html(body.content), body.log_date))
    conn.execute("UPDATE projects SET updated_at=datetime('now','localtime') WHERE id=?", (pid,))
    conn.commit()
    audit_log("project-log-create", f"project={pid} log={cur.lastrowid}",
              client_ip(request), user=user["username"])
    return {"ok": True, "id": cur.lastrowid}


@router.delete("/api/admin/projects/{pid}/logs/{log_id}")
def admin_delete_project_log(pid: int, log_id: int, request: Request,
                             user: dict = Depends(require_admin)):
    conn = db.conn()
    cur = conn.execute("DELETE FROM project_logs WHERE id = ? AND project_id = ?",
                       (log_id, pid))
    conn.commit()
    if cur.rowcount == 0:
        raise HTTPException(status_code=404, detail="日志不存在")
    audit_log("project-log-delete", f"project={pid} log={log_id}",
              client_ip(request), user=user["username"])
    return {"ok": True, "deleted": log_id}


# ---------- 项目详情页（动态渲染） ----------

STATUS_LABELS = {"idea": "构想中", "building": "开发中",
                 "maintained": "维护中", "archived": "已归档"}

PROJECT_TEMPLATE = """<!doctype html><html lang="zh-CN"><head><meta charset="UTF-8" /><meta name="viewport" content="width=device-width, initial-scale=1.0" /><meta name="theme-color" content="#ffffff" /><link rel="icon" type="image/svg+xml" href="/y-mark.svg" /><meta name="description" content="{summary}" /><link rel="preconnect" href="https://fonts.googleapis.com" /><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin /><link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap" rel="stylesheet" /><link rel="stylesheet" href="/site.css" /><title>{name} — 项目 — Y's Blog</title></head><body class="page-body">{nav}<main class="post-shell reveal"><a class="post-back" href="/projects.html">← 返回项目列表</a><div class="post-meta"><span class="project-status-badge" data-status="{status}">{status_label}</span><time>{dates}</time></div><h1 class="post-title">{name}</h1><p class="post-lead">{summary}</p><div class="project-progress-wrap"><div class="project-progress"><div class="project-progress-bar" style="width:{progress}%"></div></div><span class="project-progress-num">{progress}%</span></div>{tech_html}<div class="project-links">{links_html}</div><div class="post-body">{description}</div><div class="project-logs">{logs_html}</div></main><footer class="page-footer"><div class="page-footer-inner"><span><span data-setting="site_name">Y's Blog</span> · 记录思考，分享创造。</span><a href="/articles.html">更多文章 →</a></div></footer><div class="toast" id="toast" aria-live="polite"></div><script src="/site.js"></script><script src="/liquid-glass.js"></script></body></html>"""


def _esc(text: str) -> str:
    import html as html_mod
    return html_mod.escape(text or "", quote=True)


def render_project_page(slug: str) -> str:
    conn = db.conn()
    row = conn.execute(
        "SELECT * FROM projects WHERE slug = ? AND visibility = 'public'", (slug,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="not found")
    logs = conn.execute(
        "SELECT title, content, log_date FROM project_logs WHERE project_id = ?"
        " ORDER BY log_date DESC, id DESC", (row["id"],)).fetchall()

    try:
        tech = json.loads(row["tech_stack"] or "[]")
    except (TypeError, ValueError):
        tech = []
    tech_html = ""
    if tech:
        chips = "".join(f'<span class="project-tech-chip">{_esc(t)}</span>' for t in tech)
        tech_html = f'<div class="project-tech">{chips}</div>'

    links = []
    if row["repo_url"]:
        links.append(f'<a class="read-link" href="{_esc(row["repo_url"])}" target="_blank" rel="noopener">源码仓库 ↗</a>')
    if row["demo_url"]:
        links.append(f'<a class="read-link" href="{_esc(row["demo_url"])}" target="_blank" rel="noopener">在线演示 ↗</a>')
    links_html = f'<div>{"".join(links)}</div>' if links else ""

    logs_html = ""
    if logs:
        items = "".join(
            f'<div class="project-log-item"><div class="project-log-head"><b>{_esc(l["title"] or "开发记录")}</b>'
            f'<time>{_esc(l["log_date"])}</time></div><div class="project-log-body">{l["content"]}</div></div>'
            for l in logs)
        logs_html = f'<h2 class="project-logs-title">开发日志</h2>{items}'

    dates = row["created_at"] or ""
    if row["updated_at"] and row["updated_at"] != dates:
        dates += f" · 更新于 {row['updated_at'][:10]}"

    return PROJECT_TEMPLATE.format(
        nav=NAV_HTML,
        name=_esc(row["name"]), summary=_esc(row["summary"]),
        status=_esc(row["status"]), status_label=STATUS_LABELS.get(row["status"], row["status"]),
        dates=_esc(dates), progress=row["progress"],
        tech_html=tech_html, links_html=links_html,
        description=row["description"] or "<p>暂无详细介绍。</p>",
        logs_html=logs_html,
    )


@router.get("/projects/{page_path:path}", include_in_schema=False)
def project_page(page_path: str):
    m = re.fullmatch(r"([\w-]+)\.html", page_path)
    if not m:
        raise HTTPException(status_code=404)
    return HTMLResponse(render_project_page(m.group(1)))
