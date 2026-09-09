"""Get笔记 关系索引 → 候选 claim。

源：`71_llm_wiki_second_brain.wip/relations_index.md`。

**只读**。GMGG_Brain vault 与 Get笔记真源的铁律是「只有入库管线写」。

🔴 表种按**表头**判，不按标题文字判。
   原来硬匹配「人物索引」四个字，结果源里第三张表 `## 七、妙记新增人物（补充）`
   的 11 个人一个都没抽到——包括生财 912 大课主理人。标题会变，表头不会。

适配器**只提议不判定**：提取行、提议题号、附证据指针，准不准由「审」那一步定。
"""
from __future__ import annotations

import re
from pathlib import Path

from ..schema import Claim, Sensitivity

SOURCE = "relations"

PERSON_HEAD, ORG_HEAD = "人物", "主体"

# 「关系与状态」里出现这些词 → 提议归到哪一题。命不中落 Q7。
_HINTS: list[tuple[int, tuple[str, ...]]] = [
    (9, ("分发", "流量", "名单", "播客", "曝光", "渠道", "媒体")),
    (8, ("对标", "顾问", "权威", "口径", "判断", "复盘", "审")),
    (7, ("入口", "邀约", "牵头", "对接", "通道", "资源", "合作", "主导", "落地")),
]

_CELL_SPLIT = re.compile(r"(?<!\\)\|")     # `\|` 是表格里放竖线的标准写法，不能当分隔符


def _cells(line: str) -> list[str]:
    body = line.strip()
    body = body[1:] if body.startswith("|") else body
    body = body[:-1] if body.endswith("|") and not body.endswith("\\|") else body
    return [c.strip().replace("\\|", "|") for c in _CELL_SPLIT.split(body)]


def _is_separator(cells: list[str]) -> bool:
    return bool(cells) and all(set(c) <= set("-: ") for c in cells) and any("-" in c for c in cells)


def _tables(text: str):
    """扫全文，产出 (表种, 数据行)。识别代码围栏，避免把示例表当真数据。"""
    header: list[str] | None = None
    in_fence = False
    for line in text.splitlines():
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            header = None
            continue
        if in_fence:
            continue
        if not line.strip().startswith("|"):
            header = None                      # 表结束；下一张表要重新认表头
            continue
        cells = _cells(line)
        if _is_separator(cells):
            continue
        if header is None:
            header = cells                     # 第一行非分隔的表格行 = 表头
            continue
        yield header[0] if header else "", cells


def _propose_q(status: str) -> int:
    for q, kws in _HINTS:
        if any(k in status for k in kws):
            return q
    return 7


def harvest(path: Path) -> list[Claim]:
    if not path.exists():
        return []
    try:
        text = path.read_text(encoding="utf-8-sig")
    except (UnicodeDecodeError, OSError):
        return []

    claims: list[Claim] = []
    for kind, cells in _tables(text):
        if len(cells) < 4:
            continue
        subject, role, status, cite = cells[0], cells[1], cells[2], cells[3]
        # 🔴 evidence 前缀恒非空，所以 schema 的空值闸拦不住空 cite——
        #    「无出处 0」曾经因此是假绿灯。在这里挡。
        if not (subject.strip() and cite.strip()):
            continue
        if kind.startswith(PERSON_HEAD):
            claims.append(Claim(
                q=_propose_q(status),
                claim=f"{subject}（{role}）——{status}",
                evidence=f"{path.name}#人物索引 | {cite}",
                source=SOURCE, confidence="medium",
                sensitivity=Sensitivity.PRIVATE.value,   # 人名+关系，适配器无权判 public
            ))
        elif kind.startswith(ORG_HEAD):
            if "竞品" in role:
                continue                        # 竞品不是「我认识谁」，挂不上题就不进
            claims.append(Claim(
                q=7,
                claim=f"{subject}（{role}）——{status}",
                evidence=f"{path.name}#公司品牌索引 | {cite}",
                source=SOURCE, confidence="medium",
                sensitivity=Sensitivity.PRIVATE.value,
            ))
    return claims
