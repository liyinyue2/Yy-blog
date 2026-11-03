"""v2.1 音乐模块迁移：tracks 表新增 visibility 字段（幂等，可重复执行）。

- 执行前先将 music.db 在线备份到 data/backups/music-pre-v2.1.db
- 已通过 PRAGMA table_info 判断字段存在则跳过，禁止手改数据库
- 回滚：删除字段不可行（SQLite 限制），直接用备份文件覆盖 music.db
"""
import os
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

try:  # 完整环境（Docker / venv）走统一配置
    from app.core.config import settings  # noqa: E402
    _DB_DIR = settings.DATABASE_DIR
except ModuleNotFoundError:  # 裸机最小环境：仅 sqlite3 迁移，路径取环境变量或默认
    _DB_DIR = Path(os.environ.get("DATABASE_DIR", "data"))

BACKUP_PATH = _DB_DIR / "backups" / "music-pre-v2.1.db"


def _backup(src: Path) -> None:
    """SQLite 在线备份 API：WAL 模式下也能拿到一致快照。"""
    BACKUP_PATH.parent.mkdir(parents=True, exist_ok=True)
    src_conn = sqlite3.connect(src, timeout=15)
    dst_conn = sqlite3.connect(BACKUP_PATH, timeout=15)
    try:
        src_conn.backup(dst_conn)
    finally:
        dst_conn.close()
        src_conn.close()


def run() -> bool:
    """返回 True 表示执行了迁移，False 表示字段已存在跳过。"""
    db_path = _DB_DIR / "music.db"
    if not db_path.exists():
        print(f"跳过：{db_path} 不存在（首次启动时由应用创建）")
        return False

    conn = sqlite3.connect(db_path, timeout=15)
    try:
        cols = {row[1] for row in conn.execute("PRAGMA table_info(tracks)")}
        if "visibility" in cols:
            print("跳过：tracks.visibility 已存在")
            return False

        _backup(db_path)
        print(f"备份完成：{BACKUP_PATH}")

        conn.execute(
            "ALTER TABLE tracks ADD COLUMN visibility TEXT NOT NULL DEFAULT 'public'"
            " CHECK (visibility IN ('public', 'private'))"
        )
        conn.commit()
        print("迁移完成：tracks.visibility 已添加（默认 public）")
        return True
    finally:
        conn.close()


if __name__ == "__main__":
    run()
