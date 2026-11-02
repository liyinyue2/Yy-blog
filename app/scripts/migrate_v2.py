"""v2.0 幂等数据库迁移：CREATE TABLE IF NOT EXISTS，可重复执行。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.core.database import db  # noqa: E402

MIGRATIONS = [
    # Phase 2：用户表
    """CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'admin',
        created_at TEXT NOT NULL
    )""",
    # Phase 4：统一标签体系
    """CREATE TABLE IF NOT EXISTS tags (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS taggables (
        tag_id INTEGER NOT NULL,
        entity_type TEXT NOT NULL,
        entity_id INTEGER NOT NULL,
        UNIQUE(tag_id, entity_type, entity_id),
        FOREIGN KEY(tag_id) REFERENCES tags(id) ON DELETE CASCADE
    )""",
    # Phase 7：网盘文件表（主库）
    """CREATE TABLE IF NOT EXISTS files (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        uuid_name TEXT UNIQUE NOT NULL,
        original_name TEXT NOT NULL,
        size INTEGER NOT NULL,
        mime TEXT NOT NULL,
        uploader_id INTEGER,
        created_at TEXT NOT NULL
    )""",
]

# workspace.db（Phase 5）—— ATTACH 为 workspace schema，建表语句必须带前缀
WORKSPACE_MIGRATIONS = [
    """CREATE TABLE IF NOT EXISTS workspace.notes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL DEFAULT '',
        content TEXT NOT NULL DEFAULT '',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS workspace.todos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        content TEXT NOT NULL,
        done INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS workspace.bookmarks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        url TEXT NOT NULL,
        created_at TEXT NOT NULL
    )""",
]

# music.db（Phase 6）—— ATTACH 为 music schema
MUSIC_MIGRATIONS = [
    """CREATE TABLE IF NOT EXISTS music.tracks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        artist TEXT NOT NULL DEFAULT '',
        album TEXT NOT NULL DEFAULT '',
        duration REAL NOT NULL DEFAULT 0,
        file_path TEXT NOT NULL,
        cover_path TEXT,
        created_at TEXT NOT NULL
    )""",
]

# 清理历史版本误建到主库的表（幂等）
MAIN_CLEANUP = [
    "DROP TABLE IF EXISTS notes",
    "DROP TABLE IF EXISTS todos",
    "DROP TABLE IF EXISTS bookmarks",
    "DROP TABLE IF EXISTS tracks", "DROP TABLE IF EXISTS files",
    "DROP TABLE IF EXISTS files",
]


def _migrate_legacy_tags(conn) -> None:
    """v1 旧 tags 表带 slug 列；v2 统一标签体系仅 (id, name)。

    幂等：检测到旧 schema 时，迁移为 tags_legacy + 新 tags + taggables（article 关系一并转入）。
    """
    cols = [r[1] for r in conn.execute("PRAGMA table_info(tags)")]
    if not cols or "slug" not in cols:
        return  # 新 schema 或空库，无需迁移
    conn.execute("ALTER TABLE tags RENAME TO tags_legacy")
    conn.execute("CREATE TABLE tags (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE NOT NULL)")
    # 重建 taggables：RENAME 会把旧表的 FK 引用一并改指 tags_legacy，必须删掉重建才能指向新 tags
    conn.execute("DROP TABLE IF EXISTS taggables")
    conn.execute("""CREATE TABLE taggables (
        tag_id INTEGER NOT NULL,
        entity_type TEXT NOT NULL,
        entity_id INTEGER NOT NULL,
        UNIQUE(tag_id, entity_type, entity_id),
        FOREIGN KEY(tag_id) REFERENCES tags(id) ON DELETE CASCADE
    )""")
    # 保留原 id，迁移历史标签与文章关联
    conn.execute("INSERT OR IGNORE INTO tags (id, name) SELECT id, name FROM tags_legacy")
    conn.execute(
        "INSERT OR IGNORE INTO taggables (tag_id, entity_type, entity_id) "
        "SELECT tag_id, 'article', article_id FROM article_tags")
    conn.commit()
    n = conn.execute("SELECT COUNT(*) n FROM taggables").fetchone()["n"]
    print(f"[migrate] 旧标签体系已迁移：tags_legacy 归档，taggables 关联 {n} 条")


def run() -> None:
    db.init()
    conn = db.conn()
    _migrate_legacy_tags(conn)
    for sql in MAIN_CLEANUP:
        conn.execute(sql)
    for sql in MIGRATIONS:
        conn.execute(sql)
    for sql in WORKSPACE_MIGRATIONS:
        conn.execute(sql)
    for sql in MUSIC_MIGRATIONS:
        conn.execute(sql)
    conn.commit()
    print("迁移完成：users/tags/taggables (blog.db) + notes/todos/bookmarks (workspace) + tracks/files (music)")


if __name__ == "__main__":
    run()
