# Road v0.7 实施计划（CP7 Gate D 已通过；checkpoint 收口）

> 状态：开发者于 2026-08-20 批准原 CP0–CP6 计划并给出相应 advance YOLO；CP0 `fb52b55`、CP1 `8019969`、CP2 `55d45fc`、CP3 `55b5313`、CP4 `6f69310`、CP5 `3259c42` 与 CP6 一号作者 Gate 均已通过。CP7 Gate A 于 2026-08-24 通过，Gate B 于 2026-08-25 经开发者明确判断通过，Gate C production candidate 与两轮 Gate D 整改、完整工程复核、隔离 Tauri smoke、同一 Figma Page 增量同步均于 2026-08-25 完成；开发者随后明确通过 Gate D。自动化只证明 composition 期间零查询与最终中文一次提交，未观察到的 macOS 原生候选窗不补写为 CP7 证据，并移至 CP8 人工复核。CP6 checkpoint 是 `e22b691`；`206d03e` 与 `528124d` 是另行授权、已审阅的 preparation/hygiene，不冒充 CP6 证据；CP7 分支 `ui/cp7-v07-continuous-flow` 从该 clean preparation baseline 线性开始。本轮已授权 CP7 本地 checkpoint commit；真实 Vault、push、tag、closeout 与发布仍未授权。
>
> 目标设计：[`docs/design/road-v0-7-app-shell-design.md`](docs/design/road-v0-7-app-shell-design.md)
>
> 伴随评审物：[`docs/design/road-v0-7-planbook.html`](docs/design/road-v0-7-planbook.html)（非规范权威，不构成实现或 Gate 证据）
>
> 当前接受基线：Road v0.6 Paper v4 / Index v4 / protocol v2。

## 0. Road 目标

Road v0.7 将已接受的 Paper、Library 与 Vault 收口为一个稳定桌面工作台：

```text
紧凑 App Shell → Paper / Library 日常工作面 → Vault 环境与阻塞恢复
```

本 Road 是 Vue 结构、交互层级与视觉收口，不是数据、Core、transport、平台或发布 Road。

## 1. 权威与执行纪律

- 当前已接受产品由 [`docs/SPEC.md`](docs/SPEC.md) 定义。
- Road v0.7 App Shell 增量与 CP7 accepted override 由已批准的[设计](docs/design/road-v0-7-app-shell-design.md)定义；CP7 在 Gate D 前只写作 target，现已由开发者明确接受。
- [`docs/RULES.md`](docs/RULES.md) 继续约束作者资产、Git、证据与安全边界。
- [`docs/PROJECT.md`](docs/PROJECT.md)、源码和测试标明每个 Checkpoint 的当前事实。
- 不得把未完成 target 写成已实现；每个 CP 只从前一已通过 checkpoint commit 建分支。
- 每个 CP 单独 commit；CP0–CP6 的 advance YOLO 已用完。CP7 Gate D 与本地 checkpoint commit 已分别获得明确判断和授权；真实 Vault、push、tag、closeout 与发布始终另行授权。

## 2. 全局范围

### 2.1 包含

- `App.vue` 的紧凑 Shell 与现有页面切换整合。
- Paper、Library、Vault 的信息层级与响应式布局。
- 现有状态、确认、focus 与错误反馈的位置校准。
- development-only 灰阶 prototype。
- Vitest、Vite build、两种窗口尺寸检查和最终 Tauri smoke。
- 一号作者对同一核心任务的结构接受。

### 2.2 不包含

- Paper / Index / Vault schema 或文件迁移。
- Python、Rust、JSONL protocol、sidecar 或 Tauri capability 变更。
- 新 endpoint、依赖、Router、store、TypeScript 或 UI kit。
- AI、同步、账号、数据库、自动保存、页重排、deep-link 或内置正文编辑器。
- 移动端、Intel Mac、Windows、签名、公证、DMG、tag、push 或公开发布。

## 3. 通用证据

### 3.1 每个 UI Checkpoint

