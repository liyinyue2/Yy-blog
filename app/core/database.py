"""SQLite 连接管理：WAL + 外键 + ATTACH 多库。

- blog.db  主库（博客数据 + users + tags）
- workspace.db / music.db 以 schema 名 ATTACH 到每个连接
- 连接按线程隔离（thread-local），FastAPI 线程池下安全复用
"""
import sqlite3
import threading
from pathlib import Path

from app.core.config import settings

_ATTACHED = {"workspace": "workspace.db", "music": "music.db"}


class DatabaseManager:
    def __init__(self) -> None:
        self._local = threading.local()
        self._lock = threading.Lock()
        self._ready = False

    # ---------- 初始化 ----------
    def init(self) -> None:
        settings.ensure_dirs()
        with self._lock:
            if self._ready:
                return
            for name in ("blog.db", "workspace.db", "music.db"):
                conn = self._new_connection(settings.DATABASE_DIR / name, attach=False)
                conn.execute("PRAGMA journal_mode=WAL")
                conn.close()
            self._ready = True

    def _new_connection(self, path: Path, attach: bool = True) -> sqlite3.Connection:
        conn = sqlite3.connect(path, timeout=15)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA busy_timeout=10000")
        if attach:
            for schema, fname in _ATTACHED.items():
                conn.execute(
                    f"ATTACH DATABASE ? AS {schema}",
                    (str(settings.DATABASE_DIR / fname),),
                )
        return conn

    # ---------- 线程本地连接 ----------
    def conn(self) -> sqlite3.Connection:
        """主库连接（blog.db），已 ATTACH workspace / music 两个 schema。"""
        conn = getattr(self._local, "conn", None)
        if conn is None:
            settings.DATABASE_DIR.mkdir(parents=True, exist_ok=True)
            conn = self._new_connection(settings.DATABASE_DIR / "blog.db")
            self._local.conn = conn
        return conn

    def close_thread(self) -> None:
        conn = getattr(self._local, "conn", None)
        if conn is not None:
            conn.close()
            self._local.conn = None


db = DatabaseManager()
