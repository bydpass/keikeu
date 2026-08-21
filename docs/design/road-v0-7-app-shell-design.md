# Road v0.7：App Shell 与信息层级设计（CP6 已接受；Road 续段待规划）

> 状态：开发者于 2026-08-20 批准本设计与实施计划；CP0 `fb52b55`、CP1 `8019969`、CP2 `55d45fc`、CP3 `55b5313`、CP4 `6f69310`、CP5 `3259c42` 与 CP6 一号作者 Gate 均已通过。App Shell 增量已经产品接受且无未解决 P0/P1。开发者于 2026-08-21 决定 Road v0.7 保持开放，延顺步骤留到新的规划任务；本设计不预设其编号或范围。未来真实 Vault 操作、push、tag、closeout 与发布未由 CP6 自动授权。
>
> 基线：Road v0.6 已完成并验收的 Paper v4 / Index v4 / protocol v2。
>
> 权威边界：[`SPEC`](../SPEC.md) 定义 CP6 已接受的 Road v0.7 产品边界；本文是 App Shell 增量的详细设计与唯一验收矩阵。`PROJECT`、源码与测试继续标明当前实现；CP6 产品接受不等于尚未规划的 Road 续段或 closeout 已完成。
>
> 伴随评审物：[`Road v0.7 HTML 计划书`](road-v0-7-planbook.html)；它只展示本设计与实施计划，不新增第三份规范权威。

## 1. 核心判断

Road v0.7 不需要新的创作对象、数据 schema 或平台能力。当前最值得解决的问题是：
已接受的 Paper、Library 与 Vault 功能存在，但界面没有稳定表达它们的主次关系。

本 Road 只做一件事：

```text
把三个各自成页的功能，收口成一个以作者内容为中心的桌面工作台。
```

目标运行链保持不变：

```text
Vue → Tauri/Rust → JSONL protocol v2 → Python service/core
    → Paper v4 Markdown / Index v4 / Vault
```

## 2. Road 目标

1. 用一个紧凑、稳定的 App Shell 表达 Paper、Library 与当前 Vault 的关系。
2. 让 Paper 正文、页标题和 Library 内容成为首屏视觉中心。
3. 删除生产界面中重复的大标题、重复导航和常驻成功状态。
4. 保留 Road v0.6 的全部保存、离开保护、repair 与 unknown-result 安全合同。
5. 在 `1220×780` 与 `920×680` 同时保持可读、可操作、无横向溢出。
6. 用一号作者的真实日常路径判断结构是否更清楚，而不是用截图替代产品接受。

## 3. 明确不做

- 不修改 Paper v4 Markdown、Index v4、Vault 布局或 protocol v2。
- 不修改 Python Core、application service、Rust command 或 sidecar 生命周期。
- 不增加数据库、账号、同步、遥测、文件 watcher、插件系统或远程服务。
- 不增加 AI 生成、内置正文编辑器、自动保存、页重排、deep-link 或恢复 journal。
- 不恢复传统 Outline、Flashcard 或配方票产品链。
- 不增加 Router、Pinia、TypeScript、UI kit 或新 runtime dependency。
- 不进入移动端、Intel Mac、Windows、签名、公证、DMG 或公开发布。
- 不把视觉探索 [`boh_design.html`](boh_design.html) 直接变成生产规范。

## 4. 批准时事实与问题

### 4.1 批准时事实

- Paper 与 Library 是日常工作位置。
- Vault 负责环境选择、迁移、repair 与恢复，不是内容目的地。
- `App.vue` 已拥有 destination、当前 Paper、Vault 返回点与 pending intent。
- 子页面通过现有事件切换，不需要 Router。
- Road v0.6 已证明创建、分页、保存、退出重启和 Library 找回可以完成。

### 4.2 批准时问题

1. Paper、Library、Vault 都自行建立页面标题和导航，稳定位置不足。
2. 页面 chrome 在小窗口占据过多高度，作者内容被向下推。
3. code、路径和运行状态容易与作者内容争夺视觉中心。
4. 正常环境与阻塞恢复没有形成清楚的层级。
5. 现有设计 map 描述的是已接受 v0.6，不应被直接当成 v0.7 实施稿。

## 5. 信息架构

Road v0.7 采用“两个日常位置、一个环境入口、一条阻塞通道”：

```text
keikeu
├── Paper
│   └── 创建、编辑、分页、保存
├── Library
│   └── 搜索、找回、整理、打开与系统 handoff
├── Vault context
│   └── 查看或更改当前本地环境
└── Blocking recovery
    └── startup、migration、repair、commit_unknown
```

