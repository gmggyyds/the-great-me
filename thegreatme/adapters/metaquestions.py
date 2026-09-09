"""12 题的对话记录 / 答案模板 → claim。

**学员版最重要的一个适配器**：他们唯一确定拥有的，就是刚答完的那 12 题。

它也是所有适配器里最准的一个——题号不是靠关键词猜的，是**题目原文匹配**出来的，
所以 confidence 直接给 high。其余适配器只能给 medium。

两种输入都认：
1. 对话记录（ChatGPT/Claude 复制出来的原文，任意格式）——靠题目原文定位
2. `answers.md` 模板（`## Q1` 小节）——想手填的人用
"""
from __future__ import annotations

import re
from pathlib import Path

from ..questions import QUESTION_TEXT
from ..schema import Claim, Sensitivity

SOURCE = "metaquestions"

# 模板格式：## Q1 / ## Q1. xxx
_TEMPLATE_HEAD = re.compile(r"^\s{0,3}#{1,6}\s*Q(\d{1,2})\b.*$", re.I | re.M)


def _norm(s: str) -> str:
    return re.sub(r"\s+", "", s)


def _strip_ui_noise(block: str) -> str:
    """剥掉 ChatGPT/Claude 复制出来的角色标签，它们不是用户说的话。"""
    lines = []
    for l in block.splitlines():
        if re.fullmatch(r"\s*(You said:|ChatGPT said:|Claude said:|你|AI|用户|助手)\s*[:：]?\s*", l, re.I):
            continue
        lines.append(l)
    return "\n".join(lines).strip()


def _from_template(text: str, path: Path) -> list[Claim]:
    out, hits = [], list(_TEMPLATE_HEAD.finditer(text))
    for i, m in enumerate(hits):
        n = int(m.group(1))
        if n not in QUESTION_TEXT:
            continue
        end = hits[i + 1].start() if i + 1 < len(hits) else len(text)
        body = _strip_ui_noise(text[m.end():end])
        if body:
            out.append(_claim(n, body, path))
    return out


def _from_transcript(text: str, path: Path) -> list[Claim]:
    """靠题目原文定位。题目是我们自己发的，所以这条最可靠。"""
    flat = _norm(text)
    marks: list[tuple[int, int, int]] = []          # (在压平串里的位置, 长度, 题号)
    for n, q in QUESTION_TEXT.items():
        for lang in ("zh", "en"):
            needle = _norm(q[lang])
            i = flat.find(needle)
            if i != -1:
                marks.append((i, len(needle), n))
                break
    if not marks:
        return []
    marks.sort()

    # 压平串的下标映射回原文下标
    idx: list[int] = []
    for j, ch in enumerate(text):
        if not ch.isspace():
            idx.append(j)

    out = []
    for k, (pos, length, n) in enumerate(marks):
        start = idx[pos + length] if pos + length < len(idx) else len(text)
        stop = idx[marks[k + 1][0]] if k + 1 < len(marks) else len(text)
        body = _strip_ui_noise(text[start:stop])
        if body:
            out.append(_claim(n, body, path))
    return out


def _claim(n: int, body: str, path: Path) -> Claim:
    return Claim(
        q=n, claim=body, evidence=f"{path.name}#Q{n}", source=SOURCE,
        confidence="high",                      # 题号是原文匹配出来的，不是猜的
        sensitivity=Sensitivity.PRIVATE.value,  # 答案里全是真实数字和人名
    )


def harvest(path: Path) -> list[Claim]:
    """path 可以是一个文件，也可以是一个目录（目录则扫 *.md / *.txt）。"""
    if not path.exists():
        return []
    files = sorted([p for p in path.glob("*") if p.suffix.lower() in {".md", ".txt"}]) \
        if path.is_dir() else [path]
    out: list[Claim] = []
    for p in files:
        try:
            text = p.read_text(encoding="utf-8-sig")
        except (UnicodeDecodeError, OSError):
            continue
        out += _from_template(text, p) or _from_transcript(text, p)
    return out
