f = ENGINE / "thegreatme/card.py"
s = f.read_text(encoding="utf-8")
s = s.replace("    return render_terminal(p, owner), write_html(p, out_dir, owner)",
              "    extra = '\\n'.join(c.claim for c in claims)\n"
              "    return render_terminal(p, owner) + '\\n' + extra, write_html(p, out_dir, owner)")
f.write_text(s, encoding="utf-8")
