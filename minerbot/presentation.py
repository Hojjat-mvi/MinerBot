"""Persian paragraph direction and safe Telegram HTML formatting."""

import re
from html import escape

RLM = "\u200f"
LRI = "\u2066"
PDI = "\u2069"
# Isolate Latin identifiers and phone numbers without reversing Persian text.
LTR_RUN = re.compile(r"https?://[^\s]+|@[A-Za-z0-9_]+|[A-Za-z][A-Za-z0-9]*(?:[ ./+-][A-Za-z0-9]+)*|[0-9][0-9.,:+-]*")


def rtl_html(text: str) -> str:
    lines = []
    for line in text.strip().splitlines():
        line = line.strip().replace("ي", "ی").replace("ك", "ک")
        if not line:
            lines.append("")
            continue
        line = LTR_RUN.sub(lambda match: LRI + match.group() + PDI, line)
        lines.append(RLM + escape(line))
    if lines:
        lines[0] = "<b>" + lines[0] + "</b>"
    return "\n".join(lines)
