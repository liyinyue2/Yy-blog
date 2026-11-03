"""Word / PDF 转文章：从 v1.0 原样移植（含 zip 炸弹预检与错误泛化）。"""
import base64
import binascii
import html as html_mod
import io
import re

from fastapi import HTTPException

MAX_UPLOAD = 15 * 1024 * 1024            # 单文件 15MB
MAX_DOCX_UNCOMPRESSED = 64 * 1024 * 1024  # docx 解压后总大小上限


def _inline_runs(paragraph):
    """把 docx 段落的 run 转成带 <strong>/<em> 的行内 HTML。"""
    parts = []
    for run in paragraph.runs:
        text = html_mod.escape(run.text or "")
        if not text:
            continue
        if run.bold:
            text = f"<strong>{text}</strong>"
        if run.italic:
            text = f"<em>{text}</em>"
        parts.append(text)
    return "".join(parts) or html_mod.escape(paragraph.text or "")


def convert_docx(raw: bytes) -> tuple[str, str]:
    import zipfile

    with zipfile.ZipFile(io.BytesIO(raw)) as zf:  # 解析前预检：拒绝解压炸弹
        total = sum(info.file_size for info in zf.infolist())
        if total > MAX_DOCX_UNCOMPRESSED:
            raise ValueError(f"文档解压后过大（{total // 1048576}MB），疑似损坏或恶意构造")
    from docx import Document

    doc = Document(io.BytesIO(raw))
    title = (doc.core_properties.title or "").strip()
    blocks = []
    list_buffer = []  # (type, items)
    first_heading = ""

    def flush_list():
        nonlocal list_buffer
        if list_buffer:
            tag = "ol" if list_buffer[0][0] == "ol" else "ul"
            items = "".join(f"<li>{item}</li>" for _, item in list_buffer)
            blocks.append(f"<{tag}>{items}</{tag}>")
            list_buffer = []

    for para in doc.paragraphs:
        text = para.text.strip()
        style = (para.style.name or "").lower() if para.style is not None else ""
        if not text:
            flush_list()
            continue
        if style.startswith("title"):
            if not title:
                title = text
        elif style.startswith("heading 1"):
            flush_list()
            if not title:
                title = text
            if not first_heading:
                first_heading = text
            blocks.append(f"<h2>{html_mod.escape(text)}</h2>")
        elif style.startswith("heading 2"):
            flush_list()
            blocks.append(f"<h3>{html_mod.escape(text)}</h3>")
        elif style.startswith("heading"):
            flush_list()
            blocks.append(f"<h4>{html_mod.escape(text)}</h4>")
        elif "list number" in style:
            list_buffer.append(("ol", _inline_runs(para)))
        elif "list" in style:
            list_buffer.append(("ul", _inline_runs(para)))
        else:
            flush_list()
            blocks.append(f"<p>{_inline_runs(para)}</p>")
    flush_list()
    if not title:
        title = first_heading
    return title, "\n".join(blocks)


def convert_pdf(raw: bytes) -> tuple[str, str]:
    import pymupdf

    doc = pymupdf.open(stream=raw, filetype="pdf")
    title = (doc.metadata or {}).get("title") or ""
    paragraphs = []
    for page in doc:
        lines = [ln.strip() for ln in page.get_text("text").splitlines()]
        buf = []
        for ln in lines:
            if not ln:
                if buf:
                    paragraphs.append(" ".join(buf))
                    buf = []
                continue
            buf.append(ln)
            # 段落通常以句末标点收尾，遇到即断段
            if re.search(r"[。！？.!?]$", ln):
                paragraphs.append(" ".join(buf))
                buf = []
        if buf:
            paragraphs.append(" ".join(buf))
    doc.close()
    paragraphs = [p for p in paragraphs if p.strip()]
    if not paragraphs:
        raise HTTPException(status_code=400, detail="无法从该 PDF 中提取到文本内容（可能是扫描件或文件损坏）")
    if not title:
        title = paragraphs[0][:60]
    content = "\n".join(f"<p>{html_mod.escape(p)}</p>" for p in paragraphs)
    return title.strip(), content


def decode_upload(filename: str, b64: str) -> bytes:
    """解码 base64 请求体并做大小/类型预检；不合法直接抛 400。"""
    if not filename or not b64:
        raise HTTPException(status_code=400, detail="缺少文件名或文件内容")
    try:
        raw = base64.b64decode(b64, validate=False)
    except (binascii.Error, ValueError):
        raise HTTPException(status_code=400, detail="文件内容解码失败")
    if len(raw) > MAX_UPLOAD:
        raise HTTPException(status_code=400, detail="文件超过 15MB 限制")
    return raw


def parse_document(filename: str, raw: bytes) -> tuple[str, str]:
    """按扩展名分派解析器；错误信息泛化，细节进审计日志由调用方处理。"""
    ext = filename.lower().rsplit(".", 1)[-1]
    if ext == "docx":
        return convert_docx(raw)
    if ext == "pdf":
        return convert_pdf(raw)
    if ext == "doc":
        raise HTTPException(status_code=400, detail="暂不支持旧版 .doc，请在 Word 中另存为 .docx 后再导入")
    raise HTTPException(status_code=400, detail="仅支持 .docx 与 .pdf 文件")
