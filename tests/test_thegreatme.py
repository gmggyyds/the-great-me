"""个人上下文层（方案 D · claim 账本）回归测试。

设计要点，全部是 design.md 里被列为成败点的东西：
1. **入口闸**：挂不到 12 题上的东西，一条都不许进账本。
2. **fail-closed 脱敏**：默认全部当敏感，只有显式标 public 的才进可上云的那一份。
3. **只读**：适配器绝不写 GMGG_Brain vault（vault 铁律：只有笔记本写）。
4. **可回溯**：每条断言必须有证据指针，无出处条目 = 0。
"""
import json
import sys
from datetime import date
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from thegreatme.schema import (  # noqa: E402
    QUESTIONS, Claim, ClaimError, Sensitivity, dedup_key, load_jsonl, save_jsonl,
)


def mk(**kw):
    base = dict(q=7, claim="老同事王工在头部零售商做采购，能开供应商入围名单的门",
                evidence="relations_index.md#人物索引", source="relations",
                first_seen="2026-09-09", last_confirmed="2026-09-09",
                confidence="high", sensitivity="private")
    base.update(kw)
    return Claim(**base)


# ── schema：入口闸 ──────────────────────────────────────────
def test_twelve_questions_are_the_only_slots():
    assert sorted(QUESTIONS) == list(range(1, 13))


def test_claim_must_hang_on_a_real_question():
    """挂不到 12 题上的，一条都不许进——这是抗污染的唯一闸门。"""
    with pytest.raises(ClaimError, match="题号"):
        mk(q=13)
    with pytest.raises(ClaimError, match="题号"):
        mk(q=0)


def test_claim_must_carry_evidence():
    """无出处条目 = 0（design S2）。没有指针的断言无法对账，等于传闻。"""
    with pytest.raises(ClaimError, match="证据"):
        mk(evidence="")


def test_claim_rejects_unknown_sensitivity():
    with pytest.raises(ClaimError, match="敏感级"):
        mk(sensitivity="maybe")


def test_sensitivity_defaults_to_private_when_absent():
    """fail-closed：漏标 = 最严，不是最松。"""
    c = Claim(q=7, claim="x", evidence="y", source="s")
    assert c.sensitivity == Sensitivity.PRIVATE


def test_dedup_key_is_stable_across_reruns():
    """适配器会被反复跑。同一条不能每跑一次多一条。"""
    assert dedup_key(mk()) == dedup_key(mk(last_confirmed="2026-12-01"))
    assert dedup_key(mk()) != dedup_key(mk(claim="别的断言"))


def test_jsonl_roundtrip(tmp_path):
    p = tmp_path / "claims.jsonl"
    save_jsonl(p, [mk(), mk(q=8, claim="小李持股，判断错他自己亏钱")])
    back = load_jsonl(p)
    assert len(back) == 2 and back[0].q == 7 and back[1].q == 8


def test_load_jsonl_reports_which_line_is_broken(tmp_path):
    """真源被改坏时要炸得能定位——不能只说 JSONDecodeError。"""
    p = tmp_path / "claims.jsonl"
    p.write_text('{"q":7,"claim":"a","evidence":"b","source":"s"}\n{ 坏行 }\n', encoding="utf-8")
    with pytest.raises(ClaimError) as e:
        load_jsonl(p)
    assert "第 2 行" in str(e.value)


# ── 适配器：只读 + 只产候选 ─────────────────────────────────
from thegreatme.adapters import memories, relations  # noqa: E402

SAMPLE_RELATIONS = """# Get笔记 信息链与实体关系索引

## 二、人物索引（新增/强化）

| 人物 | 身份 | 关系与状态 | 出处 |
|---|---|---|---|
| 金燕珍（金总） | 亚马逊中国副总裁 | 拟亲自主持播客邀 Sam；峰会 CEO 论坛邀约方 | note:1919005199396092992 |
| 李佩 | 新知科技创始人 | 同场唯一同级 AI 对标者，**值得建联** | note:1920124224133142928 |

## 三、公司/品牌索引（新增/强化）

| 主体 | 类型 | 要点 | 出处 |
|---|---|---|---|
| 班布库 | 竞品 | 换运营团队后激进，**值得监控** | note:1920124179035462032 |
"""


