"""项目中心 Pydantic 模型。"""
from pydantic import BaseModel, Field


class ProjectBody(BaseModel):
    slug: str = Field(default="", max_length=64)
    name: str = Field(min_length=1, max_length=120)
    summary: str = Field(default="", max_length=500)
    description: str = Field(default="", max_length=100000)
    tech_stack: list[str] = Field(default_factory=list, max_length=12)
    status: str = Field(default="idea", pattern="^(idea|building|maintained|archived)$")
    repo_url: str = Field(default="", max_length=500)
    demo_url: str = Field(default="", max_length=500)
    progress: int = Field(default=0, ge=0, le=100)
    sort: int = Field(default=0)
    visibility: str = Field(default="public", pattern="^(public|private)$")


class ProjectLogBody(BaseModel):
    title: str = Field(default="", max_length=200)
    content: str = Field(default="", max_length=20000)
    log_date: str = Field(min_length=10, max_length=10, pattern=r"^\d{4}-\d{2}-\d{2}$")
