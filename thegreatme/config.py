"""源配置。路径不写死在代码里——写死了别人就用不了。"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

from .schema import ClaimError

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "sources.yaml"


@dataclass
class Source:
    adapter: str
    path: Path
    enabled: bool


@dataclass
class Config:
    data_dir: Path
    sources: list[Source]

    @property
    def claims(self) -> Path:
        return self.data_dir / "claims.jsonl"

    @property
    def candidates(self) -> Path:
        return self.data_dir / "candidates.jsonl"


def _resolve(p: str) -> Path:
    q = Path(p).expanduser()
    return q if q.is_absolute() else (ROOT / q)


def load(path: Path | None = None) -> Config:
    path = path or CONFIG
    if not path.exists():
        raise ClaimError(f"找不到 {path.name}。从 sources.yaml 复制一份，或跑 `thegreatme.py init`。")
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(raw.get("sources"), list):
        raise ClaimError(f"{path.name} 里缺 `sources:` 列表")
    return Config(
        data_dir=_resolve(raw.get("data_dir", "data")),
        sources=[Source(adapter=s["adapter"], path=_resolve(s["path"]),
                        enabled=bool(s.get("enabled", False)))
                 for s in raw["sources"]],
    )