```bash
npm --prefix frontend run test
npm --prefix frontend run build
.venv/bin/python scripts/check_docs.py
git diff --check
```

- 运行相关的聚焦 Vitest 后再运行完整 Vitest。
- 同时检查 `1220×780` 与 `920×680`。
- 检查可见 focus、语义名称、键盘路径、滚动和控制台错误。
- 不复制旧 pass count；记录本次命令、状态和日期。

### 3.2 Road 基线与最终集成

```bash
.venv/bin/python -m pytest
.venv/bin/python -m compileall -q src
.venv/bin/python scripts/build_sidecar.py
npm --prefix frontend run test
npm --prefix frontend run build
cargo test --manifest-path frontend/src-tauri/Cargo.toml
cargo fmt --manifest-path frontend/src-tauri/Cargo.toml --check
.venv/bin/python scripts/check_docs.py
git diff --check
```

Python/Rust 无改动不代表可以复制历史结果；CP0 与 CP5 各运行一次完整基线。

## 4. Checkpoint 总览

| CP | 分支 | 结果 | 主要 Gate |
| --- | --- | --- | --- |
| CP0 | `docs/cp0-v07-contract` | 批准合同、基线证据、current/target 校准 | 目标与排除明确 |
| CP1 | `ui/cp1-v07-grayscale` | development-only 灰阶结构 | 开发者批准信息架构 |
| CP2 | `ui/cp2-v07-shell` | production Shell 与统一导航 | dirty guard 无回归 |
| CP3 | `ui/cp3-v07-paper` | Paper 内容优先工作面 | 编辑/分页/保存无回归 |
| CP4 | `ui/cp4-v07-library-vault` | Library、Vault 与恢复层级 | 两尺寸路径完整 |
| CP5 | `test/cp5-v07-integration` | 全量检查与 Tauri 合成 smoke | 无未解决 P0/P1 |
| CP6 | `test/cp6-v07-author-gate` | 一号作者真实日常接受 | 产品 Gate 通过 |
| CP7 | `ui/cp7-v07-continuous-flow` | 连续编辑流、默认窗口与 UI 去 slop | Gate A–D 顺序通过 |

## 5. CP0 — 合同与基线

**进入条件（已满足）：** 开发者于 2026-08-20 书面批准 Road v0.7 设计与本计划，并以 advance YOLO 通过 CP0 开发者退出 Gate。

**范围：**

- 将批准的 v0.7 target 写入 SPEC，并在 PROJECT 标明 current/target 与下一 Gate。
- 校准 `design.html`、`interaction.html` 与 architecture map 的 current/target 标签。
- 冻结 Shell、Paper、Library、Vault、窗口与可访问性验收矩阵。
- 运行 §3.2 完整基线，不改 production code。

**退出 Gate：** 文档无双重权威；基线检查真实运行；无未解释失败。

## 6. CP1 — 灰阶结构原型

**范围：**

- 复用现有 development-only `PrototypeView.vue` 与 `?prototype=1`。
- 只用合成内存数据画 Shell、Paper、Library、正常 Vault context 与阻塞恢复。
- 同时渲染 `1220×780` 与 `920×680`。
- 验证 Paper/Library 切换、新 Paper、Vault 入口和阻塞页的点击路径。
- 证明 production bundle 不包含 prototype 文本或样式。

**明确不做：** bridge 调用、真实文件、产品 DTO、视觉精修或 production route 切换。

**退出 Gate：** 开发者明确批准导航层级、两种尺寸与 Paper 内容优先方向。

**结果（已通过）：** 合成 Shell、Paper、Library、新 Paper、正常 Vault context 与阻塞恢复点击路径均已实现；两种目标尺寸、键盘 focus、完整 Vitest、fresh production build 与 prototype bundle 隔离通过。开发者 advance YOLO 覆盖退出判断；证据见 [`CP1 report`](docs/acceptance/road-v0-7/cp1-grayscale/report.md)。

## 7. CP2 — Production App Shell

**范围：**

