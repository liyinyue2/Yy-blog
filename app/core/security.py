"""认证核心：JWT 双令牌签发/校验 + RBAC 依赖 + 密码哈希。"""
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException, Request
from passlib.context import CryptContext

from app.core.config import settings
from app.core.database import db

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

CREDENTIALS_ERROR = HTTPException(status_code=401, detail="令牌无效或已过期",
                                  headers={"WWW-Authenticate": "Bearer"})


# ---------- 密码 ----------
def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return pwd_context.verify(plain, hashed)
    except Exception:
        return False


# ---------- JWT ----------
def _create_token(username: str, role: str, kind: str, lifetime: timedelta) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": username,
        "role": role,
        "typ": kind,                      # access | refresh
        "iat": int(now.timestamp()),
        "exp": int((now + lifetime).timestamp()),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def create_access_token(user) -> str:
    return _create_token(user["username"], user["role"], "access",
                         timedelta(minutes=settings.ACCESS_TOKEN_MINUTES))


def create_refresh_token(user) -> str:
    return _create_token(user["username"], user["role"], "refresh",
                         timedelta(days=settings.REFRESH_TOKEN_DAYS))


def decode_token(token: str, expected_type: str = "access") -> dict:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="令牌已过期，请重新登录")
    except jwt.PyJWTError:
        raise CREDENTIALS_ERROR
    if payload.get("typ") != expected_type:
        raise CREDENTIALS_ERROR
    return payload


# ---------- 用户 ----------
def _get_user(username: str):
    return db.conn().execute(
        "SELECT id, username, password_hash, role FROM users WHERE username = ?", (username,)
    ).fetchone()


# ---------- FastAPI 依赖 ----------
def get_current_user(request: Request) -> dict:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise CREDENTIALS_ERROR
    payload = decode_token(auth[7:], "access")
    user = _get_user(payload.get("sub", ""))
    if user is None:
        raise CREDENTIALS_ERROR
    return {"id": user["id"], "username": user["username"], "role": user["role"]}


def require_role(role: str):
    """依赖工厂：要求当前用户具备指定角色。"""
    def checker(user: dict = Depends(get_current_user)) -> dict:
        if user["role"] != role:
            raise HTTPException(status_code=403, detail="权限不足")
        return user
    return checker


require_admin = require_role("admin")