- Paper 与 Library 是唯一同级的日常导航。
- Vault 作为环境上下文出现；只有需要处理环境时才进入完整工作面。
- 阻塞恢复可以替换工作面，但不能隐藏产品身份、风险说明或安全动作。

## 6. App Shell 合同

### 6.1 结构

```text
┌──────────────────────────────────────────────────────────┐
│ keikeu   Paper   Library        新 Paper   当前 Vault   │
├──────────────────────────────────────────────────────────┤
│                    当前工作面                            │
└──────────────────────────────────────────────────────────┘
```

- `keikeu` 是产品身份，不是营销 hero。
- `Paper` 与 `Library` 使用文本入口并显示当前位置。
- `新 Paper` 只切换到现有空白 Paper 路径，不新增写入 endpoint。
- Shell 从 Paper 离开前调用 PaperView 暴露的单一 `confirmDeparture()`；该方法复用现有
  departure guard，不在 App root 重写一套确认逻辑。取消时 destination 不变。
- `当前 Vault` 打开现有 Vault 工作面；默认不常驻完整绝对路径。
- Shell 在正常 ready 状态稳定存在；runtime 启动失败仍由阻塞页接管。

### 6.2 不采用永久侧 rail

当前只有两个高频、稳定、同级位置。永久 rail 会消耗窄窗口宽度，并诱导把 Vault、
设置或未来功能抬成伪同级入口。出现第三个真实高频位置前不重新评估。

### 6.3 状态归属

- dirty、saving、validation error 放在当前 Paper 附近。
- Index degraded 放在保存结果或 Library 状态附近，并持续到处理完成。
- Vault、repair 与 commit unknown 状态放在环境或阻塞工作面。
- clean/success 不占用永久徽章。

## 7. Paper 工作面

层级固定为：

```text
Shell
└── Paper context：Paper 名 / Tags / 页码 / 必要状态
    └── 当前卡页：页标题 / 可选类型 / Markdown 正文
        └── 保存 / 删除 / 加一页
```

- Paper 名、页标题、Tags、类型与正文的持久行为完全沿用 v0.6。
- 卡页占据首屏主要面积；页面 hero 从生产工作面退出。
- `code`、完整路径、created/updated 进入原生详情披露，不新增 modal 系统。
- Tags 保留在 Paper context；页类型保留在当前卡页。
- 单页时不制造无意义页码密度；多页时保持清楚的当前页状态。
- 保存、删除、加一页仍是卡页底部三个主动作，顺序和语义不变。
- `Cmd+S` 与保存按钮继续走同一 whole-Paper save。

## 8. Library 工作面

宽窗口保留已经工作的“范围—列表—详情/操作”结构：

```text
┌────范围────┬────────Paper 列表────────┬────详情 / 操作────┐
│ 全部       │ 搜索、预览、页数、Tags   │ 打开、移动、分支   │
│ 文件夹     │ 错误隔离                 │ Finder、Trash      │
│ Trash      │                          │ 恢复、永久删除      │
└────────────┴──────────────────────────┴───────────────────┘
```

- `1220×780` 使用三段布局。
- `920×680` 保留范围和列表，选中详情纵向排列在列表之后。
- 不引入 drawer、第三方组件或新的全局状态。
- Library 不编辑 Paper 正文，不管理文件提供器同步，也不复制完整搜索正文到 Vue。
- 危险操作继续使用现有原生确认边界。

## 9. Vault 与阻塞恢复

### 9.1 正常状态

- Shell 只显示可识别的 Vault 名称或通用“Vault”标签。
- 完整路径只在核对、Finder 定位或安全说明时展开。
- 更改 Vault 仍进入现有 VaultView，不改 selected-Vault 持久规则。

### 9.2 阻塞状态

以下状态可以接管完整工作面：

- 尚未选择或候选 Vault 无效；
- schema migration required；
- `repair_required`；
- `commit_unknown` 对账；
- 无法确认当前 Vault identity；
- sidecar 无法安全启动。

阻塞页必须说明：发生了什么、哪些内容没有被自动修改、当前允许的安全动作、如何返回。
不得展示半解析正文，不得自动重发 mutation。

## 10. 状态与数据流

```text
App.vue
├── status / destination / paperPath
├── Paper render generation
├── Vault return destination
├── pending durable intent
├── Shell navigation intent
└── existing child events
    ├── PaperView
    ├── LibraryView
    └── VaultView
```

- `App.vue` 继续拥有跨页面状态；Road v0.7 不引入 Router 或 store。
- Shell 先直接留在 `App.vue`；只有出现第二个真实复用点时才抽组件。
- PaperView 只新增一个窄的 `confirmDeparture()` 暴露面，并在打开或保存后把当前已保存
  path 回报给 App；dirty、baseline、close guard 与确认文案仍由 PaperView 拥有。
