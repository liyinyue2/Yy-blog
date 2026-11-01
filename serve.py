#!/usr/bin/env python3
"""Y's Blog — 全栈后端
纯 Python 标准库实现：静态资源 + REST API + SQLite 数据库。
启动：python serve.py（或 python3 serve.py），默认端口 3000，可用 PORT 环境变量覆盖。
管理后台：/yy-AviuuP3r.html（地址不可猜测，防止目录扫描；令牌通过环境变量 ADMIN_TOKEN 配置，未设置时自动生成并保存在本地 .admin_token 文件）。
"""
import base64
import binascii
import hashlib
import hmac
import html as html_mod
import io
import json
import os
import re
import secrets
import sqlite3
import threading
import time
from datetime import datetime
from functools import partial
from html.parser import HTMLParser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

ROOT = Path(__file__).parent
PUBLIC = ROOT / "public"
DB_PATH = ROOT / "blog.db"
PORT = int(os.environ.get("PORT", "3000"))
# 管理令牌：优先取环境变量；未设置时首次启动自动生成强随机值并存入 .admin_token（已加入 .gitignore，不入仓库）
# 源码中不再存在任何默认令牌，公开仓库无法被对照猜解。
ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN", "")
_TOKEN_FILE = ROOT / ".admin_token"
if not ADMIN_TOKEN:
    if _TOKEN_FILE.exists():
        ADMIN_TOKEN = _TOKEN_FILE.read_text(encoding="utf-8").strip()
    if not ADMIN_TOKEN:
        ADMIN_TOKEN = secrets.token_urlsafe(24)
        _TOKEN_FILE.write_text(ADMIN_TOKEN, encoding="utf-8")
EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
SLUG_RE = re.compile(r"^\w[\w-]{0,63}$", re.UNICODE)  # 支持中文、字母、数字、中划线

# ----------------------------------------------------------------------
# 安全加固：内存级滑动窗口限流（单机部署够用，多进程部署需换 Redis）
# ----------------------------------------------------------------------
_rate_lock = threading.Lock()
_rate_buckets = {}

# 限流桶总量上限：超过时清理全部已过期条目，防止恶意刷量撑爆内存
_RATE_MAX_KEYS = 4096

def rate_hit(key, window_seconds, max_hits):
    """记录一次访问；若窗口内已达上限返回 True（应拒绝）。"""
    now = time.monotonic()
    with _rate_lock:
        if len(_rate_buckets) > _RATE_MAX_KEYS:
            cutoff = now - max(w for w, _ in (LIMIT_MESSAGE, LIMIT_SUBSCRIBE, LIMIT_ADMIN_FAIL))
            for k in [k for k, v in _rate_buckets.items() if not v or v[-1] < cutoff]:
                del _rate_buckets[k]
        hits = _rate_buckets.setdefault(key, [])
        cutoff = now - window_seconds
        while hits and hits[0] < cutoff:
            hits.pop(0)
        if len(hits) >= max_hits:
            return True
        hits.append(now)
        return False

# 限流策略：(窗口秒数, 窗口内最大次数)
LIMIT_MESSAGE = (60, 5)      # 留言：每 IP 每分钟 5 条
LIMIT_SUBSCRIBE = (60, 5)    # 订阅：每 IP 每分钟 5 次
LIMIT_ADMIN_FAIL = (900, 5)  # 管理令牌失败：每 IP 15 分钟内 5 次，超出锁定

# 隐藏服务器指纹（不暴露 Python / http.server 版本）
SimpleHTTPRequestHandler.server_version = "YsBlog"
SimpleHTTPRequestHandler.sys_version = ""

# HSTS：本地 HTTP 无意义；部署到 HTTPS 后设置环境变量 ENABLE_HSTS=1 开启
ENABLE_HSTS = os.environ.get("ENABLE_HSTS", "") == "1"
# 对外基地址（RSS 链接用），防止 Host 头注入；生产部署时设置 BASE_URL=https://你的域名
BASE_URL = os.environ.get("BASE_URL", f"http://localhost:{PORT}")

# ----------------------------------------------------------------------
# HTML 白名单清洗：富文本（文章正文 / 关于页）入库前剥离脚本与危险内容
# ----------------------------------------------------------------------
ALLOWED_TAGS = {"p", "br", "hr", "strong", "em", "b", "i", "u", "s", "h2", "h3", "h4",
                "ul", "ol", "li", "a", "blockquote", "code", "pre"}
VOID_TAGS = {"br", "hr"}
ALLOWED_ATTRS = {"a": {"href"}}

class _HtmlWhitelister(HTMLParser):
    """只放行白名单标签；<a> 仅保留 http(s)/相对 href；其余内容一律转义输出。"""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out = []
        self.stack = []

    def handle_starttag(self, tag, attrs):
        if tag not in ALLOWED_TAGS:
            return
        if tag in VOID_TAGS:
            self.out.append(f"<{tag}>")
            return
        parts = [tag]
        for name, value in attrs:
            if tag in ALLOWED_ATTRS and name in ALLOWED_ATTRS[tag]:
                v = (value or "").strip()
                low = v.lower()
                if not (v.startswith("/") or low.startswith("http://") or low.startswith("https://")):
                    continue  # 拒绝 javascript: / data: 等危险协议
                parts.append(f'{name}="{html_mod.escape(v, quote=True)}"')
        self.out.append(f"<{' '.join(parts)}>")
        self.stack.append(tag)

    def handle_endtag(self, tag):
        if tag in ALLOWED_TAGS and tag not in VOID_TAGS and tag in self.stack:
            while self.stack:  # 闭合中间未关闭的标签
                t = self.stack.pop()
                self.out.append(f"</{t}>")
                if t == tag:
                    break

    def handle_data(self, data):
        self.out.append(html_mod.escape(data, quote=False))

    def result(self):
        while self.stack:
            self.out.append(f"</{self.stack.pop()}>")
        return "".join(self.out)

