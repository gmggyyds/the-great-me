<div align="center">

<h1>the-great-me</h1>

<p><b>答完 12 题不是结束。让它跟着你长。</b></p>

<p>把 <a href="https://github.com/gmggyyds/meta-questions">meta-questions</a> 的答案变成一份常驻的自我画像 · 新笔记持续归位 · AI 做判断前先读它</p>

<p>
  <a href="https://github.com/gmggyyds/the-great-me/actions"><img alt="CI" src="https://github.com/gmggyyds/the-great-me/actions/workflows/ci.yml/badge.svg"></a>
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

## 多久跑一次（以及为什么不能全自动）

**喂养必须由 AI 跑，定时任务只能负责把你叫起来。**

因为往画像里加东西的关键一步是「这段挂 12 题里的哪一题、是不是关于你本人的」——
那是**判断，不是解析**。shell 脚本和 cron 做不了。硬让它们做，只会得到一堆猜错题号的断言，
而错的题号比没有更糟（实测：15 条会议笔记里只有 3 条该进画像，其余 12 条是**别人**在会上
讲的行业观点，收进来会让 AI 把讲师的观点当成你的资源）。

所以是两层：

| 层 | 做什么 | 怎么装 |
|---|---|---|
| **skill** | 取数 → 标题号 → 过闸 → 入账 → 出周报和卡 | `.claude/skills/the-great-me/`，说一句「喂一轮画像」 |
| **hook** | 只提醒「N 天没长了」，**不写入** | `hooks/staleness-nudge.sh`，装法在文件头 |

```bash
python3 thegreatme.py report   # 周报：这周变了什么 + 🔴 哪块还是空的
python3 thegreatme.py card     # 进度卡：零内容，可截图
```

### 周报的重点不是进度，是缺口

`PROFILE.private.md` 是**终态快照**，看不出这周发生了什么。周报补的就是这个差：

```
## 该补的
- 🔴 「杠杆在哪」只有 3 条，是四段里最薄的一段。
- 🔴 还有 1 题一条断言都没有：
  - Q10 Swap Test：把 AI 从你现在做的这件事里完全拔掉，你是「变慢」还是「整个模式垮掉」？
- ⏳ 5 条超过 180 天没被确认，可能已经不成立了。
```

最后它会给你一句能直接丢给 AI 的话，把空着的那题问出来。周报默认**打码**，
落本地文件（600 权限），不联网不外发——想推到别处自己接，产品本身不带这条。

### 进度卡：唯一一个设计成给人看见的出口

其余所有出口都在防止内容离机，这一个反过来——它是拿来截图的，所以它**一个字的断言正文
都不碰**，只有数字和题号：

```
┌────────────────────────────────────────────┐
│ the-great-me · 伟大的我                    │
│ 12 题　███████████░　11 / 12               │
│ 我是谁        █░░░░░░░░░    8              │
│ 我手里有什么  ██████████   98              │
│ 我认识谁      █████░░░░░   46              │
│ 杠杆在哪      █░░░░░░░░░    3　← 最薄      │
│ by GMGG　github.com/gmggyyds/the-great-me  │
└────────────────────────────────────────────┘
```

同时生成 `card.html`（自包含，浏览器直接打开，深浅色自适应）。

🔴 **别在私有画像上加 logo 鼓励人截图**——那等于亲手拆掉整套护栏。可传播的必须是这张卡。
想让画像内容也能露出，走 `PROFILE.md` 那一层（public），它默认是空的，得你逐条显式标。

## 你的数据去哪了

**哪也没去。** 没有后端、没有账号、没有云同步。

- 全部落在 `data/`，被 `.gitignore` 挡着
- 引擎**写之前会自查**：目标在 git 仓里且没被 ignore，直接拒绝写（`thegreatme/guard.py`）
- 所有断言默认 `private`。可外传的那份 `PROFILE.md` **一开始是空的**——
  这是正常起点不是缺数据。要让某条能外传，得显式把它标成 `public`
- 文件权限 600，同机别的进程也读不到

想要历史和回滚？给 `data/` 建个**本地 git 仓、不加 remote**——有完整版本历史，
而且因为没有远端，物理上传不出去。

