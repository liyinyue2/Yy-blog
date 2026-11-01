"""博客业务逻辑：SQL 全参数化，字段截断与校验规则与 v1.0 一致。"""
import re
from datetime import datetime

from fastapi import HTTPException

from app.core.audit import audit_log
from app.core.database import db
from app.core.sanitize import sanitize_html
from app.modules.blog.templates import SLUG_RE, fmt_date

EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")

# 站点设置默认值（与 v1.0 一致）
DEFAULT_SETTINGS = {
    "site_name": "Y's Blog",
    "hero_muted": "记录思考，",
    "hero_main": "分享创造。",
    "hero_subline": "这是一个关于前端开发、UI设计与个人成长的自留地。",
    "about_intro": "一个在代码与设计之间来回探索的人的长期记录。",
    "about_content": ("<p>我是一名在代码与设计之间来回探索的人。这个博客没有标准答案，只有持续记录的过程："
                      "做过什么、为什么这样做，以及下一次会如何做得更好。</p>"
                      "<p>我相信好的作品来自持续观察，也来自愿意把模糊的直觉写清楚。感谢你来到这里，"
                      "如果你也喜欢把好奇心变成作品，欢迎通过订阅保持联系。</p>"),
    "social_github": "https://github.com/liyinyue2",
    "social_wechat": "",
    "social_qq": "",
    "social_douyin": "",
}


def list_articles(q: str = "", category: str = "", tag: str = "") -> list[dict]:
    conn = db.conn()
    sql = """SELECT a.id, a.slug, a.title, a.summary, a.published_at, a.views,
                    c.slug AS category_slug, c.name AS category_name
             FROM articles a JOIN categories c ON c.id = a.category_id WHERE 1=1"""
    params: list = []
    if category:
        sql += " AND c.slug = ?"
        params.append(category)
    if tag:
        sql += """ AND a.id IN (SELECT at.article_id FROM article_tags at
                   JOIN tags t ON t.id = at.tag_id WHERE t.slug = ? OR t.name = ?)"""
        params += [tag, tag]
    if q:
        like = f"%{q}%"
        sql += " AND (a.title LIKE ? OR a.summary LIKE ?)"
        params += [like, like]
    sql += " ORDER BY a.published_at DESC"
    rows = [dict(r) for r in conn.execute(sql, params)]
    for r in rows:
        r["date"] = fmt_date(r.pop("published_at"))
        r["tags"] = [t["name"] for t in conn.execute(
            """SELECT t.name FROM tags t JOIN taggables g ON g.tag_id=t.id
               WHERE g.entity_type='article' AND g.entity_id=? ORDER BY t.id""",
            (r["id"],))]
    return rows