def sanitize_html(raw):
    """富文本入库前的白名单清洗，杜绝存储型 XSS。"""
    if not raw:
        return ""
    parser = _HtmlWhitelister()
    try:
        parser.feed(raw)
        parser.close()
        return parser.result()
    except Exception:
        return html_mod.escape(raw)  # 解析异常时退化为纯文本转义

# ----------------------------------------------------------------------
# 安全审计日志：后台敏感操作全部落盘 logs/audit.log
# ----------------------------------------------------------------------
AUDIT_LOG = ROOT / "logs" / "audit.log"

def audit_log(action, detail, ip="-"):
    try:
        AUDIT_LOG.parent.mkdir(exist_ok=True)
        with open(AUDIT_LOG, "a", encoding="utf-8") as f:
            f.write(f"{datetime.now().isoformat(timespec='seconds')} | {ip} | {action} | {detail}\n")
    except OSError:
        pass  # 日志失败不影响主业务



# ----------------------------------------------------------------------
# 数据库
# ----------------------------------------------------------------------
SCHEMA = """
CREATE TABLE IF NOT EXISTS categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    slug TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    description TEXT DEFAULT ''
);
CREATE TABLE IF NOT EXISTS articles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    slug TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    category_id INTEGER NOT NULL REFERENCES categories(id),
    summary TEXT DEFAULT '',
    content TEXT DEFAULT '',
    published_at TEXT NOT NULL,
    views INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now', 'localtime')),
    updated_at TEXT DEFAULT (datetime('now', 'localtime'))
);
CREATE TABLE IF NOT EXISTS tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    slug TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS article_tags (
    article_id INTEGER NOT NULL REFERENCES articles(id) ON DELETE CASCADE,
    tag_id INTEGER NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
    PRIMARY KEY (article_id, tag_id)
);
CREATE TABLE IF NOT EXISTS subscribers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE NOT NULL,
    created_at TEXT DEFAULT (datetime('now', 'localtime'))
);
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    contact TEXT DEFAULT '',
    content TEXT NOT NULL,
    reply TEXT DEFAULT '',
    visible INTEGER DEFAULT 1,
    created_at TEXT DEFAULT (datetime('now', 'localtime'))
);
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT DEFAULT ''
);
"""

# 种子数据：来自原静态页面的 3 篇文章
SEED_CATEGORIES = [
    ("frontend", "前端开发", "组件、交互、性能，以及让产品更好用的工程细节。"),
    ("design", "UI 设计", "视觉秩序、留白、节奏与界面里那些看不见的情绪。"),
    ("life", "个人成长", "关于工作方式、长期主义，以及如何与自己相处。"),
]

SEED_ARTICLES = [
    {
        "slug": "interaction", "title": "把复杂的交互，做得像呼吸一样自然",
        "category": "frontend", "date": "2026-10-28",
        "summary": "从状态、反馈到节奏，重新理解一个好用的界面为什么让人感到轻松。",
        "tags": ["交互设计", "前端", "用户体验"],
    },
    {
        "slug": "whitespace", "title": "留白不是空白：界面中的安静力量",
        "category": "design", "date": "2026-10-16",
        "summary": "从网格、比例和层次出发，聊聊为什么克制也可以是一种表达。",
        "tags": ["UI 设计", "留白", "设计原则"],
    },
    {
        "slug": "workflow", "title": "给长期主义者的一个小型工作流",
        "category": "life", "date": "2026-09-30",
        "summary": "不追逐每一个工具，只保留那些真正帮助自己持续前进的习惯。",
        "tags": ["效率", "工作流", "长期主义"],
    },
]


def seed_content(slug):
    """优先从 seed_extract.json 读取原静态页正文；找不到则给占位正文。"""
    extract = ROOT / "seed_extract.json"
    if extract.exists():
        data = json.loads(extract.read_text(encoding="utf-8"))
        key = "post-" + slug
        if key in data:
            return data[key]["body"]
    return "<p>正文待补充。</p>"


# 站点设置默认值（后台可改）
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


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_db()
    conn.executescript(SCHEMA)
    if conn.execute("SELECT COUNT(*) AS n FROM categories").fetchone()["n"] == 0:
        conn.executemany("INSERT INTO categories (slug, name, description) VALUES (?,?,?)", SEED_CATEGORIES)
        cat_id = {row["slug"]: row["id"] for row in conn.execute("SELECT id, slug FROM categories")}
        for a in SEED_ARTICLES:
            cur = conn.execute(
                "INSERT INTO articles (slug, title, category_id, summary, content, published_at) VALUES (?,?,?,?,?,?)",
                (a["slug"], a["title"], cat_id[a["category"]], a["summary"], seed_content(a["slug"]), a["date"]),
            )
            for tag in a["tags"]:
                tag_slug = "t-" + hashlib.md5(tag.encode("utf-8")).hexdigest()[:10]
                row = conn.execute("SELECT id FROM tags WHERE name=?", (tag,)).fetchone()
                if not row:
                    row = conn.execute("INSERT INTO tags (slug, name) VALUES (?,?)", (tag_slug, tag))
                    tag_id = row.lastrowid
                else:
                    tag_id = row["id"]
                conn.execute("INSERT INTO article_tags (article_id, tag_id) VALUES (?,?)", (cur.lastrowid, tag_id))
        conn.commit()
        print("[init] 已写入种子数据：3 个分类 / 3 篇文章")
    for key, value in DEFAULT_SETTINGS.items():
        conn.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?,?)", (key, value))
    conn.commit()
    conn.close()


