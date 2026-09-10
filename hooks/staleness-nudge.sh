#!/usr/bin/env bash
# 催更提醒 —— 会话收尾时，如果画像太久没长就提一句。
#
# 它**只提醒，不写入**。理由：往画像里加东西要先判断「这段挂哪一题、是不是关于本人的」，
# 那是判断不是解析，shell 做不了。硬让 hook 去写，只会得到一堆猜错题号的断言，
# 而错的题号比没有更糟。所以 hook 负责「按时把你叫起来」，真正的活交给 skill。
#
# 装法（Claude Code，~/.claude/settings.json）：
#   { "hooks": { "Stop": [ { "hooks": [ {
#       "type": "command",
#       "command": "bash <本文件绝对路径>",
#       "timeout": 5
#   } ] } ] } }
#
# 调节：
#   THEGREATME_CONFIG   指向你的 sources.yaml（不设就用引擎仓自带那份）
#   TGM_NUDGE_DAYS      多少天没长就提醒，默认 7
#   TGM_NUDGE_COOLDOWN  提醒后多少天内不再提，默认 3（防止每轮会话都唠叨）
set -uo pipefail

DAYS="${TGM_NUDGE_DAYS:-7}"
COOLDOWN="${TGM_NUDGE_COOLDOWN:-3}"
STAMP="${TMPDIR:-/tmp}/.tgm-nudge-stamp"

emit() {  # Stop hook 的可见通道是 stdout 的 JSON systemMessage；exit 0 时 stderr 永远不显示
  python3 -c 'import json,sys; print(json.dumps({"systemMessage": sys.argv[1]}, ensure_ascii=False))' "$1"
  exit 0
}
quiet() { echo '{}'; exit 0; }

# 冷却期内不吭声
if [ -f "$STAMP" ]; then
  last=$(cat "$STAMP" 2>/dev/null || echo 0)
  now=$(date +%s)
  [ $(( (now - last) / 86400 )) -lt "$COOLDOWN" ] && quiet
fi

ENGINE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
[ -f "$ENGINE/thegreatme.py" ] || quiet

MSG=$(python3 - "$ENGINE" "$DAYS" <<'PY' 2>/dev/null
import sys, json, os
from datetime import date, timedelta
sys.path.insert(0, sys.argv[1])
try:
    from thegreatme import config
except Exception:
    raise SystemExit(0)
try:
    cfg = config.load()
    p = cfg.claims
    if not p.exists():
        raise SystemExit(0)
    newest = date.min
    n = 0
    for line in p.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            d = json.loads(line)
            n += 1
            fs = date.fromisoformat(d.get("first_seen", ""))
            newest = max(newest, fs)
        except Exception:
            continue
    if not n:
        raise SystemExit(0)
    gap = (date.today() - newest).days
    if gap >= int(sys.argv[2]):
        print(f"💡 the-great-me：画像已 {gap} 天没长（账本 {n} 条）。"
              f"说一句「喂一轮画像」，我扫最近的笔记按 12 题标号收进来；"
              f"或「出个画像周报」看看哪一段最薄。")
except Exception:
    raise SystemExit(0)
PY
)

[ -n "${MSG:-}" ] || quiet
date +%s > "$STAMP" 2>/dev/null || true
emit "$MSG"
