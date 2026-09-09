"""Claude 记忆目录 → 候选 claim。

源：`~/.claude/projects/<proj>/memory/*.md`（insights 立的规 + 长期偏好 + 项目态）。

**只读**。挂不上题的直接不产候选——闸门在适配器就生效。

🔴 frontmatter 走真 YAML，不手写正则。手写正则踩过三个静默产错的洞：
   ① 不看缩进 → `metadata.description` 盖掉顶层 `description`（真实文件全都有 metadata 块）
   ② `text.startswith("---")` → 以 `---` 开头的普通正文被当 frontmatter 硬解，凭空长出断言
   ③ 块标量 `description: >-` → claim 字面就是 `'>'`，非空、通过校验、渲染进画像
"""
from __future__ import annotations

from pathlib import Path

import yaml

from ..schema import Claim, Sensitivity

SOURCE = "memories"

# memory 的 type → 提议归到哪一题。
# 2026-09-09 在真实数据上校准过：最初收 feedback→Q1、reference→Q4，
# 208 个文件灌出 203 条候选，「我是谁」74 条全是噪音——feedback 是「怎么跟 AI 工作」
# 的规则、reference 是「去哪查证」的指针，都不是关于 Sam 的断言。入口闸的价值在此。
_TYPE_TO_Q = {"user": 1, "project": 4}
_SKIP_NAMES = {"MEMORY.md", "ARCHIVE_INDEX.md"}       # 索引文件，不是断言


def _frontmatter(text: str) -> dict:
    """只认「首行恰好是 ---、且后面某一行恰好是 ---」的块，并要求它是个 mapping。"""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    end = next((i for i, l in enumerate(lines[1:], 1) if l.strip() == "---"), None)
    if end is None:
        return {}
    try:
        data = yaml.safe_load("\n".join(lines[1:end]))
    except yaml.YAMLError:
        return {}
    return data if isinstance(data, dict) else {}


def harvest(memory_dir: Path) -> list[Claim]:
    if not memory_dir.exists():
        return []
    claims: list[Claim] = []
    for p in sorted(memory_dir.glob("*.md")):
        if p.name in _SKIP_NAMES:
            continue
        try:
            fm = _frontmatter(p.read_text(encoding="utf-8-sig"))
        except (UnicodeDecodeError, OSError):
            continue          # 一个坏文件不该带走整批（实测：一个 GBK 文件曾让 126 条全丢）
        # 🔴 目录里两种 frontmatter 格式并存：新的 `metadata.type` 嵌套（163 个）
        #    和旧的顶层 `type`（40 个，含全部 5 个 user 类型 = 「我是谁」整段的来源）。
        #    只认嵌套会砍掉旧格式那 40 个，只认顶层会漏掉新格式。两种都收。
        meta = fm.get("metadata") if isinstance(fm.get("metadata"), dict) else {}
        q = _TYPE_TO_Q.get(str(meta.get("type") or fm.get("type") or "").strip())
        if q is None:
            continue
        # `name` 是真 frontmatter 与「看起来像 YAML 的正文」之间的判据：
        # 实测 203 个带 type 的文件，缺 name 的是 0 个。
        if not str(fm.get("name") or "").strip():
            continue
        desc = fm.get("description") or fm.get("name")
        if not isinstance(desc, str) or not desc.strip():
            continue
        claims.append(Claim(
            q=q, claim=desc, evidence=str(p), source=SOURCE,
            confidence="medium", sensitivity=Sensitivity.PRIVATE.value,
        ))
    return claims
