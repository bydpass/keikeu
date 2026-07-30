# Road v0.5：Quiet Desk UI Reform and Routine Set

> 状态：**CP6 PASSED · FOLLOW-UP CHECKPOINT AUTHORIZED BY ADVANCE YOLO**
>
> 目标分支：`road_v05_ui_reform_and_routine_set`
>
> 计划日期：2026-07-29
>
> 视觉原型：[keikeu-v05-prototype.html](docs/design/keikeu_opendesign/keikeu-v05-prototype.html)
>
> 冻结的 pre-CP0 阅读快照（非权威）：[HTML](docs/road-v0-5-planbook.html) · [PDF](docs/road-v0-5-planbook.pdf)

## 1. Core judgment

v0.5 不让 keikeu 变大。它只做一件事：让现有创作路径变顺、变安静、变可信。

这一轮不是「可分发的 macOS alpha」。签名、公证、安装包、发布兼容性与公开分发属于 v0.6。v0.5 只在当前 macOS 主工作站上完成产品体验与工程秩序的收口。

用户路径保持为：

```text
Daily Card → New Paper → Paper Desk → Save
                              ↓
                         Flashcard
                              ↓
                           Library
                              ↓
                       External editor
```

v0.5 的产品判断有 5 条：

1. Paper 是主工作台，必须一眼看出可编辑与只读区域。
2. 保存建立新基线，放弃只回到最近一次成功保存，不能回到更早版本。
3. Flashcard 只呈现刚保存的内容，不与 Paper 各说各话。
4. Library 不扩功能，只守住搜索、排序、选择与返回上下文。
5. 全部页面采用同一套安静视觉语言，包括 Vault、迁移与 Core 阻塞或恢复页面。

## 2. Scope and exclusions

### 2.1 Included

- 重新实现 Paper Desk 的视觉层级与编辑手感。
- 明确名称、Summary、Highlights、Tags 的编辑入口。
- 原始草稿保持锁定与只读。
- 建立统一的 dirty state、保存基线与离开保护。
- 重排 Highlights，鼠标或触控板拖动即可。
- Flashcard 改为 Summary-first，之后每张只显示 1 个 Highlight。
- Library 保持 v0.4 行为，并保留返回时的查询上下文。
- 统一所有页面的字体、颜色、间距、焦点、空态、错误态和动作层级。
- 增加项目本地 routine skill，规范此后 keikeu 的 coding、debug、refactor、test 与 docs 流程。
- 用真实 `.app` 与复制或合成 Vault 连续 dogfood 30 分钟，修掉全部 P0/P1 与最烦的 3 个问题，再重跑 30 分钟。

### 2.2 Explicitly excluded

- AI 写作、自动续写或替作者改写。
- 云同步、账号、社区、遥测、后台网络服务。
- 新数据库、Vue Router、Pinia、UI kit、图标库、拖拽库。
- Markdown schema、Python Core、JSONL protocol 或 DTO 的产品扩展。
- 文件崩溃恢复、断电恢复与 `commit_unknown` 自动重试。
- 签名、公证、DMG、公开下载与跨版本 macOS 兼容性声明。
- iOS、Android、Windows 或移动断点验收。

## 3. Interaction contract

### 3.1 Daily Card and entry

- 启动后保留 Daily Card，按 v0.5 视觉系统重画，不删除现有入口。
- 用户从 Daily Card 新建 Paper 后进入空白 Paper Desk。
- 空白 Paper 仍使用既有 Core 创建与持久化语义，不新建另一套草稿模型。

### 3.2 Paper Desk

Paper 顶部显示名称与 Paper code。中部只允许编辑 4 类内容：

- 名称
- Summary
- Highlights
- Tags

原始草稿位于底部或次级区域，显示锁定状态与只读说明。用户不能在 v0.5 中直接改写它。

编辑区使用横线、留白与纸面层级，不用满屏圆角输入框。所有可编辑字段必须具备：

- 清楚的 label。
- 可见的 hover 与 focus 状态。
- 键盘 Tab 顺序。
- 失焦后仍能识别字段边界。
- 空值提示，但不把提示文字写入内容。

