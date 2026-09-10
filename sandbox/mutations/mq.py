f = ENGINE / "thegreatme/adapters/metaquestions.py"
s = f.read_text(encoding="utf-8")
import re as _re
s = _re.sub(r"def harvest\(([^)]*)\)( -> [^:]+)?:", r"def harvest(\1)\2:\n    return []", s, count=1)
f.write_text(s, encoding="utf-8")
