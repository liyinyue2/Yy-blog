"""文章详情页模板：从 v1.0 原样移植（public/ 前端冻结，渲染输出保持一致）。"""
import html as html_mod
import re
from datetime import datetime

from fastapi import HTTPException

from app.core.database import db

NAV_HTML = """<nav class="page-nav" aria-label="博客主导航"><a class="brand" href="/" aria-label="Y's Blog 首页"><svg viewBox="0 0 16 18" aria-hidden="true"><path fill="none" stroke-width="3.4" stroke-linecap="round" stroke-linejoin="round" d="M3.2 1.8Q6.4 5.4 8 8.6M12.8 1.8Q9.6 5.4 8 8.6Q8.35 13 8 16.4"/></svg><span data-setting="site_name">Y's Blog</span></a><div class="links" aria-label="博客分类"><a href="/">首页</a><a href="/articles.html">文章</a><a href="/messages.html">留言</a><a href="/about.html">关于</a></div><div class="actions"><button class="menu-toggle" type="button" aria-label="打开菜单" aria-expanded="false" aria-controls="mobile-menu"><svg viewBox="0 0 20 20" aria-hidden="true"><path d="M2 4h16v1.5H2zm0 5.25h16v1.5H2zM2 14.5h16V16H2z"/></svg></button></div></nav><div class="mobile-menu" id="mobile-menu" aria-label="移动端博客导航"><a href="/">首页</a><a href="/articles.html">文章</a><a href="/messages.html">留言</a><a href="/about.html">关于</a></div>"""

POST_TEMPLATE = """<!doctype html><html lang="zh-CN"><head><meta charset="UTF-8" /><meta name="viewport" content="width=device-width, initial-scale=1.0" /><meta name="theme-color" content="#ffffff" /><link rel="icon" type="image/svg+xml" href="/y-mark.svg" /><meta name="description" content="{summary}" /><link rel="preconnect" href="https://fonts.googleapis.com" /><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin /><link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap" rel="stylesheet" /><link rel="stylesheet" href="/site.css" /><title>{title} — Y's Blog</title></head><body class="page-body">{nav}<main class="post-shell reveal"><a class="post-back" href="/articles.html">← 返回文章</a><div class="post-meta"><span>{category}</span><time>{date}</time><span>· {views} 次阅读</span></div><h1 class="post-title">{title}</h1><p class="post-lead">{summary}</p><div class="post-body">{content}</div><div class="post-nav">{prev_link}{next_link}</div></main><footer class="page-footer"><div class="page-footer-inner"><span><span data-setting="site_name">Y's Blog</span> · 记录思考，分享创造。</span><a href="/articles.html">更多文章 →</a></div></footer><div class="toast" id="toast" aria-live="polite"></div><script src="/site.js"></script></body></html>"""

SLUG_RE = re.compile(r"^[\w][\w-]{0,63}$", re.UNICODE)
SLUG_FULL_RE = re.compile(r"^/post-([\w-]+)\.html$")


def fmt_date(iso: str) -> str:
    try:
        return datetime.strptime(iso, "%Y-%m-%d").strftime("%Y.%m.%d")
    except (ValueError, TypeError):
        return iso


def _render(row, conn) -> str:
    prev = conn.execute(
        "SELECT slug, title FROM articles WHERE published_at < ? ORDER BY published_at DESC LIMIT 1",
        (row["published_at"],)).fetchone()
    nxt = conn.execute(
        "SELECT slug, title FROM articles WHERE published_at > ? ORDER BY published_at ASC LIMIT 1",
        (row["published_at"],)).fetchone()
    prev_link = (f'<a class="read-link" href="/post-{prev["slug"]}.html">← 上一篇：'
                 f'{html_mod.escape(prev["title"])}</a>') if prev else "<span></span>"
    next_link = (f'<a class="read-link" href="/post-{nxt["slug"]}.html">下一篇：'
                 f'{html_mod.escape(nxt["title"])} →</a>') if nxt else "<span></span>"
    return POST_TEMPLATE.format(
        nav=NAV_HTML, title=html_mod.escape(row["title"]), summary=html_mod.escape(row["summary"]),
        category=html_mod.escape(row["category_name"]), date=fmt_date(row["published_at"]),
        views=row["views"] + 1, content=row["content"],
        prev_link=prev_link, next_link=next_link,
    )


def render_post(slug: str) -> str:
    """从数据库渲染文章详情页；文章不存在抛 404（由调用方转样式化页面）。"""
    conn = db.conn()
    row = conn.execute(
        """SELECT a.*, c.name AS category_name, c.slug AS category_slug
           FROM articles a JOIN categories c ON c.id = a.category_id WHERE a.slug = ?""",
        (slug,),
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="not found")
    conn.execute("UPDATE articles SET views = views + 1 WHERE id = ?", (row["id"],))
    conn.commit()
    return _render(row, conn)


def render_not_found() -> str:
    """文章不存在时的样式化 404 页面。"""
    return POST_TEMPLATE.format(
        nav=NAV_HTML, title="404 · 页面走丢了", summary="你要找的文章不存在或已被删除。",
        category="提示", date=datetime.now().strftime("%Y.%m.%d"), views=0,
        content=("<p>这篇文章可能已经被删除，或者链接地址有误。</p>"
                 "<p>可以先去 <a href=\"/articles.html\">文章列表</a> 看看最新的内容。</p>"),
        prev_link="<span></span>", next_link="<span></span>",
    ).replace("<div class=\"post-meta\">", "<div class=\"post-meta\" style=\"display:none\">", 1)


def parse_post_path(path: str) -> str | None:
    """从 /post-{slug}.html 提取 slug；不匹配返回 None。"""
    m = SLUG_FULL_RE.fullmatch(path)
    return m.group(1) if m else None