Highlights 每项包含短标题与正文。允许新增、删除和拖动排序。拖动只承诺鼠标与触控板，不承诺键盘重排。键盘用户仍可编辑、新增与删除。

### 3.3 Save baseline

- 任一受控字段相对最近成功保存发生变化，顶部显示「未保存」。
- `Cmd+S` 与保存按钮走同一保存函数。
- 保存成功后，当前 snapshot 成为新 baseline，状态改为「已保存至 Markdown」。
- 保存失败时不更新 baseline，不清除用户输入，不显示成功状态。
- 外部修改、stale snapshot 与 `commit_unknown` 继续走 v0.4 的既有冲突或恢复边界。

### 3.4 Dirty departure

有未保存更改时，以下动作必须进入同一离开保护：

- 前往 Flashcard 或 Library。
- 切换或新建 Paper。
- 切换 Vault。
- 关闭窗口。

对话框采用原生二选一：

- **放弃更改**：恢复最近一次成功保存的 baseline，再执行原动作。
- **继续编辑**：取消原动作并留在 Paper。

不提供「保存并前往」。用户先保存，再执行导航。Tauri production 使用官方 dialog plugin 的二选一确认，并自定义按钮文字。非 Tauri 浏览器开发环境可使用 `window.confirm` fallback。不得依赖 release WebView 中已经失败过的 `window.confirm`。

正常导航保证不丢内容。该保证不延伸到进程崩溃、系统断电或 mutation 结果未知。

## 4. Flashcard and Library

### 4.1 Flashcard

- 第 1 张只显示 Summary，让用户先记住故事整体。
- 第 2 张起每张只显示 1 个 Highlight。
- Highlight 卡片可手动展开 Summary context，默认保持收起。
- 名称、Summary 与 Highlights 必须来自最近成功保存的 Paper。
- Paper 仍 dirty 时，进入 Flashcard 先触发离开保护，不把未保存表单内容偷偷带入卡片。
- 每次打开从第 1 张开始，左右键与现有上一张、下一张行为保留。

### 4.2 Library

Library 本轮不重做信息架构或文件能力。必须保持：

- scope
- search query
- sort order
- active item
- batch selection
- scroll position

从 Paper 或 Flashcard 返回 Library 时，上述状态不乱。成功切换 Vault 或应用重启后可以重置，不新增持久化偏好。现有 move、branch、Trash、restore、permanent delete、open 与 reveal 行为不改。

## 5. Visual system for every page

最终原型是 v0.5 的视觉方向，不是可直接复制的生产模板。生产实现删除 demo 数据与「设计原则」演示面板，保留现有真实功能。

### 5.1 Tokens and layout

- warm parchment canvas
- near-black text
- ink-blue focus and primary action
- warm gray rules and secondary text
- serif carries names and major hierarchy
- sans carries controls and metadata
- no gradients
- no glass
- no hard shadow
- no nested card wall
- no pill-shaped decoration except controls that genuinely need the shape

当前窗口验收只覆盖：

- 默认窗口 `1220×780`
- 最小窗口 `920×680`

### 5.2 Page coverage

「整理全局视觉」明确覆盖全部现有页面与阻塞态：

- Daily Card
- Paper Desk
- Flashcard
- Library
- Vault 选择、初始化与切换
- migration preflight、执行、结果与失败
- Core 启动失败
- protocol mismatch
- sidecar crash 或 unavailable
- session expired
- `commit_unknown` 恢复提示
- loading、blank、empty 与 error states
- 现有确认对话框与 destructive action gate

这些页面只统一视觉、动作层级、键盘焦点与说明语言。v0.5 不借视觉改造新增业务能力。

## 6. Engineering plan

### Road branch, commit, and closeout

每个 CP 从上一个已经开发者明确通过或事先声明 YOLO 的 CP commit 创建独立堆叠分支。未通过的 CP 不能成为下一个 CP 的基线：

