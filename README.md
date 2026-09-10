<div align="center">

<img src="./banner.png" alt="the-great-me" width="100%">

<h1>the-great-me</h1>

<p><b>答完 12 题不是结束。让它跟着你长。</b></p>

<p>把 <a href="https://github.com/gmggyyds/meta-questions">meta-questions</a> 的答案变成一份常驻画像 · 新笔记按题号持续归位 · AI 做判断前先读它</p>

<p>
  <a href="https://github.com/gmggyyds/the-great-me/actions"><img alt="CI" src="https://github.com/gmggyyds/the-great-me/actions/workflows/ci.yml/badge.svg"></a>
  <img alt="version" src="https://img.shields.io/badge/plugin-v0.1.1-black">
  <img alt="tests" src="https://img.shields.io/badge/tests-107%20passed-black">
  <img alt="deps" src="https://img.shields.io/badge/runtime%20deps-pyyaml-black">
  <img alt="license" src="https://img.shields.io/badge/license-MIT-black">
</p>

<p><sub>Claude Code · Codex · Python 3.12</sub></p>

</div>

---

## 📦 装

装成 Claude Code 插件（推荐路径）：

```
/plugin marketplace add gmggyyds/the-great-me
/plugin install the-great-me
```

```bash
pip install pyyaml
python3 "$CLAUDE_PLUGIN_ROOT/thegreatme.py" init      # 默认落 ~/.the-great-me/
export THEGREATME_CONFIG=~/.the-great-me/sources.yaml # 加进 shell 配置，一次就好
```