- 在 `App.vue` 内加入紧凑顶栏，不先抽新组件。
- Paper / Library / 新 Paper / Vault 入口复用现有 destination 与事件。
- PaperView 暴露一个复用现有逻辑的 `confirmDeparture()`；App Shell 不重写确认规则。
- PaperView 在打开或保存后回报已保存 path，保证 Vault 往返仍回到同一 Paper。
- 新 Paper 只在 guard 通过后清空 path 并替换 PaperView 实例。
- 当前位置使用语义与文字表达，不只靠颜色。
- 更新 `App.test.js` 与直接 PaperView 测试，覆盖取消、确认、当前 path、新 Paper、
  当前位置和 runtime blocked。

**明确不做：** Router、store、新 bridge 方法、持久 last-location 或侧 rail。

**退出 Gate：** 导航稳定；取消不改变 destination；确认只执行一次原有 intent。

**结果（已通过）：** production 紧凑 Shell、语义当前位置、单一 dirty guard、已保存 path 的 Vault 往返、新 Paper 实例替换、durable pending-intent 锁与 runtime blocker 接管均有直接测试和合成浏览器证据；两种目标尺寸无横向溢出，完整 Vitest、fresh build 与 prototype bundle 隔离通过。开发者 advance YOLO 覆盖退出判断；证据见 [`CP2 report`](docs/acceptance/road-v0-7/cp2-shell/report.md)。

## 8. CP3 — Paper 工作面

**范围：**

- 移除重复 hero 与页面级导航，保留 Paper context 和卡页中心。
- Paper 名、Tags、页码、页标题、类型、正文与三个底部动作保持原语义。
- code/path/time 使用原生详情披露。
- clean、dirty、saving、validation 与 degraded 状态靠近影响对象。
- 更新 Paper 聚焦测试与两尺寸视觉证据。

**明确不做：** schema、保存 DTO、逐页 mutation、自动保存、页重排或 deep-link。

**退出 Gate：** 创建、编辑、分页、删除、保存、离开保护和错误恢复无行为回归。

**结果（已通过）：** 重复 hero、页面级导航与常驻 runtime/path 状态已退出；Paper 名、Tags、页数、dirty/saving/degraded 状态形成 Paper context，code/path/time 与整份删除进入原生详情，单页不显示冗余页码。保存 pending 时作者字段保持焦点但进入只读，分页、删除、类型与全局入口均锁定，避免保存返回后覆盖新输入。直接测试、两尺寸生产浏览器、中文 composition、`Cmd+S`、校验、Index degraded 与 dirty confirm 路径均通过。开发者 advance YOLO 覆盖退出判断；证据见 [`CP3 report`](docs/acceptance/road-v0-7/cp3-paper/report.md)。

## 9. CP4 — Library、Vault 与恢复

**范围：**

- Library 宽窗口保留三段结构；`920×680` 改为纵向详情。
- 保留搜索、打开、移动、分支、Trash、恢复与系统 handoff。
- 正常 Vault 降级为环境上下文，完整 VaultView 仍处理选择与维护。
- migration、repair、commit unknown 与 sidecar blocked 继续接管工作面。
- 危险操作继续复用原生确认边界。

**明确不做：** drawer 依赖、Library 正文编辑、同步状态、自动修复或 mutation replay。

**退出 Gate：** 两尺寸下日常与阻塞路径完整；Finder/Trash/恢复没有语义退化。

**结果（已通过）：** Library 重复页头与页面级导航退出，`1220×780` 保留范围—列表—详情三段，`920×680` 将详情与操作纵排在列表之后；正常 Vault 先显示零请求的本地环境 context，显式进入后才展开已有 picker。migration、`commit_unknown`、protocol mismatch、Trash/恢复、永久删除取消、Finder/default-editor handoff、pending mutation 全工作面锁、focus 与两尺寸 overflow 均有直接测试及 production-browser 证据。开发者 advance YOLO 覆盖退出判断；证据见 [`CP4 report`](docs/acceptance/road-v0-7/cp4-library-vault/report.md)。

