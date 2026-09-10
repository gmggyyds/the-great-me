f = ENGINE / "thegreatme/guard.py"
s = f.read_text(encoding="utf-8")
f.write_text(s.replace("    assert_not_in_plugin_cache(path)\n", ""), encoding="utf-8")
