"""Persian paragraph direction and safe Telegram HTML formatting."""

import re
from html import escape

RLM = "\u200f"
LRI = "\u2066"
PDI = "\u2069"
# Isolate Latin identifiers and phone numbers without reversing Persian text.
LTR_RUN = re.compile(r"https?://[^\s]+|@[A-Za-z0-9_]+|[A-Za-z][A-Za-z0-9]*(?:[ ./+-][A-Za-z0-9]+)*|[+-]?[0-9][0-9.,:]*")


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
