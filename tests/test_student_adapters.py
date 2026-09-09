"""学员版适配器：从「12 题的对话记录」和「inbox 文件夹」抽 claim。

为什么这两个是学员版的核心：
Sam 那两个适配器（relations / memories）读的是他专属的文件，学员一个都没有。
**学员唯一确定拥有的，是他刚答完的 12 题。** 所以第一个适配器必须接这个。
"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from thegreatme.adapters import folder, metaquestions  # noqa: E402
from thegreatme.questions import QUESTION_TEXT, load_questions  # noqa: E402


# ── 12 题必须来自 meta-questions 真源，不能手抄 ──────────────
def test_questions_come_from_the_metaquestions_source():
    qs = load_questions()
    assert len(qs) == 12
    assert sorted(qs) == list(range(1, 13))
    assert "3 倍" in QUESTION_TEXT[1]["zh"], "Q1 文本不对，questions.yaml 可能漂了"
    assert "Swap Test" in QUESTION_TEXT[10]["zh"]


# ── metaquestions：从对话记录抽 ─────────────────────────────
TRANSCRIPT = """You said:
<粘贴提示词>

ChatGPT said:
过去三年，有没有一件事，别人做要花 3 倍的时间或成本，你却做成了？说出具体的时间、金额和结果。

You said:
2024 年 3 月，我用 6 天做完一个跨境选品数据管道，同行外包报价 8 万、工期 6 周。

ChatGPT said:
你身上有没有一个别人觉得「你怎么会这个」的技能或经历？它当初是怎么来的？

You said:
我会写 SQL，是 2019 年被一个甲方逼出来的。

ChatGPT said:
Swap Test：把 AI 从你现在做的这件事里完全拔掉，你是「变慢」，还是「整个模式垮掉」？只能二选一。

You said:
垮掉。
"""


def test_metaquestions_extracts_the_answer_that_follows_each_question(tmp_path):
    p = tmp_path / "transcript.md"
    p.write_text(TRANSCRIPT, encoding="utf-8")
    got = {c.q: c.claim for c in metaquestions.harvest(p)}
    assert set(got) == {1, 2, 10}, f"抽到的题号不对：{sorted(got)}"
    assert "6 天做完" in got[1]
    assert "2019 年" in got[2]
    assert got[10].strip() == "垮掉。"


def test_metaquestions_does_not_swallow_the_next_question_into_the_answer(tmp_path):
    p = tmp_path / "t.md"
    p.write_text(TRANSCRIPT, encoding="utf-8")
    got = {c.q: c.claim for c in metaquestions.harvest(p)}
    assert "你身上有没有" not in got[1], "答案吃掉了下一道题"
    assert "Swap Test" not in got[2]


def test_metaquestions_evidence_points_at_the_file_and_question(tmp_path):
    p = tmp_path / "t.md"
    p.write_text(TRANSCRIPT, encoding="utf-8")
    c = next(c for c in metaquestions.harvest(p) if c.q == 10)
    assert "t.md" in c.evidence and "Q10" in c.evidence


def test_metaquestions_is_high_confidence_because_the_slot_is_unambiguous(tmp_path):
    """题号不是猜的——是题目原文匹配出来的。这是所有适配器里最准的一个。"""
    p = tmp_path / "t.md"
    p.write_text(TRANSCRIPT, encoding="utf-8")
    assert all(c.confidence == "high" for c in metaquestions.harvest(p))


def test_metaquestions_still_marks_everything_private(tmp_path):
    p = tmp_path / "t.md"
    p.write_text(TRANSCRIPT, encoding="utf-8")
    assert all(c.sensitivity == "private" for c in metaquestions.harvest(p))


def test_metaquestions_skips_unanswered_questions(tmp_path):
    """AI 问了但用户没答（对话中断）→ 不该产出空断言。"""
    p = tmp_path / "t.md"
    p.write_text("ChatGPT said:\n" + QUESTION_TEXT[1]["zh"] + "\n", encoding="utf-8")
    assert metaquestions.harvest(p) == []


def test_metaquestions_reads_the_answers_template_too(tmp_path):
    """不想贴对话记录的人，可以填我们发的模板。两种输入都要认。"""
    p = tmp_path / "answers.md"
    p.write_text("## Q1\n六天做完同行六周的活。\n\n## Q7\n老同事王工，能开供应商入围名单。\n",
                 encoding="utf-8")
    got = {c.q: c.claim for c in metaquestions.harvest(p)}
    assert set(got) == {1, 7}
    assert "六天做完" in got[1]


def test_metaquestions_works_on_english_transcripts(tmp_path):
    p = tmp_path / "en.md"
    p.write_text(QUESTION_TEXT[10]["en"] + "\n\nIt collapses.\n", encoding="utf-8")
    got = metaquestions.harvest(p)
    assert len(got) == 1 and got[0].q == 10 and "collapses" in got[0].claim


# ── folder：inbox 通用入口，入口闸在这里最吃紧 ───────────────
def test_folder_only_ingests_chunks_that_are_tagged_with_a_question(tmp_path):
    """挂不到 12 题上的一个字都不进——这是抗污染的闸门，对学员比对 Sam 更重要，
    因为学员会把整个工单和聊天记录一股脑丢进来。"""
    (tmp_path / "note.md").write_text(
        "今天开会聊了很多。\n\n"
        "Q7: 老周有行业公众号矩阵，他缺工厂端原创内容，我这边有。\n\n"
        "还聊了午饭吃什么。\n", encoding="utf-8")
    got = folder.harvest(tmp_path)
    assert len(got) == 1
    assert got[0].q == 7 and "老周" in got[0].claim
    assert "午饭" not in got[0].claim


def test_folder_reports_what_it_refused_instead_of_silently_dropping(tmp_path):
    """静默丢弃 = 学员以为收了，其实没收。必须能说出「有几段没题号，没收」。"""
    (tmp_path / "n.md").write_text("没标号的一段。\n\nQ4: 有 11000 条询盘记录。\n\n另一段没标号。\n",
                                   encoding="utf-8")
    got, skipped = folder.harvest_with_report(tmp_path)
    assert len(got) == 1
    assert skipped == 2, f"没标号的段数报错了：{skipped}"


@pytest.mark.parametrize("marker", ["Q7:", "Q7：", "## Q7", "[[Q7]]", "q7:"])
def test_folder_accepts_the_common_ways_people_write_a_tag(tmp_path, marker):
    (tmp_path / "n.md").write_text(f"{marker} 老周能帮我分发。\n", encoding="utf-8")
    got = folder.harvest(tmp_path)
    assert len(got) == 1 and got[0].q == 7


def test_folder_rejects_out_of_range_tags(tmp_path):
    (tmp_path / "n.md").write_text("Q13: 不存在的题。\n", encoding="utf-8")
    assert folder.harvest(tmp_path) == []


def test_folder_evidence_points_back_at_the_source_file(tmp_path):
    (tmp_path / "会议纪要.md").write_text("Q8: 小李持股，判断错他自己亏钱。\n", encoding="utf-8")
    c = folder.harvest(tmp_path)[0]
    assert "会议纪要.md" in c.evidence


def test_folder_survives_an_unreadable_file(tmp_path):
    (tmp_path / "good.md").write_text("Q1: 好的。\n", encoding="utf-8")
    (tmp_path / "bad.md").write_bytes("Q1: 中文\n".encode("gbk"))
    assert len(folder.harvest(tmp_path)) == 1
