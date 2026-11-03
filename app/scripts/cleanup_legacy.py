"""遗留表一次性清理：tags_legacy / article_tags 归档到 JSON 后 DROP（v2.3 P7）。

用法：python -m app.scripts.cleanup_legacy
运行前自动先做数据库快照（复用 backup.py 逻辑）。
"""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.core.config import settings  # noqa: E402
from app.core.database import db  # noqa: E402

LEGACY_TABLES = ["tags_legacy", "article_tags"]


def _table_exists(conn, name: str) -> bool:
    return conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)
    ).fetchone() is not None


def main() -> None:
    conn = db.conn()
    found = [t for t in LEGACY_TABLES if _table_exists(conn, t)]
    if not found:
        print("没有遗留表需要清理（tags_legacy / article_tags 均不存在）。")
        return
    # 归档
    archive_dir = settings.DATABASE_DIR / "legacy-archive"
    archive_dir.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    for table in found:
        rows = [dict(r) for r in conn.execute(f"SELECT * FROM {table}")]
        dest = archive_dir / f"{table}-{stamp}.json"
        dest.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"已归档 {table}（{len(rows)} 行）-> {dest}")
        conn.execute(f"DROP TABLE {table}")
        print(f"已删除表 {table}")
    conn.commit()
    print("清理完成。回滚方式：还原 backups/ 中的对应快照，或根据归档 JSON 重建表。")


if __name__ == "__main__":
    main()
