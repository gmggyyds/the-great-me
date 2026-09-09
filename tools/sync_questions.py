#!/usr/bin/env python3
"""从 meta-questions 真源重新生成 thegreatme/questions.yaml。

两个仓各写一份题目文本 = 双权威 = 早晚漂移。所以这里只从真源生成。

    python3 tools/sync_questions.py [--source ~/repos/meta-questions/source/meta_questions.yaml]
"""
from __future__ import annotations

import argparse
from pathlib import Path

import yaml

DEFAULT = Path.home() / "repos" / "meta-questions" / "source" / "meta_questions.yaml"
OUT = Path(__file__).resolve().parent.parent / "thegreatme" / "questions.yaml"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source", type=Path, default=DEFAULT)
    a = ap.parse_args()
    if not a.source.exists():
        print(f"🔴 找不到 meta-questions 真源：{a.source}\n"
              f"   先 clone：git clone https://github.com/gmggyyds/meta-questions ~/repos/meta-questions")
        return 2
    src = yaml.safe_load(a.source.read_text(encoding="utf-8"))
    out = {
        "_generated_from": f"meta-questions v{src['version']} · source/meta_questions.yaml",
        "_warning": "生成物。别手改——改了就和 meta-questions 漂移了。改真源后重跑 tools/sync_questions.py。",
        "version": src["version"],
        "segments": [
            {"n": s["n"], "title_zh": s["title_zh"], "title_en": s["title_en"],
             "questions": [{"id": q["id"], "n": int(q["id"][1:]), "zh": q["zh"],
                            "en": q["en"], "want": q["want"]} for q in s["questions"]]}
            for s in sorted(src["segments"], key=lambda x: x["n"])
        ],
    }
    OUT.write_text(yaml.safe_dump(out, allow_unicode=True, sort_keys=False, width=10**6),
                   encoding="utf-8")
    n = sum(len(s["questions"]) for s in out["segments"])
    print(f"✅ {OUT.name} ← meta-questions v{src['version']}（{n} 题）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
