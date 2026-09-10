#!/usr/bin/env python3
"""the-great-me — 让 12 题的答案常驻，并跟着你长。

    thegreatme.py harvest      跑所有启用的源 → 候选（不直接进账本）
    thegreatme.py review       看候选（默认掩码，--unmask 看全文）
    thegreatme.py accept --all 候选进账本
    thegreatme.py render       账本 → PROFILE.md（可外传）+ PROFILE.private.md（本机）
    thegreatme.py status       账本体检
    thegreatme.py doctor       检查配置与数据安全（第一次用先跑这个）

源配置在 `sources.yaml`。数据落 `data/`（已 gitignore + 写前自查）。
"""
from __future__ import annotations

import argparse
import os
import sys
from collections import Counter
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from thegreatme import card as card_mod  # noqa: E402
from thegreatme import config, guard, ledger  # noqa: E402
from thegreatme import report as report_mod  # noqa: E402
from thegreatme import render as render_mod  # noqa: E402
from thegreatme.adapters import folder, memories, metaquestions, relations  # noqa: E402
from thegreatme.questions import QUESTION_TEXT, SOURCE_VERSION  # noqa: E402
from thegreatme.schema import (  # noqa: E402
    SEGMENTS, ClaimError, dedup_key, load_jsonl, save_jsonl,
)

ADAPTERS = {
    "metaquestions": metaquestions.harvest,
    "folder": folder.harvest,
    "relations": relations.harvest,
    "memories": memories.harvest,
}


def cmd_doctor(args) -> int:
    cfg = config.load()
    print(f"12 题来自 meta-questions v{SOURCE_VERSION}（{len(QUESTION_TEXT)} 题）")
    print(f"数据目录 {cfg.data_dir}")
    try:
        guard.assert_not_tracked(cfg.claims)
        print("  ✅ 数据不会被 git 收走")
    except ClaimError as e:
        print(f"  🔴 {e}")
        return 2
    print("源：")
    for s in cfg.sources:
        mark = "✅" if s.enabled else "· 关闭"
        exists = "" if s.path.exists() or not s.enabled else "  🔴 路径不存在"
        print(f"  {mark} {s.adapter:16s} {s.path}{exists}")
    if not any(s.enabled and s.path.exists() for s in cfg.sources):
        print("\n还没有可用的源。最快的开始方式：把 12 题的对话记录复制成 .md")
        print(f"放进 {cfg.data_dir / 'metaquestions'}/，然后跑 `thegreatme.py harvest`。")
    return 0


def cmd_harvest(args) -> int:
    cfg = config.load()
    existing = {dedup_key(c) for c in load_jsonl(cfg.candidates)}
    fresh, skipped_total = [], 0
    for s in cfg.sources:
        if not s.enabled:
            continue
        fn = ADAPTERS.get(s.adapter)
        if fn is None:
            print(f"  ⚠️  未知适配器 {s.adapter}，跳过")
            continue
        try:
            if s.adapter == "folder":
                got, skipped = folder.harvest_with_report(s.path)
                skipped_total += skipped
            else:
                got = fn(s.path)
        except Exception as e:                    # 一个源炸不该带走别的源
            print(f"  ⚠️  {s.adapter} 失败，已跳过：{e}")
            continue
        new = [c for c in got if dedup_key(c) not in existing]
        for c in new:
            existing.add(dedup_key(c))
        fresh += new
        print(f"  {s.adapter:16s} 抽出 {len(got):3d} 条，新增 {len(new):3d} 条")
    save_jsonl(cfg.candidates, load_jsonl(cfg.candidates) + fresh)
    if skipped_total:
        print(f"\n  ⓘ inbox 里有 {skipped_total} 段没标题号，没收。")
        print("     它们不是废的——拿去问你的 AI：「这段改变了我 12 题里的哪一条？」")
        print("     挂得上就回来在段首写 `Q7:` 再跑一次。")
    print(f"→ 候选共 {len(load_jsonl(cfg.candidates))} 条待审")
    return 0


def cmd_review(args) -> int:
    if args.unmask:
        print("⚠️  本次输出含 private 断言全文，不要在 AI 会话中运行。", file=sys.stderr)
    cfg = config.load()
    cands = load_jsonl(cfg.candidates)
    if not cands:
        print("没有待审候选。先跑 harvest。")
        return 0
    for seg, (lo, hi) in SEGMENTS.items():
        rows = [c for c in cands if lo <= c.q <= hi]
        if not rows:
            continue
        print(f"\n## {seg}（{len(rows)} 条）")
        for c in rows[: args.limit]:
            print("  " + render_mod.review_line(c, unmask=args.unmask))
    print(f"\n合计 {len(cands)} 条待审。进账本：thegreatme.py accept --all")
    return 0


