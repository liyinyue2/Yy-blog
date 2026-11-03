"""AI 中心：对话 CRUD + SSE 流式聊天。

安全红线：
- API 密钥仅存服务端 .env（AI_API_KEY），任何响应体/前端代码不出现；
- 上游为 OpenAI 兼容 /chat/completions（stream=true），经服务端转发；
- /chat 限流 60s/10 次；聊天与对话增删均有审计埋点（不记录正文，只记录元信息）；
- 前端一律 textContent 渲染，杜绝注入；CSP 不放宽（SSE 同源，connect-src 'self' 即可）。
"""
import json
import urllib.error
import urllib.request

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.core.audit import audit_log
from app.core.config import settings
from app.core.database import db
from app.core.ratelimit import client_ip, rate_hit
from app.core.security import require_admin

router = APIRouter(prefix="/api/space/ai", tags=["ai"])

AI_RATE_LIMIT = (60, 10)      # 60 秒窗口，10 次聊天
MAX_HISTORY = 20              # 送入上游的历史消息条数上限
MAX_CONTENT = 8000            # 单条消息长度上限

SYSTEM_PROMPT = ("你是站长个人的 AI 助手，回答简洁、实用、友好。"
                 "使用与用户相同的语言（默认中文）。")


class ConversationBody(BaseModel):
    title: str = Field(default="新的对话", max_length=120)


class ChatBody(BaseModel):
    conversation_id: int = Field(ge=1)
    content: str = Field(min_length=1, max_length=MAX_CONTENT)


def _get_conversation(cid: int):
    row = db.conn().execute("SELECT * FROM ai_conversations WHERE id = ?", (cid,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="对话不存在")
    return row


# ---------- 会话 CRUD ----------

@router.get("/conversations")
def list_conversations(user: dict = Depends(require_admin)):
    rows = db.conn().execute(
        """SELECT c.id, c.title, c.created_at, c.updated_at,
                  (SELECT COUNT(*) FROM ai_messages m WHERE m.conversation_id = c.id) AS message_count
           FROM ai_conversations c ORDER BY c.updated_at DESC, c.id DESC LIMIT 100""").fetchall()
    return [dict(r) for r in rows]


@router.post("/conversations")
def create_conversation(body: ConversationBody, request: Request,
                        user: dict = Depends(require_admin)):
    conn = db.conn()
    cur = conn.execute("INSERT INTO ai_conversations (title) VALUES (?)",
                       (body.title.strip()[:120] or "新的对话",))
    conn.commit()
    audit_log("ai-conversation-create", f"id={cur.lastrowid}",
              client_ip(request), user=user["username"])
    return {"ok": True, "id": cur.lastrowid, "title": body.title.strip()[:120] or "新的对话"}


@router.delete("/conversations/{cid}")
def delete_conversation(cid: int, request: Request, user: dict = Depends(require_admin)):
    _get_conversation(cid)
    conn = db.conn()
    conn.execute("DELETE FROM ai_conversations WHERE id = ?", (cid,))  # 消息级联
    conn.commit()
    audit_log("ai-conversation-delete", f"id={cid}", client_ip(request), user=user["username"])
    return {"ok": True, "deleted": cid}


@router.get("/conversations/{cid}/messages")
def list_messages(cid: int, user: dict = Depends(require_admin)):
    _get_conversation(cid)
    rows = db.conn().execute(
        "SELECT id, role, content, created_at FROM ai_messages"
        " WHERE conversation_id = ? ORDER BY id ASC", (cid,)).fetchall()
    return [dict(r) for r in rows]


# ---------- SSE 流式聊天 ----------

def _upstream_stream(messages: list[dict]):
    """调用 OpenAI 兼容上游（流式），逐段 yield 文本增量。密钥只在这里出现。"""
    url = settings.AI_BASE_URL.rstrip("/") + "/chat/completions"
    payload = json.dumps({
        "model": settings.AI_MODEL,
        "messages": messages,
        "stream": True,
    }).encode()
    req = urllib.request.Request(url, data=payload, method="POST")
    req.add_header("Authorization", f"Bearer {settings.AI_API_KEY}")
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            for raw in resp:
                line = raw.decode("utf-8", "replace").strip()
                if not line.startswith("data:"):
                    continue
                data = line[5:].strip()
                if data == "[DONE]":
                    return
                try:
                    chunk = json.loads(data)
                    delta = chunk["choices"][0].get("delta", {}).get("content")
                except (ValueError, KeyError, IndexError):
                    continue
                if delta:
                    yield delta
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:300]
        yield f"\n[上游错误 {exc.code}] {detail}"
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        yield f"\n[上游连接失败] {exc}"


@router.post("/chat")
def chat(body: ChatBody, request: Request, user: dict = Depends(require_admin)):
    if not settings.AI_API_KEY:
        raise HTTPException(status_code=503, detail="AI 服务未配置：请在服务器 .env 中设置 AI_API_KEY / AI_BASE_URL / AI_MODEL")
    ip = client_ip(request)
    if rate_hit(f"aichat:{user['username']}:{ip}", *AI_RATE_LIMIT):
        raise HTTPException(status_code=429, detail="AI 请求太频繁，请一分钟后再试")

    _get_conversation(body.conversation_id)
    content = body.content.strip()
    conn = db.conn()
    conn.execute(
        "INSERT INTO ai_messages (conversation_id, role, content) VALUES (?,?,?)",
        (body.conversation_id, "user", content[:MAX_CONTENT]))
    # 首条消息自动作为会话标题
    title_row = conn.execute(
        "SELECT title FROM ai_conversations WHERE id = ?", (body.conversation_id,)).fetchone()
    if title_row and title_row["title"] == "新的对话":
        conn.execute("UPDATE ai_conversations SET title = ? WHERE id = ?",
                     (content[:60], body.conversation_id))
    history = conn.execute(
        "SELECT role, content FROM ai_messages WHERE conversation_id = ?"
        " ORDER BY id DESC LIMIT ?", (body.conversation_id, MAX_HISTORY)).fetchall()
    conn.execute("UPDATE ai_conversations SET updated_at=datetime('now','localtime') WHERE id=?",
                 (body.conversation_id,))
    conn.commit()

    upstream_messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    upstream_messages += [{"role": r["role"], "content": r["content"]}
                          for r in reversed(history)]

    conversation_id = body.conversation_id

    def event_stream():
        full = []
        yield f"data: {json.dumps({'ok': True, 'conversation_id': conversation_id}, ensure_ascii=False)}\n\n"
        try:
            for delta in _upstream_stream(upstream_messages):
                full.append(delta)
                yield f"data: {json.dumps({'delta': delta}, ensure_ascii=False)}\n\n"
        finally:
            text = "".join(full)
            if text.strip():
                c = db.conn()
                c.execute(
                    "INSERT INTO ai_messages (conversation_id, role, content) VALUES (?,?,?)",
                    (conversation_id, "assistant", text[:MAX_CONTENT * 2]))
                c.execute("UPDATE ai_conversations SET updated_at=datetime('now','localtime') WHERE id=?",
                          (conversation_id,))
                c.commit()
            audit_log("ai-chat", f"conv={conversation_id} chars={len(text)}",
                      ip, user=user["username"])
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"})
