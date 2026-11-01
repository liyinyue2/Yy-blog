"""审计日志：格式与 v1.0 完全一致（时间 | IP | 动作 | 详情）。"""
import threading
from datetime import datetime
from pathlib import Path

from app.core.config import settings

_lock = threading.Lock()


def audit_log(action: str, detail: str = "", ip: str = "-", user: str = "-") -> None:
    """写一条审计日志；日志失败不影响主业务。"""
    try:
        log_path: Path = settings.LOG_DIR / "audit.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        line = f"{datetime.now().isoformat(timespec='seconds')} | {ip} | {user} | {action} | {detail}\n"
        with _lock, open(log_path, "a", encoding="utf-8") as f:
            f.write(line)
    except OSError:
        pass