## 10. CP5 — 集成与安全 Gate

**范围：**

- 运行 §3.2 完整检查。
- 用 synthetic Vault 或完整副本运行当前源码 Tauri smoke。
- 覆盖启动、创建、分页、保存、Library 找回、Vault 进入/返回与正常退出。
- 覆盖 dirty departure、Index degraded、repair 与 commit unknown 的合成路径。
- 检查 production bundle、控制台、子进程退出与残留进程。

**真实数据边界：** 不选择、不迁移、不损坏唯一真实 Vault；不改持久配置。

**退出 Gate：** 无未解决 P0/P1；自动检查、平台 smoke 和未执行项分别记录。

**结果（已通过）：** Python `265`、Vitest `77`、Rust `12`、compileall、sidecar build、Vite build、Rust format、文档与 bundle 隔离均通过。隔离 fake Home 的当前源码 Tauri smoke 实际完成启动、两页保存、Library 找回、Vault 往返、原生 dirty 两分支、`920×680`、Index degraded/rebuild、repair/recheck、fault-injected `commit_unknown` 重启与 no-replay；正常 sidecar 按 SHA 恢复并复启，host/child/Vite 均无残留。无未解决 P0/P1、无 scope drift；证据见 [`CP5 report`](docs/acceptance/road-v0-7/cp5-integration/report.md)。

## 11. CP6 — 一号作者 Gate（已通过）

**进入条件（已满足）：** CP5 checkpoint 工程 Gate 已通过；开发者在 CP6 前另行授予了
本次真实 Vault 有界授权，该授权不延续至后续操作。

**场景：**

1. 启动后判断当前工作位置并进入已有或新 Paper。
2. 创建、命名、分页、标记并保存一份真实 Paper。
3. 带未保存草稿分别测试一次取消离开与确认离开。
4. 在 Library 找回整份 Paper，完成一次整理或系统 handoff。
5. 查看当前 Vault 环境入口，但不进行非必要迁移或破坏实验。
6. 在 `1220×780` 与 `920×680` 判断舒适度、清楚度与操作直觉。

**记录：** 只记录完成情况、介入次数、P0–P3 与去标识化判断，不记录正文、名称、
Tags、路径或内容截图。

**退出 Gate：** 核心任务完成；作者能解释 Paper/Library/Vault 层级；无未解决 P0/P1。

**结果（已通过）：** 开发者于 2026-08-21 明确声明“CP6 通过”，整体确认六个场景、
两种目标尺寸与层级理解满足退出 Gate，且无未解决 P0/P1。功能介入次数、分视口叙述与
P2/P3 未单独报告，不虚构为 0。Gate 后去标识化检查确认所选 Home 内 Vault 仍为 v4、
migration stage `ready`、Index `current`，候选应用与 Vite 正常退出且无残留；未记录正文、
名称、Tags、路径、截图或原始日志。证据见 [`CP6 report`](docs/acceptance/road-v0-7/cp6-author/report.md)。

## 12. CP7 — 连续编辑流与默认窗口（Gate D 已通过）

**进入条件（已满足）：** CP6 产品 Gate 已通过；开发者已选择“连续编辑流”，通过
“冷编辑台 + Opus 标题 + 系统工具控件”，并于 2026-08-24 明确批准按推荐顺序开始。

**固定目标：**

