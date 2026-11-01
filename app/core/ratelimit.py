"""内存滑动窗口限流（复用 v1.0 逻辑，并加桶总量上限防内存膨胀）。"""
import threading
import time

from app.core.config import settings

_buckets: dict[str, list[float]] = {}
_lock = threading.Lock()
_MAX_KEYS = 4096  # 超过后清理全部已过期桶，防恶意刷量撑爆内存


def rate_hit(key: str, window_seconds: int, max_hits: int) -> bool:
    """记录一次访问；窗口内已达上限返回 True（应拒绝）。"""
    now = time.monotonic()
    with _lock:
        if len(_buckets) > _MAX_KEYS:
            cutoff = now - window_seconds
            for k in [k for k, hits in _buckets.items() if not hits or hits[-1] < cutoff]:
                _buckets.pop(k, None)
        hits = _buckets.setdefault(key, [])
        cutoff = now - window_seconds
        while hits and hits[0] < cutoff:
            hits.pop(0)
        if len(hits) >= max_hits:
            return True
        hits.append(now)
        return False


def client_ip(request) -> str:
    """取客户端真实 IP（Nginx 反代场景优先 X-Real-IP）。"""
    real = request.headers.get("X-Real-IP")
    if real:
        return real
    fwd = request.headers.get("X-Forwarded-For")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "-"