`init` 这一步不能省。插件装在 `~/.claude/plugins/cache/<市场>/<插件>/<版本>/`，版本号是目录名的一部分，
`plugin update` 会把整个版本目录换掉。不建自己的配置，数据就落在缓存里，某次更新之后画像凭空消失。
引擎会直接拒绝往那儿写（[guard.py](https://github.com/gmggyyds/the-great-me/blob/main/thegreatme/guard.py)），
但知道理由比撞上报错省事。

或者直接 clone：

```bash
git clone https://github.com/gmggyyds/the-great-me
cd the-great-me
pip install pyyaml                  # 跑测试再装 pytest：pip install -r requirements.txt
python3 thegreatme.py doctor        # 第一次先跑这个，看配置对不对
```

在这个目录里开 Claude Code，`.claude/skills/` 会自动带上同一个 skill
（它是指向 `skills/` 的软链，不是拷贝——两份拷贝早晚漂移）。

装完对 AI 说一句「**喂一轮画像**」，skill 会跑完整条流程：取数 → 标题号 → 过闸 → 入账 → 出周报和卡。
想手动跑，四条命令：

```bash
python3 thegreatme.py harvest       # 跑所有启用的源，出候选（不直接进账本）
python3 thegreatme.py review        # 看抽到了什么，默认打码
python3 thegreatme.py accept --all  # 候选进账本
python3 thegreatme.py render        # 出 PROFILE.md（可外传）+ PROFILE.private.md（本机）
```

九个子命令：`init` / `doctor` / `harvest` / `review` / `accept` / `render` / `report` / `card` / `status`。

## 🎯 它解决什么

每开一个新对话，AI 完全不认识你。

你问它「我该不该做这件事」，它只能拿你刚打的那三行字回答，于是给出一份任何人都能拿到的通用模板。
而真正决定答案的那几样东西——你手上攒了三年的数据、那个能替你开门的人、你缺的到底是代码杠杆还是资本杠杆——
它一个都不知道，你也懒得每次重讲一遍。

更别扭的是：你其实已经把自己讲清楚过一次了。那份花一小时答出来的 12 题报告，
躺在某个对话窗口里，两周后你自己都翻不出来，AI 更读不到。

于是你尝试自救，把笔记、纪要、聊天记录一股脑倒进某个「第二大脑」文件夹。
三个月后它变成一坨谁也不敢删的东西，AI 读了反而更糊涂——里面混着别人在会上讲的行业观点，
它把讲师的判断当成了你的资源。

**the-great-me 做的事只有一件：把这些收成一份带出处的断言账本，让 AI 在替你判断之前先读到它。**
挂不上 12 题的内容一个字都进不来。

<table>
<tr><th width="50%">没有它</th><th width="50%">有它</th></tr>
<tr valign="top"><td>

- 每个新对话都从「我是做什么的」重讲一遍
- 12 题报告躺在某个窗口里，找不回来
- 想沉淀就只能全量倒进一个文件夹
- AI 分不清哪句是你的资源、哪句是别人的观点
- 攒起来的都是客户名、供应商、人脉、收入——不敢让它长大

</td><td>

- 一份常驻画像，判断类问题前自动读
- 12 题是账本的骨架，缺哪一题一眼看得见
- 只收挂得上题号的，其余挡在门外
- 每条断言带出处，能查回是哪份材料、什么时候确认的
- 全落本地、`0600` 权限、写之前自查是不是要上云

</td></tr>
</table>

## 🚪 那道闸

`12 题答案 + 平时的笔记 → 题号闸 → 账本 → 两份画像`

两份画像：`PROFILE.md` 可外传，`PROFILE.private.md` 只在你机器上。

闸门的判据只有一条：**这段挂 12 题里的哪一题、是不是关于你本人的。**
挂不上就丢掉，不猜、不硬塞——猜错的题号比不收更糟。

这不是洁癖。会议录音里大量内容是**别人**在讲行业观点，笔记 App 里
攒了几年的东西大多是转发和摘抄——它们是知识，不是关于你的断言。
全量投喂等于把少量信号连着大量噪音一起塞给 AI，画像只会越喂越糊。
实测：一批 15 条素材只有 3 条过闸，这个比例是正常的。

因为这一步是判断不是解析，所以它**必须由 AI 跑，定时任务只能负责把你叫起来**：

| 层 | 做什么 | 在哪 |
|---|---|---|
| skill | 取数 → 标题号 → 过闸 → 入账 → 出周报和卡 | [skills/the-great-me/](https://github.com/gmggyyds/the-great-me/tree/main/skills/the-great-me)，说一句「喂一轮画像」 |
| hook | 只提醒「N 天没长了」，不写入 | [hooks/staleness-nudge.sh](https://github.com/gmggyyds/the-great-me/blob/main/hooks/staleness-nudge.sh)，装法在文件头（需要 bash） |

## 🔁 让它跟着你长

**第一步，把 12 题的答案放进来。** 最省事的做法：把你跟 AI 那段对话整段复制，
存成 `data/metaquestions/我的对话.md`。不用整理格式——引擎靠题目原文定位，
ChatGPT、Claude 复制出来的都认。或者填 [data/metaquestions/answers.template.md](https://github.com/gmggyyds/the-great-me/blob/main/data/metaquestions/answers.template.md)，`## Q1` 下面写答案，没答的留空。

**第二步，让 AI 每次先读它。** 在 `~/.claude/CLAUDE.md`（Claude Code）或 `AGENTS.md`（Codex）里加一行：

```markdown
> 做判断类的事之前先读：<你的路径>/data/PROFILE.private.md
```

选品、投资、招人、合作、定价、「我该怎么办」这类问题它会先看你的底牌；改代码、查数据这类纯执行的活不用读。

**第三步，之后有新东西丢进 `data/inbox/`，段首标个题号：**

```markdown
Q9: 认识一个做行业公众号的，他缺一线的原创素材，我这边正好有——这是他愿意帮我分发的理由。
```

再跑一次 `harvest`。没标题号的段落不会被收，但引擎会告诉你拒了几段——
那些正是该拿去问 AI 的：「这段改变了我 12 题里的哪一条？」挂得上再回来标号。

### 周报看的不是进度，是缺口

`PROFILE.private.md` 是终态快照，看不出这周发生了什么。`report` 补的就是这个差：
哪一段最薄、哪几题一条断言都没有、哪些断言超过 180 天没被任何源再确认过（可能已经不成立了），
最后给你一句能直接丢给 AI 的话，把空着的那题问出来。周报默认打码、落本地文件、不联网不外发。

### 进度卡是唯一设计成给人看见的出口

其余所有出口都在防止内容离机，这一个反过来——它是拿来截图的，所以它一个字的断言正文都不碰，
只有数字和题号：四段各多少条、12 题答了几题、哪一段最薄。
`card` 同时生成自包含的 `card.html`，浏览器直接打开，深浅色自适应。

想让画像内容也能露出，走 `PROFILE.md` 那一层，它默认是空的，得你逐条显式标 `public`。

## 🔒 你的数据去哪了

哪也没去。没有后端、没有账号、没有云同步、没有遥测。

- 全部落在 `data_dir` 下，被 `.gitignore` 挡着
- 写之前引擎自查一遍：目标在 git 仓里且没被 ignore，直接拒绝写。这个检查每次写入都重查、不缓存——
  数据目录一旦被加上 git remote，下一次 `render` 立刻拒写
- 零 remote 的本地 git 仓放行：护栏显式为它开了口。想要历史和回滚就这么建——
  有完整版本历史，而且因为没有远端，物理上传不出去
- 三级敏感度 `public` / `internal` / `private`，缺省 `private`。可外传的 `PROFILE.md` 一开始是空的，
  这是正常起点不是缺数据
- 账本、两份画像、周报全部 `0600`。只有 `card.html` 不设 600，它本来就是给人看的

把数据整个挪出这个仓（画像和引擎本来也不该住在一起）：

```bash
cp sources.yaml ~/.mine/sources.yaml     # 把里面的 data_dir 改成你想要的位置
export THEGREATME_CONFIG=~/.mine/sources.yaml
# 或者每次显式指定：python3 thegreatme.py --config ~/.mine/sources.yaml status
```

配置里的相对路径按该配置文件所在目录算，不是按仓根——不然数据会被写回引擎目录，而引擎目录是个公开仓。
之后 `git pull` 更新引擎完全不碰你的数据。

## 🔌 接你自己的语料源

多数情况不用写代码。

[folder 适配器](https://github.com/gmggyyds/the-great-me/blob/main/thegreatme/adapters/folder.py)
只认一件事：`data/inbox/` 里的 `.md` / `.txt`，段落开头标了 `Q<n>:`。
所以任何能把内容打到标准输出的 CLI，现在就已经能接进来了：

```bash
your-notes-cli export --since <上次的水位> > data/inbox/notes.md
```

缺的从来不是适配器，是一条「抓下来的时候顺手标题号」的规则。把它写进 `~/.claude/CLAUDE.md`：

> 把任何外部笔记写进 `the-great-me/data/inbox/` 之前：
> 先读 [questions.yaml](https://github.com/gmggyyds/the-great-me/blob/main/thegreatme/questions.yaml)
> 里的 12 题，逐段给内容标上 `Q<n>:` 前缀。
> 挂不上任何一题的段落直接丢掉，不要硬塞。
> 每段末尾附出处（笔记 id / 会议 token + 日期），审的时候要能查回去。

标题号本来就该由读得懂内容的那一方做，让规则去做等于把 AI 当成那一层，换任何新工具都不用改代码。
落完盘照常 `harvest → review → accept`，「审」那一步还会再把关一次。

### 真需要写适配器的情况

源不是 CLI，而是结构化文件（markdown 表格、带 frontmatter 的笔记目录）。
`sources.yaml` 里那两个默认关闭的（`relations` / `memories`）就是示例，
照着 [adapters/](https://github.com/gmggyyds/the-great-me/tree/main/thegreatme/adapters) 里的写法加一个。三条规矩：

1. 只读，永远不写回源
2. 只提议不判定：提取内容、提议题号、附证据指针，准不准交给「审」那一步
3. 默认 `private`：适配器无权判定什么能外传

## 🧪 实测过什么

| 项 | 数 |
|---|---|
| 单元测试 | 107 条全过（`python3 -m pytest -q`） |
| 端到端「学员旅程沙箱」 | 24 项检查全过（`python3 sandbox/student_journey.py`） |
| 沙箱变异自检 | 4 个变异用例逐个注入进产品，断言沙箱必须报红 |
| CI 关卡 | 四道：pytest → 沙箱 → 变异自检 → 数据目录必须被 gitignore |
| 引擎体量 | 1,549 行 Python（`thegreatme/` 1,273 + CLI 276）；测试 1,115 行、沙箱 274 行都另计 |
| 运行时依赖 | 1 个：pyyaml（pytest 只是开发依赖） |

几条值得说的：

- **变异用例是防止沙箱变成橡皮图章的。** CI 会把 `cache` / `cardleak` / `mq` / `unmask` 四个已知缺陷
  逐个注回产品代码，沙箱必须每次都红。一个从不会失败的检查等于没有检查。
- **进度卡的零内容验证是三重的**：终端版和 `card.html` 双查敏感串，再逐条拿账本里每条断言的前 12 字去比对。
- **gitignore 那道 CI 关是双向的**：既断言 `data/` 被 ignore，也反向断言 `data/metaquestions/answers.template.md` 不能被 ignore。
- CI 跑在 Python 3.12 上，更低版本没验过。

12 题的题面来自 meta-questions v0.2.0，由
[tools/sync_questions.py](https://github.com/gmggyyds/the-great-me/blob/main/tools/sync_questions.py)
从真源生成而不是手抄——两个仓各写一份题目文本，早晚漂移。

```bash
python3 tools/sync_questions.py     # 需要本地 clone 了 meta-questions
```

## 📁 目录

```
the-great-me/
├── thegreatme.py              CLI 入口，9 个子命令
├── sources.yaml               你的画像从哪些源长出来（改这个，不改代码）
├── requirements.txt           pyyaml 是唯一运行时依赖，pytest 只用于开发
│
├── thegreatme/
│   ├── questions.yaml         12 题的规范文本，从 meta-questions 真源生成
│   ├── questions.py           题面加载与题号解析
│   ├── schema.py              claim 账本：只存断言和指针，不存原文；原子写
│   ├── ledger.py              候选进账本的合并语义（相等性只有一套）
│   ├── config.py              路径从配置读，不写死在代码里
│   ├── guard.py               写入前护栏：会上云的目标一律拒写
│   ├── render.py              账本 → PROFILE.md（可外传）+ PROFILE.private.md（本机）
│   ├── pulse.py               账本 → 结构性统计，一个字的断言内容都不碰
│   ├── report.py              周报：这周变了什么 + 哪一段还是空的
│   ├── card.py                进度卡：终端版 + 自包含 card.html，零内容
│   └── adapters/
│       ├── metaquestions.py   12 题对话记录 / 答案模板（题目原文匹配，最准的一个）
│       ├── folder.py          inbox：只收标了题号的段落，并报出拒了几段
│       ├── relations.py       结构化人物索引示例（默认关闭）
│       └── memories.py        带 frontmatter 的笔记目录示例（默认关闭）
│
├── skills/the-great-me/       Claude Code skill：说「喂一轮画像」跑全流程
├── hooks/staleness-nudge.sh   催更 hook：只提醒，不写入
├── sandbox/
│   ├── student_journey.py     端到端 24 项：装成插件之后的那条真实路径
│   └── mutations/             4 个变异用例，用来验证沙箱自己会红
├── tools/sync_questions.py    从 meta-questions 真源重新生成 questions.yaml
├── tests/                     单元测试 107 条
└── data/                      你的东西住这儿，被 gitignore 挡着
    └── metaquestions/answers.template.md   想手填的人用这个（唯一不被 ignore 的内容文件）
```

## ⭐ 国民级精品

**AI 时代最大的瓶颈，是你自己。**

不是模型不够强。是它不认识你——不知道你手里有什么、你的判断是怎么下的、
你到底在哪一步反复拖累了它。

下面四个，每一个拆的都是你身上的一处卡点。

| | 你卡在哪 | 它做什么 |
|---|---|---|
| **[meta-questions](https://github.com/gmggyyds/meta-questions)**<br><sub>AI 时代的元问题</sub> | AI 给你的是人均答案，因为它不知道你手里有什么 | 12 个问题问出你的优势、资源、关系网。**适合你的，才是最好的** |
| **the-great-me**<br><sub>更伟大的自己 · 你在这儿</sub> | 每开一次新对话，AI 都从零重新认识你一遍 | 把你的判断沉成常驻画像，让每次沟通都比上一次更懂你一点 |
| **[xxoo](https://github.com/gmggyyds/xxoo)**<br><sub>吸星大法</sub> | 你抄的那套方法论，是给**别人的**生意写的 | 逐环拿你的业务去对，把别人的化成你自己的 |
| **[agents-deep-insights](https://github.com/gmggyyds/agents-deep-insights)**<br><sub>会话照妖镜</sub> | 你以为是 AI 不行，其实是你在同一个地方反复绊住它 | 扫出你到底在哪拖累了它 |

连起来是一条线：

```
问心   我是谁、我手里有什么         meta-questions
铸我   让 AI 每次都带着这个认知      the-great-me
吸星   把外面的东西化成我的          xxoo
明镜   回头看我到底卡在哪            agents-deep-insights
```

**适合自己的，才有无限可能。** 这四个没有一个是给你标准答案的——
它们只干一件事：**让 AI 从「认识人类」变成「认识你」。**

## 🧭 说到底

- **它不替你做决定。** 它只是让你和 AI 手上有一份带出处的底牌清单。
- **它不猜你的笔记该归哪一题。** 挂不上 12 题的一个字都进不来，猜错比不收更糟。
- **它不联网、不上传、不分析你。** 没有后端，没有遥测，写之前还会自查一遍会不会上云。

一份写完就找不回来的报告，和一份 AI 每次判断前都会读的画像，中间差的不是内容，是它住在哪儿。

**答完 12 题了？把它放进来，让它跟着你长。**

<sub>MIT License</sub>
