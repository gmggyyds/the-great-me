"""周报：这一周画像变了什么，以及**哪块还是空的**。

为什么需要它：`PROFILE.private.md` 是**终态快照**，每次重新渲染，看不出这周发生了什么。
而画像的价值恰恰在增量——「这周新增了 8 条」不重要，「杠杆那一段还是只有 3 条」才重要。

所以周报的重心不是汇报进度，是**指出缺口**：哪一段最薄、哪几题一条都没有、
哪些断言超过半年没被任何源再确认过（可能已经不成立了）。

默认打码，跟 `review` 同一条规矩：CLI 是给 agent 跑的，private 原文进 stdout
就等于进会话 transcript 就等于上传模型 API。要看全文得显式 --unmask。
"""
from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

from . import guard
from .pulse import Pulse, snapshot, stale_days
from .questions import QUESTION_TEXT
from .render import _is_stale, review_line
from .schema import SEGMENTS, Claim

BRAND = "the-great-me · 伟大的我"
BRAND_URL = "https://github.com/gmggyyds/the-great-me"


def iso_week(today: str) -> str:
    y, w, _ = date.fromisoformat(today).isocalendar()
    return f"{y}-W{w:02d}"


def _window(today: str, days: int) -> str:
    t = date.fromisoformat(today)
    return f"{(t - timedelta(days=days)).isoformat()} → {today}"


def build(claims: list[Claim], today: str | None = None, *, window_days: int = 7,
          unmask: bool = False, owner: str = "", sources: list[str] | None = None,
          per_segment: int = 8) -> str:
    # per_segment=0 表示不截断。默认截断的理由：第一次建账本时「本周新增」等于全部条数，
    # 一份 155 行的清单会把周报真正的重点（缺口那一节）挤到看不见的地方。
    today = today or date.today().isoformat()
    p: Pulse = snapshot(claims, today, window_days=window_days, sources=sources)
    who = f"{owner} · " if owner else ""
    cutoff = date.fromisoformat(today) - timedelta(days=window_days)

    L: list[str] = [
        f"# {who}画像周报 · {iso_week(today)}",
        "",
        f"> {_window(today, window_days)}　账本 {p.total} 条　"
        f"12 题答了 {p.answered_count} 题",
        "",
        "---",
        "",
        "## 这周变了什么",
        "",
    ]
    if p.added_total:
        detail = "、".join(f"{seg} +{n}" for seg, n in p.added.items() if n)
        L += [f"- **新增 {p.added_total} 条**：{detail}"]
    else:
        L += ["- **新增 0 条** —— 这一周画像没长。不是坏事，但连着几周为 0 就说明源断了。"]
    if p.refreshed:
        L += [f"- 刷新 {p.refreshed} 条（源里依据还在，没过期）"]
    L += [f"- 陈旧 {p.stale} 条（超过 {stale_days()} 天没被任何源再确认）", ""]

    # 新增明细：默认打码，只给指针
    new_claims = [c for c in claims
                  if (d := _safe(c.first_seen)) and d > cutoff]
    if new_claims:
        L += ["## 这周新增的", ""]
        if not unmask:
            L += ["<sub>默认打码。要看全文：`report --unmask`——⚠️ 别在 AI 会话里跑。</sub>", ""]
        seg_of = {q: s for s, (lo, hi) in SEGMENTS.items() for q in range(lo, hi + 1)}
        for seg in SEGMENTS:
            rows = sorted([c for c in new_claims if seg_of.get(c.q) == seg],
                          key=lambda c: (c.q, c.first_seen))
            if not rows:
                continue
            L += [f"### {seg}", ""]
            # per_segment=0 = 不截断。写成 rows[:0] 会一条都不显示（切片的 0 是「取零个」，
            # 不是「不限制」）——这个 off-by-one 让 --top 0 的语义正好反过来。
            shown = rows[:per_segment] if per_segment else rows
            L += [f"- {review_line(c, unmask=unmask)}" for c in shown]
            if len(rows) > len(shown):
                L += [f"- <sub>……还有 {len(rows) - len(shown)} 条，"
                      f"看全部：`report --top 0`</sub>"]
            L += [""]

    # 缺口——周报真正的价值
    L += ["## 该补的", ""]
    gaps = 0
    thin = p.by_segment.get(p.thinnest, 0)
    if p.total and thin * 3 <= p.total / len(SEGMENTS) * 2:
        gaps += 1
        L += [f"- 🔴 **「{p.thinnest}」只有 {thin} 条**，是四段里最薄的一段。"]
    if p.empty:
        gaps += 1
        L += [f"- 🔴 **还有 {len(p.empty)} 题一条断言都没有**："]
        for q in p.empty:
            txt = (QUESTION_TEXT.get(q, {}) or {}).get("zh", "")
            L += [f"  - **Q{q}** {txt}"]
    stale_rows = [c for c in claims if _is_stale(c, today)]
    if stale_rows:
        gaps += 1
        L += [f"- ⏳ **{len(stale_rows)} 条超过 {stale_days()} 天没被确认**，"
              "可能已经不成立了。挨条看一眼：还算数就让源再提一次，不算数就从账本删掉。"]
    if not gaps:
        L += ["- 没有明显缺口。12 题都有内容，四段厚度均衡，没有陈旧断言。"]
    L += [""]

    # 下一步：给一句能直接丢给 AI 的话
    L += ["## 下一步", ""]
    if p.empty:
        q = p.empty[0]
        txt = (QUESTION_TEXT.get(q, {}) or {}).get("zh", "")
        L += ["把这句话丢给你的 AI：", "",
              "```",
              f"我要补 the-great-me 的第 {q} 题：{txt}",
              "问我几个问题把它问出来，问完帮我写成一段，段首标 Q" + str(q) + "：，",
              "我丢进 inbox/。",
              "```", ""]
    else:
        L += ["把最近的会议纪要 / 笔记喂一轮：", "",
              "```",
              "扫一下我最近的笔记，按 12 题标好题号写进 the-great-me 的 inbox，"
              "挂不上的丢掉，不是关于我本人的也丢掉。",
              "```", ""]

    L += ["---", "",
          f"<sub>{BRAND} · {BRAND_URL}　"
          f"账本 {p.total} 条 · 连了 {len(p.sources)} 个源 · 生成于 {today}</sub>", ""]
    return "\n".join(L).rstrip() + "\n"


def _safe(s: str):
    try:
        return date.fromisoformat(s)
    except (TypeError, ValueError):
        return None


def write(text: str, out_dir: Path, today: str | None = None) -> Path:
    today = today or date.today().isoformat()
    path = out_dir / f"REPORT_{iso_week(today)}.md"
    guard.assert_not_tracked(path)
    guard.assert_within(out_dir, path)
    out_dir.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    path.chmod(0o600)          # 打码版也可能含指针；跟画像同级对待
    return path
