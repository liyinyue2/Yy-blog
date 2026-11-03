"""博客模块 Pydantic 模型：所有请求体必须定义 Model（v2.0 硬约束）。"""
from pydantic import BaseModel, Field


class ArticleBody(BaseModel):
    title: str = Field(default="", max_length=300)
    slug: str = Field(default="", max_length=100)
    category: str = Field(default="", max_length=100)
    summary: str = Field(default="", max_length=500)
    content: str = Field(default="", max_length=400000)
    date: str = Field(default="", max_length=10)
    kind: str = Field(default="article", pattern="^(article|note)$")
    tags: list[str] = Field(default_factory=list, max_length=20)


class CategoryBody(BaseModel):
    slug: str = Field(default="", max_length=100)
    name: str = Field(default="", max_length=80)
    description: str = Field(default="", max_length=400)


class CategoryUpdateBody(BaseModel):
    name: str = Field(default="", max_length=80)
    description: str = Field(default="", max_length=400)


class MessagePostBody(BaseModel):
    name: str = Field(default="", max_length=60)
    contact: str = Field(default="", max_length=150)
    content: str = Field(default="", max_length=1200)


class MessageUpdateBody(BaseModel):
    reply: str | None = Field(default=None, max_length=600)
    visible: bool | None = None
    status: str | None = Field(default=None, max_length=10)


class ModerateBody(BaseModel):
    ids: list[int] = Field(default_factory=list, max_length=200)
    status: str = Field(min_length=1, max_length=10)


class SubscribeBody(BaseModel):
    email: str = Field(min_length=3, max_length=254)


class ConvertBody(BaseModel):
    filename: str = Field(min_length=1, max_length=255)
    data: str = Field(min_length=1, max_length=20_000_000)  # base64，对应 15MB 原文件
