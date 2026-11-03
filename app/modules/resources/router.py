"""资源库：只读 JSON 内容源（content/resources.json）。

为什么不进数据库：资源是人工维护的静态清单，改 JSON 即生效，
不需要迁移、后台表单与权限；等出现"投稿 / 排序 / 分组拖拽"再迁表。
放在 content/ 而不是 data/：data/ 是运行期数据库目录且被 .gitignore 排除，
内容源必须随仓库走，否则克隆下来页面是空的。
"""
import json
from pathlib import Path

from fastapi import APIRouter, Query

router = APIRouter(prefix="/api/public", tags=["resources"])

SRC = Path("content/resources.json")


@router.get("/resources")
def list_resources(kind: str = Query("", max_length=20)) -> list[dict]:
    """公开只读。kind 为空返回全部；分类由前端从数据里自行去重得出。"""
    if not SRC.exists():
        return []
    data = json.loads(SRC.read_text(encoding="utf-8"))
    items = data.get("items", []) if isinstance(data, dict) else data
    rows = [i for i in items if isinstance(i, dict) and i.get("title") and i.get("url")]
    if kind:
        rows = [i for i in rows if i.get("kind") == kind]
    return rows
