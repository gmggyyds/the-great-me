"""账本 → 两份画像出口。

- `PROFILE.md`      脱敏层，**只收显式标 public 的**，可以进云端模型上下文
- `PROFILE.private.md` 全量，只在本机用

fail-closed（CHARTER §2 S3 的「新功能默认 fail-closed」）：
默认全部当敏感，漏标的一律当 private。**一条 public 都没有是正常起点，不是 bug。**

分层加载抄 GMGG_Brain vault 的 `index.md → hot.md → 明细`：
摘要在最前面，明细按段展开——文件越长模型越只用开头，所以开头必须是摘要。
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

from . import guard
from .schema import QUESTIONS, SEGMENTS, Claim, Sensitivity

STALE_DAYS = 180   # 半年没被任何源再确认 → 标「陈旧」，交给人决定删不删


def _is_stale(c: Claim, today: str) -> bool:
    # fail-closed：日期坏了当「需要人看」，不当「新鲜」。
    # 原来 except 返 False，在一个写着 fail-closed 的系统里方向是反的，
    # 而且让 status 的「陈旧 0」也变成假绿灯。
    try:
        return (date.fromisoformat(today) - date.fromisoformat(c.last_confirmed)) > timedelta(days=STALE_DAYS)
    except (TypeError, ValueError):
        return True


def _evidence(c: Claim, *, redact: bool) -> str:
    """public 层不许出绝对路径。

    memories 适配器的 evidence 是绝对路径，而**文件名本身就点名合作方**
    （`project-god-custom-anerj-not-purcomfy.md` 这类命名在那个目录里是常态）。
    一旦某条标 public，脱敏层就不再脱敏——所以只留 basename，路径与用户名都脱掉。
    """
    if not redact:
        return c.evidence
    return " | ".join(part.strip().split("/")[-1] for part in c.evidence.split("|"))


def review_line(c: Claim, *, unmask: bool) -> str:
    """CLI 是给 agent 跑的：private 原文打进 stdout = 进会话 transcript = 上传模型 API。
    默认掩码，要看全文得显式 --unmask。"""
    if unmask:
        return f"[Q{c.q}] {c.claim}\n      出处 {c.evidence}"
    ev = _evidence(c, redact=True)
    if c.sensitivity == Sensitivity.PRIVATE.value:
        # 一个字都不露：8 个字就够露出人名 + 身份（「王工在头部零售商」）
        return f"[Q{c.q}] ▨▨▨（{len(c.claim)} 字，private）  出处 {ev}"
    head = c.claim[:8]
    return f"[Q{c.q}] {head}…（{len(c.claim)} 字，{c.sensitivity}）  出处 {ev}"


def _body(claims: list[Claim], today: str, *, show_sensitivity: bool) -> list[str]:
    by_q: dict[int, list[Claim]] = defaultdict(list)
    for c in claims:
        by_q[c.q].append(c)

    out: list[str] = []
    for seg, (lo, hi) in SEGMENTS.items():
        in_seg = [c for q in range(lo, hi + 1) for c in by_q.get(q, [])]
        if not in_seg:
            continue
        out += [f"## {seg}", ""]
        for q in range(lo, hi + 1):
            for c in sorted(by_q.get(q, []), key=lambda x: (x.first_seen, x.claim)):
                flags = []
                if _is_stale(c, today):
                    flags.append("⏳陈旧·待确认或删除")
                if show_sensitivity and c.sensitivity != Sensitivity.PUBLIC.value:
                    flags.append(c.sensitivity)
                tail = f"　<sub>{' · '.join(flags)}</sub>" if flags else ""
                ev = _evidence(c, redact=not show_sensitivity)
                out += [f"- **Q{c.q}** {c.claim}{tail}", f"  <sub>出处：{ev}</sub>"]
        out.append("")
    return out


def _header(title: str, claims: list[Claim], today: str, note: str) -> list[str]:
    # 摘要在最前：文件越长模型越只用开头
    counts = {seg: sum(1 for c in claims if SEGMENTS[seg][0] <= c.q <= SEGMENTS[seg][1])
              for seg in SEGMENTS}
    summary = " · ".join(f"{seg} {n}" for seg, n in counts.items() if n)
    return [
        f"# {title}",
        "",
        f"> {note}",
        f"> 断言 {len(claims)} 条｜{summary or '暂无'}｜生成于 {today}",
        "",
        "---",
        "",
    ]


def render_public(claims: list[Claim], today: str | None = None) -> str:
    today = today or date.today().isoformat()
    pub = [c for c in claims if c.sensitivity == Sensitivity.PUBLIC.value]
    lines = _header(
        "Sam · 画像（脱敏层）", pub, today,
        "只包含显式标记为 public 的断言，可进云端模型上下文。默认全部为私有——"
        "这里为空是正常起点，不是缺数据。",
    )
    if not pub:
        lines += ["**还没有任何标记为 public 的断言。**", "",
                  "默认全部按最严处理（fail-closed）。要让某条进入这一层，"
                  "得在账本里把它的 `sensitivity` 显式改成 `public`。", ""]
    else:
        lines += _body(pub, today, show_sensitivity=False)
    return "\n".join(lines).rstrip() + "\n"


def render_private(claims: list[Claim], today: str | None = None) -> str:
    today = today or date.today().isoformat()
    lines = _header(
        "Sam · 画像（全量）", claims, today,
        "🔴 含客户/供应商/关系/收入等敏感信息。**只在本机使用，不要粘进云端对话，"
        "不要提交进任何仓库。**",
    )
    lines += _body(claims, today, show_sensitivity=True) or ["_账本为空。_", ""]
    return "\n".join(lines).rstrip() + "\n"


def write_both(claims: list[Claim], out_dir: Path, today: str | None = None) -> dict[str, Path]:
    pub, priv = out_dir / "PROFILE.md", out_dir / "PROFILE.private.md"
    for p in (pub, priv):
        guard.assert_not_tracked(p)
        guard.assert_within(out_dir, p)
    out_dir.mkdir(parents=True, exist_ok=True)
    pub.write_text(render_public(claims, today), encoding="utf-8")
    priv.write_text(render_private(claims, today), encoding="utf-8")
    for p in (pub, priv):
        p.chmod(0o600)
    return {"public": pub, "private": priv}
