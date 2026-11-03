"""Y's Blog v2.0 — 应用配置。

所有配置经 pydantic-settings 从环境变量读取，代码中零硬编码密钥。
"""
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # 服务
    PORT: int = 8000                      # 容器内 uvicorn 端口（仅内网）
    BASE_URL: str = "http://localhost"    # 对外基地址（RSS 等链接用）
    ENV: str = "development"              # development | production

    # 路径
    DATABASE_DIR: Path = Path("data")     # SQLite 数据库目录
    UPLOAD_DIR: Path = Path("uploads")    # 私有上传目录（Nginx 不可直达）
    LOG_DIR: Path = Path("logs")          # 审计日志目录

    # 认证
    JWT_SECRET: str = ""                  # 必须由环境变量/.env 提供
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_MINUTES: int = 15
    REFRESH_TOKEN_DAYS: int = 7
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = ""              # 仅 init_admin.py 首次建号读取

    # CORS：白名单，逗号分隔，禁止 *
    CORS_ORIGINS: str = "http://localhost:8081,http://localhost:3001,http://localhost:3000"

    # HTTPS 就绪后设 ENABLE_HSTS=1，注入 Strict-Transport-Security
    ENABLE_HSTS: bool = False

    # AI 中心（OpenAI 兼容接口；密钥仅存服务端，绝不下发前端）
    AI_API_KEY: str = ""
    AI_BASE_URL: str = "https://api.openai.com/v1"
    AI_MODEL: str = "gpt-4o-mini"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    def ensure_dirs(self) -> None:
        for p in (self.DATABASE_DIR, self.UPLOAD_DIR, self.LOG_DIR,
                  self.UPLOAD_DIR / "music", self.UPLOAD_DIR / "cloud"):
            p.mkdir(parents=True, exist_ok=True)


settings = Settings()
