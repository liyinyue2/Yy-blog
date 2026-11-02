"""v2.0 幂等数据库迁移：CREATE TABLE IF NOT EXISTS，可重复执行。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.core.database import db  # noqa: E402

BLOG_SCHEMA = [
    """CREATE TABLE IF NOT EXISTS categories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        slug TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        description TEXT DEFAULT ''
    )""",
    """CREATE TABLE IF NOT EXISTS articles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        slug TEXT UNIQUE NOT NULL,
        title TEXT NOT NULL,
        category_id INTEGER NOT NULL REFERENCES categories(id),
        summary TEXT DEFAULT '',
        content TEXT DEFAULT '',
        published_at TEXT NOT NULL,
        views INTEGER DEFAULT 0,
        created_at TEXT DEFAULT (datetime('now', 'localtime')),
        updated_at TEXT DEFAULT (datetime('now', 'localtime'))
    )""",
    """CREATE TABLE IF NOT EXISTS subscribers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE NOT NULL,
        created_at TEXT DEFAULT (datetime('now', 'localtime'))
    )""",
    """CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        contact TEXT DEFAULT '',
        content TEXT NOT NULL,
        reply TEXT DEFAULT '',
        visible INTEGER DEFAULT 1,
        created_at TEXT DEFAULT (datetime('now', 'localtime'))
    )""",
    """CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT DEFAULT ''
    )""",
]

INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_articles_published ON articles(published_at)",
    "CREATE INDEX IF NOT EXISTS idx_taggables_entity ON taggables(entity_type, entity_id)",
    "CREATE INDEX IF NOT EXISTS idx_messages_visible ON messages(visible, id)",
]

SEED_CATEGORIES = [
    ("frontend", "前端开发", "组件、交互、性能，以及让产品更好用的工程细节。"),
    ("design", "UI 设计", "视觉秩序、留白、节奏与界面里那些看不见的情绪。"),
    ("life", "个人成长", "关于工作方式、长期主义，以及如何与自己相处。"),
]

MIGRATIONS = [
    """CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'admin',
        created_at TEXT NOT NULL
    )""",
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

PROJECT_MIGRATIONS = [
    """CREATE TABLE IF NOT EXISTS projects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        slug TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        summary TEXT DEFAULT '',
        description TEXT DEFAULT '',
        tech_stack TEXT DEFAULT '[]',
        status TEXT NOT NULL DEFAULT 'idea'
            CHECK (status IN ('idea','building','maintained','archived')),
        repo_url TEXT DEFAULT '',
        demo_url TEXT DEFAULT '',
        progress INTEGER NOT NULL DEFAULT 0,
        cover_path TEXT DEFAULT '',
        sort INTEGER NOT NULL DEFAULT 0,
        visibility TEXT NOT NULL DEFAULT 'public'
            CHECK (visibility IN ('public','private')),
        created_at TEXT DEFAULT (datetime('now','localtime')),
        updated_at TEXT DEFAULT (datetime('now','localtime'))
    )""",
    """CREATE TABLE IF NOT EXISTS project_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
        title TEXT DEFAULT '',
        content TEXT DEFAULT '',
        log_date TEXT NOT NULL,
        created_at TEXT DEFAULT (datetime('now','localtime'))
    )""",
    "CREATE INDEX IF NOT EXISTS idx_project_logs_project ON project_logs(project_id)",
]

POMODORO_MIGRATIONS = [
    """CREATE TABLE IF NOT EXISTS pomodoro_sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        label TEXT DEFAULT '',
        minutes INTEGER NOT NULL DEFAULT 25,
        completed INTEGER NOT NULL DEFAULT 0,
        started_at TEXT NOT NULL
    )""",
]

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

# 仅清理曾误建到主库的工作台/音乐表。files 属于主库，绝不能 DROP。
MAIN_CLEANUP = [
    "DROP TABLE IF EXISTS notes",
    "DROP TABLE IF EXISTS todos",
    "DROP TABLE IF EXISTS bookmarks",
    "DROP TABLE IF EXISTS tracks",
]


def _table_exists(conn, name: str) -> bool:
    return conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)
    ).fetchone() is not None


def _migrate_legacy_tags(conn) -> None:
    """v1 旧 tags 表带 slug 列；v2 统一标签体系仅 (id, name)。"""
    cols = [r[1] for r in conn.execute("PRAGMA table_info(tags)")]
    if not cols or "slug" not in cols:
        return
    conn.execute("ALTER TABLE tags RENAME TO tags_legacy")
    conn.execute("CREATE TABLE tags (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE NOT NULL)")
    conn.execute("DROP TABLE IF EXISTS taggables")
    conn.execute("""CREATE TABLE taggables (
        tag_id INTEGER NOT NULL,
        entity_type TEXT NOT NULL,
        entity_id INTEGER NOT NULL,
        UNIQUE(tag_id, entity_type, entity_id),
        FOREIGN KEY(tag_id) REFERENCES tags(id) ON DELETE CASCADE
    )""")
    conn.execute("INSERT OR IGNORE INTO tags (id, name) SELECT id, name FROM tags_legacy")
    if _table_exists(conn, "article_tags"):
        conn.execute(
            "INSERT OR IGNORE INTO taggables (tag_id, entity_type, entity_id) "
            "SELECT tag_id, 'article', article_id FROM article_tags")
    conn.commit()
    n = conn.execute("SELECT COUNT(*) n FROM taggables").fetchone()["n"]
    print(f"[migrate] 旧标签体系已迁移：tags_legacy 归档，taggables 关联 {n} 条")


def _seed(conn) -> None:
    from app.modules.blog.service import DEFAULT_SETTINGS
    if conn.execute("SELECT COUNT(*) n FROM categories").fetchone()["n"] == 0:
        conn.executemany(
            "INSERT INTO categories (slug, name, description) VALUES (?,?,?)",
            SEED_CATEGORIES,
        )
    for key, value in DEFAULT_SETTINGS.items():
        conn.execute(
            "INSERT OR IGNORE INTO settings (key, value) VALUES (?,?)",
            (key, value),
        )


def _ensure_track_visibility(conn) -> None:
    """v2.1：tracks.visibility 字段幂等保障。

    单独的迁移脚本在进程被硬杀时可能随未 checkpoint 的 WAL 一起丢失，
    因此在每次启动迁移中做条件 ALTER，保证字段必然存在（自愈）。
    """
    cols = {r[1] for r in conn.execute("PRAGMA music.table_info(tracks)")}
    if "visibility" not in cols:
        conn.execute(
            "ALTER TABLE music.tracks ADD COLUMN visibility TEXT NOT NULL DEFAULT 'public'"
            " CHECK (visibility IN ('public', 'private'))"
        )


def _ensure_article_kind(conn) -> None:
    """v2.2 P1：articles.kind 字段幂等保障（article/note），启动自愈。"""
    cols = {r[1] for r in conn.execute("PRAGMA table_info(articles)")}
    if "kind" not in cols:
        conn.execute(
            "ALTER TABLE articles ADD COLUMN kind TEXT NOT NULL DEFAULT 'article'"
            " CHECK (kind IN ('article', 'note'))"
        )


def _ensure_todo_fields(conn) -> None:
    """v2.3 P3：workspace.todos 增强字段（due 到期日 / priority 优先级），启动自愈。"""
    cols = {r[1] for r in conn.execute("PRAGMA workspace.table_info(todos)")}
    if "due" not in cols:
        conn.execute("ALTER TABLE workspace.todos ADD COLUMN due TEXT NOT NULL DEFAULT ''")
    if "priority" not in cols:
        conn.execute("ALTER TABLE workspace.todos ADD COLUMN priority INTEGER NOT NULL DEFAULT 0")


def run(quiet: bool = False) -> None:
    db.init()
    conn = db.conn()
    for sql in BLOG_SCHEMA:
        conn.execute(sql)
    _migrate_legacy_tags(conn)
    for sql in MAIN_CLEANUP:
        conn.execute(sql)
    for sql in MIGRATIONS:
        conn.execute(sql)
    for sql in PROJECT_MIGRATIONS:
        conn.execute(sql)
    for sql in WORKSPACE_MIGRATIONS:
        conn.execute(sql)
    for sql in MUSIC_MIGRATIONS:
        conn.execute(sql)
    for sql in POMODORO_MIGRATIONS:
        conn.execute(sql)
    _ensure_track_visibility(conn)
    _ensure_article_kind(conn)
    _ensure_todo_fields(conn)
    for sql in INDEXES:
        conn.execute(sql)
    _seed(conn)
    conn.commit()
    if not quiet:
        print("迁移完成：blog 核心表 + users/tags/taggables/files + workspace + music")


if __name__ == "__main__":
    run()
