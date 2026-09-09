<div align="center">

<h1>the-great-me</h1>

<p><b>答完 12 题不是结束。让它跟着你长。</b></p>

<p>把 <a href="https://github.com/gmggyyds/meta-questions">meta-questions</a> 的答案变成一份常驻的自我画像 · 新笔记持续归位 · AI 做判断前先读它</p>

<p>
  <img alt="license" src="https://img.shields.io/badge/license-MIT-black">
  <img alt="deps" src="https://img.shields.io/badge/runtime%20deps-pyyaml-black">
  <img alt="data" src="https://img.shields.io/badge/your%20data-never%20leaves%20your%20machine-black">
</p>

</div>

---

## 这是什么

你答完 [meta-questions](https://github.com/gmggyyds/meta-questions) 的 12 题，拿到一份报告——然后呢？

那份报告躺在某个对话窗口里，两周后你自己都找不到。下次开一个新对话，AI 又完全不认识你，
你又得从头解释一遍「我是做什么的、我手上有什么」。

**the-great-me 把那些答案变成一份存在你自己电脑上的账本**，并且：

- 以后记的笔记、会议纪要、工单，标一下题号就能持续归进去
- AI 在帮你做判断之前，先读到「你是谁、你有什么、你认识谁」
- 每条断言都带出处，能查回是哪份材料说的、什么时候确认的

## 30 秒看懂它在干嘛

```
你的 12 题答案 ──┐
                 ├──▶ 只收挂得上 12 题的 ──▶ 账本 ──▶ 两份画像
平时的笔记 ──────┘     （挂不上的挡在门外）        ├── PROFILE.md          能外传的
                                                   └── PROFILE.private.md  只在你机器上
```

**挂不上 12 题的东西，一个字都进不来。** 这不是洁癖——把什么都倒进去，
三个月后它会变成一坨谁也不敢删的东西，AI 读了反而更糊涂。

## 开始用

```bash
git clone https://github.com/gmggyyds/the-great-me
cd the-great-me
pip install -r requirements.txt
python3 thegreatme.py doctor        # 第一次先跑这个，看配置对不对
```

### 第一步：把 12 题的答案放进来

**最省事**：把你跟 AI 那段对话**整段复制**，存成 `data/metaquestions/我的对话.md`。
不用整理格式——引擎靠**题目原文**定位，ChatGPT、Claude、豆包复制出来的都认。

**或者**：填 `data/metaquestions/answers.template.md`，`## Q1` 下面写答案。没答的留空。

```bash
python3 thegreatme.py harvest       # 抽出候选
python3 thegreatme.py review        # 看抽到了什么（默认打码）
python3 thegreatme.py accept --all  # 进账本
python3 thegreatme.py render        # 生成画像
```

### 第二步：让 AI 每次先读它

在 `~/.claude/CLAUDE.md`（Claude Code）或 `AGENTS.md`（Codex）里加一行：

```markdown
> 做判断类的事之前先读：<你的路径>/data/PROFILE.private.md
```

选品、投资、招人、合作、定价、「我该怎么办」——这类问题它会先看你的底牌。
改代码、查数据这类纯执行的活不用读。

### 第三步：让它跟着你长

以后有新东西丢进 `data/inbox/`，段首标个题号：

```markdown
Q9: 老周有行业公众号矩阵，他缺工厂端的原创内容，我这边有——这是他愿意帮我分发的理由。
```

再跑一次 `harvest`。**没标题号的段落不会被收**，但引擎会告诉你拒了几段——
那些正是该拿去问 AI 的：**「这段改变了我 12 题里的哪一条？」** 挂得上再回来标号。

## 你的数据去哪了

**哪也没去。** 没有后端、没有账号、没有云同步。

- 全部落在 `data/`，被 `.gitignore` 挡着
- 引擎**写之前会自查**：目标在 git 仓里且没被 ignore，直接拒绝写（`thegreatme/guard.py`）
- 所有断言默认 `private`。可外传的那份 `PROFILE.md` **一开始是空的**——
  这是正常起点不是缺数据。要让某条能外传，得显式把它标成 `public`
- 文件权限 600，同机别的进程也读不到

想要历史和回滚？给 `data/` 建个**本地 git 仓、不加 remote**——有完整版本历史，
而且因为没有远端，物理上传不出去。

## 12 个问题从哪来

不在这个仓里手抄。`thegreatme/questions.yaml` 由 `tools/sync_questions.py` 从
[meta-questions](https://github.com/gmggyyds/meta-questions) 的真源生成——
两个仓各写一份题目文本，早晚漂移。

```bash
python3 tools/sync_questions.py     # 需要本地 clone 了 meta-questions
```

## 接你自己的语料源

`sources.yaml` 里那两个默认关闭的（`relations` / `memories`）是示例，
照着 `thegreatme/adapters/` 里它们的写法加一个就行。三条规矩：

1. **只读**，永远不写回源
2. **只提议不判定**：提取内容、提议题号、附证据指针，准不准交给「审」那一步
3. **默认 private**：适配器无权判定什么能外传

## 它不做什么

- **不替你做决定。** 它只是让你和 AI 手上有一份带出处的底牌清单。
- **不猜你的笔记该归哪一题。** inbox 里没标题号的不会被猜进某一题——猜错比不收更糟。
- **不联网、不上传、不分析你。** 没有遥测，没有后端。

## License

MIT
