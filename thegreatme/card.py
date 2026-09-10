"""进度卡 —— 唯一一个**设计成给人看见**的出口。

其余所有出口（PROFILE.private.md、review、周报）都在防止内容离机；这一个反过来，
它是拿来截图发出去的。所以它的硬约束不是「脱敏」，是**根本不碰内容**：
它只读 pulse 里的数字和题号，连一条断言的指针都不取。

在私有画像上加 logo 鼓励人截图，等于亲手拆掉整套护栏。可传播的必须是另一张东西。

顺带它是最好的广告：「杠杆在哪只有 3 条」这种话本身就勾人，而一个字都不涉密。
"""
from __future__ import annotations

import unicodedata
from pathlib import Path

from . import guard
from .pulse import Pulse, snapshot
from .schema import QUESTIONS, SEGMENTS, Claim

BRAND_ZH = "the-great-me · 伟大的我"
BRAND_BY = "by GMGG"
BRAND_URL = "github.com/gmggyyds/the-great-me"
TAGLINE = "在你问 AI 任何问题之前，先回答这 12 个问题"


def _w(s: str) -> int:
    """显示宽度。终端对齐全靠它，拍脑袋的码点范围一定会错。

    只有 East_Asian_Width 为 W（宽）/ F（全角）的才占 2 格。
    ⚠️ 制表块 █ ░ 和箭头 ← 属于 A（ambiguous），绝大多数终端按 **1 格**渲染——
    按 2 格算会让整张卡的右边框参差不齐（2026-09-10 实测）。
    """
    return sum(2 if unicodedata.east_asian_width(c) in ("W", "F") else 1 for c in s)


def _pad(s: str, width: int) -> str:
    return s + " " * max(0, width - _w(s))


def _bar(n: int, total: int, cells: int = 12, fill: str = "█", empty: str = "░") -> str:
    if total <= 0:
        return empty * cells
    k = round(cells * n / total)
    k = max(1, k) if n else 0
    return fill * min(k, cells) + empty * max(0, cells - k)


def render_terminal(p: Pulse, owner: str = "") -> str:
    inner = 44
    who = f"　{owner}" if owner else ""
    rows: list[str] = []
    rows.append(BRAND_ZH + who)
    rows.append("")
    rows.append(f"12 题　{_bar(p.answered_count, len(QUESTIONS))}　{p.answered_count} / {len(QUESTIONS)}")
    rows.append("")
    biggest = max(p.by_segment.values() or [0])
    for seg, n in p.by_segment.items():
        mark = "　← 最薄" if seg == p.thinnest and p.total else ""
        rows.append(f"{_pad(seg, 14)}{_bar(n, biggest, 10)} {n:>4}{mark}")
    rows.append("")
    delta = f"本周 +{p.added_total}" if p.added_total else "本周无新增"
    rows.append(f"连了 {len(p.sources)} 个源 · {delta} · 陈旧 {p.stale}")
    rows.append("")
    rows.append(f"{BRAND_BY}　{BRAND_URL}")

    top = "┌" + "─" * inner + "┐"
    bot = "└" + "─" * inner + "┘"
    body = ["│ " + _pad(r, inner - 2) + " │" for r in rows]
    return "\n".join([top, *body, bot])