- `新 Paper` 只有在 departure guard 通过后才清空 `paperPath` 并递增 Paper render
  generation，确保当前 PaperView 被替换而不是在同一实例里静默换稿。
- Paper/Library 切换和 Vault 入口只组合已有状态、事件与上述窄接口。
- 子页面现有 DTO、request 与 mutation ownership 不变。
- production bundle 仍不得包含 development-only prototype。

## 11. 视觉合同

- 继续使用现有 parchment、paper、ink blue、near-black、danger 与 success token。
- 系统 sans 用于导航、控件、状态和标签；serif 用于 Paper 名、页标题与作者正文候选；
  monospace 只用于 code、路径、schema 与诊断值。
- 不用营销落地页尺寸、渐变、玻璃、硬阴影、装饰性 pill 或永久成功状态。
- 危险色只表示 destructive 或 blocking 状态。
- 阴影只在真实层级需要时使用；优先使用边框、间距和背景层次。

## 12. 可访问性与窗口合同

- 全部导航和操作有语义名称、可见 focus 与键盘路径。
- 当前导航位置不能只靠颜色表达。
- 状态不能只靠颜色或动画表达；遵守 reduced-motion。
- `1220×780` 与 `920×680` 必须同时检查内容、滚动、焦点和确认路径。
- 小窗口可纵向重排次要详情，但不能裁掉正文、保存动作或恢复路径。
- 页面切换后焦点进入可预测位置；确认取消后回到发起动作。

## 13. 已决定的开放问题

| 问题 | Road v0.7 决定 |
| --- | --- |
| Shell 形状 | 紧凑顶栏，不采用永久 rail |
| Paper 信息常驻 | Paper 名、Tags、页码常驻；code/path/time 进入详情 |
| Library `920×680` | 纵向重排，不引入 drawer |
| 一次/日启动卡 | 保留现有行为，不在 UI Road 改设备状态 |
| 上次位置恢复 | 不增加持久状态，沿用当前启动逻辑 |
| 新依赖 | 不增加 |
| 后端合同 | 不改变 |

## 14. 接受场景

### 14.1 Road v0.7 验收矩阵

| 区域 | 必须成立 | 明确不得发生 | 最低证据 |
| --- | --- | --- | --- |
| App Shell | 使用紧凑顶栏；Paper 与 Library 是唯一同级日常位置；新 Paper 与 Vault 分别是动作和环境入口；当前位置同时由文字和语义表达。离开 dirty Paper 前调用 PaperView 的同一 guard：取消后 destination、draft、path 与焦点不变；确认后只执行一次原 intent；已保存 path 在 Vault 往返后保留。runtime blocked 可接管工作面。 | 永久侧 rail、Router、store、第二套 dirty 规则、常驻成功徽章或新 bridge endpoint。 | CP1 合成原型点击路径与两尺寸审阅；CP2 聚焦 App/PaperView Vitest；CP5 runtime blocked 与 dirty departure 合成 smoke。 |
| Paper | 层级固定为 Shell → Paper context（名称、Tags、页码、必要状态）→ 当前卡页（标题、类型、正文）→ 保存/删除/加一页。重复 hero 和页面级导航退出；code/path/time 进入原生详情披露。创建、编辑、分页、删除、whole-Paper 保存、`Cmd+S`、错误恢复和离开保护保持 v0.6 行为。 | schema、DTO、逐页 mutation、自动保存、页重排、deep-link 或静默换稿。 | CP3 直接行为测试；`1220×780`、`920×680` 浏览器证据；键盘、焦点、中文 IME 与错误状态 smoke。 |
| Library | `1220×780` 保留“范围—列表—详情/操作”三段；`920×680` 保留范围与列表，详情纵向排列在列表之后。搜索、打开、移动、分支、Finder、Trash、恢复和永久删除保持现有语义与确认边界。 | drawer 依赖、正文编辑、同步状态、自动修复、完整正文复制到 Vue 或危险动作只靠 hover。 | CP4 聚焦 Library 测试；两尺寸逐路径浏览器检查；Trash、恢复与系统 handoff 使用 synthetic Vault 或完整副本验证。 |
| Vault 与阻塞恢复 | 正常 Shell 只显示可识别的 Vault 名称或通用标签，完整路径按需披露；选择与持久化规则不变。未选择/无效候选、migration、`repair_required`、`commit_unknown`、identity unknown 与 sidecar failure 可接管工作面，并说明发生了什么、未自动修改什么、允许的安全动作和返回路径。 | 把 Vault 提升为第三个日常位置、展示半解析作者正文、自动 repair、自动重发 mutation 或改变 selected-Vault 规则。 | CP4 Vault/恢复聚焦测试与两尺寸路径；CP5 synthetic Vault/完整副本 smoke；CP6 仅按窄授权使用既有真实 v4 Vault。未来任何真实 Vault 操作仍须按 RULES 另行明确授权，并同时受新任务范围限制。 |
| 窗口 | Paper、Library、正常 Vault 与阻塞恢复均在 `1220×780`、`920×680` 检查。两尺寸无横向溢出；主要内容、保存动作、危险操作与恢复路径可见或可通过明确纵向滚动到达；小窗口只重排次要详情。 | 裁掉正文/保存/恢复动作、隐藏确认路径、仅凭截图推断可操作性或把窄窗口问题留到 CP5。 | CP1–CP4 每个相关 Checkpoint 的实际浏览器尺寸检查、overflow/scroll/console 记录；CP5 当前源码 Tauri smoke。 |
| 可访问性 | 导航、表单和操作有语义名称与键盘路径；当前位置和状态不只靠颜色或动画；focus 可见。页面切换后焦点进入可预测标题或首要控件；确认取消后回到发起动作；危险动作说明后果；遵守 reduced-motion。 | 仅 hover 可达、仅颜色表达、焦点丢失、动画承载必要信息或自制不可访问确认系统。 | 聚焦 Vitest 覆盖名称、状态和确认分支；两尺寸键盘 walkthrough；CP3 中文输入 smoke；CP5 原生确认与 focus 恢复 smoke。 |