| CP | Branch |
| --- | --- |
| CP0 | `process/cp0-authority-routine` |
| CP1 | `ui/cp1-paper-desk` |
| CP2 | `ui/cp2-departure-protection` |
| CP3 | `ui/cp3-flashcard-sync` |
| CP4 | `ui/cp4-library-context` |
| CP5 | `ui/cp5-whole-app-visual` |
| CP6 | `qa/cp6-dogfood-acceptance` |

Commit 必须先得到明确授权，再按 `docs/RULES.md` §7 精确 stage、检查 cached diff 并调用 `aic`。最终 checkpoint 通过并 commit 后，另建 `docs/archive/snapshots/road-v0-5.html` closeout change，按 `docs/RULES.md` §8 汇总全部 CP 记录；不把该 snapshot 冒充产品验收。

### CP0 · Authority, routine, and test harness

Deliverables:

- 将本 Planbook 接入项目 authority map，保留 v0.4 SPEC 作为当前运行边界，直到 v0.5 验收。
- 新建 `.agents/skills/keikeu-routine/`：
  - `SKILL.md`
  - `agents/openai.yaml`
- 使用 skill-creator 生成并运行 quick validation。
- 复核并锁定 dirty departure 的官方 dialog binding。候选为与现有 Rust plugin 兼容的 `@tauri-apps/plugin-dialog@2.7.2`，只有确认当前 lock 与 API 后才写入 npm lock。

Dialog binding lock:

- JavaScript binding 精确锁定为 `@tauri-apps/plugin-dialog@2.7.2`，与 Rust `tauri-plugin-dialog = "=2.7.2"` 配对。
- CP2 使用异步 `confirm()` 与自定义 `okLabel`、`cancelLabel`；Tauri capability 只增加经当前生成 schema 核对的 `dialog:allow-message`、event listen/unlisten 与 window destroy 权限。
- CP0 不改 Vue caller 或 capability。`window.confirm` 只保留为 CP2 的非 Tauri 浏览器 fallback。

Routine 的强制 checkpoint：

1. 读 authority 与全部 caller。
2. 运行 Git preflight。
3. 写明 Task、Will edit、Will not edit。
4. 找 root cause，做最小 patch。
5. bug fix 留 1 个 focused regression check。
6. UI change 跑 focused Vitest、默认与最小尺寸、真实 Tauri smoke。
7. Vault、迁移、delete 与 recovery 只用 fixture、copy 或 synthetic data。
8. 交付前检查 final diff、status、checks、risks 与 Git state。

不增加 Git hooks、CI gate、后台 agent、脚本资产或第二套规则。Routine 只引用 `AGENTS.md`、`docs/SPEC.md` 与 `docs/RULES.md`，不复制它们。

Exit gate:

- skill validation 通过。
- routine 完成开发者逐段 QA。
- 规则没有与仓库 authority 冲突。

CP0 record — 2026-07-29:

- `keikeu-routine` 通过 skill-creator quick validation；未增加 hooks、CI gate、后台 agent 或辅助资产。
- active authority map 已接入本 Planbook，v0.4 SPEC 继续约束当前 runtime。
- JavaScript 与 Rust dialog plugin 均精确锁定为 `2.7.2`；实际类型声明确认 `confirm()`、`okLabel` 与 `cancelLabel` 可用。
- documentation check、48 个 Vitest、Vite production build、10 个 Rust tests 与 `git diff --check` 通过。
- 自动检查与 routine 开发者逐段验收已通过；开发者于 2026-07-29 明确通过 CP0，并由 `aic` 提交为 `11c2149`。

### CP1 · Paper Desk

Entry gate:

- CP0 已由开发者明确通过并 commit。
- 首次真实使用 routine 完成 preflight 与 scope 声明；允许在第一份产品 patch 前根据实际摩擦修正 routine 1 次。

Deliverables:

- 用真实 DTO 接通最终 Paper 布局。
- 完成 4 类编辑区、只读原稿、dirty 指示与保存动作。
- 完成 Highlight 的新增、删除与 pointer drag reorder。
- 保留外部修改拒绝与未知 frontmatter。

