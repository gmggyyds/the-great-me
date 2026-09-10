f = ENGINE / "thegreatme/render.py"
s = f.read_text(encoding="utf-8")
s = s.replace('def review_line(c: Claim, *, unmask: bool) -> str:',
              'def review_line(c: Claim, *, unmask: bool = True) -> str:\n    unmask = True')
f.write_text(s, encoding="utf-8")