def test_relations_adapter_extracts_people_as_network_claims(tmp_path):
    src = tmp_path / "relations_index.md"
    src.write_text(SAMPLE_RELATIONS, encoding="utf-8")
    got = relations.harvest(src)
    assert got, "没抽出任何候选"
    people = [c for c in got if "金燕珍" in c.claim]
    assert len(people) == 1
    c = people[0]
    assert c.q in (7, 8, 9), f"人物应归到「我认识谁」段，实际 Q{c.q}"
    assert "note:1919005199396092992" in c.evidence, "证据指针必须带回原始 note id"
    assert c.source == "relations"


def test_relations_adapter_marks_everything_private_by_default(tmp_path):
    """人名、关系、邀约都是敏感的。适配器无权判定 public。"""
    src = tmp_path / "relations_index.md"
    src.write_text(SAMPLE_RELATIONS, encoding="utf-8")
    for c in relations.harvest(src):
        assert c.sensitivity == "private", f"适配器不该产出非 private 的候选：{c.claim[:20]}"


def test_relations_adapter_never_writes_anything(tmp_path):
    """铁律：GMGG_Brain vault 只有笔记本写。适配器一律只读。"""
    src = tmp_path / "relations_index.md"
    src.write_text(SAMPLE_RELATIONS, encoding="utf-8")
    before = {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    relations.harvest(src)
    after = {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    assert before == after, "适配器动了源文件"


def test_relations_adapter_is_idempotent(tmp_path):
    src = tmp_path / "relations_index.md"
    src.write_text(SAMPLE_RELATIONS, encoding="utf-8")
    a, b = relations.harvest(src), relations.harvest(src)
    assert [dedup_key(c) for c in a] == [dedup_key(c) for c in b]


SAMPLE_MEMORY = """---
name: project-sc-review-collector
description: "SC官方评论采集器已上线(1212条/三源视图/飞书表)"
metadata:
  type: project
---

谈自家评论采集前必读。
"""


def test_memories_adapter_maps_type_to_a_question(tmp_path):
    m = tmp_path / "project-sc-review-collector.md"
    m.write_text(SAMPLE_MEMORY, encoding="utf-8")
    got = memories.harvest(tmp_path)
    assert len(got) == 1
    assert got[0].q in QUESTIONS
    assert got[0].evidence.endswith("project-sc-review-collector.md")


def test_memories_adapter_skips_files_without_a_mappable_type(tmp_path):
    """挂不上题的不产候选——闸门在适配器就生效，不留到审那一步。"""
    (tmp_path / "MEMORY.md").write_text("# Memory Index\n- 一堆指针\n", encoding="utf-8")
    (tmp_path / "weird.md").write_text("---\nname: x\nmetadata:\n  type: 未知类型\n---\n正文\n",
                                       encoding="utf-8")
    assert memories.harvest(tmp_path) == []


# ── 渲染器：fail-closed 是敏感数据的最后一道闸 ──────────────
from thegreatme import render  # noqa: E402


def _mixed():
    return [
        mk(q=1, claim="六天做完同行报价八万六周的数据管道", sensitivity="public"),
        mk(q=4, claim="约 11000 条客户询盘记录", sensitivity="internal"),
        mk(q=7, claim="王工在头部零售商做采购，能开供应商入围名单", sensitivity="private"),
    ]


def test_public_profile_contains_only_public_claims(tmp_path):
    pub = render.render_public(_mixed())
    assert "六天做完" in pub
    assert "11000" not in pub, "internal 泄漏进了可上云那份"
    assert "王工" not in pub, "🔴 private 泄漏进了可上云那份"


def test_private_profile_contains_everything(tmp_path):
    priv = render.render_private(_mixed())
    for needle in ("六天做完", "11000", "王工"):
        assert needle in priv


def test_unlabelled_claims_never_reach_the_public_profile():
    """fail-closed 的实测：没标过敏感级的（=默认 private）绝不能出现在可上云那份。"""
    c = Claim(q=1, claim="某条从没标过敏感级的断言", evidence="e", source="s")
    assert c.sensitivity == "private"
    assert "某条从没标过" not in render.render_public([c])


def test_public_profile_says_so_when_empty():
    """一条 public 都没有是**正常起点**（默认全私）。不能崩，也不能假装有内容。"""
    out = render.render_public([mk(sensitivity="private")])
    assert "还没有" in out or "暂无" in out


def test_profiles_group_by_the_four_segments():
    priv = render.render_private(_mixed())
    for seg in ("我是谁", "我手里有什么", "我认识谁"):
        assert seg in priv


def test_stale_claims_are_flagged_not_silently_kept():
    """只进不出会死。过期的要被标出来，让人能决定删不删。"""
    old = mk(last_confirmed="2020-01-01")
    priv = render.render_private([old], today="2026-09-09")
    assert "过期" in priv or "陈旧" in priv


def test_every_rendered_claim_carries_its_evidence_pointer():
    """S2：无出处条目 = 0。渲染出来也要能看见指针，否则没法对账。"""
    priv = render.render_private(_mixed())
    assert "relations_index.md#人物索引" in priv


def test_feedback_and_reference_memories_do_not_become_claims(tmp_path):
    """真实数据实测：feedback 类 74 条全灌进 Q1，全是噪音。

    `feedback` 是「怎么跟 AI 工作」的规则、`reference` 是「去哪查证」的指针，
    两者都不是关于 Sam 的断言——挂不到 12 题任何一题上，就不该进来。
    这条是入口闸在真实数据上被校准后的结果，不是理论洁癖。
    """
    for t in ("feedback", "reference"):
        (tmp_path / f"{t}-x.md").write_text(
            f"---\nname: {t}-x\ndescription: 某条{t}\nmetadata:\n  type: {t}\n---\n正文\n",
            encoding="utf-8")
    assert memories.harvest(tmp_path) == []


def test_user_and_project_memories_still_come_through(tmp_path):
    # 旧格式（顶层 type），真实目录里有 40 个，含全部 5 个 user
    (tmp_path / "user-a.md").write_text(
        "---\nname: user-a\ndescription: Sam 是谁\ntype: user\n---\n", encoding="utf-8")
    (tmp_path / "project-b.md").write_text(
        "---\nname: project-b\ndescription: 在跑的项目\nmetadata:\n  type: project\n---\n", encoding="utf-8")
    got = memories.harvest(tmp_path)
    assert {c.q for c in got} == {1, 4}


# ── 审查修复：F1–F7（每条都对应一个实测出来的漏）───────────
import os  # noqa: E402
import subprocess  # noqa: E402

from thegreatme import guard  # noqa: E402


def test_F1_refuses_to_write_into_a_git_repo_that_does_not_ignore_it(tmp_path):
    """实锤：~/.claude 是带 GitHub remote 的 git 仓，而 PROFILE.private.md 未被 ignore，
    离一次 `git add -A` 就把 37KB 客户/供应商/人脉推上 GitHub。
    文案写「不要提交进任何仓库」没有任何执行力——所以写之前自己查。"""
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    target = tmp_path / "self" / "claims.jsonl"
    with pytest.raises(ClaimError, match="未被 git ignore"):
        guard.assert_not_tracked(target)
    (tmp_path / ".gitignore").write_text("self/\n", encoding="utf-8")
    guard.assert_not_tracked(target)          # 配好 ignore 后放行


def test_F1_writing_outside_any_repo_is_fine(tmp_path):
    guard.assert_not_tracked(tmp_path / "x" / "claims.jsonl")


def test_F2_bool_cannot_slip_through_the_question_gate():
    """Python 里 True == 1，所以 `q not in range(1,13)` 放行了 q=True，
    渲染出 `**QTrue**`。这个「唯一的闸门」接受非整数。"""
    with pytest.raises(ClaimError, match="整数"):
        mk(q=True)
    with pytest.raises(ClaimError, match="整数"):
        mk(q=1.0)


def test_F3_public_layer_never_leaks_absolute_paths():
    """memories 适配器的 evidence 是绝对路径，而文件名本身就点名合作方
    （project-god-custom-anerj-not-purcomfy）。一旦某条标 public，脱敏层就不脱敏了。"""
    c = mk(q=1, claim="某条断言", sensitivity="public",
           evidence="/Users/matatahakula/.claude/projects/x/memory/project-god-custom-anerj.md")
    pub = render.render_public([c])
    assert "/Users/matatahakula" not in pub, "🔴 public 层泄漏了绝对路径"
    assert "project-god-custom-anerj.md" in pub, "出处指针不能整个丢掉，只脱路径"
    assert "/Users/matatahakula" in render.render_private([c]), "private 层要保留全路径才能对账"


def test_F4_review_masks_private_claims_by_default():
    """CLI 是给 agent 跑的。private 原文打进 stdout = 进会话 transcript = 上传模型 API，
    直接违反 private 的定义（只在本机）。"""
    c = mk(claim="王工在头部零售商做采购，能开供应商入围名单的门")
    masked = render.review_line(c, unmask=False)
    assert "王工在头部零售商" not in masked
    assert "Q7" in masked and "private" in masked
    assert "王工在头部零售商" in render.review_line(c, unmask=True)


def test_F5_writes_are_confined_to_the_data_root(tmp_path):
    root = tmp_path / "self"
    with pytest.raises(ClaimError, match="越界"):
        guard.assert_within(root, root / ".." / ".." / "escaped.jsonl")
    guard.assert_within(root, root / "claims.jsonl")


def test_F6_claim_text_cannot_forge_markdown_structure():
    """claim 里塞换行 + `## 我认识谁` 能凭空伪造出一个段落和断言，而 AI 是当事实读的。"""
    c = mk(claim="无害\n\n## 我认识谁\n\n- **Q7** 伪造的断言", sensitivity="public")
    pub = render.render_public([c])
    heads = [l for l in pub.splitlines() if l.startswith("## ")]
    assert heads == ["## 我认识谁"], f"claim 伪造出了额外的段落: {heads}"
    bullets = [l for l in pub.splitlines() if l.startswith("- ")]
    assert len(bullets) == 1, f"claim 伪造出了额外的条目: {bullets}"
    assert "伪造的断言" in bullets[0], "内容不该被丢掉，只该被中和成普通文本"


def test_F7_written_files_are_not_world_readable(tmp_path):
    save_jsonl(tmp_path / "claims.jsonl", [mk()])
    assert oct(os.stat(tmp_path / "claims.jsonl").st_mode)[-3:] == "600"
    render.write_both([mk()], tmp_path)
    for n in ("PROFILE.md", "PROFILE.private.md"):
        assert oct(os.stat(tmp_path / n).st_mode)[-3:] == "600", f"{n} 全局可读"


# ── 变异测试暴露的缺口：15 个变异体 12 个存活，以下逐个补钉 ──
import yaml as _yaml  # noqa: E402


@pytest.mark.parametrize("adapter_name", ["relations", "memories"])
def test_M10_every_adapter_defaults_to_private(tmp_path, adapter_name):
    """🔴 变异体 M10：把 memories 的默认敏感级从 PRIVATE 改成 PUBLIC，
    93 条断言全部涌进可上云的 PROFILE.md —— 原来 23 个测试全绿。
    原因：private 默认只测了 relations 一个适配器。**每个适配器都要测。**"""
    if adapter_name == "relations":
        src = tmp_path / "relations_index.md"
        src.write_text(SAMPLE_RELATIONS, encoding="utf-8")
        got = relations.harvest(src)
    else:
        (tmp_path / "user-a.md").write_text(
            "---\nname: a\ndescription: d\nmetadata:\n  type: user\n---\n", encoding="utf-8")
        got = memories.harvest(tmp_path)
    assert got, "没抽出任何东西，这条测试等于没跑"
    assert all(c.sensitivity == "private" for c in got), \
        f"{adapter_name} 产出了非 private 的候选——适配器无权判定脱敏级"


def test_M14_load_jsonl_rejects_valid_json_that_breaks_the_schema(tmp_path):
    """🔴 变异体 M14：把「第 N 行不合规」的 raise 改成 continue（坏行静默跳过）→ 全绿。
    原因：只测了 JSONDecodeError 分支，没测「合法 JSON 但 schema 不过」那条。"""
    p = tmp_path / "claims.jsonl"
    p.write_text('{"q":7,"claim":"好的","evidence":"e","source":"s"}\n'
                 '{"q":99,"claim":"题号越界","evidence":"e","source":"s"}\n', encoding="utf-8")
    with pytest.raises(ClaimError) as e:
        load_jsonl(p)
    assert "第 2 行" in str(e.value)


def test_M3_company_rows_point_at_the_note_id_not_the_prose(tmp_path):
    """🔴 变异体 M3：公司表证据指针取错列（指向正文而非 note id）→ 全绿。
    原因：样例里唯一那条公司是「竞品」会被跳过，公司分支的产出从没被断言过内容。"""
    src = tmp_path / "r.md"
    src.write_text("""## 三、公司/品牌索引

| 主体 | 类型 | 要点 | 出处 |
|---|---|---|---|
| 招商局服贸基金 | 国家资本 | 100亿盘子，潜在资本通道 | note:1920130318692684688 |
""", encoding="utf-8")
    got = relations.harvest(src)
    assert len(got) == 1
    assert "招商局服贸基金" in got[0].claim
    assert "note:1920130318692684688" in got[0].evidence, "证据指针没指向 note id"
    assert "100亿盘子" not in got[0].evidence, "证据指针指到正文去了"


def test_M13_propose_q_actually_discriminates(tmp_path):
    """🔴 变异体 M13：_propose_q 直接 return 7（启发式整个作废）→ 全绿。
    原因：原断言是 `c.q in (7,8,9)`，覆盖整个段，穿得过去。"""
    src = tmp_path / "r.md"
    src.write_text("""## 二、人物索引

| 人物 | 身份 | 关系与状态 | 出处 |
|---|---|---|---|
| A | x | 拟亲自主持播客，帮忙分发 | note:1 |
| B | y | 权威口径来源，可要一手判断 | note:2 |
| C | z | 合作入口，项目主导 | note:3 |
""", encoding="utf-8")
    by_name = {c.claim[0]: c.q for c in relations.harvest(src)}
    assert by_name["A"] == 9, "分发/播客 应归 Q9"
    assert by_name["B"] == 8, "权威/判断 应归 Q8"
    assert by_name["C"] == 7, "入口/主导 应归 Q7"


def test_M8_every_single_claim_carries_a_visible_pointer():
    """🔴 变异体 M8：只给 relations 源输出出处、memories 源不输出 → 全绿。
    原因：原断言只查「某一个 needle 在全文里」，不是「每条都有」。"""
    claims = [mk(q=1, source="a"), mk(q=4, source="b", claim="另一条"),
              mk(q=7, source="c", claim="第三条")]
    priv = render.render_private(claims)
    assert priv.count("出处：") == len(claims)


def test_R2_all_person_tables_are_picked_up_not_just_the_first(tmp_path):
    """🔴 真实数据上正在错：源里有三张表（人物索引/公司索引/**妙记新增人物**），
    适配器按标题关键词硬匹配，第三张 11 个人一个都没抽到——包括生财 912 大课主理人。
    改成按**表头**判表种，而不是按标题文字。"""
    src = tmp_path / "r.md"
    src.write_text("""## 二、人物索引

| 人物 | 身份 | 关系与状态 | 出处 |
|---|---|---|---|
| 甲 | x | 合作入口 | note:1 |

## 七、妙记新增人物（补充）

| 人物 | 身份 | 关系与状态 | 渠道 |
|---|---|---|---|
| 国民 | 生财912大课主理人 | 课程共建核心对接人 | [M] |
""", encoding="utf-8")
    got = relations.harvest(src)
    assert {c.claim[0] for c in got} == {"甲", "国"}, f"漏表了：{[c.claim[:6] for c in got]}"


def test_R1_escaped_pipes_do_not_shift_the_columns(tmp_path):
    """🔴 表格里放竖线的标准写法就是 `\\|`。不认转义 → 断言被腰斩、证据指针指向正文碎片。
    比崩溃更糟：条目照进账本，「无出处 0」照样绿，但指针是假的。"""
    src = tmp_path / "r.md"
    src.write_text("""## 二、人物索引

| 人物 | 身份 | 关系与状态 | 出处 |
|---|---|---|---|
| 张三 | 顾问 | 口径 A \\| 口径 B | note:1 |
""", encoding="utf-8")
    got = relations.harvest(src)
    assert len(got) == 1
    assert "口径 A | 口径 B" in got[0].claim, f"断言被腰斩：{got[0].claim}"
    assert got[0].evidence.endswith("note:1"), f"指针错位：{got[0].evidence}"


def test_R3_rows_without_a_real_citation_do_not_enter(tmp_path):
    """🔴「无出处 = 0」是假绿灯：evidence 前缀恒非空，空 cite 永远拦不住。"""
    src = tmp_path / "r.md"
    src.write_text("""## 二、人物索引

| 人物 | 身份 | 关系与状态 | 出处 |
|---|---|---|---|
| 有出处 | x | y | note:1 |
| 没出处 | x | y |  |
""", encoding="utf-8")
    got = relations.harvest(src)
    assert [c.claim[:3] for c in got] == ["有出处"], "没出处的那条混进来了"


def test_M1_nested_frontmatter_does_not_shadow_the_top_level_description(tmp_path):
    """🔴 真实 memory 文件全都有 metadata: 嵌套块。正则不看缩进、后写覆盖先写 →
    metadata.description 会盖掉真正的 description，静默产出错误内容。"""
    (tmp_path / "a.md").write_text(
        "---\nname: a\ndescription: 真正的描述\nmetadata:\n  type: project\n"
        "  description: 内部元数据噪音\n---\n正文\n", encoding="utf-8")
    got = memories.harvest(tmp_path)
    assert len(got) == 1
    assert got[0].claim == "真正的描述", f"被嵌套字段盖掉了：{got[0].claim}"


def test_M2_prose_starting_with_a_rule_is_not_mistaken_for_frontmatter(tmp_path):
    """🔴 以 --- 开头的普通 markdown 会被当 frontmatter 硬解，凭空长出断言。

    判据是 `name`：实测 203 个带 type 的真实 memory 文件，缺 name 的是 0 个。"""
    (tmp_path / "a.md").write_text(
        "---\n\n# 我的笔记\n\ntype: project\ndescription: 这不是 frontmatter\n\n---\n",
        encoding="utf-8")
    assert memories.harvest(tmp_path) == []


def test_M3_block_scalars_do_not_become_garbage_claims(tmp_path):
    """🔴 `description: >` 折叠块 → claim 字面就是 '>'，非空、通过校验、进账本、渲染进画像。"""
    (tmp_path / "a.md").write_text(
        "---\nname: a\ndescription: >-\n  第一行\n  第二行\nmetadata:\n  type: project\n---\n",
        encoding="utf-8")
    got = memories.harvest(tmp_path)
    assert len(got) == 1
    assert got[0].claim.startswith("第一行"), f"块标量没解开：{got[0].claim!r}"


def test_M6_one_unreadable_file_does_not_kill_the_whole_harvest(tmp_path):
    """🔴 实测：往 memory 目录塞一个 GBK 文件 → harvest 吐 traceback，
    另外 126 条好数据全丢，~/.claude/self/ 目录都没建出来。"""
    (tmp_path / "good.md").write_text(
        "---\nname: g\ndescription: 好的\nmetadata:\n  type: user\n---\n", encoding="utf-8")
    (tmp_path / "bad.md").write_bytes("---\ndescription: 中文\n---\n".encode("gbk"))
    got = memories.harvest(tmp_path)
    assert len(got) == 1 and got[0].claim == "好的", "一个坏文件带走了整批"


def test_D1_save_is_atomic_so_a_failure_cannot_destroy_the_ledger(tmp_path):
    """🔴 open('w') 先截断后写：写一半异常 = 账本被腰斩。
    ~/.claude/self/ 在 git 之外、没备份、没版本 —— 不可逆丢失。"""
    p = tmp_path / "claims.jsonl"
    save_jsonl(p, [mk(), mk(q=8, claim="第二条")])
    assert len(load_jsonl(p)) == 2

    class Boom(Claim):
        pass
    bad = Boom(q=1, claim="炸", evidence="e", source="s")
    bad.claim = object()                     # 序列化时炸
    with pytest.raises(Exception):
        save_jsonl(p, [mk(), bad])
    assert len(load_jsonl(p)) == 2, "🔴 账本被写坏了，原数据没了"


def test_A2_accept_preserves_human_edits_instead_of_silently_dropping_them(tmp_path):
    """🔴 accept 用 dedup_key 判「进不进账本」，用 __eq__ 判「从候选里删不删」——两套相等性。
    结果：人审后把 confidence 提到 high、sensitivity 放开、时间刷新的那条，
    **不进账本但照样被删掉**，一个字不报。对一个「审」是核心闸门的系统，这是致命的。"""
    from thegreatme import ledger
    old = mk(confidence="medium", sensitivity="private", last_confirmed="2026-03-01")
    edited = mk(confidence="high", sensitivity="public", last_confirmed="2026-09-09")
    merged, stats = ledger.merge([old], [edited])
    assert len(merged) == 1, "同一条断言不该变成两条"
    m = merged[0]
    assert m.confidence == "high" and m.sensitivity == "public", "人审的改动被吞了"
    assert m.last_confirmed == "2026-09-09", "确认时间没刷新"
    assert m.first_seen == old.first_seen, "首次出现时间不该被覆盖"
    assert stats["updated"] == 1 and stats["added"] == 0


def test_A1_duplicates_within_one_batch_do_not_both_enter():
    from thegreatme import ledger
    merged, stats = ledger.merge([], [mk(), mk()])
    assert len(merged) == 1 and stats["added"] == 1


def test_A4_reharvesting_an_existing_claim_refreshes_its_last_confirmed():
    """🔴「陈旧」的语义原来是反的：harvest 因 dedup 命中而整条丢弃，
    last_confirmed 冻结在首次抽取日 —— 源里明明还在的断言，180 天后一律被标陈旧。"""
    from thegreatme import ledger
    old = mk(last_confirmed="2026-01-01")
    merged, _ = ledger.merge([old], [mk(last_confirmed="2026-09-09")])
    assert merged[0].last_confirmed == "2026-09-09"


def test_V1_bad_dates_are_blocked_at_the_door(): 
    """第一层：坏日期根本进不了账本。"""
    for bad in ("", "not-a-date", "2026-13-45", "2026/09/09", None):
        with pytest.raises(ClaimError, match="ISO 日期"):
            mk(last_confirmed=bad)


def test_V1_and_if_one_slips_in_it_counts_as_stale_not_fresh():
    """第二层：万一有人手改账本绕过构造器，也必须当「需要人看」。

    原来 `except ValueError: return False` 在一个写着 fail-closed 的系统里方向是反的，
    而且让 status 的「陈旧 0」也变成假绿灯。"""
    c = mk()
    for bad in ("", "not-a-date", "2026-13-45"):
        object.__setattr__(c, "last_confirmed", bad)     # 模拟手改过的账本
        assert render._is_stale(c, "2026-09-09"), f"坏日期 {bad!r} 被当成新鲜的"
