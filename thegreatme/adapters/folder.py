"""inbox 文件夹 → claim。学员把任何笔记丢进来的通用入口。

🔴 入口闸在这里最吃紧：学员会把整个工单、聊天记录、会议纪要一股脑丢进来。
   所以**只收显式标了题号的段落**，没标号的一个字不进——但要**报出来收了几段、
   拒了几段**。静默丢弃比不收更糟：学员会以为收了。

没标号的那些不是浪费——它们正是该拿去问 AI 的：
「这段改变了我 12 题里的哪一条？」挂得上再回来标号。
"""
from __future__ import annotations

import re
from pathlib import Path

from ..questions import QUESTION_TEXT
from ..schema import Claim, Sensitivity

SOURCE = "folder"

# 认这些写法：Q7: / Q7： / ## Q7 / [[Q7]] / q7:
_TAG = re.compile(r"^\s*(?:#{1,6}\s*)?\[{0,2}\s*Q(\d{1,2})\s*\]{0,2}\s*[:：.、]?\s*", re.I)


def _chunks(text: str):
    """按空行切段。"""
    for raw in re.split(r"\n\s*\n", text):
        if raw.strip():
            yield raw.strip()


def harvest_with_report(inbox: Path) -> tuple[list[Claim], int]:
    """返回 (claims, 因为没题号而没收的段数)。"""
    if not inbox.exists():
        return [], 0
    out: list[Claim] = []
    skipped = 0
    for p in sorted(inbox.rglob("*")):
        if p.is_dir() or p.suffix.lower() not in {".md", ".txt"}:
            continue
        try:
            text = p.read_text(encoding="utf-8-sig")
        except (UnicodeDecodeError, OSError):
            continue
        for chunk in _chunks(text):
            m = _TAG.match(chunk)
            if not m:
                skipped += 1
                continue
            n = int(m.group(1))
            if n not in QUESTION_TEXT:
                skipped += 1
                continue
            body = chunk[m.end():].strip()
            if not body:
                skipped += 1
                continue
            out.append(Claim(
                q=n, claim=body, evidence=f"inbox/{p.name}", source=SOURCE,
                confidence="medium",                      # 题号是人标的，但内容没人审过
                sensitivity=Sensitivity.PRIVATE.value,
            ))
    return out, skipped


def harvest(inbox: Path) -> list[Claim]:
    return harvest_with_report(inbox)[0]