- Paper context、页导航、当前页与底部动作形成连续纵向编辑流；不增加 sidebar 或移动端专属导航。
- 默认桌面窗口为 `720×900`，最小几何为 `720×680`，满足默认 `width / height <= 1` 且仍可调整为横版。`375×812` 只作浏览器响应式证据。
- Tags 使用单行 comma-separated UI。Vue 使用可逆 CSV-style 引号适配，底层继续传递原有 `string[]`，不改变 Paper v4 Markdown；macOS Tags 字段关闭自动更正与智能引号转换，原生实证确认 ASCII 直引号未被改成弯引号。
- Paper 详情与 Library Paper 预览均使用不占文档流的原生 Popover；Library 每个结果的预览与触发器相邻，不把详情块插到列表下方，不下压 Paper 或文件夹操作。
- Library 搜索在中文输入法 composition 期间不请求服务；提交后只发送一次最终中文检索词。
- 文件夹软删除与恢复原子移动完整目录树，不再要求作者清理 `.DS_Store`、嵌套目录或其他未知项；废纸篓中的永久删除经不可撤销确认后才使用 no-follow 递归销毁。
- 删除常驻 dirty 文案，但保留离开、换稿、Vault 与关闭窗口的唯一 guard。
- Opus serif 只用于 Paper 名与页标题；正文和系统控件使用 sans。文本输入 focus 保持安静，按钮与导航仍有清楚键盘 outline。Figma meta `#627078` 在 production 中因 WCAG 对比度校正为 `#5c6a71`。

**明确不做：** 不改变 Paper v4、Index v4、protocol v2、DTO、Rust command、sidecar、
恢复状态或 Library 的范围/列表/操作能力；不直接 `split(",")`；不增加依赖、Router、
store、UI kit、自制弹窗框架、移动端构建、真实 Vault 操作、签名、tag、push 或 release。
唯一 Core 例外是 `soft_delete_folder`、`restore_folder`、`permanently_delete_folder` 的完整目录树生命周期；
`merge_folders` 与重命名仍保持严格 Paper 预检。Tauri 仅修改默认窗口几何；capability 与持久配置不变。

### Gate A — 合同（已通过：2026-08-24）

- 校准 SPEC、PROJECT、本文、详细设计、active maps、README 与伴随 Planbook 的 current/target。
- 冻结 Tags 可逆规则、`720×900` 默认窗口、四尺寸证据与不做清单。
- 退出条件：权威无冲突；文档检查与 `git diff --check` 通过；不声称 Figma 或 production 完成。

**结果：** current/target、Tags 可逆规则、默认窗口、四尺寸证据与不做清单已冻结；该 Gate 只批准合同，不冒充后续视觉或工程证据。

### Gate B — Figma 交付（已通过：2026-08-25）

- 在现有 keikeu UI 文件新建 `CP7 · 连续编辑流` Page。
- 建立母版、状态/响应式 frame、共享 token/控件、`UI/UX 入门` 与 `行业模板` Sections；教学区不进入 production bundle。
- 对照 HTML master 检查 `375×812`、`720×900`、`920×680`、`1220×780`，完成节点审计与开发者最终视觉批准。
- Gate B 通过前，不把临时风格令牌写入 production。

**结果：** `CP7 · 连续编辑流` Page、母版、四尺寸/关键状态、tokens/系统控件及两个非 production 教学区已交付并完成节点审计；开发者明确声明“Gate B 通过”。Gate D 后续增量已经同步到同一 Page 的 `06 · Gate D Library 后续整改` Section（`152:138`），覆盖 IME 提交、top-layer 预览、范围旁文件夹操作、长名称收缩与 ADR-0008；截图复核与节点边界审计均通过。这不撤销或重写原 Gate B 历史判断。

### Gate C — Production 与工程证据（原始证据及后续整改复核均完成）

- 原始 Gate C 只改 Vue/CSS、直接测试与 Tauri 窗口几何；Tags 适配在 Vue 层完成。本轮经开发者明确授权增加三项窄整改：Library IME dispatch、Library top-layer preview 与 `vault.py` 完整文件夹生命周期。
- Tags 覆盖普通值、字面逗号、双引号、空项、外侧空白、重复项、`U+FEFF` 与未闭合引号阻塞；Vue 不得用比 Core 更宽的 `.trim()` 静默改变合法 Tag，也不得因无关保存拆分既有值。
- 四尺寸检查正文、保存、危险动作、恢复路径、滚动与 `scrollWidth <= clientWidth`；覆盖中文 composition、`Cmd+S`、saving lock、错误与安全状态。
- 运行聚焦/完整 Vitest、Vite build、完整 Python/Rust 基线、文档 Gate，并用隔离 synthetic Vault 完成 Tauri smoke。