CP1 只批准信息架构方向；CP2–CP4 分别证明 production 实现；CP5 证明集成与平台路径；
CP6 已证明一号作者接受。任一较早证据仍不得替代较晚 Gate。

### 14.2 原 CP0–CP6 接受场景（已通过）

App Shell 增量只在以下场景通过时接受；CP6 已给出整体通过判断：

1. 作者从启动进入 Paper，能够立即识别当前工作位置和主要内容。
2. 有未保存草稿时切换 Library、新 Paper 或 Vault，取消与确认两路都正确。
3. 作者创建、分页、保存 Paper，并从 Library 找回继续编辑。
4. Library 在两种目标窗口尺寸下完成搜索、打开、整理与 Trash 路径。
5. Vault 正常状态保持安静；阻塞与恢复状态仍完整、准确、可操作。
6. 键盘、focus、确认、错误和 reduced-motion 不因结构重排退化。
7. 没有 Paper、Index、Vault、protocol、Python 或 Rust 行为变化。

自动检查、合成 Vault smoke、平台 smoke 与一号作者接受仍是不同证据。

这些场景证明原 CP0–CP6 增量已接受，不证明开发者后来提出的 Road 续段已经规划或完成。

## 15. 风险与控制

| 风险 | 控制 |
| --- | --- |
| 视觉重构偷带产品功能 | 每个 Checkpoint 对照本设计的明确不做清单 |
| Shell 绕过 dirty guard | 所有全局入口复用同一 App-root departure intent |
| 小窗口隐藏关键动作 | `920×680` 每个 Checkpoint 都检查，不留到收尾 |
| Vault 被降级后隐藏安全信息 | 只降级正常上下文；阻塞状态仍接管工作面 |
| CSS 全局改动造成回归 | 先复用 token，按工作面分段提交，不整文件重写 |
| 原型污染生产 bundle | 沿用现有 `?prototype=1` development-only 边界与 bundle 检查 |
| 并行文档把 current/target 混写 | SPEC 只写目标摘要；本文的验收矩阵拥有详细判据；PROJECT、源码与测试继续标明 current |

## 16. 书面审阅 Gate（已通过：2026-08-20）

开发者已逐项确认：

- [x] Road v0.7 只做 App Shell 与信息层级，不增加产品能力。
- [x] 紧凑顶栏、两个日常位置和 Vault 环境入口的层级正确。
- [x] Paper、Library、Vault 与阻塞恢复的结构正确。
- [x] 不修改 Paper v4、Index v4、protocol v2、Python 或 Rust。
- [x] `1220×780`、`920×680`、键盘与一号作者 Gate 足以判断完成。
- [x] [`PLAN_road_v0_7.md`](../../PLAN_road_v0_7.md) 的 Checkpoint 顺序可以执行。

该批准与 advance YOLO 已用于通过 CP0–CP6；实际证据见各 checkpoint report。CP6 的窄范围真实 Vault 使用已经单独授权并完成，但不延伸到后续操作。Road 续段仍待新任务规划；push、tag、closeout 与发布未获授权。