def get_article(slug: str) -> dict:
    conn = db.conn()
    row = conn.execute(
        """SELECT a.*, c.name AS category_name, c.slug AS category_slug
           FROM articles a JOIN categories c ON c.id=a.category_id WHERE a.slug=?""", (slug,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="文章不存在")
    article = dict(row)
    article["date"] = fmt_date(article.pop("published_at"))
    article["tags"] = [t["name"] for t in conn.execute(
        """SELECT t.name FROM tags t JOIN taggables g ON g.tag_id=t.id
           WHERE g.entity_type='article' AND g.entity_id=? ORDER BY t.id""",
        (article["id"],))]
    return article


def list_categories() -> list[dict]:
    return [dict(r) for r in db.conn().execute(
        """SELECT c.id, c.slug, c.name, c.description,
                  (SELECT COUNT(*) FROM articles a WHERE a.category_id = c.id) AS article_count
           FROM categories c ORDER BY c.id""")]


def list_public_messages() -> list[dict]:
    return [dict(r) for r in db.conn().execute(
        "SELECT id, name, content, reply, created_at FROM messages WHERE visible=1 ORDER BY id DESC LIMIT 200")]


def create_message(name: str, contact: str, content: str) -> dict:
    conn = db.conn()
    name = (name or "").strip()[:30] or "匿名"
    contact = (contact or "").strip()[:100]
    content = (content or "").strip()[:1000]
    if not content:
        raise HTTPException(status_code=400, detail="留言内容不能为空")
    cur = conn.execute("INSERT INTO messages (name, contact, content) VALUES (?,?,?)", (name, contact, content))
    conn.commit()
    return {"ok": True, "id": cur.lastrowid, "message": "留言成功，感谢你的分享！"}


def subscribe(email: str) -> dict:
    conn = db.conn()
    email = (email or "").strip().lower()
    if len(email) > 254 or not EMAIL_RE.match(email):
        raise HTTPException(status_code=400, detail="请输入有效的邮箱地址")
    exists = conn.execute("SELECT id FROM subscribers WHERE email=?", (email,)).fetchone()
    # 已订阅与首次订阅返回一致，防止邮箱枚举
    message = "已订阅，下一封更新会寄到你的邮箱。"
    if not exists:
        conn.execute("INSERT INTO subscribers (email) VALUES (?)", (email,))
        conn.commit()
    return {"ok": True, "message": message}


def get_settings() -> dict:
    return {r["key"]: r["value"] for r in db.conn().execute("SELECT key, value FROM settings")}


def update_settings(data: dict, user: str, ip: str) -> dict:
    conn = db.conn()
    saved = 0
    for key, value in data.items():
        if key in DEFAULT_SETTINGS and isinstance(value, str):
            if key == "about_content":
                value = sanitize_html(value[:50000])  # 关于页富文本白名单清洗 + 长度上限
            else:
                value = value[:2000]
            conn.execute(
                "INSERT INTO settings (key, value) VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (key, value))
            saved += 1
    conn.commit()
    audit_log("settings-update", f"{saved} 项", ip, user=user)
    return {"ok": True, "message": f"已保存 {saved} 项设置"}


def admin_list_articles() -> list[dict]:
    rows = [dict(r) for r in db.conn().execute(
        """SELECT a.id, a.slug, a.title, a.summary, a.published_at, a.views,
                  c.slug AS category_slug, c.name AS category_name
           FROM articles a JOIN categories c ON c.id=a.category_id ORDER BY a.published_at DESC""")]
    for r in rows:
        r["date"] = fmt_date(r.pop("published_at"))
    return rows


def admin_list_messages() -> list[dict]:
    return [dict(r) for r in db.conn().execute(
        "SELECT id, name, contact, content, reply, visible, created_at FROM messages ORDER BY id DESC")]


def admin_list_subscribers() -> list[dict]:
    return [dict(r) for r in db.conn().execute(
        "SELECT id, email, created_at FROM subscribers ORDER BY id DESC")]


def admin_stats() -> dict:
    conn = db.conn()
    return {
        "articles": conn.execute("SELECT COUNT(*) n FROM articles").fetchone()["n"],
        "categories": conn.execute("SELECT COUNT(*) n FROM categories").fetchone()["n"],
        "tags": conn.execute("SELECT COUNT(*) n FROM tags").fetchone()["n"],
        "subscribers": conn.execute("SELECT COUNT(*) n FROM subscribers").fetchone()["n"],
        "messages": conn.execute("SELECT COUNT(*) n FROM messages").fetchone()["n"],
        "views": conn.execute("SELECT COALESCE(SUM(views),0) n FROM articles").fetchone()["n"],
    }


def admin_update_message(mid: int, reply: str | None, visible: bool | None, user: str, ip: str) -> dict:
    conn = db.conn()
    fields, params = [], []
    if reply is not None:
        fields.append("reply=?")
        params.append(reply.strip()[:500])
    if visible is not None:
        fields.append("visible=?")
        params.append(1 if visible else 0)
    if not fields:
        raise HTTPException(status_code=400, detail="没有需要更新的字段")
    params.append(mid)
    cur = conn.execute(f"UPDATE messages SET {', '.join(fields)} WHERE id=?", params)
    conn.commit()
    if cur.rowcount == 0:
        raise HTTPException(status_code=404, detail="留言不存在")
    audit_log("message-update", f"id={mid} fields={','.join(f.rstrip('=') for f in fields)}", ip, user=user)
    return {"ok": True, "message": "已更新留言"}


def admin_delete_message(mid: int, user: str, ip: str) -> dict:
    conn = db.conn()
    cur = conn.execute("DELETE FROM messages WHERE id=?", (mid,))
    conn.commit()
    if cur.rowcount == 0:
        raise HTTPException(status_code=404, detail="留言不存在")
    audit_log("message-delete", f"id={mid}", ip, user=user)
    return {"ok": True, "deleted": mid}


def admin_delete_subscriber(sid: int, user: str, ip: str) -> dict:
    conn = db.conn()
    cur = conn.execute("DELETE FROM subscribers WHERE id=?", (sid,))
    conn.commit()
    if cur.rowcount == 0:
        raise HTTPException(status_code=404, detail="订阅者不存在")
    audit_log("subscriber-delete", f"id={sid}", ip, user=user)
    return {"ok": True, "deleted": sid}


def save_article(old_slug: str | None, data, user: str, ip: str) -> dict:
    conn = db.conn()
    raw_slug = (data.slug or "").strip().lower().replace(" ", "-")[:64]
    title = (data.title or "").strip()[:120]
    category = (data.category or "").strip()[:64]
    summary = (data.summary or "").strip()[:300]
    content = sanitize_html((data.content or "").strip()[:300000])
    date = (data.date or datetime.now().strftime("%Y-%m-%d")).strip()[:10]
    tags = [t.strip()[:50] for t in (data.tags or [])[:20] if t.strip()]

    if not title:
        raise HTTPException(status_code=400, detail="标题不能为空")
    cat = conn.execute("SELECT id FROM categories WHERE slug=? OR name=?", (category, category)).fetchone()
    if not cat:
        raise HTTPException(status_code=400, detail=f"分类不存在：{category}")
    try:
        datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="日期格式应为有效的 YYYY-MM-DD")

    # slug：留空则根据标题自动生成；与现有文章冲突时自动加序号后缀
    auto_slug = not raw_slug
    if auto_slug:
        stem = re.sub(r"[^\w-]+", "", title.lower().replace(" ", "-"), flags=re.UNICODE).strip("-")[:40]
        raw_slug = stem or f"post-{datetime.now().strftime('%Y%m%d')}"
    slug = raw_slug
    for i in range(2, 100):
        taken = conn.execute("SELECT 1 FROM articles WHERE slug=? AND slug != ?", (slug, old_slug or "")).fetchone()
        if not taken:
            break
        if not auto_slug:
            raise HTTPException(status_code=400, detail=f"slug 已被占用：{slug}（可留空让系统自动生成）")
        slug = f"{raw_slug}-{i}"
    if not SLUG_RE.match(slug):
        raise HTTPException(status_code=400, detail="slug 只能包含中文、字母、数字和中划线")

    try:
        if old_slug:
            cur = conn.execute(
                """UPDATE articles SET slug=?, title=?, category_id=?, summary=?, content=?,
                   published_at=?, updated_at=datetime('now','localtime') WHERE slug=?""",
                (slug, title, cat["id"], summary, content, date, old_slug))
            if cur.rowcount == 0:
                raise HTTPException(status_code=404, detail="文章不存在")
            article_id = conn.execute("SELECT id FROM articles WHERE slug=?", (slug,)).fetchone()["id"]
            conn.execute("DELETE FROM article_tags WHERE article_id=?", (article_id,))
        else:
            cur = conn.execute(
                "INSERT INTO articles (slug,title,category_id,summary,content,published_at) VALUES (?,?,?,?,?,?)",
                (slug, title, cat["id"], summary, content, date))
            article_id = cur.lastrowid
        for tag in tags:
            # v2 统一标签体系：tags(name) + taggables(entity_type='article')
            row = conn.execute("SELECT id FROM tags WHERE name=?", (tag,)).fetchone()
            tag_id = row["id"] if row else conn.execute(
                "INSERT INTO tags (name) VALUES (?)", (tag,)).lastrowid
            conn.execute("INSERT OR IGNORE INTO taggables (tag_id,entity_type,entity_id) VALUES (?,'article',?)",
                         (tag_id, article_id))
        conn.commit()
    except HTTPException:
        raise
    except Exception:
        conn.rollback()
        audit_log("db-error", f"save-article {slug}", ip, user=user)
        raise HTTPException(status_code=500, detail="保存失败，请稍后再试")

    action = "更新" if old_slug else "创建"
    audit_log(f"article-{action}", slug, ip, user=user)
    return {"ok": True, "message": f"已{action}文章：{title}", "slug": slug,
            "url": f"/post-{slug}.html", "auto_slug": auto_slug}


def delete_article(slug: str, user: str, ip: str) -> dict:
    conn = db.conn()
    cur = conn.execute("DELETE FROM articles WHERE slug=?", (slug,))
    conn.commit()
    if cur.rowcount == 0:
        raise HTTPException(status_code=404, detail="文章不存在")
    audit_log("article-delete", slug, ip, user=user)
    return {"ok": True, "deleted": slug}


def create_category(data, user: str, ip: str) -> dict:
    conn = db.conn()
    slug = (data.slug or "").strip()[:64]
    name = (data.name or "").strip()[:50]
    desc = (data.description or "").strip()[:300]
    if not SLUG_RE.match(slug):
        raise HTTPException(status_code=400, detail="slug 只能包含中文、字母、数字和中划线")
    if not name:
        raise HTTPException(status_code=400, detail="分类名称不能为空")
    if conn.execute("SELECT id FROM categories WHERE slug=?", (slug,)).fetchone():
        raise HTTPException(status_code=400, detail=f"slug 已存在：{slug}")
    conn.execute("INSERT INTO categories (slug, name, description) VALUES (?,?,?)", (slug, name, desc))
    conn.commit()
    audit_log("category-create", slug, ip, user=user)
    return {"ok": True, "message": f"已创建分类：{name}"}


def update_category(slug: str, data, user: str, ip: str) -> dict:
    conn = db.conn()
    name = (data.name or "").strip()[:50]
    desc = (data.description or "").strip()[:300]
    if not name:
        raise HTTPException(status_code=400, detail="分类名称不能为空")
    cur = conn.execute("UPDATE categories SET name=?, description=? WHERE slug=?", (name, desc, slug))
    conn.commit()
    if cur.rowcount == 0:
        raise HTTPException(status_code=404, detail="分类不存在")
    audit_log("category-update", slug, ip, user=user)
    return {"ok": True, "message": f"已更新分类：{name}"}


def delete_category(slug: str, user: str, ip: str) -> dict:
    conn = db.conn()
    count = conn.execute(
        "SELECT COUNT(*) n FROM articles WHERE category_id=(SELECT id FROM categories WHERE slug=?)",
        (slug,)).fetchone()["n"]
    if count:
        raise HTTPException(status_code=400, detail=f"该分类下还有 {count} 篇文章，请先移动文章再删除")
    cur = conn.execute("DELETE FROM categories WHERE slug=?", (slug,))
    conn.commit()
    if cur.rowcount == 0:
        raise HTTPException(status_code=404, detail="分类不存在")
    audit_log("category-delete", slug, ip, user=user)
    return {"ok": True, "deleted": slug}


def rss_xml(base_url: str) -> bytes:
    import html as html_mod

    conn = db.conn()
    rows = conn.execute(
        "SELECT a.slug,a.title,a.summary,a.published_at FROM articles a ORDER BY a.published_at DESC LIMIT 20").fetchall()
    site_name = conn.execute("SELECT value FROM settings WHERE key='site_name'").fetchone()
    site_name = (site_name["value"] if site_name else "") or "Y's Blog"

    esc = lambda s: html_mod.escape(s or "", quote=False)
    items = "".join(
        f"<item><title>{esc(r['title'])}</title>"
        f"<link>{base_url}/post-{r['slug']}.html</link>"
        f"<description>{esc(r['summary'])}</description>"
        f"<pubDate>{r['published_at']}</pubDate><guid>/post-{r['slug']}.html</guid></item>"
        for r in rows)
    rss = (f'<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel>'
           f"<title>{esc(site_name)}</title>"
           f"<link>{base_url}/</link>"
           f"<description>记录思考，分享创造。</description>{items}</channel></rss>")
    return rss.encode("utf-8")