**结果：** production candidate 已实现连续流、可逆 CSV-style Tags、Popover、quiet focus 与 `720×900` 默认窗口（最小 `720×680`）。真实 Chromium 已在 `375×812`、`720×900`、`920×680`、`1220×780` 检查无横向溢出，并验证 Popover 的 Escape、light-dismiss 与焦点返回；macOS 原生输入确认 Tags 中的 ASCII 直引号未被转换为弯引号。隔离假 Home 的 Tauri 在 `720×900` 启动，初始化 synthetic Vault，保存 Markdown/Index 并验证详情 Popover。首次冷 sidecar 启动发生一次超时；随后重启与完整 smoke 通过，记录为已知环境现象而非功能阻塞。Vitest `9` 个文件 / `88` 个测试、pytest `269`、Rust `12`、Python compileall、Cargo fmt、sidecar build、Vite build、文档 Gate 与 `git diff --check` 均通过；production bundle 未发现 prototype marker。不复制历史数字。

**后续整改复核（2026-08-25）：** 真实浏览器用最大合法的 `200` 字符文件夹名与 `12` 份 Paper 重跑 `375×812`、`720×900`、`920×680`、`1220×780`；四档 document、Shell、结果、范围与操作控件均无横向溢出。真实 DOM composition 序列在 `b` / `ba` 阶段零查询，提交“暴食”后仅新增一次查询；原生候选窗本身未由桌面自动化可靠触发，因此不冒充人工候选窗证据。每行 native Popover 的 top layer、唯一 ID、Enter/Escape、焦点返回和开合前后几何均通过。最终 debug bundle 在隔离假 Home 的 `720×900` Tauri 中通过长名称、预览与中文最终值；去标识的 `fixture——folder` 连同 `.DS_Store`、嵌套文件和 symlink 完整移入废纸篓并整树恢复，Vault 外链接目标未改变。pytest `283`、Vitest `9` 个文件 / `99` 个测试、Rust `12`、Python compileall、Cargo fmt、sidecar build、Vite build、debug app bundle、文档 Gate、bundle marker scan 与 `git diff --check` 均通过；未触碰真实 Vault。

桌面工具曾因同名应用解析误启动旧 release `.app`；约六分钟内没有点击或输入，也没有执行 mutation，但该实例可能读取过默认启动配置，因此不计入任何 smoke。误启实例已终止，后续只按 debug bundle 绝对路径运行。

### Gate D — 开发者 UI 接受（已通过：2026-08-25）

- 开发者判断连续编辑流、默认窗口、横版重排、Popover、quiet focus 与状态层级。
- 无未解决 P0/P1 后才记录 CP7 通过并创建 checkpoint commit；P2/P3 不虚构为 0。
- snapshot、tag、push、签名、打包、发布和真实 Vault 始终是 Gate D 之外的独立决定。

**首轮结果（未通过：2026-08-25）：** 开发者报告六项阻塞：窄屏偶数文件夹与创建模块互相拉伸、一个已去标识文件夹删除失败且原因不可见、纵向文件夹范围压低 Paper、Tags 标签与占位文字错位、详情关闭按钮与重复分隔线不合格，以及 Vault / Library / Paper 未处于同一顶栏高度。

**首批整改快照（已被后续退回覆盖）：** 窄屏范围改为原生紧凑下拉，偶数/奇数文件夹下范围区高度一致，Paper 保持首屏；folder mutation 的失败报告在刷新后保留，失败不再跳走，完整成功后才切回“全部”。Tags 改为 baseline 对齐；详情关闭按钮移除自动焦点并使用灰色边框，首项重复分隔线退出；窄屏 Shell 保持单行 `56px` 顶栏。该快照曾保留“未知项阻断”与 inline Library 预览，因此不再代表当前候选。