_HTML = """<!DOCTYPE html>
<html lang="zh"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{brand}</title>
<style>
  :root {{ color-scheme: light dark;
    --bg:#0f1115; --card:#171a21; --fg:#e8eaed; --dim:#8b93a1;
    --bar:#3a3f4b; --on:#7dd3a0; --warn:#e3b341; }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; padding:24px 16px; background:var(--bg); color:var(--fg);
    font-family:-apple-system,"PingFang SC","Microsoft YaHei","Noto Sans CJK SC",
      "Helvetica Neue",Arial,sans-serif;
    display:flex; justify-content:center; }}
  .card {{ width:100%; max-width:520px; background:var(--card); border-radius:18px;
    padding:28px 28px 20px; border:1px solid #262b35; }}
  h1 {{ font-size:19px; margin:0 0 2px; letter-spacing:.3px; }}
  .tag {{ color:var(--dim); font-size:12px; margin:0 0 22px; }}
  .big {{ display:flex; align-items:baseline; gap:10px; margin:0 0 6px; }}
  .big b {{ font-size:40px; line-height:1; font-variant-numeric:tabular-nums; }}
  .big span {{ color:var(--dim); font-size:13px; }}
  .track {{ height:8px; border-radius:4px; background:var(--bar); overflow:hidden; margin:0 0 24px; }}
  .track i {{ display:block; height:100%; background:var(--on); }}
  table {{ width:100%; border-collapse:collapse; font-size:14px; }}
  td {{ padding:7px 0; vertical-align:middle; }}
  td.n {{ text-align:right; font-variant-numeric:tabular-nums; width:58px; }}
  td.b {{ width:46%; }}
  .mini {{ height:6px; border-radius:3px; background:var(--bar); overflow:hidden; }}
  .mini i {{ display:block; height:100%; background:#6b7280; }}
  .thin td {{ color:var(--warn); }}
  .thin td:first-child::after {{ content:"　最薄"; font-size:11px; opacity:.75; }}
  .thin .mini i {{ background:var(--warn); }}
  .meta {{ color:var(--dim); font-size:12px; margin:22px 0 0;
    padding-top:14px; border-top:1px solid #262b35;
    display:flex; justify-content:space-between; gap:12px; flex-wrap:wrap; }}
  @media (prefers-color-scheme: light) {{
    :root {{ --bg:#f4f5f7; --card:#fff; --fg:#1b1f24; --dim:#6b7280; --bar:#e6e8ec; }}
    .card {{ border-color:#e6e8ec; }} .meta {{ border-top-color:#e6e8ec; }}
  }}
</style></head><body>
<div class="card">
  <h1>{brand}{who}</h1>
  <p class="tag">{tagline}</p>
  <div class="big"><b>{answered}</b><span>/ {nq} 题已作答</span></div>
  <div class="track"><i style="width:{pct}%"></i></div>
  <table>{rows}</table>
  <p class="meta"><span>连了 {nsrc} 个源 · {delta} · 陈旧 {stale}</span>
     <span>{by} · {url}</span></p>
</div></body></html>
"""


def render_html(p: Pulse, owner: str = "") -> str:
    biggest = max(p.by_segment.values() or [0]) or 1
    rows = []
    for seg, n in p.by_segment.items():
        cls = ' class="thin"' if seg == p.thinnest and p.total else ""
        pct = round(100 * n / biggest)
        rows.append(
            f'<tr{cls}><td>{seg}</td>'
            f'<td class="b"><div class="mini"><i style="width:{pct}%"></i></div></td>'
            f'<td class="n">{n}</td></tr>'
        )
    return _HTML.format(
        brand=BRAND_ZH, who=(f"　{owner}" if owner else ""), tagline=TAGLINE,
        answered=p.answered_count, nq=len(QUESTIONS),
        pct=round(100 * p.answered_count / len(QUESTIONS)),
        rows="".join(rows), nsrc=len(p.sources),
        delta=(f"本周 +{p.added_total}" if p.added_total else "本周无新增"),
        stale=p.stale, by=BRAND_BY, url=BRAND_URL,
    )


def write_html(p: Pulse, out_dir: Path, owner: str = "") -> Path:
    path = out_dir / "card.html"
    guard.assert_not_tracked(path)
    guard.assert_within(out_dir, path)
    out_dir.mkdir(parents=True, exist_ok=True)
    path.write_text(render_html(p, owner), encoding="utf-8")
    return path                # 不 chmod 600：这张卡本来就是给人看的


def build(claims: list[Claim], out_dir: Path, today: str | None = None, *,
          owner: str = "", sources: list[str] | None = None,
          window_days: int = 7) -> tuple[str, Path]:
    p = snapshot(claims, today, window_days=window_days, sources=sources)
    return render_terminal(p, owner), write_html(p, out_dir, owner)


_ = SEGMENTS  # 段序由 schema 定，这里只是显式声明依赖