Exit gate:

- 用户能在 5 秒内指出可编辑区域。
- 鼠标和键盘可完成保存前的全部必要操作，排序除外。
- focused Vitest 与默认、最小尺寸截图通过。

CP1 record — 2026-07-29:

- `PaperView` 直接复用现有 DTO 与保存流，改为名称、Summary、Highlights、Tags 四个横线式编辑区；系统编号改为只读 metadata，原始草稿默认折叠且不可编辑。
- Highlights 使用原生 drag/drop 把手；新增、删除、上移、下移继续提供鼠标与键盘路径，未增加依赖或第二套标签状态。
- focused Vitest `13`、全量 Vitest `50` 与 Vite production build 通过；真实指针拖动把前两条 Highlight 成功换位，保存后 baseline 状态回到「已保存至 Markdown」。
- 合成 DTO 浏览器 QA 在 [`1220×780`](docs/acceptance/road-v0-5/cp1-paper-1220x780.png) 与 [`920×680`](docs/acceptance/road-v0-5/cp1-paper-920x680.png) 无横向溢出或裁字；键盘 focus probe 确认字段获得 `3px solid` accent outline，editable hover 另有明确底线反馈。最小窗口将边注移到编辑区之后。
- CP1 不依赖桌面 API，因此未运行 Tauri smoke；真实 Vault、真实 Home 与作者内容未参与。开发者已事先声明 CP1 YOLO，exit gate 据此通过。

### CP2 · Baseline and departure protection

Deliverables:

- 建立统一 baseline snapshot 与 dirty comparison。
- 所有离开路径进入一个 navigation guard。
- Tauri 原生二选一确认接通，浏览器仅作开发 fallback。
- window close、Vault switch、Paper switch 与 navigation 共用语义。

Exit gate:

- 放弃只恢复最近保存。
- 继续编辑不改变内容或当前页面。
- 保存失败不清空输入。
- 没有 mutation 自动重试。

CP2 record — 2026-07-29:

- `PaperView` 以完整表单 clone 保存最近成功 baseline；导航、Paper 新建/切换、Vault 切换与窗口关闭全部进入同一个异步 `requestDeparture()`。已保存 Paper 的 Vault picker 取消路径保留当前 path；未保存 Draft 不开放直接 Vault 切换。
- 「继续编辑」不改表单或页面；「放弃更改」先恢复最近成功 baseline，再执行原动作。保存失败与 `commit_unknown` 不更新 baseline，也不重试 `paper.save`。
- Tauri 使用原生 `confirm()`，按钮精确为「放弃更改」与「继续编辑」；浏览器只保留 `window.confirm` fallback。窗口关闭先同步阻止，再由同一 guard 决定是否 `destroy()`。
- Markdown 已耐久写入后，偶发索引刷新失败不再被误报为 Paper 保存失败；服务只尝试一次索引刷新，Markdown 继续作为权威。
- focused Vitest `33`、全量 Vitest `57`、Python `235`、Rust `10`、Vite production build 与 compileall 通过。合成 Tauri smoke 验证导航和关闭窗口两条原生路径：继续编辑保留 dirty 内容，放弃更改允许导航或销毁窗口。
- [`1220×780`](docs/acceptance/road-v0-5/cp2-departure-1220x780.png) 与 [`920×680`](docs/acceptance/road-v0-5/cp2-departure-920x680.png) Tauri 实际窗口无横向溢出或裁字；测试未读取或改写真实 Vault、真实配置或作者内容。开发者已事先声明 CP2 YOLO，exit gate 据此通过。

### CP3 · Flashcard synchronization

Deliverables:

- Summary-first。
- 每张 1 个 Highlight。
- 手动展开 Summary context。
- 只读取最近成功保存的 Paper。

Exit gate:

- Paper 与 Flashcard 的名称、摘要、亮点一致。
- dirty Paper 不能绕过离开保护。
- 每次进入从第 1 张开始。

CP3 record — 2026-07-29:

