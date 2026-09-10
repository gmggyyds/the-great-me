#!/usr/bin/env python3
"""the-great-me 学员旅程沙箱 —— 端到端，装成插件之后的那条真实路径。

    python3 sandbox/student_journey.py            # 全绿才算过
    SANDBOX_MUTATE=<mut.py> python3 sandbox/student_journey.py   # 注入变异，验沙箱本身会红

它覆盖的是单元测试碰不到的那一层：装成插件之后引擎跑在缓存目录里、
配置和数据在别处、软链有没有被 clone 变成拷贝、学员粘贴整段对话能不能被认出来。

完全隔离：独立 HOME、独立数据目录，一个字都不碰真实画像。
按**插件缓存的形状**布置引擎，好把「装成插件」那条路上的坑一起验掉。

学员是虚构的：阿柚，做宠物用品独立站。她的敏感信息用固定字符串，
最后逐个断言它们没有出现在任何一个可外传的出口里。
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent          # 本脚本就住在被测仓里
SB = Path(os.environ.get("SANDBOX_DIR") or
          (Path(tempfile.gettempdir()) / "tgm-sandbox"))
HOME = SB / "home"
# 故意做成插件缓存的形状，验「拒绝往缓存里写」
ENGINE = HOME / ".claude/plugins/cache/the-great-me/the-great-me/0.1.1"
MINE = HOME / ".the-great-me"

PASS, FAIL = [], []


def check(name, ok, detail=""):
    (PASS if ok else FAIL).append(name)
    print(f"  {'✅' if ok else '❌'} {name}" + (f"\n       {detail}" if detail and not ok else ""))


def run(*args, cwd=None, env=None, check_rc=False):
    e = dict(os.environ)
    e.update({"HOME": str(HOME), "PYTHONDONTWRITEBYTECODE": "1"})
    e.pop("THEGREATME_CONFIG", None)
    if env:
        e.update(env)
    p = subprocess.run([sys.executable, str(ENGINE / "thegreatme.py"), *args],
                       cwd=cwd or str(SB), capture_output=True, text=True, env=e, timeout=90)
    if check_rc and p.returncode != 0:
        print(p.stdout, p.stderr)
    return p


def cfg_env():
    return {"THEGREATME_CONFIG": str(MINE / "sources.yaml")}


# ---------------------------------------------------------------- 布置
def setup():
    if SB.exists():
        shutil.rmtree(SB)
    ENGINE.parent.mkdir(parents=True)
    # 用 git clone 而不是 cp -r：cp 会把软链变成拷贝，正好验不了软链那件事
    subprocess.run(["git", "clone", "-q", "--depth", "1", f"file://{REPO}", str(ENGINE)],
                   check=True, capture_output=True)
    # 变异入口：把产品故意改坏，用来验证这个沙箱本身抓不抓得到问题。
    # 第一次跑就全绿的测试要怀疑——先证明它会红，绿才算数。
    mut = os.environ.get("SANDBOX_MUTATE")
    if mut:
        exec(compile(Path(mut).read_text(encoding="utf-8"), mut, "exec"),
             {"ENGINE": ENGINE, "Path": Path, "re": re})
        print(f"⚠️  已注入变异：{Path(mut).name}")
    print(f"引擎（插件缓存形状）: {ENGINE}")
    print(f"隔离 HOME: {HOME}\n")


# ---------------------------------------------------------------- 学员素材
PERSONA = {
    "客户": "宠物集合店「毛球日记」的采购张姐，微信 zhangjie_pet_1988",
    "供应商": "东莞宏茂宠物用品厂，老板电话 137xxxx8821",
    "收入": "独立站月流水 38 万",
}


def twelve_question_transcript() -> str:
    """学员最省事的那条路：把跟 AI 答题的对话**整段复制**丢进去。

    适配器靠**题目原文**定位，所以这里的题目必须逐字来自 questions.yaml，
    不能手抄——手抄就测不出「原文匹配」这件事到底成不成立。
    """
    import yaml
    qs = yaml.safe_load((ENGINE / "thegreatme/questions.yaml").read_text(encoding="utf-8"))
    answers = {
        1: "2024 年帮「毛球日记」把 200 个 SKU 的详情页三周内全部重做完，同行报价是三个月起。",
        2: "我会自己拍产品视频还会剪，同行都觉得做采购的不该会这个——是早年在婚庆公司跟摄影师学的。",
        3: "同行习惯来问我宠物用品的选品和供应链，上周张姐还来问猫爬架的爆款结构。",
        4: "① 3 年的独立站订单数据约 4.6 万单 ② 东莞两家代工厂的深度关系 ③ 一个 1.2 万人的养宠社群。",
        5: "社群买不到——它是三年一条条回复攒起来的，投放能买流量买不到信任。",
        6: "订单数据基本躺着，攒了三年一次都没拿去做选品分析。",
        7: f"{PERSONA['客户']} 能带我进线下连锁的采购体系，那扇门我自己敲不开。",
        8: "大学室友现在在头部宠物品牌做产品，他会直说不行，因为他没打算跟我合作。",
        9: "养宠社群里有几个宠物博主，他们缺稳定的选品内容，我这儿正好有。",
        11: "如果 AI 免费无限，我这个生意应该是「一个人 + 一套自动选品和内容管线」，而不是现在带四个客服。",
        12: f"缺的是代码杠杆。以前没拿到是因为不会写也请不起人（{PERSONA['收入']}，养不起工程师）。",
    }
    L = ["# 我跟 AI 答 12 题的对话（整段复制）", ""]
    for seg in qs["segments"]:
        for q in seg["questions"]:
            n = q["n"]
            L += [f"AI：{q['zh']}", ""]
            L += [f"我：{answers.get(n, '（这题我先跳过）')}", ""]
    return "\n".join(L)


INBOX_TAGGED = f"""<!-- 源：飞书妙记 obcnFAKE001「9 月供应链复盘」2026-09-02，48 分钟，3 人 -->

