---
name: the-great-me
description: 把外部笔记（Get笔记 / 飞书妙记 / 会议纪要 / 工单）按 12 题标好题号喂进个人画像账本，跑完 harvest→accept→render，出周报和可截图的进度卡。触发词：更新我的画像 / 喂一轮画像 / the-great-me / 画像周报 / 我的进度卡 / 扫一下我最近的笔记。
version: 0.1.0
---

# the-great-me · 让 12 题的答案常驻并跟着你长

**为什么要有这个 skill**：往画像里加东西的关键一步是「这段挂 12 题里的哪一题、是不是关于本人的」——
那是**判断，不是解析**。shell 脚本和 cron 做不了，只有读得懂内容的一方能做。所以喂养必须由 AI 跑，
定时任务只能负责按时把你叫起来。

## 先确认环境

```bash
export THEGREATME_CONFIG=<用户的 sources.yaml>   # 没设就是仓里自带那份
python3 <引擎目录>/thegreatme.py doctor
```

`doctor` 会报数据目录在哪、连了哪些源。**数据目录不在引擎仓里**是正常的（画像和引擎不该同居）。

## 12 题的权威文本

只从 `thegreatme/questions.yaml` 读，**不要凭记忆写题目**。两个仓各写一份题目文本必然漂移。

## 执行步骤

### 1. 取原文

用户说了源就用那个；没说就问一句「扫哪一段时间的、哪个源」。常用：

```bash
getnote notes --limit 30                     # 得到 / Get 笔记（要会员，无会员全线 403）
getnote note <id> --field content            # 取全文
lark-cli minutes minutes get --params '{"minute_token":"<token>"}'   # 飞书妙记，只能按 token 取单条
```

原文落**暂存目录**，不要直接进 inbox——inbox 里只放标好号的成品。

### 2. 逐条读，标题号（这一步是全流程的重点）

三条硬规矩，任何一条破了都会污染账本：

1. **挂不上任何一题的段落直接丢掉。** 不猜、不硬塞——错的题号比没有更糟。
2. **只收关于「本人」的断言。** 会议录音里大量是**别人**在讲行业观点（税务、IP、欧洲市场、
   工艺…）——那些是行业知识，该进第二大脑。往画像里塞会让 AI 下次把某个讲师的观点
   当成用户自己的资源。实测：15 条 Get笔记只有 3 条过闸，这个比例是正常的。
3. **归属存疑就不收**，或者收了在文件头注明「待本人核」。多人场里谁在说话往往判不准。

写成 inbox 文件，**一条源一个文件**，文件名带 id 和日期：

```markdown
<!-- 源：Get笔记 recorder_audio <id>「<标题>」<日期>，<时长>，<几人>，<类型>
     取用：`getnote note <id> --field content` -->

Q12: <一句话断言。空行分段，段首 Q<n>: >

Q6: <另一条>
```

文件名 `getnote_2026-08-28_<id>.md` —— 适配器取的**证据就是文件名**，名字含糊就查不回去。

### 3. 入账

```bash
python3 thegreatme.py harvest      # 会报「拒了几段」，念给用户听
python3 thegreatme.py review       # 默认打码；🔴 绝不要加 --unmask，那会把画像全文打进会话
python3 thegreatme.py accept --all
python3 thegreatme.py render
```

### 4. 出周报和进度卡

```bash
python3 thegreatme.py report       # 落本地文件；默认打码
python3 thegreatme.py card         # 终端卡 + 自包含 HTML，零内容，可截图
```

**周报的重点是「该补的」那一节**，不是新增了几条。念给用户听的顺序是：
哪一段最薄 → 哪几题还空着 → 有几条超过半年没被确认。

## 🔴 红线

- **`review --unmask` / `report --unmask` 绝不在 AI 会话里跑。** 画像含客户、供应商、人脉、收入，
  打进 stdout 就等于进 transcript 就等于上传模型 API。
- **画像内容不许贴进任何对外产出**：文档、开源仓、给同事看的东西、聊天记录。
- **可以给人看的只有进度卡**（`card`）——它一个字的断言正文都不碰，只有数字和题号。
- 数据目录若是本地 git 仓，**永远不要给它加 remote**。护栏每次写入都会重查，加了就开始拒写。

## 收尾

告诉用户三件事，别念流水账：

1. 这轮从几个源收了几条、**拒了几段**（拒了多少往往比收了多少更说明问题）
2. 现在最薄的是哪一段、哪几题还空着
3. 进度卡在哪，可以直接截图