# ----------------------------------------------------------------------
# 文章页面模板
# ----------------------------------------------------------------------
NAV_HTML = """<nav class="page-nav" aria-label="博客主导航"><a class="brand" href="/" aria-label="Y's Blog 首页"><svg viewBox="0 0 16 18" aria-hidden="true"><path fill="none" stroke-width="3.4" stroke-linecap="round" stroke-linejoin="round" d="M3.2 1.8Q6.4 5.4 8 8.6M12.8 1.8Q9.6 5.4 8 8.6Q8.35 13 8 16.4"/></svg><span data-setting="site_name">Y's Blog</span></a><div class="links" aria-label="博客分类"><a href="/">首页</a><a href="/articles.html">文章</a><a href="/messages.html">留言</a><a href="/about.html">关于</a></div><div class="actions"><button class="menu-toggle" type="button" aria-label="打开菜单" aria-expanded="false" aria-controls="mobile-menu"><svg viewBox="0 0 20 20" aria-hidden="true"><path d="M2 4h16v1.5H2zm0 5.25h16v1.5H2zM2 14.5h16V16H2z"/></svg></button></div></nav><div class="mobile-menu" id="mobile-menu" aria-label="移动端博客导航"><a href="/">首页</a><a href="/articles.html">文章</a><a href="/messages.html">留言</a><a href="/about.html">关于</a></div>"""

POST_TEMPLATE = """<!doctype html><html lang="zh-CN"><head><meta charset="UTF-8" /><meta name="viewport" content="width=device-width, initial-scale=1.0" /><meta name="theme-color" content="#ffffff" /><link rel="icon" type="image/svg+xml" href="/y-mark.svg" /><meta name="description" content="{summary}" /><link rel="preconnect" href="https://fonts.googleapis.com" /><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin /><link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap" rel="stylesheet" /><link rel="stylesheet" href="/site.css" /><title>{title} — Y's Blog</title></head><body class="page-body">{nav}<main class="post-shell reveal"><a class="post-back" href="/articles.html">← 返回文章</a><div class="post-meta"><span>{category}</span><time>{date}</time><span>· {views} 次阅读</span></div><h1 class="post-title">{title}</h1><p class="post-lead">{summary}</p><div class="post-body">{content}</div><div class="post-nav">{prev_link}{next_link}</div></main><footer class="page-footer"><div class="page-footer-inner"><span><span data-setting="site_name">Y's Blog</span> · 记录思考，分享创造。</span><a href="/articles.html">更多文章 →</a></div></footer><div class="toast" id="toast" aria-live="polite"></div><script src="/site.js"></script></body></html>"""


def fmt_date(iso):
    try:
        return datetime.strptime(iso, "%Y-%m-%d").strftime("%Y.%m.%d")
    except ValueError:
        return iso


def render_post(slug):
    """从数据库渲染文章详情页；文章不存在返回 None。"""
    conn = get_db()
    row = conn.execute(
        """SELECT a.*, c.name AS category_name, c.slug AS category_slug
           FROM articles a JOIN categories c ON c.id = a.category_id WHERE a.slug = ?""",
        (slug,),
    ).fetchone()
    if not row:
        conn.close()
        return None
    conn.execute("UPDATE articles SET views = views + 1 WHERE id = ?", (row["id"],))
    conn.commit()
    prev = conn.execute(
        "SELECT slug, title FROM articles WHERE published_at < ? ORDER BY published_at DESC LIMIT 1", (row["published_at"],)).fetchone()
    nxt = conn.execute(
        "SELECT slug, title FROM articles WHERE published_at > ? ORDER BY published_at ASC LIMIT 1", (row["published_at"],)).fetchone()
    conn.close()
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


# ----------------------------------------------------------------------
# Word / PDF 导入转换
# ----------------------------------------------------------------------
MAX_UPLOAD = 15 * 1024 * 1024   # 单文件 15MB
MAX_BODY = 25 * 1024 * 1024     # JSON 请求体上限（base64 有 33% 膨胀）


def _inline_runs(paragraph):
    """把 docx 段落的 run 转成带 <strong>/<em> 的行内 HTML。"""
    parts = []
    for run in paragraph.runs:
        text = html_mod.escape(run.text or "")
        if not text:
            continue
        if run.bold:
            text = f"<strong>{text}</strong>"
        if run.italic:
            text = f"<em>{text}</em>"
        parts.append(text)
    return "".join(parts) or html_mod.escape(paragraph.text or "")


MAX_DOCX_UNCOMPRESSED = 64 * 1024 * 1024   # docx 解压后总大小上限（防 zip 炸弹撑爆内存）