**想把数据整个挪出这个仓**（画像和引擎本来也不该住在一起）：

```bash
cp sources.yaml ~/.mine/sources.yaml     # 把里面的 data_dir 改成你想要的位置
export THEGREATME_CONFIG=~/.mine/sources.yaml
# 或者每次显式指定：thegreatme.py --config ~/.mine/sources.yaml status
```

配置里的**相对路径按该配置文件所在目录算**，不是按仓根——不然数据会被写回引擎目录，
而引擎目录是个公开仓。之后 `git pull` 更新引擎完全不碰你的数据。

## 12 个问题从哪来

不在这个仓里手抄。`thegreatme/questions.yaml` 由 `tools/sync_questions.py` 从
[meta-questions](https://github.com/gmggyyds/meta-questions) 的真源生成——
两个仓各写一份题目文本，早晚漂移。

```bash
python3 tools/sync_questions.py     # 需要本地 clone 了 meta-questions
```

## 接你自己的语料源

先确认**要不要写代码**。多数情况不用。

### 有 CLI 的源 —— 不用写适配器

`folder` 适配器只认一件事：`data/inbox/` 里的 `.md`，段落开头标了 `Q<n>:`。
所以任何能把内容打到标准输出的 CLI，**现在就已经能接进来了**。
缺的从来不是适配器，是一条「抓下来的时候顺手标题号」的规则。

**① 让 CLI 把原文落进 `data/inbox/`**

```bash
# 得到 / Get 笔记 —— 能列表、能增量
getnote notes --all > data/inbox/getnote.md
getnote notes --since-id <上次最后一条的 id>     # 之后只取新增

# 飞书妙记 —— 只能按 token 取单条，CLI 没有列表接口
#（minute_token = 妙记链接 /minutes/ 后面那段）
lark-cli minutes minutes get --params '{"minute_token":"<token>"}'
```

⚠️ **先确认这些 CLI 在你手上是通的**，别等标完题号才发现拉不到东西：

- Get 笔记的 OpenAPI **要会员**。没有的话 `getnote quota` 直接返回
  `403 / not_member`，`notes`、`kbs` 一并不可用。
- 飞书妙记走的是你自建应用的凭证，得先给应用开 `minutes:minutes:readonly`。

两个源的节奏也不一样：得到可以定期扫，妙记是**开完会顺手粘一条**。
换成别的工具同理——只要它有 CLI，这一步就是一行重定向。

**② 加一条规则，让 AI 在落盘前标题号**

写进 `~/.claude/CLAUDE.md`（或你那个 agent 的规则文件）：

> 把任何外部笔记写进 `the-great-me/data/inbox/` 之前：
> 先读 `thegreatme/questions.yaml` 里的 12 题，逐段给内容标上 `Q<n>:` 前缀。
> **挂不上任何一题的段落直接丢掉，不要硬塞。**
> 每段末尾附出处（笔记 id / 妙记 token + 日期），审的时候要能查回去。

标题号这件事本来就该由**读得懂内容的那一方**做——它是判断，不是解析。
写成 Python 适配器只会得到一堆猜错的题号（见下面「它不做什么」第二条）。
让规则去做，等于把 AI 当成那一层，而且换任何新工具都不用改代码。

落完盘照常 `harvest → review → accept`，「审」那一步还会再把关一次。

### 真需要写适配器的情况

源不是 CLI，而是结构化文件（markdown 表格、带 frontmatter 的笔记目录）。
`sources.yaml` 里那两个默认关闭的（`relations` / `memories`）就是示例，
照着 `thegreatme/adapters/` 里它们的写法加一个。三条规矩：

1. **只读**，永远不写回源
2. **只提议不判定**：提取内容、提议题号、附证据指针，准不准交给「审」那一步
3. **默认 private**：适配器无权判定什么能外传

## 它不做什么

- **不替你做决定。** 它只是让你和 AI 手上有一份带出处的底牌清单。
- **不猜你的笔记该归哪一题。** inbox 里没标题号的不会被猜进某一题——猜错比不收更糟。
- **不联网、不上传、不分析你。** 没有遥测，没有后端。

## License

MIT