- 未成功保存、没有 Markdown path 的 Draft 不再开放 Flashcard；保存成功后入口才启用，避免 `flashcard.open(null)` 错开索引中的其他 Paper。
- Flashcard 每次从 Python 重新读取已保存 Markdown，只投影该基线的名称、Summary 与 Highlights；dirty 表单必须先经过 CP2 离开保护，放弃后不会把未保存内容带入卡片。
- Summary 固定为第 1 张，之后每张只显示 1 个 Highlight；Summary context 只在 Highlight 卡片上手动展开。返回 Paper 后再次进入，位置重置为 `1 / 3`。
- focused Vitest `31`、Flashcard service pytest `1`、全量 Vitest `57`、Python `235`、Vite production build、compileall 与 documentation check 通过。
- [`1220×780`](docs/acceptance/road-v0-5/cp3-flashcard-1220x780.png) 展示 Summary 首页；[`920×680`](docs/acceptance/road-v0-5/cp3-flashcard-920x680.png) 展示单个 Highlight 与展开的 Summary context。两次合成浏览器渲染均无横向溢出，未读取或改写真实 Vault、真实配置或作者内容。
- CP3 未新增桌面 API 或生命周期行为，因此未把浏览器渲染冒充 Tauri smoke。开发者已事先声明 CP3 YOLO，exit gate 据此通过。

### CP4 · Library context

Deliverables:

- 保留 scope、query、sort、active item、batch selection 与 scroll。
- 返回 Library 时恢复内存上下文。
- 成功切换 Vault 与应用重启后重置。

Exit gate:

- v0.4 Library 功能矩阵无回归。
- 返回上下文不跳动。
- 无 Router、Pinia 或新的持久化偏好。

CP4 record — 2026-07-29:

- `App` 只用 Vue 原生 `KeepAlive` 缓存 Library；Paper、Flashcard 与 Vault 仍按原生命周期卸载。成功切换 Vault 或 Core restart-ready 会销毁旧缓存并建立默认上下文，Vault 取消不会重置。
- scope、query、sort、active item、batch selection 与 window scroll 六项内存上下文，经 Library → Paper → Library、Library → Flashcard → Library 与 Vault 取消后均恢复；重新激活仍以原查询参数刷新 Python 投影。
- Library 停用后解绑 `Escape` 与 `⌘F`；实际浏览器 smoke 发现 DOM 收缩会在 `onDeactivated` 前把 `scrollY` 压回 `0`，因此改在三个离开动作发出前保存位置，激活后先恢复、刷新后再校准，避免查询等待造成可见跳动或隐藏页面异步误滚动。
- focused Vitest `27`、全量 Vitest `60`、Python `235`、Rust `10`、Vite production build、compileall 与 documentation check 通过；v0.4 Library 功能矩阵未回归。
- [`1220×780`](docs/acceptance/road-v0-5/cp4-library-context-1220x780.png) 与 [`920×680`](docs/acceptance/road-v0-5/cp4-library-context-920x680.png) 合成浏览器往返均恢复相同六项上下文且无横向溢出。临时合成 Tauri 在两个窗口尺寸各完成 Paper → Library 往返，并以可访问 heading 确认 `Ideas` scope 仍在。
- smoke 注入与临时入口已删除，未调用真实 Vault、真实配置或作者内容；无 Router、Pinia、依赖或持久偏好。开发者已事先声明 CP4 YOLO，exit gate 据此通过。

### CP5 · Whole-app visual pass

Deliverables:

- 用同一 token、type scale、focus、spacing 与 action hierarchy 覆盖全部页面。
- 整理 loading、empty、blocked、recovery 与 destructive states。
- 完成 `1220×780` 与 `920×680` 真实渲染检查。
- 尊重 `prefers-reduced-motion` 与可见焦点。

Exit gate:

- 没有横向溢出、被裁文字、不可见焦点或动作层级冲突。
- Vault、迁移与 Core 阻塞页面不再像另一套应用。
- 功能与数据边界未因视觉重构改变。

CP5 record — 2026-07-29:

