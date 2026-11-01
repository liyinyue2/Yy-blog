"""HTML 白名单清洗：从 v1.0 serve.py 原样移植，行为保持一致。"""
import html as html_mod
from html.parser import HTMLParser

ALLOWED_TAGS = {"p", "br", "hr", "strong", "em", "b", "i", "u", "s", "h2", "h3", "h4",
                "ul", "ol", "li", "a", "blockquote", "code", "pre"}
VOID_TAGS = {"br", "hr"}
ALLOWED_ATTRS = {"a": {"href"}}


class _HtmlWhitelister(HTMLParser):
    """只放行白名单标签；<a> 仅保留 http(s)/相对 href；其余内容一律转义输出。"""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out = []
        self.stack = []

    def handle_starttag(self, tag, attrs):
        if tag not in ALLOWED_TAGS:
            return
        if tag in VOID_TAGS:
            self.out.append(f"<{tag}>")
            return
        parts = [tag]
        for name, value in attrs:
            if tag in ALLOWED_ATTRS and name in ALLOWED_ATTRS[tag]:
                v = (value or "").strip()
                low = v.lower()
                if not (v.startswith("/") or low.startswith("http://") or low.startswith("https://")):
                    continue  # 拒绝 javascript: / data: 等危险协议
                parts.append(f'{name}="{html_mod.escape(v, quote=True)}"')
        self.out.append(f"<{' '.join(parts)}>")
        self.stack.append(tag)

    def handle_endtag(self, tag):
        if tag in ALLOWED_TAGS and tag not in VOID_TAGS and tag in self.stack:
            while self.stack:  # 闭合中间未关闭的标签
                t = self.stack.pop()
                self.out.append(f"</{t}>")
                if t == tag:
                    break

    def handle_data(self, data):
        self.out.append(html_mod.escape(data, quote=False))

    def result(self):
        while self.stack:
            self.out.append(f"</{self.stack.pop()}>")
        return "".join(self.out)


def sanitize_html(raw: str) -> str:
    """富文本入库前的白名单清洗，杜绝存储型 XSS。"""
    if not raw:
        return ""
    parser = _HtmlWhitelister()
    try:
        parser.feed(raw)
        parser.close()
        return parser.result()
    except Exception:
        return html_mod.escape(raw)  # 解析异常时退化为纯文本转义
