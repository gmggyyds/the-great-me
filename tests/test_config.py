"""配置定位与路径解析。

要钉住的是一件容易悄悄搞错的事：**配置搬到仓外之后，里面的相对路径按谁算。**
`data: ` 显然是相对配置文件自己那个目录说的；若还按仓根算，数据会被写回引擎目录里，
而引擎目录是个公开仓——画像就这么进了 git。
"""
import textwrap
from pathlib import Path

import pytest

from thegreatme import config
from thegreatme.schema import ClaimError

SAMPLE = textwrap.dedent("""
    data_dir: mydata
    sources:
      - adapter: folder
        path: inbox
        enabled: true
      - adapter: memories
        path: ~/notes
        enabled: false
""")


def _write(tmp_path, text=SAMPLE, name="sources.yaml"):
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    return p


def test_explicit_path_wins(tmp_path):
    cfg = config.load(_write(tmp_path))
    assert cfg.data_dir == tmp_path / "mydata"


def test_env_var_is_used_when_no_explicit_path(tmp_path, monkeypatch):
    monkeypatch.setenv(config.ENV_CONFIG, str(_write(tmp_path)))
    assert config.load().data_dir == tmp_path / "mydata"


def test_explicit_path_beats_env_var(tmp_path, monkeypatch):
    other = tmp_path / "other"
    other.mkdir()
    monkeypatch.setenv(config.ENV_CONFIG, str(_write(other)))
    cfg = config.load(_write(tmp_path))
    assert cfg.data_dir == tmp_path / "mydata"


def test_falls_back_to_repo_config(monkeypatch):
    monkeypatch.delenv(config.ENV_CONFIG, raising=False)
    assert config.resolve_path() == config.CONFIG


def test_relative_paths_are_relative_to_the_config_file(tmp_path, monkeypatch):
    """核心用例：配置在仓外时，相对路径必须落在配置旁边，不能落回仓里。"""
    monkeypatch.setenv(config.ENV_CONFIG, str(_write(tmp_path)))
    cfg = config.load()
    assert cfg.data_dir == tmp_path / "mydata"
    folder = next(s for s in cfg.sources if s.adapter == "folder")
    assert folder.path == tmp_path / "inbox"
    # 决不能解析到引擎仓里去——那是公开仓
    assert config.ROOT not in cfg.data_dir.parents
    assert config.ROOT not in folder.path.parents


def test_tilde_paths_expand_to_home_not_to_the_config_dir(tmp_path, monkeypatch):
    """`~/notes` 要展开成家目录，不能被当成相对路径挂到配置目录下面。"""
    monkeypatch.setenv(config.ENV_CONFIG, str(_write(tmp_path)))
    mem = next(s for s in config.load().sources if s.adapter == "memories")
    assert mem.path == Path.home() / "notes"
    assert mem.path != tmp_path / "~/notes"


def test_default_config_still_resolves_into_the_repo():
    """默认那份就在仓根，语义不变——这次改动不许动到开箱即用的行为。"""
    cfg = config.load(config.CONFIG)
    assert cfg.data_dir == config.ROOT / "data"


def test_claims_and_candidates_live_in_data_dir(tmp_path):
    cfg = config.load(_write(tmp_path))
    assert cfg.claims == tmp_path / "mydata" / "claims.jsonl"
    assert cfg.candidates == tmp_path / "mydata" / "candidates.jsonl"


def test_missing_config_says_which_path(tmp_path):
    with pytest.raises(ClaimError) as e:
        config.load(tmp_path / "nope.yaml")
    assert "nope.yaml" in str(e.value)


def test_config_without_sources_list_is_rejected(tmp_path):
    p = _write(tmp_path, "data_dir: x\n")
    with pytest.raises(ClaimError) as e:
        config.load(p)
    assert "sources" in str(e.value)
