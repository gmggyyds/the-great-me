"""周报与进度卡。

最要紧的一条是 `test_card_leaks_no_claim_content`：进度卡是**唯一一个设计成给人看见**的
出口，它能被传播的前提就是它一个字的断言正文都不碰。这条测试红了就意味着截图会泄露客户/
供应商/人脉——比任何功能回归都严重。
"""
from datetime import date, timedelta

import pytest

from thegreatme import card as card_mod
from thegreatme import report as report_mod
from thegreatme.pulse import snapshot
from thegreatme.schema import Claim

SECRET = "王工在头部零售商做买手，能把我们的货直接排进货架"
TODAY = "2026-09-10"


def mk(q, claim=SECRET, days_ago=0, confirmed_ago=None, sensitivity="private"):
    t = date.fromisoformat(TODAY)
    fs = (t - timedelta(days=days_ago)).isoformat()
    lc = (t - timedelta(days=confirmed_ago if confirmed_ago is not None else days_ago)).isoformat()
    return Claim(q=q, claim=claim, evidence="notes/secret_client_list.md",
                 source="folder", first_seen=fs, last_confirmed=lc,
                 sensitivity=sensitivity)


# ---------- pulse ----------

def test_counts_by_segment_and_question():
    p = snapshot([mk(1), mk(1), mk(7), mk(12)], TODAY)
    assert p.total == 4
    assert p.by_segment == {"我是谁": 2, "我手里有什么": 0, "我认识谁": 1, "杠杆在哪": 1}
    assert p.by_question[1] == 2
    assert p.answered == [1, 7, 12]
    assert p.empty == [2, 3, 4, 5, 6, 8, 9, 10, 11]


def test_thinnest_is_the_emptiest_segment():
    p = snapshot([mk(1), mk(1), mk(1), mk(4), mk(7), mk(12)], TODAY)
    assert p.thinnest == "我手里有什么"      # 1 条，比 我认识谁/杠杆在哪 的 1 条更靠前


def test_added_counts_only_the_window():
    p = snapshot([mk(1, days_ago=2), mk(1, days_ago=30)], TODAY, window_days=7)
    assert p.added["我是谁"] == 1
    assert p.added_total == 1


def test_refreshed_is_old_but_recently_confirmed():
    """不是新的，但这轮又被源确认了一次——说明那条依据还在。"""
    p = snapshot([mk(4, days_ago=60, confirmed_ago=1)], TODAY, window_days=7)
    assert p.added_total == 0
    assert p.refreshed == 1


def test_stale_counts_over_the_threshold():
    p = snapshot([mk(4, days_ago=400, confirmed_ago=400), mk(4, days_ago=1)], TODAY)
    assert p.stale == 1


def test_empty_ledger_does_not_crash():
    p = snapshot([], TODAY)
    assert p.total == 0 and len(p.empty) == 12 and p.thinnest in ("我是谁",)


# ---------- 进度卡：可传播的前提 ----------

@pytest.mark.parametrize("renderer", ["terminal", "html"])
def test_card_leaks_no_claim_content(renderer):
    """🔴 进度卡是拿来截图发出去的。断言正文、证据指针，一个都不许出现。"""
    claims = [mk(1), mk(4), mk(7), mk(12)]
    p = snapshot(claims, TODAY)
    out = (card_mod.render_terminal(p) if renderer == "terminal"
           else card_mod.render_html(p))
    assert SECRET not in out
    assert "王工" not in out
    assert "secret_client_list" not in out
    for c in claims:                      # 逐条查，别只查那个显眼的
        assert c.claim not in out
        assert c.evidence not in out


def test_card_build_end_to_end_leaks_nothing(tmp_path):
    """走 CLI 真正调用的那条路，并且**把写到磁盘的 HTML 读回来查**。

    只测 render_terminal / render_html 是不够的：泄露可以发生在 build() 里，
    也可以发生在落盘那一步。2026-09-10 变异实测——在 build() 里拼上正文，
    只测渲染函数的那批用例全绿。
    """
    claims = [mk(1), mk(4), mk(7), mk(12)]
    term, path = card_mod.build(claims, tmp_path, TODAY, owner="某人",
                                sources=["folder", "memories"])
    on_disk = path.read_text(encoding="utf-8")
    for blob in (term, on_disk):
        assert SECRET not in blob
        assert "王工" not in blob
        assert "secret_client_list" not in blob
        for c in claims:
            assert c.claim not in blob
            assert c.evidence not in blob
    assert path.name == "card.html" and "the-great-me" in on_disk