Q4: 东莞宏茂那条线今年累计下单 11 万件，是三家代工里唯一能接 500 件起订的。

Q7: {PERSONA['供应商']} 愿意为我们单独开一条小批量试产线，这是别家谈不下来的条件。
"""

INBOX_UNTAGGED = """这段是会上别人讲的行业观点，没标题号，按设计应该一个字都进不来。

跨境宠物赛道今年的关键词是合规，欧盟新规下半年落地。

另一段同样没标号。
"""


def seed_student_data():
    (MINE / "data/metaquestions").mkdir(parents=True, exist_ok=True)
    (MINE / "data/inbox").mkdir(parents=True, exist_ok=True)
    (MINE / "data/metaquestions/我和AI的对话.md").write_text(
        twelve_question_transcript(), encoding="utf-8")
    (MINE / "data/inbox/feishu_2026-09-02_obcnFAKE001.md").write_text(
        INBOX_TAGGED, encoding="utf-8")
    (MINE / "data/inbox/没标号的一堆.md").write_text(INBOX_UNTAGGED, encoding="utf-8")


# ---------------------------------------------------------------- 用例
def main():
    setup()

    print("── 1. 装完就跑（学员还没建配置）──")
    p = run("doctor")
    blob = p.stdout + p.stderr
    # ⚠️ 判据不能是「输出里有『插件缓存』」——doctor 的**成功**行就写着
    #    「✅ 数据不会被 git 收走，也不在插件缓存里」，那句话在通过和失败时都成立，
    #    等于什么都没测（2026-09-10 变异实测：摘掉护栏，这条照样绿）。
    #    判据必须是只在失败时才出现的东西：非零退出 + 拒写字样 + 没有那句绿灯。
    check("默认配置指向插件缓存时，doctor 报红而不是假绿灯",
          p.returncode != 0 and "拒绝写" in blob and "✅ 数据不会被 git 收走" not in blob,
          f"rc={p.returncode} / {blob[:220]}")
    check("报错里给了出路（init）", "thegreatme.py init" in blob)

    print("\n── 2. init 建自己的配置 ──")
    p = run("init", str(MINE))
    check("init 成功", p.returncode == 0 and (MINE / "sources.yaml").exists(), p.stderr[:200])
    check("配置在插件缓存之外", ".claude/plugins" not in str(MINE / "sources.yaml"))
    check("顺带建好 inbox / metaquestions",
          (MINE / "data/inbox").is_dir() and (MINE / "data/metaquestions").is_dir())

    seed_student_data()
    print("\n── 3. doctor 用新配置 ──")
    p = run("doctor", env=cfg_env())
    check("doctor 全绿", p.returncode == 0 and "✅ 数据不会被 git 收走" in p.stdout, p.stdout[:300])

    print("\n── 4. harvest（学员主路径：粘贴的 12 题对话）──")
    p = run("harvest", env=cfg_env())
    out = p.stdout
    m = re.search(r"metaquestions\s+抽出\s+(\d+)", out)
    nmq = int(m.group(1)) if m else 0
    check(f"metaquestions 适配器从整段对话里靠题目原文定位到答案（抽出 {nmq} 条）", nmq >= 8,
          out[:400])
    m = re.search(r"folder\s+抽出\s+(\d+)", out)
    nf = int(m.group(1)) if m else 0
    check(f"folder 收了标了题号的段落（{nf} 条）", nf == 2, out[:400])
    check("没标题号的段落被拒，并且**报了数**", "没标题号" in out, out[:400])

    print("\n── 5. review 默认打码 ──")
    p = run("review", "--limit", "50", env=cfg_env())
    leaked = [k for k, v in PERSONA.items() if v.split("，")[0] in p.stdout]
    check("review 不泄露任何敏感串", not leaked, f"泄露了：{leaked}")
    check("用 ▨ 掩码", "▨" in p.stdout)

    print("\n── 6. accept + render ──")
    run("accept", "--all", env=cfg_env())
    p = run("render", env=cfg_env())
    pub = (MINE / "data/PROFILE.md").read_text(encoding="utf-8")
    priv = (MINE / "data/PROFILE.private.md").read_text(encoding="utf-8")
    check("PROFILE.md（可外传层）默认为空", "还没有任何标记为 public 的断言" in pub)
    check("PROFILE.private.md 有内容", "Q1" in priv and len(priv) > 500)
    check("标题不叫别人的名字", "Sam" not in priv and "Sam" not in pub)
    mode = oct((MINE / "data/PROFILE.private.md").stat().st_mode)[-3:]
    check(f"私有画像权限 600（实际 {mode}）", mode == "600")

    print("\n── 7. 🔴 进度卡：可传播的前提 ──")
    p = run("card", env=cfg_env())
    html = (MINE / "data/card.html").read_text(encoding="utf-8")
    bad = []
    for k, v in PERSONA.items():
        for blob, where in ((p.stdout, "终端卡"), (html, "card.html")):
            if v.split("，")[0] in blob:
                bad.append(f"{where}/{k}")
    # 逐条断言正文也查一遍，别只查那几个显眼的
    claims = [json.loads(l)["claim"] for l in
              (MINE / "data/claims.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    for c in claims:
        if c[:12] in p.stdout or c[:12] in html:
            bad.append("断言正文")
            break
    check("进度卡零内容（终端版 + HTML 双查，逐条断言）", not bad, f"泄露：{bad}")
    check("卡上有品牌", "by GMGG" in p.stdout and "gmggyyds/the-great-me" in html)

    print("\n── 8. 周报 ──")
    p = run("report", "--print", env=cfg_env())
    rep = p.stdout
    check("周报默认打码", not any(v.split("，")[0] in rep for v in PERSONA.values()))
    check("周报指出缺口", "该补的" in rep)
    check("点名还没答的题（学员跳过了 Q10）", "Q10" in rep, rep[-800:])

    print("\n── 9. 数据目录做成本地 git 仓（README 推荐的做法）──")
    d = MINE / "data"
    for a in (["init", "-q", "."], ["config", "user.email", "t@t"], ["config", "user.name", "t"]):
        subprocess.run(["git", *a], cwd=d, capture_output=True)
    subprocess.run(["git", "add", "claims.jsonl"], cwd=d, capture_output=True)
    subprocess.run(["git", "commit", "-qm", "init"], cwd=d, capture_output=True)
    p = run("render", env=cfg_env())
    check("零 remote 的本地仓：放行（README 推荐的做法不该被自己的护栏拒）",
          p.returncode == 0, p.stdout + p.stderr)

    subprocess.run(["git", "remote", "add", "origin",
                    "https://github.com/someone/notes.git"], cwd=d, capture_output=True)
    p = run("render", env=cfg_env())
    check("一旦加了 remote：立刻开始拒写（每次写都重查，不缓存）",
          p.returncode != 0 and "git ignore" in p.stdout + p.stderr,
          (p.stdout + p.stderr)[:300])

    print("\n── 10. 软链没被 clone 变成拷贝 ──")
    link = ENGINE / ".claude/skills/the-great-me"
    check("skill 在 .claude/skills 下仍是软链", link.is_symlink(),
          f"实际：{'目录' if link.is_dir() else '不存在'}")
    check("软链指得到真源", (link / "SKILL.md").exists())

    print("\n" + "═" * 56)
    print(f"通过 {len(PASS)} / {len(PASS) + len(FAIL)}")
    if FAIL:
        print("失败：")
        for f in FAIL:
            print(f"  ❌ {f}")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
