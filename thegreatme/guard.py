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


def _git(args, cwd):
    try:
        return subprocess.run(["git", *args], cwd=cwd, capture_output=True,
                              text=True, timeout=5)
    except (OSError, subprocess.SubprocessError):
        return None


# 插件缓存的形状：~/.claude/plugins/cache/<市场>/<插件>/<版本>/
# 版本号是目录名的一部分，`claude plugin update` 会换掉整个版本目录。
_PLUGIN_CACHE = ("/.claude/plugins/cache/", "/.claude/plugins/marketplaces/")


def assert_not_in_plugin_cache(path: Path) -> None:
    """插件缓存里的东西会被 `plugin update` 整目录换掉 —— 画像写进去就是等着丢。

    装成插件之后，引擎跑在缓存目录里，而自带的 sources.yaml 写的是 `data_dir: data`，
    相对路径按配置文件所在目录算 → 数据正好落在缓存里。用户不会知道，直到某次更新之后
    155 条断言凭空消失（2026-09-10 装完插件当场复现）。

    这里 fail-closed：宁可不写，也不写到一个随时会被清掉的地方。
    """
    s = str(path.resolve() if path.is_absolute() else path.absolute())
    if any(seg in s for seg in _PLUGIN_CACHE):
        raise ClaimError(
            f"拒绝写 {path}：它在**插件缓存**里，`claude plugin update` 会把整个版本目录换掉，"
            "写进去的画像会随更新一起消失。\n"
            "修法：跑 `thegreatme.py init` 建一份自己的配置（默认落 ~/.the-great-me/），"
            "然后 `export THEGREATME_CONFIG=~/.the-great-me/sources.yaml`。"
        )


def assert_not_tracked(path: Path) -> None:
    """目标若落在某个 git work tree 内，要么该仓没有 remote，要么它得被 ignore。

    判据是「能不能离机」，不是「在不在 git 里」。
    仓里**一个 remote 都没有**时，`git add -A` 也没有地方可推 —— 这正是 README 推荐的
    「给数据目录建个本地 git 仓、不加 remote」：拿到完整版本历史，又物理上传不出去。
    早先只认 ignore，于是**推荐的做法会被自己的护栏拒绝**，报错还让人去 ignore 掉那个
    文件——正好废掉版本历史这个初衷（2026-09-10 实测）。

    每次写都重新查一遍：哪天这个仓被加了 remote，下一次写就会重新开始拒绝。
    """
    # 挂在这里而不是各写入点：5 个写入点都要过 assert_not_tracked，这是唯一的收口。
    assert_not_in_plugin_cache(path)
    d = path.parent
    probe = d if d.exists() else next((p for p in d.parents if p.exists()), Path("/"))
    inside = _git(["rev-parse", "--is-inside-work-tree"], probe)
    if inside is None:
        return                                   # 没有 git 就没有这个风险
    if inside.returncode != 0 or inside.stdout.strip() != "true":
        return
    remotes = _git(["remote"], probe)
    if remotes is not None and remotes.returncode == 0 and not remotes.stdout.strip():
        return                                   # 零 remote：推不出去
    ignored = _git(["check-ignore", "-q", str(path)], probe)
    if ignored is None or ignored.returncode != 0:
        raise ClaimError(
            f"拒绝写 {path}：它在一个**有远端**的 git 仓库里，且未被 git ignore。\n"
            f"画像含客户/供应商/人脉/收入，一次 `git add -A` 就会离机。\n"
            f"两条修法，二选一：\n"
            f"  · 在该仓 .gitignore 里加一行 `{path.parent.name}/`\n"
            f"  · 或把数据目录做成**独立的本地 git 仓、不加 remote**"
            f"（有版本历史，且推不出去）"
        )


def assert_within(root: Path, path: Path) -> None:
    """写入必须待在数据根目录内。现在没有外部输入面，这条是给下一个加 --out-dir 的人留的。"""
    r, p = root.resolve(), path.resolve()
    if not (p == r or r in p.parents):
        raise ClaimError(f"路径越界：{path} 不在 {root} 内")
