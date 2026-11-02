"""审计日志在线查看：读取 logs/audit.log，倒序分页 + 关键词过滤（require_admin）。"""
from fastapi import APIRouter, Depends, HTTPException

from app.core.config import settings
from app.core.security import require_admin

router = APIRouter(prefix="/api/admin", tags=["audit"])

MAX_SCAN_LINES = 5000


@router.get("/audit")
def view_audit(limit: int = 50, offset: int = 0, q: str = "",
               user: dict = Depends(require_admin)):
    limit = max(1, min(limit, 200))
    offset = max(0, offset)
    keyword = (q or "").strip().lower()
    log_path = settings.LOG_DIR / "audit.log"
    if not log_path.exists():
        return {"items": [], "total": 0}
    try:
        with open(log_path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()[-MAX_SCAN_LINES:]
    except OSError:
        raise HTTPException(status_code=500, detail="审计日志读取失败")
    items = []
    for line in reversed(lines):          # 新的在前
        line = line.rstrip("\n")
        if not line:
            continue
        parts = [p.strip() for p in line.split("|", 4)]
        while len(parts) < 5:
            parts.append("")
        row = {"time": parts[0], "ip": parts[1], "user": parts[2],
               "action": parts[3], "detail": parts[4]}
        if keyword and keyword not in line.lower():
            continue
        items.append(row)
    return {"items": items[offset:offset + limit], "total": len(items),
            "limit": limit, "offset": offset}