def test_report_write_end_to_end_masks_on_disk(tmp_path):
    """周报同理：落盘那份也得是打码的。"""
    text = report_mod.build([mk(7, days_ago=1)], TODAY)
    path = report_mod.write(text, tmp_path, TODAY)
    on_disk = path.read_text(encoding="utf-8")
    assert SECRET not in on_disk and "▨▨▨" in on_disk
    assert path.name == f"REPORT_{report_mod.iso_week(TODAY)}.md"
    assert oct(path.stat().st_mode)[-3:] == "600"


def test_card_shows_the_numbers_that_make_it_worth_sharing():
    p = snapshot([mk(1), mk(4), mk(4), mk(7)], TODAY)
    out = card_mod.render_terminal(p)
    assert "the-great-me" in out and "by GMGG" in out
    assert "我是谁" in out and "杠杆在哪" in out
    assert "3 / 12" in out                # 12 题答了 3 题


def test_card_box_edges_line_up():
    """CJK / 制表块 / 箭头混排时右边框必须齐。宽度算错就是这里露出来。"""
    p = snapshot([mk(1), mk(4)], TODAY)
    lines = card_mod.render_terminal(p, owner="某人").splitlines()
    widths = {card_mod._w(ln) for ln in lines}
    assert len(widths) == 1, f"边框不齐，出现了 {sorted(widths)} 几种宽度"


def test_block_and_arrow_glyphs_count_as_one_column():
    """█ ░ ← 是 East_Asian_Width=A（ambiguous），终端按 1 格渲染。
    按 2 格算会让整张卡参差不齐（2026-09-10 实测）。"""
    assert card_mod._w("█░←") == 3
    assert card_mod._w("我是谁") == 6


# ---------- 周报 ----------

def test_report_masks_by_default():
    text = report_mod.build([mk(7, days_ago=1)], TODAY)
    assert SECRET not in text
    assert "▨▨▨" in text


def test_report_unmask_shows_content():
    text = report_mod.build([mk(7, days_ago=1)], TODAY, unmask=True)
    assert SECRET in text


def test_report_names_the_thin_segment_and_empty_questions():
    """周报的价值在缺口，不在进度。"""
    claims = [mk(4, days_ago=1) for _ in range(9)] + [mk(1, days_ago=1)]
    text = report_mod.build(claims, TODAY)
    assert "最薄" in text
    assert "Q10" in text                       # 杠杆段一条都没有
    assert "Swap Test" in text                 # 把题目原文摆出来，不只报题号


def test_report_top_zero_means_no_truncation():
    """rows[:0] 是「取零个」不是「不限制」——这个 off-by-one 会让 --top 0 语义反过来。"""
    claims = [mk(4, days_ago=1) for _ in range(12)]
    few = report_mod.build(claims, TODAY, per_segment=3)
    allrows = report_mod.build(claims, TODAY, per_segment=0)
    assert few.count("▨▨▨") == 3
    assert allrows.count("▨▨▨") == 12
    assert "还有 9 条" in few


def test_report_says_so_when_nothing_changed():
    text = report_mod.build([mk(4, days_ago=90, confirmed_ago=90)], TODAY)
    assert "新增 0 条" in text


def test_report_and_card_carry_the_brand():
    p = snapshot([mk(1)], TODAY)
    assert "the-great-me" in report_mod.build([mk(1)], TODAY)
    assert "gmggyyds/the-great-me" in card_mod.render_html(p)


# ---------- owner 不许写死 ----------

def test_owner_is_not_hardcoded():
    """曾经 render.py 里写死 "Sam · 画像"，学员生成的标题也叫 Sam。"""
    from thegreatme import render
    assert render._title("", "全量") == "画像（全量）"
    assert render._title("阿May", "全量") == "阿May · 画像（全量）"
    assert "Sam" not in render.render_private([mk(1)], TODAY)
