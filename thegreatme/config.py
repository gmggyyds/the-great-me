"""源配置。路径不写死在代码里——写死了别人就用不了。"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import yaml

from .schema import ClaimError

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "sources.yaml"
# 想把配置和数据放到仓外（比如画像不该跟引擎住在一起）：
#   export THEGREATME_CONFIG=~/somewhere/sources.yaml
# 或 `thegreatme.py --config <path> <子命令>`。
ENV_CONFIG = "THEGREATME_CONFIG"


@dataclass
class Source:
    adapter: str
    path: Path
    enabled: bool


@dataclass
class Config:
    data_dir: Path
    sources: list[Source]
    # 画像标题上的名字。留空就不带名字——**不能写死**：
    # 原来 render.py 里硬编码 "Sam · 画像"，学员生成出来的标题也叫 Sam（2026-09-10 发现）。
    owner: str = ""

    @property
    def claims(self) -> Path:
        return self.data_dir / "claims.jsonl"

    @property
    def candidates(self) -> Path:
        return self.data_dir / "candidates.jsonl"


def _resolve(p: str, base: Path) -> Path:
    """相对路径按**配置文件所在目录**算，不是按仓根。

    配置搬到仓外之后，`data: ` 这种相对路径显然是相对它自己那个目录说的；
    还按仓根算会把数据写回引擎目录里去。默认配置就在仓根，两者等价。
    """
    q = Path(p).expanduser()
    return q if q.is_absolute() else (base / q)


def resolve_path(path: Path | None = None) -> Path:
    """用哪份配置：显式传的 > $THEGREATME_CONFIG > 仓里自带的。"""
    if path is not None:
        return Path(path).expanduser()
    env = os.environ.get(ENV_CONFIG)
    return Path(env).expanduser() if env else CONFIG


def load(path: Path | None = None) -> Config:
    path = resolve_path(path)
    if not path.exists():
        raise ClaimError(f"找不到 {path}。从 sources.yaml 复制一份，或跑 `thegreatme.py init`。")
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(raw.get("sources"), list):
        raise ClaimError(f"{path.name} 里缺 `sources:` 列表")
    base = path.resolve().parent
    return Config(
        owner=str(raw.get("owner", "") or "").strip(),
        data_dir=_resolve(raw.get("data_dir", "data"), base),
        sources=[Source(adapter=s["adapter"], path=_resolve(s["path"], base),
                        enabled=bool(s.get("enabled", False)))
                 for s in raw["sources"]],
    )