def convert_docx(raw):
    import zipfile
    with zipfile.ZipFile(io.BytesIO(raw)) as zf:  # 解析前预检：拒绝解压炸弹
        total = sum(info.file_size for info in zf.infolist())
        if total > MAX_DOCX_UNCOMPRESSED:
            raise ValueError(f"文档解压后过大（{total // 1048576}MB），疑似损坏或恶意构造")
    from docx import Document
    doc = Document(io.BytesIO(raw))
    title = (doc.core_properties.title or "").strip()
    blocks = []
    list_buffer = []  # (type, items)
    first_heading = ""

    def flush_list():
        nonlocal list_buffer
        if list_buffer:
            tag = "ol" if list_buffer[0][0] == "ol" else "ul"
            items = "".join(f"<li>{item}</li>" for _, item in list_buffer)
            blocks.append(f"<{tag}>{items}</{tag}>")
            list_buffer = []

    for para in doc.paragraphs:
        text = para.text.strip()
        style = (para.style.name or "").lower() if para.style is not None else ""
        if not text:
            flush_list()
            continue
        if style.startswith("title"):
            if not title:
                title = text
        elif style.startswith("heading 1"):
            flush_list()
            if not title:
                title = text
            if not first_heading:
                first_heading = text
            blocks.append(f"<h2>{html_mod.escape(text)}</h2>")
        elif style.startswith("heading 2"):
            flush_list()
            blocks.append(f"<h3>{html_mod.escape(text)}</h3>")
        elif style.startswith("heading"):
            flush_list()
            blocks.append(f"<h4>{html_mod.escape(text)}</h4>")
        elif "list number" in style:
            list_buffer.append(("ol", _inline_runs(para)))
        elif "list" in style:
            list_buffer.append(("ul", _inline_runs(para)))
        else:
            flush_list()
            blocks.append(f"<p>{_inline_runs(para)}</p>")
    flush_list()
    if not title:
        title = first_heading
    return title, "\n".join(blocks)


def convert_pdf(raw):
    import pymupdf
    doc = pymupdf.open(stream=raw, filetype="pdf")
    title = (doc.metadata or {}).get("title") or ""
    paragraphs = []
    for page in doc:
        lines = [ln.strip() for ln in page.get_text("text").splitlines()]
        buf = []
        for ln in lines:
            if not ln:
                if buf:
                    paragraphs.append(" ".join(buf))
                    buf = []
                continue
            buf.append(ln)
            # 段落通常以句末标点收尾，遇到即断段
            if re.search(r"[。！？.!?]$", ln):
                paragraphs.append(" ".join(buf))
                buf = []
        if buf:
            paragraphs.append(" ".join(buf))
    doc.close()
    paragraphs = [p for p in paragraphs if p.strip()]
    if not title and paragraphs:
        title = paragraphs[0][:60]
    content = "\n".join(f"<p>{html_mod.escape(p)}</p>" for p in paragraphs)
    return title.strip(), content


def render_not_found():
    """文章不存在时的样式化 404 页面。"""
    return POST_TEMPLATE.format(
        nav=NAV_HTML, title="404 · 页面走丢了", summary="你要找的文章不存在或已被删除。",
        category="提示", date=datetime.now().strftime("%Y.%m.%d"), views=0,
        content=("<p>这篇文章可能已经被删除，或者链接地址有误。</p>"
                 "<p>可以先去 <a href=\"/articles.html\">文章列表</a> 看看最新的内容。</p>"),
        prev_link="<span></span>", next_link="<span></span>",
    ).replace("<div class=\"post-meta\">", "<div class=\"post-meta\" style=\"display:none\">", 1)


def handle_convert(self, conn):
    data = self.read_json_body()
    if data is None:
        return self.send_json({"error": "请求体不是合法 JSON"}, 400)
    filename = (data.get("filename") or "").strip()
    b64 = (data.get("data") or "").strip()
    if not filename or not b64:
        return self.send_json({"error": "缺少文件名或文件内容"}, 400)
    try:
        raw = base64.b64decode(b64, validate=False)
    except (binascii.Error, ValueError):
        return self.send_json({"error": "文件内容解码失败"}, 400)
    if len(raw) > MAX_UPLOAD:
        return self.send_json({"error": "文件超过 15MB 限制"}, 400)
    ext = filename.lower().rsplit(".", 1)[-1]
    stem = filename.rsplit(".", 1)[0].strip() or "未命名文章"
    try:
        if ext == "docx":
            title, content = convert_docx(raw)
        elif ext == "pdf":
            title, content = convert_pdf(raw)
        elif ext == "doc":
            return self.send_json({"error": "暂不支持旧版 .doc，请在 Word 中另存为 .docx 后再导入"}, 400)
        else:
            return self.send_json({"error": "仅支持 .docx 与 .pdf 文件"}, 400)
    except ImportError as exc:
        audit_log("convert-error", f"缺少解析库: {exc}", self.client_address[0])
        return self.send_json({"error": "服务器未安装文档解析库，请联系管理员"}, 500)
    except Exception as exc:  # 解析失败给友好提示（不泄漏内部异常细节）
        audit_log("convert-error", f"{filename}: {type(exc).__name__}: {exc}", self.client_address[0])
        return self.send_json({"error": "文件解析失败，请确认文件未损坏后重试"}, 400)
    if not title:
        title = stem
    return self.send_json({
        "ok": True,
        "title": title.strip() or stem,
        "content": content,
        "chars": len(re.sub(r"<[^>]+>", "", content)),
    })


