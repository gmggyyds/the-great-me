"""账本合并：候选进账本时的语义。

存在的理由是一个致命 bug：原来 `accept` 用 `dedup_key` 判「进不进账本」、
用 dataclass 的 `__eq__` 判「从候选里删不删」——**两套相等性**。
于是人审后把 confidence 提到 high、sensitivity 放开、时间刷新的那条，
**不进账本，但照样从候选里被删掉，一个字不报**。

对一个「审」就是核心闸门的系统，静默作废人审结果是最致命的一种 bug。
所以合并必须是 merge 而不是 skip：命中已有 → 更新可变字段，保留 first_seen。
"""
from __future__ import annotations

from dataclasses import replace

from .schema import Claim, dedup_key

# 人审能改、且应该被带进账本的字段。first_seen 不在其中——它记的是「什么时候第一次知道」。
MUTABLE = ("claim", "last_confirmed", "confidence", "sensitivity", "source")


def merge(existing: list[Claim], incoming: list[Claim]) -> tuple[list[Claim], dict[str, int]]:
    """返回 (合并后的账本, {added, updated, unchanged})。"""
    index = {dedup_key(c): i for i, c in enumerate(existing)}
    out = list(existing)
    stats = {"added": 0, "updated": 0, "unchanged": 0}

    for c in incoming:
        k = dedup_key(c)
        if k not in index:
            index[k] = len(out)
            out.append(c)
            stats["added"] += 1
            continue
        cur = out[index[k]]
        changes = {f: getattr(c, f) for f in MUTABLE if getattr(c, f) != getattr(cur, f)}
        # last_confirmed 只前进不后退：重跑旧快照不该让账本倒退
        if "last_confirmed" in changes and changes["last_confirmed"] < cur.last_confirmed:
            del changes["last_confirmed"]
        if changes:
            out[index[k]] = replace(cur, **changes)
            stats["updated"] += 1
        else:
            stats["unchanged"] += 1
    return out, stats
