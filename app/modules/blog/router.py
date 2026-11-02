"""博客路由：公开只读 + 管理写（JWT RBAC），接口行为镜像 v1.0。"""
import re

from fastapi import APIRouter, Body, Depends, HTTPException, Request, Response
from fastapi.responses import HTMLResponse

from app.core.audit import audit_log
from app.core.config import settings
from app.core.ratelimit import client_ip, rate_hit
from app.core.security import require_admin
from app.modules.blog import convert, service
from app.modules.blog.models import (ArticleBody, CategoryBody, CategoryUpdateBody,
                                     ConvertBody, MessagePostBody, MessageUpdateBody,
                                     SubscribeBody)
from app.modules.blog.templates import parse_post_path, render_not_found, render_post

router = APIRouter(tags=["blog"])

# 限流策略（与 v1.0 一致）
LIMIT_MESSAGE = (60, 5)
LIMIT_SUBSCRIBE = (60, 5)


# ---------- 文章详情页（动态渲染，/rss.xml 由 Nginx 映射到 /api/rss） ----------
@router.get("/post-{post_path:path}", include_in_schema=False)
def post_page(post_path: str):
    m = re.fullmatch(r"([\w-]+)\.html", post_path)
    if not m:
        raise HTTPException(status_code=404)
    try:
        return HTMLResponse(render_post(m.group(1)))
    except HTTPException:
        return HTMLResponse(render_not_found(), status_code=404)


# ---------- 公开只读 ----------
@router.get("/api/articles")
def articles(q: str = "", category: str = "", tag: str = "", kind: str = ""):
    return service.list_articles(q=q, category=category, tag=tag, kind=kind)


@router.get("/api/articles/{slug}")
def article_detail(slug: str):
    return service.get_article(slug)


@router.get("/api/categories")
def categories():
    return service.list_categories()


@router.get("/api/messages")
def messages():
    return service.list_public_messages()


@router.post("/api/messages")
def post_message(body: MessagePostBody, request: Request):
    ip = client_ip(request)
    if rate_hit(f"msg:{ip}", *LIMIT_MESSAGE):
        raise HTTPException(status_code=429, detail="操作太频繁了，请稍后再试")
    return service.create_message(body.name, body.contact, body.content)


@router.post("/api/subscribe")
def subscribe(body: SubscribeBody, request: Request):
    ip = client_ip(request)
    if rate_hit(f"sub:{ip}", *LIMIT_SUBSCRIBE):
        raise HTTPException(status_code=429, detail="操作太频繁了，请稍后再试")
    return service.subscribe(body.email)


@router.get("/api/settings")
def settings_public():
    return service.get_settings()


@router.get("/api/rss", include_in_schema=False)
@router.get("/rss.xml", include_in_schema=False)
def rss():
    return Response(content=service.rss_xml(settings.BASE_URL),
                    media_type="application/rss+xml; charset=utf-8")


# ---------- 管理接口（JWT RBAC，替代 v1.0 的 X-Admin-Token） ----------
@router.get("/api/stats")
def admin_stats(user: dict = Depends(require_admin)):
    return service.admin_stats()


@router.get("/api/admin/articles")
def admin_articles(user: dict = Depends(require_admin)):
    return service.admin_list_articles()


@router.post("/api/admin/articles")
def admin_create_article(body: ArticleBody, request: Request, user: dict = Depends(require_admin)):
    return service.save_article(None, body, user["username"], client_ip(request))


@router.put("/api/admin/articles/{slug}")
def admin_update_article(slug: str, body: ArticleBody, request: Request,
                         user: dict = Depends(require_admin)):
    return service.save_article(slug, body, user["username"], client_ip(request))


@router.delete("/api/admin/articles/{slug}")
def admin_delete_article(slug: str, request: Request, user: dict = Depends(require_admin)):
    return service.delete_article(slug, user["username"], client_ip(request))


@router.post("/api/admin/convert")
def admin_convert(body: ConvertBody, request: Request, user: dict = Depends(require_admin)):
    ip = client_ip(request)
    raw = convert.decode_upload(body.filename, body.data)
    stem = body.filename.rsplit(".", 1)[0].strip() or "未命名文章"
    try:
        title, content = convert.parse_document(body.filename, raw)
    except ImportError as exc:
        audit_log("convert-error", f"缺少解析库: {exc}", ip, user=user["username"])
        raise HTTPException(status_code=500, detail="服务器未安装文档解析库，请联系管理员")
    except HTTPException:
        raise
    except Exception as exc:
        audit_log("convert-error", f"{body.filename}: {type(exc).__name__}: {exc}", ip, user=user["username"])
        raise HTTPException(status_code=400, detail="文件解析失败，请确认文件未损坏后重试")
    if not title:
        title = stem
    if not content.strip():
        raise HTTPException(status_code=400, detail="无法从该文件中提取到文本内容（可能是扫描件或空文档）")
    return {"ok": True, "title": title.strip() or stem, "content": content,
            "chars": len(re.sub(r"<[^>]+>", "", content))}


@router.post("/api/admin/categories")
def admin_create_category(body: CategoryBody, request: Request, user: dict = Depends(require_admin)):
    return service.create_category(body, user["username"], client_ip(request))


@router.put("/api/admin/categories/{slug}")
def admin_update_category(slug: str, body: CategoryUpdateBody, request: Request,
                          user: dict = Depends(require_admin)):
    return service.update_category(slug, body, user["username"], client_ip(request))


@router.delete("/api/admin/categories/{slug}")
def admin_delete_category(slug: str, request: Request, user: dict = Depends(require_admin)):
    return service.delete_category(slug, user["username"], client_ip(request))


@router.get("/api/admin/messages")
def admin_messages(user: dict = Depends(require_admin)):
    return service.admin_list_messages()


@router.put("/api/admin/messages/{mid}")
def admin_update_message(mid: int, body: MessageUpdateBody, request: Request,
                         user: dict = Depends(require_admin)):
    return service.admin_update_message(mid, body.reply, body.visible,
                                        user["username"], client_ip(request))


@router.delete("/api/admin/messages/{mid}")
def admin_delete_message(mid: int, request: Request, user: dict = Depends(require_admin)):
    return service.admin_delete_message(mid, user["username"], client_ip(request))


@router.get("/api/admin/subscribers")
def admin_subscribers(user: dict = Depends(require_admin)):
    return service.admin_list_subscribers()


@router.delete("/api/admin/subscribers/{sid}")
def admin_delete_subscriber(sid: int, request: Request, user: dict = Depends(require_admin)):
    return service.admin_delete_subscriber(sid, user["username"], client_ip(request))


@router.put("/api/admin/settings")
def admin_settings_update(request: Request, payload: dict[str, str] = Body(...),
                          user: dict = Depends(require_admin)):
    """站点设置：字段白名单与清洗规则在 service 层执行。"""
    return service.update_settings(payload, user["username"], client_ip(request))
