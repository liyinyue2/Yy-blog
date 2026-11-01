"""认证路由：登录（双令牌）/ 刷新 / 登出 / 当前用户。"""
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from app.core.audit import audit_log
from app.core.database import db
from app.core.ratelimit import client_ip, rate_hit, rate_limited
from app.core.security import (create_access_token, create_refresh_token,
                               decode_token, get_current_user, verify_password)

router = APIRouter(prefix="/api/auth", tags=["auth"])

# 登录失败限流：同 IP 15 分钟内错 5 次锁定（复用 v1.0 纪律）
LIMIT_LOGIN_FAIL = (15 * 60, 5)


class LoginBody(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=128)


class RefreshBody(BaseModel):
    refresh_token: str = Field(min_length=10, max_length=2048)


@router.post("/login")
def login(body: LoginBody, request: Request):
    ip = client_ip(request)
    # 锁定判断与失败记录分离：只统计失败尝试，成功登录不占额度（与 v1.0 语义一致）
    if rate_limited(f"login-fail:{ip}", *LIMIT_LOGIN_FAIL):
        audit_log("login-locked", body.username, ip)
        raise HTTPException(status_code=429, detail="失败次数过多，请 15 分钟后再试")

    user = db.conn().execute(
        "SELECT id, username, password_hash, role FROM users WHERE username = ?",
        (body.username,),
    ).fetchone()

    if user is None or not verify_password(body.password, user["password_hash"]):
        rate_hit(f"login-fail:{ip}", *LIMIT_LOGIN_FAIL)
        audit_log("login-fail", body.username, ip)
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    audit_log("login-ok", f"role={user['role']}", ip, user=user["username"])
    return {
        "access_token": create_access_token(user),
        "refresh_token": create_refresh_token(user),
        "token_type": "Bearer",
        "expires_in": 15 * 60,
    }


@router.post("/refresh")
def refresh(body: RefreshBody, request: Request):
    ip = client_ip(request)
    payload = decode_token(body.refresh_token, "refresh")   # 无效/过期抛 401
    user = db.conn().execute(
        "SELECT id, username, password_hash, role FROM users WHERE username = ?",
        (payload.get("sub", ""),),
    ).fetchone()
    if user is None:
        raise HTTPException(status_code=401, detail="用户不存在")
    return {
        "access_token": create_access_token(user),
        "refresh_token": create_refresh_token(user),
        "token_type": "Bearer",
        "expires_in": 15 * 60,
    }


@router.post("/logout")
def logout(request: Request, user: dict = Depends(get_current_user)):
    # JWT 无状态：登出即客户端丢弃令牌；此处仅留审计痕迹
    audit_log("logout", "-", client_ip(request), user=user["username"])
    return {"ok": True, "message": "已登出"}


@router.get("/me")
def me(user: dict = Depends(get_current_user)):
    return user
