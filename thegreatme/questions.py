"""12 题的规范文本。

**不手抄。** `questions.yaml` 由 `tools/sync_questions.py` 从 meta-questions 的真源
（`source/meta_questions.yaml`）生成——两个仓各写一份题目文本，早晚漂移。
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml

_PATH = Path(__file__).parent / "questions.yaml"


@lru_cache(maxsize=1)
def _data() -> dict:
    return yaml.safe_load(_PATH.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def load_questions() -> dict[int, dict]:
    """{题号: {zh, en, want, id}}"""
    return {q["n"]: q for s in _data()["segments"] for q in s["questions"]}


QUESTION_TEXT = load_questions()
SOURCE_VERSION = _data()["version"]
