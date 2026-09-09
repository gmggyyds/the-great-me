"""claim 账本的 schema 与读写。

一条 claim = 一句关于「我是谁 / 我有什么 / 我认识谁 / 杠杆在哪」的断言，
**只存断言和指针，不存原文**——原文永远留在它自己的源里，不产生第二真源。

两条不可退让的性质（design.md §6）：
1. **入口闸**：挂不到 12 题上的东西一条都不许进。这是抗污染的唯一闸门。
   Sam 自己的数据点：印象笔记 1245 篇真金率 3%，全量投喂就是把 3% 带进画像。
2. **fail-closed**：敏感级漏标 = 按最严处理。渲染时只有显式标 public 的才进可上云那份。
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import asdict, dataclass, field
from datetime import date
from enum import Enum
from pathlib import Path

# 12 题就是全部的格子。加格子要改真源（元问题仓），不在这里改。
QUESTIONS = list(range(1, 13))

SEGMENTS = {
    "我是谁": (1, 3),
    "我手里有什么": (4, 6),
    "我认识谁": (7, 9),
    "杠杆在哪": (10, 12),
}


class ClaimError(ValueError):
    """账本被改坏 / 候选不合规。报错必须说清是哪一条、哪一行。"""


class Sensitivity(str, Enum):
    PUBLIC = "public"      # 可进云端模型上下文
    INTERNAL = "internal"  # 公司内部，不上云
    PRIVATE = "private"    # 只在本机（客户名/供应商/收入/关系）


class Confidence(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class Claim:
    q: int
    claim: str
    evidence: str            # 指针，不是原文：`relations_index.md#人物索引` / `note:191882...`
    source: str              # 哪个适配器产的
    first_seen: str = field(default_factory=lambda: date.today().isoformat())
    last_confirmed: str = field(default_factory=lambda: date.today().isoformat())
    confidence: str = Confidence.MEDIUM.value
    sensitivity: str = Sensitivity.PRIVATE.value   # fail-closed：漏标=最严

    def __post_init__(self) -> None:
        # Python 里 True == 1，所以裸 `not in QUESTIONS` 会放行 q=True，渲染出 `**QTrue**`。
        # 这是「抗污染的唯一闸门」，它必须先验类型再验范围。
        if isinstance(self.q, bool) or not isinstance(self.q, int) or self.q not in QUESTIONS:
            raise ClaimError(
                f"题号必须是 1–12 的整数，实际是 {self.q!r}（{type(self.q).__name__}）；"
                "挂不上题的东西不许进账本")
        if not str(self.claim).strip():
            raise ClaimError("断言不能为空")
        # 断言里塞换行 + `## 段名` 能凭空伪造出段落和条目，而 AI 是当事实读的。
        # 压平换行还不够——渲染后行内仍留着 `## `，所以把结构前缀一并中和。
        flat = re.sub(r"\s*\n+\s*", " ", str(self.claim)).strip()
        self.claim = re.sub(r"(^|\s)(#{1,6}|[-*+]|\d+\.)\s+", r"\1", flat).strip()
        if not str(self.evidence).strip():
            raise ClaimError(f"证据指针不能为空（Q{self.q}: {str(self.claim)[:24]}…）；无出处的断言等于传闻")
        if self.sensitivity not in {s.value for s in Sensitivity}:
            raise ClaimError(f"敏感级只能是 public/internal/private，实际是 {self.sensitivity!r}")
        for f in ("first_seen", "last_confirmed"):
            try:
                date.fromisoformat(getattr(self, f))
            except (TypeError, ValueError):
                raise ClaimError(
                    f"{f} 必须是 ISO 日期（YYYY-MM-DD），实际是 {getattr(self, f)!r}"
                ) from None
        if self.confidence not in {c.value for c in Confidence}:
            raise ClaimError(f"置信度只能是 high/medium/low，实际是 {self.confidence!r}")

    def segment(self) -> str:
        for name, (lo, hi) in SEGMENTS.items():
            if lo <= self.q <= hi:
                return name
        raise ClaimError(f"题号 {self.q} 不属于任何一段")   # 理论上不可达，validate 已挡


def dedup_key(c: Claim) -> str:
    """同一条断言反复跑不该长出第二条。key 只吃「哪一题 + 说了什么 + 出处」，
    不吃时间戳——否则每跑一次就多一条，这正是「只进不出」的第一步。"""
    raw = f"{c.q}\x1f{c.claim.strip()}\x1f{c.evidence.strip()}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def save_jsonl(path: Path, claims: list[Claim]) -> Path:
    """原子写。

    `open("w")` 是先截断后写：写一半异常 = 账本被腰斩。而账本在 git 之外、
    没备份、没版本 —— 那就是不可逆丢失。所以先写 .tmp，成功了再 replace。
    """
    from . import guard
    guard.assert_not_tracked(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    try:
        with tmp.open("w", encoding="utf-8") as f:
            for c in claims:
                f.write(json.dumps(asdict(c), ensure_ascii=False) + "\n")
            f.flush()
            os.fsync(f.fileno())
        tmp.chmod(0o600)      # 同机任何进程都能读这份东西，别留 0644
        tmp.replace(path)     # POSIX 原子
    finally:
        tmp.unlink(missing_ok=True)
    return path


def load_jsonl(path: Path) -> list[Claim]:
    if not path.exists():
        return []
    out: list[Claim] = []
    for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            out.append(Claim(**json.loads(line)))
        except json.JSONDecodeError as e:
            raise ClaimError(f"{path.name} 第 {i} 行不是合法 JSON：{e}") from e
        except (TypeError, ClaimError) as e:
            raise ClaimError(f"{path.name} 第 {i} 行不合规：{e}") from e
    return out
