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
]

# workspace.db（Phase 5）
WORKSPACE_MIGRATIONS = [
    """CREATE TABLE IF NOT EXISTS notes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL DEFAULT '',
        content TEXT NOT NULL DEFAULT '',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS todos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        content TEXT NOT NULL,
        done INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS bookmarks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        url TEXT NOT NULL,
        created_at TEXT NOT NULL
    )""",
]

# music.db（Phase 6）
MUSIC_MIGRATIONS = [
    """CREATE TABLE IF NOT EXISTS tracks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        artist TEXT NOT NULL DEFAULT '',
        album TEXT NOT NULL DEFAULT '',
        duration REAL NOT NULL DEFAULT 0,
        file_path TEXT NOT NULL,
        cover_path TEXT,
        created_at TEXT NOT NULL
    )""",
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


def run() -> None:
    db.init()
    conn = db.conn()
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
