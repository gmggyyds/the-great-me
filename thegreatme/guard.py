"""写入前的护栏。

存在的理由：`render.py` 里写着「不要提交进任何仓库」——**文案没有执行力**。
而它默认写入的 `~/.claude/self/` 恰好在一个带 GitHub remote 的 git 仓里，
`PROFILE.private.md` 一度不在 ignore 名单上，离一次 `git add -A` 就上云。

所以写之前自己查一遍，别指望人记得配 .gitignore。
"""
from __future__ import annotations

import subprocess
from pathlib import Path

from .schema import ClaimError


def assert_not_tracked(path: Path) -> None:
    """目标若落在某个 git work tree 内，必须被 ignore；否则拒绝写。"""
    d = path.parent
    probe = d if d.exists() else next((p for p in d.parents if p.exists()), Path("/"))
    try:
        inside = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"], cwd=probe,
            capture_output=True, text=True, timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return                                   # 没有 git 就没有这个风险
    if inside.returncode != 0 or inside.stdout.strip() != "true":
        return
    ignored = subprocess.run(["git", "check-ignore", "-q", str(path)], cwd=probe,
                             capture_output=True, timeout=5)
    if ignored.returncode != 0:
        raise ClaimError(
            f"拒绝写 {path}：它在一个 git 仓库里且**未被 git ignore**。\n"
            f"画像含客户/供应商/人脉/收入，一次 `git add -A` 就会离机。\n"
            f"修法：在该仓 .gitignore 里加一行 `{path.parent.name}/`，再重跑。"
        )


def assert_within(root: Path, path: Path) -> None:
    """写入必须待在数据根目录内。现在没有外部输入面，这条是给下一个加 --out-dir 的人留的。"""
    r, p = root.resolve(), path.resolve()
    if not (p == r or r in p.parents):
        raise ClaimError(f"路径越界：{path} 不在 {root} 内")
