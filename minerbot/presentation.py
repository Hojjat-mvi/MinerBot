"""Persian paragraph direction and safe Telegram HTML formatting."""

import re
from html import escape

RLM = "\u200f"
LRI = "\u2066"
PDI = "\u2069"
# Isolate Latin identifiers and phone numbers without reversing Persian text.
LTR_RUN = re.compile(r"https?://[^\s]+|@[A-Za-z0-9_]+|/[A-Za-z][A-Za-z0-9_]*(?:@[A-Za-z0-9_]+)?|[A-Za-z][A-Za-z0-9]*(?:[ ./+-][A-Za-z0-9]+)*|[+-]?[0-9][0-9.,:]*")


def rtl_html(text: str, *, bold_lines: tuple[str, ...] = ()) -> str:
    lines = []
    emphasized = {line.strip().replace("ي", "ی").replace("ك", "ک") for line in bold_lines}
    for line in text.strip().splitlines():
        line = line.strip().replace("ي", "ی").replace("ك", "ک")
        if not line:
            lines.append("")
            continue
        bold = not lines or line in emphasized
        line = LTR_RUN.sub(lambda match: LRI + match.group() + PDI, line)
        rendered = RLM + escape(line)
        lines.append("<b>" + rendered + "</b>" if bold else rendered)
    return "\n".join(lines)


def telegram_text_parts(text: str, *, bold_lines: tuple[str, ...] = ()) -> list[str]:
    """Render within Telegram's UTF-16 limit, including added direction marks."""
    from html import unescape

    def fits(rendered: str) -> bool:
        plain = unescape(rendered.replace('<b>', '').replace('</b>', ''))
        return len(plain.encode('utf-16-le')) <= 4096 * 2

    rendered = rtl_html(text, bold_lines=bold_lines)
    if fits(rendered):
        return [rendered]
    # At most two direction marks and one line-direction mark per character.
    # Small plain-text chunks also avoid splitting an HTML tag/entity in half.
    parts = []
    remaining = text
    while remaining:
        boundary = min(len(remaining), 900)
        if boundary < len(remaining):
            newline = remaining.rfind('\n', 0, boundary)
            if newline > 0:
                boundary = newline + 1
        chunk, remaining = remaining[:boundary], remaining[boundary:]
        if chunk.strip():
            parts.append(rtl_html(chunk, bold_lines=bold_lines))
    return parts