- 根级视觉 token 统一为低饱和纸面、墨色正文与 ink-blue signal，并集中定义原生 macOS 字体栈、小圆角、焦点和 reduced-motion。Paper、Flashcard、Library、Vault/迁移与 Core loading/blocked/recovery 使用同一视觉语言；development-only Prototype 只同步 token，不进入生产 bundle。
- Paper 与 Flashcard 的长名称、Library 的长文件夹/结果、Vault 的长路径与迁移错误都允许收缩和换行；Library 在紧凑宽度使用两列工具区。普通 destructive action 保持描边，只有最终确认层使用实心 danger，未改变既有动作语义。
- 合成浏览器在 `1220×780` 与 `920×680` 检查 Paper ready/empty/daily、Flashcard ready/error、Library ready/empty/error、Vault picker/migration-ready/migration-blocked、Core starting/blocked 共 `26` 个渲染组合：均无横向溢出。`focus-visible` probe 为 `3px` ink-blue outline，`prefers-reduced-motion: reduce` 将 transition 与 animation 收敛至 `0.00001s`。
- 五类代表证据各保留两个尺寸：[`Paper 1220`](docs/acceptance/road-v0-5/cp5-paper-1220x780.png) / [`920`](docs/acceptance/road-v0-5/cp5-paper-920x680.png)、[`Flashcard 1220`](docs/acceptance/road-v0-5/cp5-flashcard-1220x780.png) / [`920`](docs/acceptance/road-v0-5/cp5-flashcard-920x680.png)、[`Library 1220`](docs/acceptance/road-v0-5/cp5-library-1220x780.png) / [`920`](docs/acceptance/road-v0-5/cp5-library-920x680.png)、[`Vault migration 1220`](docs/acceptance/road-v0-5/cp5-vault-migration-1220x780.png) / [`920`](docs/acceptance/road-v0-5/cp5-vault-migration-920x680.png)、[`Core blocked 1220`](docs/acceptance/road-v0-5/cp5-runtime-blocked-1220x780.png) / [`920`](docs/acceptance/road-v0-5/cp5-runtime-blocked-920x680.png)。Flashcard 两张图分别覆盖 Summary 首页与单个 Highlight。
- 合成 Tauri 窗口在两个尺寸均通过 Paper → Flashcard → Library → Vault 语义导航，并确认 Vault 的安全返回控件；没有打开系统目录选择器。临时 smoke 入口、bridge 注入和所有进程均已删除或退出。
- 全量 Vitest `60`、Python `235`、Rust `10`、Vite production build、compileall、documentation check 与 `git diff --check` 通过。测试未连接或改写真实 Vault、真实配置或作者内容；开发者已事先声明 CP5 YOLO，exit gate 据此通过。CP6 的真实 dogfood 与产品验收仍未开始。

### CP6 · Dogfood and acceptance

Deliverables:

- 构建唯一可识别的真实 keikeu `.app`。
- 使用 copied 或 synthetic Vault，连续使用 30 分钟。
- 记录路径、窗口尺寸、数据来源、实际问题与严重级别。
- 修复全部 P0/P1 与最烦的 3 件事。
- 再跑 30 分钟，并记录修复前后差异。

CP6 record — 2026-07-30:

- 独立 Agent dogfood 已完成两轮 30 分钟记录；未发现 P0/P1，Round 1 最烦的 3 件事已修复并在 Round 2 复验。
- [`CP6 report`](docs/acceptance/road-v0-5/cp6-dogfood/report.md) 记录 candidate hash、隔离数据、页面路径、Core/迁移恢复与自动检查；后续 P2 修复让未落盘 Draft 可直接进入 Vault picker，dirty Draft 仍走同一离开保护。
- 全局 `--rule` 从 `#d9d5ca` 加深为 `#b8b2a6`，覆盖 Paper、Flashcard、Library、Vault/迁移与 Core 状态页；当前源码 Tauri 在 `1220×780` 与 `920×680` 复验通过。
- 开发者已明确通过 CP6；后续 checkpoint 已由 advance YOLO 授权，因此 Road 保持打开，不归档、不打 tag。