# ----------------------------------------------------------------------
# HTTP 处理
# ----------------------------------------------------------------------
class BlogHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(PUBLIC), **kwargs)

    # ---------- 基础工具 ----------
    def end_headers(self):
        # 统一注入安全响应头
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "strict-origin-when-cross-origin")
        self.send_header("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        if ENABLE_HSTS:  # 部署 HTTPS 后由环境变量开启
            self.send_header("Strict-Transport-Security", "max-age=63072000; includeSubDomains")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src https://fonts.gstatic.com; "
            "script-src 'self'; "
            "img-src 'self' data: https: http:; "
            "connect-src 'self'",
        )
        super().end_headers()

    def send_json(self, payload, status=200):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def send_html(self, html, status=200):
        body = html.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def read_json_body(self):
        try:
            length = int(self.headers.get("Content-Length", 0) or 0)
        except (TypeError, ValueError):
            return None  # 畸形 Content-Length 头 → 视为非法请求
        if length <= 0:
            return {}
        if length > MAX_BODY:
            self._discard_body(length)  # 读掉请求体，避免连接被 RST / 污染下一个请求
            return None
        try:
            data = json.loads(self.rfile.read(length).decode("utf-8"))
            return data if isinstance(data, dict) else None  # 拒绝数组/字符串等非对象结构
        except (ValueError, UnicodeDecodeError):
            return None

    def _discard_body(self, length, hard_cap=64 * 1024 * 1024):
        """分块读掉并丢弃请求体（防止套接字残留数据导致连接重置）。"""
        remaining = min(length, hard_cap)
        while remaining > 0:
            chunk = self.rfile.read(min(remaining, 65536))
            if not chunk:
                break
            remaining -= len(chunk)

    def is_admin(self):
        return hmac.compare_digest(self.headers.get("X-Admin-Token", ""), ADMIN_TOKEN)

    def log_message(self, fmt, *args):  # 精简日志
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {self.command} {self.path}")

    # ---------- API 实现 ----------
    def _content_length(self):
        try:
            value = int(self.headers.get("Content-Length", 0) or 0)
        except (TypeError, ValueError):
            return 0
        return value if value > 0 else 0

    def handle_api(self, method):
        parsed = urlparse(self.path)
        path = unquote(parsed.path).rstrip("/") or "/api"
        query = {k: v[0] for k, v in parse_qs(parsed.query).items()}
        if method in ("POST", "PUT") and self._content_length() > MAX_BODY:
            self._discard_body(self._content_length())
            return self.send_json({"error": "请求体过大（上限 25MB）"}, 413)
        conn = get_db()
        try:
            # ----- 公开接口 -----
            if method == "GET" and path == "/api/health":
                return self.send_json({"ok": True, "time": datetime.now().isoformat(timespec="seconds")})

            if method == "GET" and path == "/api/articles":
                sql = """SELECT a.id, a.slug, a.title, a.summary, a.published_at, a.views,
                                c.slug AS category_slug, c.name AS category_name
                         FROM articles a JOIN categories c ON c.id = a.category_id WHERE 1=1"""
                params = []
                if query.get("category"):
                    sql += " AND c.slug = ?"
                    params.append(query["category"])
                if query.get("tag"):
                    sql += """ AND a.id IN (SELECT at.article_id FROM article_tags at
                               JOIN tags t ON t.id = at.tag_id WHERE t.slug = ? OR t.name = ?)"""
                    params += [query["tag"], query["tag"]]
                if query.get("q"):
                    like = f"%{query['q']}%"
                    sql += " AND (a.title LIKE ? OR a.summary LIKE ?)"
                    params += [like, like]
                sql += " ORDER BY a.published_at DESC"
                rows = [dict(r) for r in conn.execute(sql, params)]
                for r in rows:
                    r["date"] = fmt_date(r.pop("published_at"))
                    r["tags"] = [t["name"] for t in conn.execute(
                        "SELECT t.name FROM tags t JOIN article_tags at ON at.tag_id=t.id WHERE at.article_id=? ORDER BY t.id", (r["id"],))]
                return self.send_json(rows)

            m = re.fullmatch(r"/api/articles/([\w-]+)", path)
            if m:
                slug = m.group(1)
                if method == "GET":
                    row = conn.execute(
                        """SELECT a.*, c.name AS category_name, c.slug AS category_slug
                           FROM articles a JOIN categories c ON c.id=a.category_id WHERE a.slug=?""", (slug,)).fetchone()
                    if not row:
                        return self.send_json({"error": "文章不存在"}, 404)
                    article = dict(row)
                    article["date"] = fmt_date(article.pop("published_at"))
                    article["tags"] = [t["name"] for t in conn.execute(
                        "SELECT t.name FROM tags t JOIN article_tags at ON at.tag_id=t.id WHERE at.article_id=? ORDER BY t.id", (article["id"],))]
                    return self.send_json(article)
                return self.send_json({"error": "方法不允许"}, 405)

            if method == "GET" and path == "/api/categories":
                rows = [dict(r) for r in conn.execute(
                    """SELECT c.id, c.slug, c.name, c.description,
                              (SELECT COUNT(*) FROM articles a WHERE a.category_id = c.id) AS article_count
                       FROM categories c ORDER BY c.id""")]
                return self.send_json(rows)

            if method == "GET" and path == "/api/tags":
                rows = [dict(r) for r in conn.execute(
                    """SELECT t.id, t.slug, t.name,
                              (SELECT COUNT(*) FROM article_tags at WHERE at.tag_id = t.id) AS article_count
                       FROM tags t ORDER BY article_count DESC, t.name""")]
                return self.send_json(rows)

            if method == "GET" and path == "/api/stats":
                stats = {
                    "articles": conn.execute("SELECT COUNT(*) n FROM articles").fetchone()["n"],
                    "categories": conn.execute("SELECT COUNT(*) n FROM categories").fetchone()["n"],
                    "tags": conn.execute("SELECT COUNT(*) n FROM tags").fetchone()["n"],
                    "subscribers": conn.execute("SELECT COUNT(*) n FROM subscribers").fetchone()["n"],
                    "messages": conn.execute("SELECT COUNT(*) n FROM messages").fetchone()["n"],
                    "views": conn.execute("SELECT COALESCE(SUM(views),0) n FROM articles").fetchone()["n"],
                }
                return self.send_json(stats)

            if method == "GET" and path == "/api/settings":
                rows = {r["key"]: r["value"] for r in conn.execute("SELECT key, value FROM settings")}
                return self.send_json(rows)

            if method == "GET" and path == "/api/messages":
                rows = [dict(r) for r in conn.execute(
                    "SELECT id, name, content, reply, created_at FROM messages WHERE visible=1 ORDER BY id DESC LIMIT 200")]
                return self.send_json(rows)

            if method == "POST" and path == "/api/messages":
                if rate_hit(f"msg:{self.client_address[0]}", *LIMIT_MESSAGE):
                    return self.send_json({"error": "操作太频繁了，请稍后再试"}, 429)
                data = self.read_json_body()
                if data is None:
                    return self.send_json({"error": "请求体不是合法 JSON"}, 400)
                name = (data.get("name") or "").strip()[:30] or "匿名"
                contact = (data.get("contact") or "").strip()[:100]
                content = (data.get("content") or "").strip()[:1000]
                if not content:
                    return self.send_json({"error": "留言内容不能为空"}, 400)
                cur = conn.execute("INSERT INTO messages (name, contact, content) VALUES (?,?,?)", (name, contact, content))
                conn.commit()
                return self.send_json({"ok": True, "id": cur.lastrowid, "message": "留言成功，感谢你的分享！"})

            if method == "POST" and path == "/api/subscribe":
                if rate_hit(f"sub:{self.client_address[0]}", *LIMIT_SUBSCRIBE):
                    return self.send_json({"error": "操作太频繁了，请稍后再试"}, 429)
                data = self.read_json_body()
                if data is None:
                    return self.send_json({"error": "请求体不是合法 JSON"}, 400)
                email = (data.get("email") or "").strip().lower()
                if len(email) > 254 or not EMAIL_RE.match(email):
                    return self.send_json({"error": "请输入有效的邮箱地址"}, 400)
                exists = conn.execute("SELECT id FROM subscribers WHERE email=?", (email,)).fetchone()
                if exists:
                    # 与首次订阅返回一致，避免攻击者借此枚举哪些邮箱已订阅
                    return self.send_json({"ok": True, "message": "已订阅，下一封更新会寄到你的邮箱。"})
                conn.execute("INSERT INTO subscribers (email) VALUES (?)", (email,))
                conn.commit()
                return self.send_json({"ok": True, "message": "已订阅，下一封更新会寄到你的邮箱。"})

            # ----- 管理接口 -----
            if path.startswith("/api/admin"):
                ip = self.client_address[0]
                if not self.is_admin():
                    # 只统计失败尝试：同 IP 15 分钟内错 5 次 → 临时锁定
                    if rate_hit(f"admin-fail:{ip}", *LIMIT_ADMIN_FAIL):
                        audit_log("admin-locked", f"{method} {path}", ip)
                        return self.send_json({"error": "令牌错误次数过多，已临时锁定 15 分钟"}, 429)
                    audit_log("admin-auth-fail", f"{method} {path}", ip)
                    return self.send_json({"error": "未授权：请检查管理令牌"}, 401)

                if method == "GET" and path == "/api/admin/subscribers":
                    rows = [dict(r) for r in conn.execute(
                        "SELECT id, email, created_at FROM subscribers ORDER BY id DESC")]
                    return self.send_json(rows)

                if method == "GET" and path == "/api/admin/articles":
                    rows = [dict(r) for r in conn.execute(
                        """SELECT a.id, a.slug, a.title, a.summary, a.published_at, a.views,
                                  c.slug AS category_slug, c.name AS category_name
                           FROM articles a JOIN categories c ON c.id=a.category_id ORDER BY a.published_at DESC""")]
                    for r in rows:
                        r["date"] = fmt_date(r.pop("published_at"))
                    return self.send_json(rows)

                if method == "POST" and path == "/api/admin/articles":
                    data = self.read_json_body()
                    if data is None:
                        return self.send_json({"error": "请求体不是合法 JSON"}, 400)
                    return self._save_article(conn, None, data)

                if method == "POST" and path == "/api/admin/convert":
                    return handle_convert(self, conn)

                m = re.fullmatch(r"/api/admin/articles/([\w-]+)", path)
                if m:
                    slug = m.group(1)
                    if method == "PUT":
                        data = self.read_json_body()
                        if data is None:
                            return self.send_json({"error": "请求体不是合法 JSON"}, 400)
                        return self._save_article(conn, slug, data)
                    if method == "DELETE":
                        cur = conn.execute("DELETE FROM articles WHERE slug=?", (slug,))
                        conn.commit()
                        if cur.rowcount == 0:
                            return self.send_json({"error": "文章不存在"}, 404)
                        audit_log("article-delete", slug, self.client_address[0])
                        return self.send_json({"ok": True, "deleted": slug})

                # ----- 分类管理 -----
                if method == "POST" and path == "/api/admin/categories":
                    data = self.read_json_body()
                    if data is None:
                        return self.send_json({"error": "请求体不是合法 JSON"}, 400)
                    slug = (data.get("slug") or "").strip()[:64]
                    name = (data.get("name") or "").strip()[:50]
                    desc = (data.get("description") or "").strip()[:300]
                    if not SLUG_RE.match(slug):
                        return self.send_json({"error": "slug 只能包含中文、字母、数字和中划线"}, 400)
                    if not name:
                        return self.send_json({"error": "分类名称不能为空"}, 400)
                    if conn.execute("SELECT id FROM categories WHERE slug=?", (slug,)).fetchone():
                        return self.send_json({"error": f"slug 已存在：{slug}"}, 400)
                    conn.execute("INSERT INTO categories (slug, name, description) VALUES (?,?,?)", (slug, name, desc))
                    conn.commit()
                    audit_log("category-create", slug, self.client_address[0])
                    return self.send_json({"ok": True, "message": f"已创建分类：{name}"})

                m = re.fullmatch(r"/api/admin/categories/([\w-]+)", path)
                if m:
                    slug = m.group(1)
                    if method == "PUT":
                        data = self.read_json_body()
                        if data is None:
                            return self.send_json({"error": "请求体不是合法 JSON"}, 400)
                        name = (data.get("name") or "").strip()[:50]
                        desc = (data.get("description") or "").strip()[:300]
                        if not name:
                            return self.send_json({"error": "分类名称不能为空"}, 400)
                        cur = conn.execute("UPDATE categories SET name=?, description=? WHERE slug=?", (name, desc, slug))
                        conn.commit()
                        if cur.rowcount == 0:
                            return self.send_json({"error": "分类不存在"}, 404)
                        return self.send_json({"ok": True, "message": f"已更新分类：{name}"})
                    if method == "DELETE":
                        count = conn.execute("SELECT COUNT(*) n FROM articles WHERE category_id=(SELECT id FROM categories WHERE slug=?)", (slug,)).fetchone()["n"]
                        if count:
                            return self.send_json({"error": f"该分类下还有 {count} 篇文章，请先移动文章再删除"}, 400)
                        cur = conn.execute("DELETE FROM categories WHERE slug=?", (slug,))
                        conn.commit()
                        if cur.rowcount == 0:
                            return self.send_json({"error": "分类不存在"}, 404)
                        audit_log("category-delete", slug, self.client_address[0])
                        return self.send_json({"ok": True, "deleted": slug})

                # ----- 标签管理 -----
                m = re.fullmatch(r"/api/admin/tags/([a-z0-9-]+)", path)
                if m and method == "DELETE":
                    tag_slug = m.group(1)
                    cur = conn.execute("DELETE FROM tags WHERE slug=?", (tag_slug,))
                    conn.commit()
                    if cur.rowcount == 0:
                        return self.send_json({"error": "标签不存在"}, 404)
                    return self.send_json({"ok": True, "deleted": tag_slug})

                # ----- 留言管理 -----
                if method == "GET" and path == "/api/admin/messages":
                    rows = [dict(r) for r in conn.execute(
                        "SELECT id, name, contact, content, reply, visible, created_at FROM messages ORDER BY id DESC")]
                    return self.send_json(rows)

                m = re.fullmatch(r"/api/admin/messages/(\d+)", path)
                if m:
                    mid = int(m.group(1))
                    if method == "PUT":
                        data = self.read_json_body()
                        if data is None:
                            return self.send_json({"error": "请求体不是合法 JSON"}, 400)
                        fields, params = [], []
                        if "reply" in data:
                            fields.append("reply=?")
                            params.append((data.get("reply") or "").strip()[:500])
                        if "visible" in data:
                            fields.append("visible=?")
                            params.append(1 if data.get("visible") else 0)
                        if not fields:
                            return self.send_json({"error": "没有需要更新的字段"}, 400)
                        params.append(mid)
                        cur = conn.execute(f"UPDATE messages SET {', '.join(fields)} WHERE id=?", params)
                        conn.commit()
                        if cur.rowcount == 0:
                            return self.send_json({"error": "留言不存在"}, 404)
                        audit_log("message-update", f"id={mid} fields={','.join(f.rstrip('=') for f in fields)}", self.client_address[0])
                        return self.send_json({"ok": True, "message": "已更新留言"})
                    if method == "DELETE":
                        cur = conn.execute("DELETE FROM messages WHERE id=?", (mid,))
                        conn.commit()
                        if cur.rowcount == 0:
                            return self.send_json({"error": "留言不存在"}, 404)
                        audit_log("message-delete", f"id={mid}", self.client_address[0])
                        return self.send_json({"ok": True, "deleted": mid})

                # ----- 站点设置 -----
                if method == "PUT" and path == "/api/admin/settings":
                    data = self.read_json_body()
                    if data is None:
                        return self.send_json({"error": "请求体不是合法 JSON"}, 400)
                    saved = 0
                    for key, value in data.items():
                        if key in DEFAULT_SETTINGS and isinstance(value, str):
                            if key == "about_content":
                                value = sanitize_html(value[:50000])  # 关于页富文本白名单清洗 + 长度上限
                            else:
                                value = value[:2000]
                            conn.execute("INSERT INTO settings (key, value) VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, value))
                            saved += 1
                    conn.commit()
                    audit_log("settings-update", f"{saved} 项", self.client_address[0])
                    return self.send_json({"ok": True, "message": f"已保存 {saved} 项设置"})

            return self.send_json({"error": "接口不存在"}, 404)
        except sqlite3.Error as exc:
            audit_log("db-error", f"{method} {path}: {exc}", self.client_address[0])
            return self.send_json({"error": "服务器内部错误，请稍后再试"}, 500)  # 不向客户端泄漏 SQL 细节
        finally:
            conn.close()

    def _save_article(self, conn, old_slug, data):
        raw_slug = (data.get("slug") or "").strip().lower().replace(" ", "-")[:64]
        title = (data.get("title") or "").strip()[:120]
        category = (data.get("category") or "").strip()[:64]
        summary = (data.get("summary") or "").strip()[:300]
        content = sanitize_html((data.get("content") or "").strip()[:300000])
        date = (data.get("date") or datetime.now().strftime("%Y-%m-%d")).strip()[:10]
        tags = [t.strip()[:50] for t in (data.get("tags") or [])[:20] if t.strip()]
        if not title:
            return self.send_json({"error": "标题不能为空"}, 400)
        cat = conn.execute("SELECT id FROM categories WHERE slug=? OR name=?", (category, category)).fetchone()
        if not cat:
            return self.send_json({"error": f"分类不存在：{category}"}, 400)
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", date):
            return self.send_json({"error": "日期格式应为 YYYY-MM-DD"}, 400)
        try:
            datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            return self.send_json({"error": f"日期不存在：{date}（例如 2026-02-30 是无效日期）"}, 400)

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
                return self.send_json({"error": f"slug 已被占用：{slug}（可留空让系统自动生成）"}, 400)
            slug = f"{raw_slug}-{i}"
        if not SLUG_RE.match(slug):
            return self.send_json({"error": "slug 只能包含中文、字母、数字和中划线"}, 400)
        try:
            if old_slug:
                cur = conn.execute(
                    """UPDATE articles SET slug=?, title=?, category_id=?, summary=?, content=?,
                       published_at=?, updated_at=datetime('now','localtime') WHERE slug=?""",
                    (slug, title, cat["id"], summary, content, date, old_slug))
                if cur.rowcount == 0:
                    return self.send_json({"error": "文章不存在"}, 404)
                article_id = conn.execute("SELECT id FROM articles WHERE slug=?", (slug,)).fetchone()["id"]
                conn.execute("DELETE FROM article_tags WHERE article_id=?", (article_id,))
            else:
                cur = conn.execute(
                    "INSERT INTO articles (slug,title,category_id,summary,content,published_at) VALUES (?,?,?,?,?,?)",
                    (slug, title, cat["id"], summary, content, date))
                article_id = cur.lastrowid
            for tag in tags:
                row = conn.execute("SELECT id FROM tags WHERE name=?", (tag,)).fetchone()
                tag_id = row["id"] if row else conn.execute(
                    "INSERT INTO tags (slug,name) VALUES (?,?)", ("t-" + hashlib.md5(tag.encode("utf-8")).hexdigest()[:10], tag)).lastrowid
                conn.execute("INSERT OR IGNORE INTO article_tags (article_id,tag_id) VALUES (?,?)", (article_id, tag_id))
            conn.commit()
            action = "更新" if old_slug else "创建"
            audit_log(f"article-{action}", slug, self.client_address[0])
            return self.send_json({
                "ok": True, "message": f"已{action}文章：{title}", "slug": slug,
                "url": f"/post-{slug}.html", "auto_slug": auto_slug,
            })
        except sqlite3.Error as exc:
            conn.rollback()
            audit_log("db-error", f"save-article {slug}: {exc}", self.client_address[0])
            return self.send_json({"error": "保存失败，请稍后再试"}, 500)

    # ---------- RSS ----------
    def handle_rss(self):
        conn = get_db()
        rows = conn.execute(
            "SELECT a.slug,a.title,a.summary,a.published_at FROM articles a ORDER BY a.published_at DESC LIMIT 20").fetchall()
        site_name = conn.execute("SELECT value FROM settings WHERE key='site_name'").fetchone()
        conn.close()
        site_name = (site_name["value"] if site_name else "") or "Y's Blog"
        esc = lambda s: html_mod.escape(s or "", quote=False)
        items = "".join(
            f"<item><title>{esc(r['title'])}</title>"
            f"<link>{BASE_URL}/post-{r['slug']}.html</link>"
            f"<description>{esc(r['summary'])}</description>"
            f"<pubDate>{r['published_at']}</pubDate><guid>/post-{r['slug']}.html</guid></item>"
            for r in rows)
        rss_title = site_name
        rss = (f'<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel>'
               f"<title>{esc(rss_title)}</title>"
               f"<link>{BASE_URL}/</link>"
               f"<description>记录思考，分享创造。</description>{items}</channel></rss>")
        body = rss.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/rss+xml; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    # ---------- 路由 ----------
    def do_GET(self):
        parsed = urlparse(self.path)
        path = unquote(parsed.path)
        if path.startswith("/api/"):
            return self.handle_api("GET")
        if path == "/rss.xml":
            return self.handle_rss()
        m = re.fullmatch(r"/post-([\w-]+)\.html", path)
        if m:
            html = render_post(m.group(1))
            if html is not None:
                return self.send_html(html)
            # 数据库里没有这篇文章 → 样式化 404
            return self.send_html(render_not_found(), 404)
        return super().do_GET()

    def do_POST(self):
        if urlparse(self.path).path.startswith("/api/"):
            return self.handle_api("POST")
        self.send_json({"error": "不支持的操作"}, 405)

    def do_PUT(self):
        if urlparse(self.path).path.startswith("/api/"):
            return self.handle_api("PUT")
        self.send_json({"error": "不支持的操作"}, 405)

    def do_DELETE(self):
        if urlparse(self.path).path.startswith("/api/"):
            return self.handle_api("DELETE")
        self.send_json({"error": "不支持的操作"}, 405)


def main():
    init_db()
    handler = partial(BlogHandler)
    print(f"Y's Blog 全栈服务已启动：http://localhost:{PORT}")
    print(f"管理后台：http://localhost:{PORT}/yy-AviuuP3r.html")
    print(f"管理令牌：{'来自 ADMIN_TOKEN 环境变量' if os.environ.get('ADMIN_TOKEN') else f'{ADMIN_TOKEN}'}")
    if _TOKEN_FILE.exists():
        print("[安全提示] 令牌保存在 .admin_token（已加入 .gitignore，不会被提交到仓库）；生产部署请改用 ADMIN_TOKEN 环境变量。")
    ThreadingHTTPServer(("0.0.0.0", PORT), handler).serve_forever()


if __name__ == "__main__":
    main()