**后续整改与最终判断：** 普通文件夹删除现在把完整目录树原子移入废纸篓，恢复整树回移；只有废纸篓中的不可撤销二次确认才执行 identity-pinned、fd-relative、symlink-safe 递归销毁。Library 搜索在 composition 期间不刷新，提交词同值去重；每个 Paper 结果使用与触发器相邻的原生 top-layer Popover，不再占据列表下方版面。文件夹操作紧贴范围控件，所有原生控件与 `200` 字符名称在四档均受容器约束。协议/DTO/Paper/Index 不变，决策见 [ADR-0008](docs/architecture/decisions/0008-whole-folder-trash-lifecycle.md)。源码、全量工程、真实浏览器四档、隔离 Tauri 与 Figma 增量证据已经完成，独立终审为 `0 P0 / 0 P1`；开发者于 2026-08-25 明确通过 Gate D。原生 macOS 候选窗未由自动化触发，不冒充 CP7 证据，转为 CP8 的独立人工复核项。

## 13. 已知风险

| 风险 | 控制 |
| --- | --- |
| UI Road 变成新功能 Road | 每个 CP 重复明确不做清单 |
| App Shell 绕过离开保护 | CP2 统一 App-root intent，并直接测试取消/确认 |
| Paper 层级变化影响输入焦点 | CP3 覆盖焦点、快捷键与中文输入 smoke |
| Library 小窗口丢失危险动作 | CP4 `920×680` 逐路径检查，不依赖 hover |
| Vault 降级掩盖安全 Gate | 正常 context 与 blocking surface 明确分开 |
| 原型进入生产 bundle | CP1、CP5 两次 bundle 检查 |
| 并行文档产生双重权威 | CP0 在批准后一次校准 SPEC/PROJECT/maps |
| comma-separated UI 拆坏含逗号 Tag | Vue 层使用可逆 CSV-style 适配并覆盖无损 round-trip |
| 临时风格直接进入 production | Gate B 最终视觉批准先于 Gate C |
| 默认竖向窗口退化横版 | 同源布局同时验证四尺寸，不建立第二套产品逻辑 |
| 中文输入法组合态触发中间查询 | CP7 composition 期间不 dispatch、最终值同值去重；原生候选窗按 CP8 P1 Gate 使用实体键盘人工复核 |
| Library 预览下压操作区或键盘顺序过长 | 每个结果旁使用 native top-layer Popover，覆盖 Tab、Escape 与 light-dismiss |
| 完整文件夹永久删除越界或失败语义不清 | 软删除/恢复整树原子移动；永久删除二次确认、同父隔离、fd-relative no-follow、设备与 identity 竞态回归；递归失败保留剩余树并明确报告，已销毁 entry 不虚构为可回滚 |

## 14. 实施计划批准 Gate（已通过：2026-08-20）

开发者已确认：

- [x] Road 名称与范围为“App Shell 与信息层级收口”。
- [x] CP0–CP6 顺序和分支边界可执行。
- [x] CP1 灰阶 Gate 先于 production UI 修改。
- [x] 不新增依赖，不修改后端或持久数据合同。
- [x] CP5 使用 synthetic Vault / 完整副本，CP6 的真实 Vault 另行授权。
- [x] CP0–CP6 开发者退出判断与本地 checkpoint commit 采用 advance YOLO；证据仍须实际运行且不得复制或虚构。

本次批准与 advance YOLO 已用于通过 CP0–CP6；历史测试仍不得复制为当前证据。CP6 的窄范围真实 Vault 授权已经使用完毕，不延伸到未来真实 Vault 操作或 Git 远端动作。

## 15. CP7 启动批准 Gate（已通过：2026-08-24）

开发者明确回复“照你说的办，开始”，批准了先清理 preparation、再建立 CP7 权威、进入
Figma、确定 Tags 合同并在最终视觉批准后实施 production 的顺序。该批准允许创建当前
分支并推进工作，不替代 checkpoint commit 授权、Gate B 最终视觉判断或 Gate D 产品接受，也不授权真实 Vault、
push、tag、closeout、签名、打包或发布。
