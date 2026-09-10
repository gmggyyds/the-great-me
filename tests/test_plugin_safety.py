"""装成插件之后的写入安全 + `init`。

背景：插件装到 `~/.claude/plugins/cache/<市场>/<插件>/<版本>/`，**版本号是目录名的一部分**，
`claude plugin update` 换掉整个版本目录。而引擎自带的 sources.yaml 写的是 `data_dir: data`，
相对路径按配置文件所在目录算 → 数据正好落在缓存里。用户不会知道，直到某次更新之后画像凭空消失。

2026-09-10 装完插件当场复现：`doctor` 对着插件缓存报「✅ 数据不会被 git 收走」——假绿灯。
"""
from pathlib import Path

import pytest

from thegreatme import guard
from thegreatme.schema import ClaimError

CACHE = ".claude/plugins/cache/the-great-me/the-great-me/0.1.0/data/claims.jsonl"
MARKET = ".claude/plugins/marketplaces/the-great-me/data/claims.jsonl"


def test_refuses_to_write_into_plugin_cache(tmp_path):
    with pytest.raises(ClaimError, match="插件缓存"):
        guard.assert_not_in_plugin_cache(tmp_path / CACHE)


def test_refuses_to_write_into_marketplace_cache(tmp_path):
    with pytest.raises(ClaimError, match="插件缓存"):
        guard.assert_not_in_plugin_cache(tmp_path / MARKET)


def test_error_points_at_a_command_that_exists(tmp_path):
    """报错让人跑 `init`——那个命令必须真的在。
    此前 config.load 的报错里就写着「或跑 thegreatme.py init」，而 init 根本不存在，
    等于把人指到一条死路上（2026-09-10 发现）。"""
    import thegreatme as _pkg  # noqa: F401
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "tgm_cli", Path(__file__).resolve().parent.parent / "thegreatme.py")
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)
    with pytest.raises(ClaimError) as e:
        guard.assert_not_in_plugin_cache(tmp_path / CACHE)
    assert "init" in str(e.value)
    assert hasattr(cli, "cmd_init"), "报错指向的 init 命令不存在"


def test_normal_paths_pass(tmp_path):
    guard.assert_not_in_plugin_cache(tmp_path / "data" / "claims.jsonl")
    guard.assert_not_in_plugin_cache(Path.home() / ".the-great-me/data/claims.jsonl")


def test_the_check_runs_on_every_write_path(tmp_path, monkeypatch):
    """挂在 assert_not_tracked 里，因为 5 个写入点都要过它——这是唯一的收口。
    只在某一个出口加检查，另外四个就是敞开的。"""
    called = []
    real = guard.assert_not_in_plugin_cache
    monkeypatch.setattr(guard, "assert_not_in_plugin_cache",
                        lambda p: (called.append(p), real(p))[1])
    guard.assert_not_tracked(tmp_path / "data" / "claims.jsonl")
    assert called, "assert_not_tracked 没有过插件缓存检查"


def test_init_creates_config_outside_the_cache(tmp_path):
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "tgm_cli2", Path(__file__).resolve().parent.parent / "thegreatme.py")
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)

    class A:
        path = str(tmp_path / "mine")
        force = False

    assert cli.cmd_init(A()) == 0
    cfg = tmp_path / "mine" / "sources.yaml"
    assert cfg.exists()
    assert (tmp_path / "mine" / "data" / "inbox").is_dir()
    assert (tmp_path / "mine" / "data" / "metaquestions").is_dir()
    # 再跑一次不覆盖
    assert cli.cmd_init(A()) == 0
