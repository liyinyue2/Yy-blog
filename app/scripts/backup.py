"""数据库备份脚本：三库全部 .backup 到 backups/ 目录（可用 cron 定时执行）。

用法：python -m app.scripts.backup
服务器部署后建议 cron：0 3 * * * cd /opt/ysblog && ./venv/bin/python -m app.scripts.backup
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.core.config import settings  # noqa: E402

DATABASES = ["blog.db", "workspace.db", "music.db"]


def main() -> None:
    import sqlite3

    backup_dir = Path("backups")
    backup_dir.mkdir(exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    for name in DATABASES:
        src = settings.DATABASE_DIR / name
        if not src.exists():
            continue
        dest = backup_dir / f"{name.replace('.db', '')}-{stamp}.db"
        src_conn = sqlite3.connect(src)
        dst_conn = sqlite3.connect(dest)
        with dst_conn:
            src_conn.backup(dst_conn)
        dst_conn.close()
        src_conn.close()
        print(f"已备份 {name} -> {dest}")
    # 只保留最近 14 份
    backups = sorted(backup_dir.glob("*.db"))
    for old in backups[:-42]:
        old.unlink()
        print(f"清理过期备份: {old.name}")


if __name__ == "__main__":
    main()
