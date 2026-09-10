"""账本 → 结构性统计。周报和进度卡共用这一份。

**这里一个字的断言内容都不碰**，只数数、只看日期。
理由：它的两个消费者（周报文件、可截图的进度卡）都可能被人看见，
而断言内容是客户/供应商/人脉/收入。把「统计」和「内容」在源头就分开，
比在每个出口各写一遍脱敏可靠——出口会增加，源头只有一个。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta

from .render import STALE_DAYS, _is_stale
from .schema import QUESTIONS, SEGMENTS, Claim


def _d(s: str) -> date | None:
    try:
        return date.fromisoformat(s)
    except (TypeError, ValueError):
        return None


@dataclass
class Pulse:
    """一次快照。字段全是数字或题号，没有任何断言正文。"""
    today: str
    window_days: int
    total: int = 0
    by_segment: dict[str, int] = field(default_factory=dict)
    by_question: dict[int, int] = field(default_factory=dict)
    answered: list[int] = field(default_factory=list)      # 有 >=1 条断言的题号
    empty: list[int] = field(default_factory=list)         # 一条都没有的题号
    added: dict[str, int] = field(default_factory=dict)    # 窗口内新增，按段
    refreshed: int = 0                                     # 窗口内被源再次确认（非新增）
    stale: int = 0                                         # 超过 STALE_DAYS 没被确认
    public: int = 0
    thinnest: str = ""                                     # 条数最少的那一段
    sources: list[str] = field(default_factory=list)       # 启用的适配器名

    @property
    def added_total(self) -> int:
        return sum(self.added.values())

    @property
    def answered_count(self) -> int:
        return len(self.answered)


def snapshot(claims: list[Claim], today: str | None = None, *, window_days: int = 7,
             sources: list[str] | None = None) -> Pulse:
    today = today or date.today().isoformat()
    t = _d(today) or date.today()
    cutoff = t - timedelta(days=window_days)

    p = Pulse(today=today, window_days=window_days, total=len(claims),
              sources=sorted(sources or []))
    p.by_question = {q: 0 for q in QUESTIONS}
    p.by_segment = {seg: 0 for seg in SEGMENTS}
    p.added = {seg: 0 for seg in SEGMENTS}

    seg_of = {q: seg for seg, (lo, hi) in SEGMENTS.items() for q in range(lo, hi + 1)}

    for c in claims:
        seg = seg_of.get(c.q)
        p.by_question[c.q] = p.by_question.get(c.q, 0) + 1
        if seg:
            p.by_segment[seg] += 1
        if c.sensitivity == "public":
            p.public += 1
        if _is_stale(c, today):
            p.stale += 1
        fs, lc = _d(c.first_seen), _d(c.last_confirmed)
        if fs and fs > cutoff:
            if seg:
                p.added[seg] += 1
        elif lc and lc > cutoff:
            # 不是新的，但这轮又被源确认了一次 —— 说明那条依据还在
            p.refreshed += 1

    p.answered = [q for q in QUESTIONS if p.by_question.get(q)]
    p.empty = [q for q in QUESTIONS if not p.by_question.get(q)]
    # 最薄的一段：条数最少的。全为 0 时取第一段（此时整个账本是空的，说什么都对）
    p.thinnest = min(SEGMENTS, key=lambda s: (p.by_segment[s], list(SEGMENTS).index(s)))
    return p


def stale_days() -> int:
    return STALE_DAYS