def cmd_accept(args) -> int:
    cfg = config.load()
    cands = load_jsonl(cfg.candidates)
    if not cands:
        print("没有待审候选。")
        return 0
    keep = cands if args.all else [c for c in cands if c.q == args.q]
    if not keep:
        print("没有符合条件的候选。")
        return 1
    merged, stats = ledger.merge(load_jsonl(cfg.claims), keep)
    save_jsonl(cfg.claims, merged)
    kept_ids = {id(c) for c in keep}
    rest = [c for c in cands if id(c) not in kept_ids]
    save_jsonl(cfg.candidates, rest)
    print(f"→ 新增 {stats['added']} · 更新 {stats['updated']} · 无变化 {stats['unchanged']}"
          f"；剩余待审 {len(rest)}")
    if args.all:
        print("⚠️  accept --all 是省事路径。断言准不准，只有你自己看过才算数。")
    return 0


def cmd_report(args) -> int:
    cfg = config.load()
    claims = load_jsonl(cfg.claims)
    srcs = [s.adapter for s in cfg.sources if s.enabled]
    text = report_mod.build(claims, window_days=args.days, unmask=args.unmask,
                            owner=cfg.owner, sources=srcs, per_segment=args.top)
    path = report_mod.write(text, cfg.data_dir)
    print(f"  周报 {path}")
    if args.print:
        print()
        print(text)
    elif not args.unmask:
        print("  （默认打码。`report --print` 直接打到终端，`--unmask` 看全文——别在 AI 会话里跑）")
    return 0


def cmd_card(args) -> int:
    cfg = config.load()
    claims = load_jsonl(cfg.claims)
    srcs = [s.adapter for s in cfg.sources if s.enabled]
    term, path = card_mod.build(claims, cfg.data_dir, owner=cfg.owner,
                                sources=srcs, window_days=args.days)
    print()
    print(term)
    print()
    print(f"  可截图版 {path}（自包含 HTML，浏览器直接打开）")
    print("  这张卡**不含任何断言内容**，只有数字和题号——随便发。")
    return 0


def cmd_render(args) -> int:
    cfg = config.load()
    claims = load_jsonl(cfg.claims)
    out = render_mod.write_both(claims, cfg.data_dir, owner=cfg.owner)
    npub = sum(1 for c in claims if c.sensitivity == "public")
    print(f"  可外传 {out['public']}（{npub} 条 public）")
    print(f"  本机用 {out['private']}（{len(claims)} 条）")
    if claims and npub == 0:
        print("\n  ⓘ 一条 public 都没有是**正常起点**——默认全部按最严处理。")
        print("     要让某条能外传，在 claims.jsonl 里把它的 sensitivity 改成 public。")
    return 0


def cmd_status(args) -> int:
    cfg = config.load()
    claims = load_jsonl(cfg.claims)
    today = date.today().isoformat()
    print(f"账本 {cfg.claims}\n  断言 {len(claims)} 条")
    for seg, (lo, hi) in SEGMENTS.items():
        n = sum(1 for c in claims if lo <= c.q <= hi)
        print(f"    {seg}: {n}" + ("   ← 这段还空着，只能你自己答" if n == 0 else ""))
    print(f"  敏感级: {dict(Counter(c.sensitivity for c in claims))}")
    print(f"  陈旧(>{render_mod.STALE_DAYS}天): {sum(1 for c in claims if render_mod._is_stale(c, today))}")
    print(f"  无出处: {sum(1 for c in claims if not c.evidence.strip())}  ← 必须是 0")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="the-great-me · 让 12 题的答案常驻并跟着你长")
    ap.add_argument("--config", metavar="PATH",
                    help="用别处的 sources.yaml（也可用环境变量 THEGREATME_CONFIG）。"
                         "里面的相对路径按该文件所在目录算。")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("doctor").set_defaults(fn=cmd_doctor)
    sub.add_parser("harvest").set_defaults(fn=cmd_harvest)
    r = sub.add_parser("review")
    r.add_argument("--limit", type=int, default=8)
    r.add_argument("--unmask", action="store_true", help="打印全文。⚠️ 含 private，别在 AI 会话里跑")
    r.set_defaults(fn=cmd_review)
    a = sub.add_parser("accept")
    a.add_argument("--all", action="store_true")
    a.add_argument("--q", type=int)
    a.set_defaults(fn=cmd_accept)
    sub.add_parser("render").set_defaults(fn=cmd_render)
    rp = sub.add_parser("report", help="周报：这周变了什么 + 哪块还是空的")
    rp.add_argument("--days", type=int, default=7)
    rp.add_argument("--print", action="store_true", help="同时打到终端")
    rp.add_argument("--top", type=int, default=8,
                    help="每段最多列几条新增明细，0 = 不截断（默认 8）")
    rp.add_argument("--unmask", action="store_true",
                    help="新增明细显示全文。⚠️ 含 private，别在 AI 会话里跑")
    rp.set_defaults(fn=cmd_report)
    cd = sub.add_parser("card", help="进度卡：零内容、可截图、可传播")
    cd.add_argument("--days", type=int, default=7)
    cd.set_defaults(fn=cmd_card)
    sub.add_parser("status").set_defaults(fn=cmd_status)
    args = ap.parse_args()
    # 落成环境变量，config.load() 的 7 个调用点就都不用改签名
    if args.config:
        os.environ[config.ENV_CONFIG] = args.config
    try:
        return args.fn(args)
    except ClaimError as e:
        print(f"🔴 {e}", file=sys.stderr)
        return 2
    except Exception as e:
        print(f"🔴 未预期错误：{type(e).__name__}: {e}", file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