Exit gate:

- 我能马上看懂哪里可编辑。
- 我不怕点错导航。
- 保存和放弃符合直觉。
- 鼠标和键盘都顺手。
- 连续用半小时不烦。
- 正常交互不会丢内容。
- 开发者已确认 CP6 产品验收；Road 仅在后续 checkpoint 完成后才可归档或打 tag。

## 7. Test and evidence plan

### Automated checks

```bash
.venv/bin/python -m pytest
.venv/bin/python -m compileall -q src
npm --prefix frontend run test
npm --prefix frontend run build
cargo test --manifest-path frontend/src-tauri/Cargo.toml
.venv/bin/python scripts/check_docs.py
git diff --check
```

UI 变更必须增加或更新 focused Vitest，至少覆盖：

- dirty indicator
- save success and failure
- discard to latest baseline
- continue editing
- guarded navigation
- window close request
- Flashcard Summary-first
- one-Highlight-per-card
- Library context restore and reset

### Platform evidence

当前开发者已永久批准在 keikeu 后续工程 build 与 dogfood 中使用 macOS 27 beta 与 Xcode 27 beta。该批准只覆盖工程工作，不自动构成 release、minimum-system 或跨版本兼容性证据。

每个 UI checkpoint 至少保留：

- `1220×780` screenshot
- `920×680` screenshot
- focused test output
- Tauri `.app` launch smoke when the changed path depends on desktop APIs
- copied 或 synthetic Vault provenance

### Product acceptance

v0.5 通过需要同时满足：

1. 所有 active checkpoint exit gate 全部通过。
2. 无未解决 P0/P1。
3. 最烦的 3 件事已修复并复验。
4. 两轮各 30 分钟 dogfood 有真实记录。
5. 开发者明确确认，不用自动测试代替产品接受。

## 8. Risks and boundaries

| Risk | Control |
| --- | --- |
| 原生确认在 Tauri release 中表现与浏览器不同 | production 用官方 dialog plugin，真实 `.app` smoke，不把 browser demo 当平台证据 |
| baseline 与保存状态漂移 | 只有成功保存更新 baseline，失败与 unknown 不更新 |
| 视觉重构误伤 v0.4 功能 | 每个 checkpoint 只改一条行为链，Library 保持 parity matrix |
| KeepAlive 留下跨 Vault 的旧上下文 | 成功 Vault switch 与 restart 明确 reset |
| 拖动排序伤害键盘可用性 | 编辑、新增、删除保留键盘路径，v0.5 明示不承诺键盘重排 |
| 「不丢内容」被误读成 crash recovery | 验收只承诺正常交互，崩溃与断电另立 Road |
| beta 工具链被误当 release 证据 | 工程批准与分发兼容性结论分开记录 |

## 9. Decisions already locked

- Road 名称为 v0.5。
- v0.5 的中心是 UI 舒心性与交互易用性。
- 可分发 macOS alpha 属于 v0.6。
- 原始草稿只读。
- dirty departure 是原生二选一，不做应用内三选一。
- 不提供「保存并前往」。
- Flashcard Summary-first，每张只显示 1 个 Highlight。
- 全局视觉覆盖全部页面。
- 当前窗口只验收 `1220×780` 与 `920×680`。
- routine 使用 skill + checkpoint evidence，不使用 Git hooks 或 CI gate。
- v0.5 结束条件是 dogfood 后修完真实摩擦，不是继续加功能。

## 10. References

- Final UI prototype: `docs/design/keikeu_opendesign/keikeu-v05-prototype.html`
- Current product scope: `docs/SPEC.md`
- Current phase and authority map: `docs/PROJECT.md`
- Engineering and Git rules: `docs/RULES.md`
- Runtime architecture: `docs/architecture/architecture.html`
- Existing interaction map: `docs/design/interaction.html`
- Existing visual map: `docs/design/design.html`
- Tauri dialog plugin: <https://v2.tauri.app/plugin/dialog/>
