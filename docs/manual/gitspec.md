> **HUMAN MANUAL — NON-NORMATIVE.** 这是给人看的入门说明。仓库权限与正式规则只看 [`docs/RULES.md` §7](../RULES.md#7-git)；下面的命令示例不会自动授权 agent 提交、合并或推送。

# Git 手册

> 目标：知道自己在哪、改了什么、保存到哪。别炸历史。

## 1. 先懂四个地方

```text
工作区 ──git add──> 暂存区 ──git commit──> 本地历史 ──git push──> GitHub
  文件               下次提交             已保存提交            共享副本
```

只记四句：

- `git add` 是“选进下一次提交”，不是上传。
- `git commit` 是“保存到本机历史”，不是上传。
- `git push` 才会改 GitHub。
- 未提交的修改不在历史里，也不在 GitHub。

## 2. 第一反应：看现场

每次开工先敲：

```bash
git status --short --branch
git branch --show-current
```

常见输出：

```text
 M file.py    改了，未暂存
M  file.py    已暂存
MM file.py    暂存后又改了
?? file.py    Git 还不认识的新文件
 D file.py    删除了，未暂存
## main...origin/main [ahead 1]    本地多一个提交
```

两列记法：左边是暂存区，右边是工作区。

看到不认识的修改：停。那可能是自己、同伴或 agent 留下的工作。

## 3. 第二反应：看差异

```bash
git diff
git diff --staged
git log --oneline --decorate -n 10
```

- `git diff`：还没暂存的改动。
- `git diff --staged`：下一次 commit 真正会收进去的内容。
- `git log`：最近保存过什么。

看不懂 diff，就不 commit。

## 4. 每天只走这条路

### 开一条小分支

先确认工作树干净，再开分支：

```bash
git switch -c codex/<short-task>
```

例子：

```bash
git switch -c codex/fix-vault-picker
```

一条分支只做一件事。

### 改文件，跑检查

```bash
git status --short
git diff
```

keikeu 代码改动：

```bash
.venv/bin/python -m pytest
.venv/bin/python -m compileall -q src
```

只有文档改动：

```bash
.venv/bin/python scripts/check_docs.py
git diff --check
```

没有运行的检查，要明说。

### 精确暂存

```bash
git add path/to/file1 path/to/file2
git diff --staged
git status --short
```

别上来就 `git add .`。先选明确文件。

一个文件里混了两件事时，再用：

```bash
git add -p
```

### 提交

```bash
git commit -m "fix: keep vault selection after restart"
```

常用开头够了：

```text
docs: 文档
fix:  修 bug
feat: 新行为
test: 测试
```

好消息说明“做了什么”。`update`、`changes`、`final` 都等于没说。

### 合进 main

```bash
git switch main
git merge --ff-only codex/<short-task>
```

`--ff-only` 合不了就会停，不会自作聪明制造复杂历史。此时先看：

```bash
git status
git log --oneline --decorate --graph --all -n 20
```

不要条件反射地 rebase。

### 推送

```bash
git push origin main
```

这一步会改共享仓库。先确认 main、commit 和测试都对。Agent 必须得到明确授权才能 push。

## 5. 分支、commit、tag 到底是什么

```text
commit = 一张保存好的快照
branch = 会随着新 commit 前进的路标
HEAD   = 你现在站的位置
tag    = 钉死在某个 commit 上的里程碑
```

创建 annotated tag：

```bash
git tag -a v0.2.0 -m "keikeu Road v0.2 complete"
```

它先只存在本机。要让 GitHub 看见，单独推送：

```bash
git push origin v0.2.0
```

## 6. 远端：先看，再动

```bash
git fetch origin
git status --short --branch
git log --oneline main..origin/main
git log --oneline origin/main..main
```

- `fetch`：更新你对远端的认识。
- `origin/main`：上次 fetch 后的本地记录，不是实时网页。
- `pull`：会改本地文件或历史，不是“看看”。
- `push`：会改远端。

## 7. 安全撤销

暂存错了，但想保留文件修改：

```bash
git restore --staged path/to/file
```

已经提交了坏改动，尤其是已经 push：

```bash
git revert <commit-hash>
```

`revert` 会增加一个反向提交，历史仍看得懂。

合并冲突，不想继续：

```bash
git merge --abort
```

想丢弃未提交修改时，先复制文件，再确认精确路径。`git restore <file>` 会直接吃掉该文件的未暂存修改。

## 8. 红色按钮

初学阶段不要独自运行：

```bash
git reset --hard
git clean -fd
git push --force
git branch -D <branch>
git rebase <branch>
```

它们不是邪术，但会丢工作或改写历史。需要时先说清目标、影响和恢复办法。共享历史禁止普通 `--force`。

## 9. 冲突时别猜

你会看到：

```text
[七个 <] HEAD
这一边
[七个 =]
另一边
[七个 >] branch-name
```

做法：

```bash
git status
# 人工读懂两边，编辑文件，删除冲突标记
git add path/to/resolved-file
# 跑测试，再完成 merge commit
```

不要盲选 ours 或 theirs。两边都可能有用，也可能都错。

## 10. 出事协议

感觉不对，只运行只读命令：

```bash
git status --short --branch
git diff
git diff --staged
git log --oneline --decorate --graph --all -n 20
```

然后停手，保存终端输出，问人。不要用破坏命令“试试看”。

## 11. 和 coding agent 合作

开工前告诉它：

```text
任务是什么
允许改哪些文件
明确不改什么
是否允许 commit / merge / push
```

交接时必须拿到：

```text
当前 branch 和 HEAD
修改与未跟踪文件
跑过和没跑的检查
是否 staged / committed / pushed
剩余风险与下一条安全命令
```

Agent 写代码。人拥有 diff 和历史。

## 12. 一分钟命令表

| 想做什么 | 命令 |
| --- | --- |
| 我在哪、脏不脏 | `git status --short --branch` |
| 看未暂存改动 | `git diff` |
| 看下次提交内容 | `git diff --staged` |
| 看最近历史 | `git log --oneline --decorate -n 10` |
| 开小分支 | `git switch -c codex/<task>` |
| 选文件 | `git add <exact-paths>` |
| 保存到本地历史 | `git commit -m "type: summary"` |
| 看远端 | `git fetch origin` |
| 改远端 | `git push origin <branch-or-tag>` |
| 标记版本 | `git tag -a <version> -m "message"` |

最后只记：

```text
先 status。
再 diff。
小分支，小 commit。
看不懂就停。
```

想看四个区域如何移动，打开 [`git-interactive.html`](git-interactive.html)。正式权限永远回到 [`RULES §7`](../RULES.md#7-git)。
