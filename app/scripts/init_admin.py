"""创建初始管理员账号：从环境变量 ADMIN_USERNAME / ADMIN_PASSWORD 读取。

密码只在本脚本运行瞬间使用，绝不写入代码或文档。幂等：账号已存在则跳过。
用法：python -m app.scripts.init_admin
"""
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.core.config import settings  # noqa: E402
from app.core.database import db  # noqa: E402
from app.core.security import hash_password  # noqa: E402


def main() -> None:
    db.init()
    conn = db.conn()
    conn.execute(
        """CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'admin',
            created_at TEXT NOT NULL
        )"""
    )

    username = settings.ADMIN_USERNAME
    password = settings.ADMIN_PASSWORD
    if not password:
        print("错误：请通过环境变量 ADMIN_PASSWORD 提供初始密码（不得硬编码）")
        sys.exit(1)

    exists = conn.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()
    if exists:
        print(f"账号 {username} 已存在，跳过")
        return

    conn.execute(
        "INSERT INTO users (username, password_hash, role, created_at) VALUES (?,?,?,?)",
        (username, hash_password(password), "admin", datetime.now().isoformat(timespec="seconds")),
    )
    conn.commit()
    print(f"已创建管理员账号：{username}（bcrypt 哈希存储）")


if __name__ == "__main__":
    main()
