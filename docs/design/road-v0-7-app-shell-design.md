# Road v0.7：App Shell、连续编辑流与响应式 Anchor 设计

> 状态：开发者于 2026-08-20 批准原设计与实施计划；CP0 `fb52b55`、CP1 `8019969`、CP2 `55d45fc`、CP3 `55b5313`、CP4 `6f69310`、CP5 `3259c42` 与 CP6 一号作者 Gate 均已通过。CP7 于 2026-08-25 通过 Gate D，并在 `1e17cea` 建立本地 checkpoint。CP8 完成 source、完整工程、五档布局、Figma 与实体键盘 macOS IME Gate，开发者于 2026-08-26 明确通过 Gate D 并判定 Road v0.7 产品与实施正式完工。最终 checkpoint 为 `2f03aee`；[Road snapshot](../archive/snapshots/road-v0-7.html) 已在其后独立归档。CP6 的一次有界真实 v4 Vault 作者 Gate 已完成且授权已耗尽；此后未再操作真实 Vault，push、tag、签名、打包与发布均未执行。
>
> 基线：Road v0.6 已完成并验收的 Paper v4 / Index v4 / protocol v2。
>
> 权威边界：[`SPEC`](../SPEC.md) 定义 CP8 已接受产品边界；本文保留 CP0–CP6 历史，并拥有 CP7/CP8 详细设计与验收矩阵。`PROJECT`、源码与测试继续标明当前实现与 Road 收口边界；工程证据不等于开发者接受。
>
> 伴随评审物：[`Road v0.7 HTML 计划书`](road-v0-7-planbook.html)；它只展示本设计与实施计划，不新增第三份规范权威。
>
> 文档同步：2026-08-26 按 CP8 production source 复核；2026-08-30 再确认开发者 TUI、
> 技术手册与根目录 `CONTEXT.md` 路由均在产品界面和运行链之外。§§1–16 保留 CP0–CP6 历史，
> 当前界面以 §17（CP7）与 §18（CP8）override 为准。

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

> 历史边界：本节记录 CP0–CP6 的范围—列表—详情基线。当前 production 已由 §17.3
> 覆盖为 scope/sidebar + 主结果/操作流，Paper 预览进入 top-layer Popover；§18.3 再定义
> 竖版双 Anchor。以下结构不再是 CP8 截图基准。

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

  **2026-09-05 独立修复候选说明：** 上句保留 CP2 当时的组件分工记录；当前候选将窗口监听器交给 App，Paper 只保留 dirty／baseline 与 departure 判断。2026-09-05 开发者人工复核已通过常规退出入口保护（强制退出除外）；检查与验收分别见[关闭保护报告](../acceptance/close-guard-2026-09-04.md)，不重写 CP2 的历史验收。
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

下表保留 CP0–CP6 的接受与证据口径；当前 CP8 presentation 还必须叠加 §17.5 与 §18.5
矩阵。尤其 Library 的 inline/纵向详情已由 §17.3 top-layer Popover 覆盖。

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
- [x] `PLAN_road_v0_7.md`（Git 历史：`78eb755:docs/archive/road-v0-7/PLAN_road_v0_7.md`） 的 Checkpoint 顺序可以执行。

该批准与 advance YOLO 已用于通过 CP0–CP6；实际证据见各 checkpoint report。CP6 的窄范围真实 Vault 使用已经单独授权并完成，但不延伸到后续操作。CP7 使用下节新增合同；push、tag、closeout 与发布未获授权。

## 17. CP7 override：连续编辑流（accepted）

CP7 不推翻 CP6 已接受的 Shell、Paper/Library 同级关系、Vault 环境入口或阻塞恢复。
它主要替换 Paper 的视觉/文本适配与默认窗口几何；Gate D 后续整改另有两项窄 override：
Library 的 IME-safe 搜索与 top-layer Paper 预览，以及三个既有文件夹 Trash 生命周期方法。
未列出的 CP6 合同继续有效，Paper v4、Index v4、protocol v2、DTO、Rust 与 sidecar 不变。

### 17.1 结构与风格

```text
Shell → Paper context → 页面导航 → 当前页标题/类型/Markdown → 删除/加一页/保存
```

- 默认窗口 `720×900`，满足 `width / height = 0.8`；Tauri 最小几何锁定为 `720×680`，横版仍由同一 DOM/CSS 重排。`375×812` 仅是浏览器响应式证据，不等于 Tauri 最小窗口或移动端交付。
- 风格关键词固定为“冷编辑台 + Opus 标题 + 系统工具控件”。Opus serif 只用于 Paper 名与页标题；品牌、控件、正文和对话框使用系统 sans；code/path/页号使用 mono。Figma meta `#627078` 在 production 中因 WCAG 对比度校正为 `#5c6a71`。
- Tags 是一个单行 comma-separated 输入；不使用 chips 或逐行 textarea。macOS 字段关闭自动更正与智能引号转换；原生实证确认 ASCII 直引号未被改成弯引号。
- Paper 详情是小型原生 Popover，不进入 Paper grid；路径可换行，支持键盘开关、Escape、light-dismiss 和焦点返回。Library Paper 预览沿用同一 top-layer 组件规则，见 §17.3。
- 输入编辑态只用轻微冷色底与细底线，不使用高存在感 focus 边框；按钮、导航和高对比模式仍保留清楚系统 outline。
- 页面不显示常驻 dirty 文案。saving、validation、stale、`repair_required`、`commit_unknown` 与 `index_degraded` 仍按其既有责任出现。

### 17.2 Tags 可逆适配

Paper v4、DTO、JSONL 与 Markdown 继续传递有序 `string[]`；逗号仍可属于一个 Tag。Vue
只在字段边界使用 CSV-style 表示：含逗号或双引号的值加双引号，内部双引号写作 `""`。
解析保留顺序，沿用既有 trim、空项丢弃和首次去重语义；Vue 必须与 Core 使用同一
外侧空白集合，不能单独依赖会额外删除 `U+FEFF` 的 JavaScript `.trim()`；未闭合引号阻止保存并保留输入。
禁止 `join(", ")` 后 `split(",")`，也禁止迁移或静默规范化既有 Markdown。

### 17.3 Library 与文件夹生命周期 override

- Library 搜索框在 `compositionstart` 到提交事件之间只更新本地输入显示，不发出
  `library.query`，也不以中间拼音重渲染候选窗；提交后发送最终中文值，同值的尾随
  `input` 被父层去重。
- 每个 Paper 结果后紧邻自己的 `popover="auto"` 预览，结果按钮使用 `show` 而非
  `toggle`。Popover 进入浏览器 top layer，不参加列表高度计算，不把 Paper 或文件夹操作
  推到底部；关闭、Escape、light-dismiss、Tab 顺序和“打开整份 Paper”均保持可达。
- 当前文件夹与废纸篓文件夹操作紧贴范围控件，并在 DOM 中位于结果区之前；Paper 结果
  数量不会把它们推到底部。所有原生 `select` / `input` / `button` 与 grid track 必须允许
  收缩，最大合法 `200` 字符名称在四档不得扩大 document `scrollWidth`。
- 经确认的 `soft_delete_folder` 把 `cache/<folder>` 完整目录树原子移入
  `.trash/cache/<folder>`；`.DS_Store`、损坏 Markdown、嵌套目录与符号链接 entry 不再
  成为人工清理阻断。`restore_folder` 整树回移，目标完全同名或 NFC+casefold 等价时
  全有或全无地拒绝，不做部分合并。
- `permanently_delete_folder` 仍需废纸篓中的不可撤销确认；Core 固定精确 inode，同父
  随机隔离，并逐层使用 fd-relative、no-follow 后序删除。设备/挂载、identity 或并发名称
  变化会停止删除并保留可识别路径；递归开始后的底层失败不能回滚已销毁 entry，剩余树
  恢复为原废纸篓名称并明确报告失败。符号链接只删除链接本身。`merge_folders` 与重命名
  不使用本 override，继续严格 Paper 预检。完整决策见
  [ADR-0008](../architecture/decisions/0008-whole-folder-trash-lifecycle.md)。

### 17.4 Figma 交付

现有 keikeu UI 文件新建 `CP7 · 连续编辑流` Page，至少包含：母版、四尺寸/关键状态、
tokens 与系统控件、`UI/UX 入门`、`行业模板`。后两区是非规范学习/复用材料，不建立
production UI kit。HTML master 仍是 Gate B 对照物；节点审计和开发者最终视觉批准后才
允许进入 Gate C。上述交付与节点审计已经完成，开发者于 2026-08-25 明确判断 Gate B
通过；HTML master 继续只作对照，不构成 production 或 Gate D 证据。
Gate D 后续整改已在同一 Page 的 `06 · Gate D Library 后续整改` Section（`152:138`）
增量同步 Library Popover、composition-safe search、范围旁文件夹操作、长名称收缩与完整
文件夹 Trash 文案/状态；Section 截图复核和递归节点边界审计均通过。该同步证明设计与
候选实现对齐，不替代开发者 Gate D 判断。

### 17.5 CP7 验收矩阵

| 面 | 必须成立 | 不得发生 | 证据 |
| --- | --- | --- | --- |
| 连续流 | context、页、正文、动作按纵向顺序可扫描；底部动作可滚动到达 | sidebar、手机专属导航、横向滚动、整体缩小 | 四尺寸浏览器证据与开发者判断 |
| Tags | 单行 CSV-style UI 对普通值、逗号、双引号、空项、外空白、重复、`U+FEFF` 与畸形引号可逆/可阻塞 | `split(",")`、JS `.trim()` 扩大规范化、DTO/Markdown/schema 变化、无关保存拆 Tag | Workbench + PaperView Vitest，保存 intent 断言 |
| 详情/focus | Popover 不撑开布局，键盘关闭后焦点返回；文本 focus 安静但可辨认 | inline 大片详情、仅 hover、移除按钮 focus | 四尺寸、键盘与高对比检查 |
| Library 搜索/预览 | composition 期间零查询，提交后一次最终词；每行相邻 native Popover 进入 top layer；文件夹操作紧贴范围且不因结果数/预览开合下沉；`200` 字符名称不扩张页面 | 拼音中间查询、重复提交、共享远端 Popover 导致长 Tab 路径、inline 预览下压操作、原生 option 撑宽 grid | Projection + LibraryView Vitest，真实 DOM composition、Tab/Escape、四尺寸几何与隔离 Tauri smoke |
| 文件夹生命周期 | 软删除/恢复完整目录树原子移动；永久删除二次确认后按精确身份 no-follow 递归；外部链接目标不变 | 未知项要求人工清理、部分搬运、目标覆盖、跟随链接或跨挂载删除 | synthetic Vault 直接测试：unknown/nested/symlink、NFC 冲突、source/destination replacement、destructive-stage device race |
| dirty/安全 | 无常驻 dirty 文案；离开、新 Paper、Vault、关闭仍复用唯一 guard | 自动保存、第二套确认、隐藏 saving/error/recovery | App/Paper 直接测试与 Tauri native smoke |
| 窗口 | 实际 Tauri 默认 `720×900`；横版仍可用；`scrollWidth <= clientWidth` | 默认宽高比大于 1、裁掉保存/危险/恢复动作 | config 检查、四尺寸浏览器、实际 Tauri 启动 |
| 范围 | 原 Vue/CSS/Tauri 几何加 §17.3 的窄 Library/Core 例外；协议/DTO/Paper/Index/Rust/sidecar 不变 | 把整树策略扩到 merge/rename、真实作者内容变化、依赖或命令扩张 | diff/ADR 审计、全量 Python/Vitest/Rust/build/docs |

### 17.6 Gate 顺序

Gate A 合同 → Gate B Figma 与最终视觉批准 → Gate C production/工程证据 → Gate D
开发者 UI 接受。较早 Gate 不替代较晚 Gate；CP7 checkpoint 只有在 Gate D 无未解决 P0/P1
时通过。snapshot、tag、push、签名、打包和发布继续独立决定。

Gate A、Gate B、Gate C production candidate、原始工程证据与 Gate D 后续整改复核均已
完成。Gate D 首轮开发者 UI 验收因六项 UI/功能问题未通过；首批整改后又退回完整文件夹
删除、Library 中文 IME 与 Paper 预览三项。§17.3 后续整改已通过全量工程、真实浏览器
四尺寸/DOM composition、隔离 Tauri 与同一 Figma Page 增量同步，独立终审为
`0 P0 / 0 P1`；开发者于 2026-08-25 明确通过 Gate D。原生 macOS 候选窗未由自动化可靠
触发，因此不回填为 CP7 证据并转入 CP8 人工复核。CP7 本地 checkpoint 为 `1e17cea`；
既有首次冷 sidecar 启动超时仍只记为环境现象。

## 18. CP8 accepted override：响应式页签、竖版 Anchor 与原生 IME

CP8 不改变 CP7 已接受的视觉语言、连续编辑流、CSV-style Tags、Popover、完整文件夹 Trash
生命周期或唯一 dirty-departure guard。它修复页数增加与竖版布局下的导航/操作可达性，
并把此前无法由自动化证明的 macOS 原生候选窗提升为明确的产品接受 Gate。

### 18.1 Shell 与 Paper 页签滚轮

```text
keikeu | 编辑 Paper | 新 Paper | Library | … | Vault
        └─────── 单行 56px；同一离开保护 ───────┘

Paper context
└── [01][02][03] … 所有页都在单行局部滚轮中
    └── 当前页标题 / 类型 / Markdown
        └── 删除本页 / 加一页 / 保存
```

- Shell 在所有方向保持单行 `56px`；只调整可见文案与顺序。`新 Paper` 仍在唯一 guard 通过
  后清空 path 并替换 PaperView，不增加 Router、store 或第二套确认。
- 所有页签按钮始终在 DOM 中。轨道每屏约显示三个等宽槽位，`1/3/4/6/7/12` 页都保持
  单行恒高；不换行、不循环、不加前后箭头。
- 只有页签轨道恢复细横向滚动条，使用 `overflow-x: scroll` 与 scroll-snap；document 自身
  仍满足 `scrollWidth <= clientWidth`。
- 载入、直接点选、加页或删页后，当前按钮以 `inline: center`、`block: nearest` 自动进入
  可见中部。`aria-current`、键盘焦点、直接点选、跨边界加删页和 saving lock 不退化。

### 18.2 竖版 Paper Anchor 与正文滚动

竖版只由原生 `@media (orientation: portrait)` 定义，即 `height >= width`；不再引入一套
按具体机型或像素宽度分叉的产品逻辑。

- Markdown textarea 高度为 `clamp(220px, 34dvh, 300px)`，关闭纵向 resize；超过可见
  高度的正文只在输入框内滚动。横版继续允许纵向 resize。
- “删除本页 / 加一页 / 保存”成为底部 sticky Anchor。Anchor 使用不透明冷编辑台背景、
  safe-area padding 与正文尾部滚动留白，不得遮住第 `80` 行、validation/error、焦点或
  屏幕阅读器可达内容。
- Anchor 不改变按钮顺序、保存调用、删除确认或 page draft 语义。

### 18.3 竖版 Library 双 Anchor 与 Popover

- 竖版 Library 在 Shell 下方固定两枚等高 sticky Anchor：“范围 / 排序”和“新文件夹”。
- “范围 / 排序”使用 native Popover，包含两个原生 select；值和事件继续进入既有范围与
  排序状态。“新文件夹”Popover 复用既有 `folderName`、校验与创建请求。
- 两个触发器均支持 Enter/Space；Popover 支持 Escape、light-dismiss 和关闭后焦点返回。
  创建失败时输入和 Popover 保留，成功后才关闭。
- 横版继续使用既有 Library sidebar、排序栏和内联新文件夹；Paper 预览仍是每行相邻的
  top-layer Popover。CP8 不修改 Library DTO、搜索、文件夹 mutation 或 Core。

### 18.4 Figma 原位覆写

在修改 Figma 前先保存版本历史
`CP7 Gate D accepted · before CP8 overwrite`。现有 Page `71:2` 原位重命名为
`CP8 · 响应式锚点与横向滚轮` 并覆写，不建立第二套活动母版。

同一 Page 必须表达 `375×812`、`720×900`、`720×680`、`920×680`、`1220×780` 五档，
以及 `4/6/12` 页滚轮、长正文框内滚动、Paper 底部 Anchor、Library 顶部双 Anchor、两个
Popover 与修正后的单层 Shell。继续复用本地 token、组件和 Opus 字体角色；逐段回读节点、
截图并运行递归 bounds 与字体审计。Figma 同步只证明设计对齐，不代替源码、平台或
Gate D 证据。

Gate C 已在 Figma file `Eubz4vHZ0YaCk0Mki12ljS` 完成：桌面 version-history 保存流程使用
精确标题 `CP7 Gate D accepted · before CP8 overwrite`，Page `71:2` 原位重命名为
`CP8 · 响应式锚点与横向滚轮`，主要 Sections 为 `71:4` / `71:5`。五档 viewport、bounds、
字体与 CP7 residue 递归审计全部 clean。connector 不暴露 version ID，因此不伪造该值。

### 18.5 CP8 验收矩阵

| 面 | 必须成立 | 不得发生 | 最低证据 |
| --- | --- | --- | --- |
| Shell | 单行 `56px`；“编辑 Paper → 新 Paper → Library … Vault”；唯一 guard 不变 | 双层 Shell、换行、第二套确认或直接清空 dirty draft | App/Prototype Vitest、五档 DOM 几何与 dirty 两分支 |
| 页签滚轮 | 所有页在 DOM；约三槽、单行恒高、局部可横滚、scroll-snap；活动页在载入/选择/加删后居中 | 第二行、循环、箭头、document 横向滚动或活动页不可见 | `1/3/4/6/7/12` 页 Vitest + 五档真实布局 |
| Paper 竖版 | textarea `clamp(220px, 34dvh, 300px)`、内部滚动；底部 Anchor 不遮内容/错误/焦点 | 输入框把页面撑出视口、纵向 resize、Anchor 覆盖第 `80` 行 | 80 行正文、最大名称、滚至末行与 focus 检查 |
| Library 竖版 | 双 Anchor 等高且贴 Shell；两个 native Popover 可键盘开关、Escape/light-dismiss、焦点返回；失败保留输入，成功关闭 | 范围占据首屏、inline 面板推低 Paper、失败清空输入或焦点丢失 | Library Vitest、竖版真实 DOM 与 synthetic 创建失败/成功 |
| 横版 | 既有 sidebar、排序与内联新文件夹不变；Paper textarea 仍可纵向 resize | 把竖版 Anchor 叠到横版或改变 Library 能力 | `720×680`、`920×680`、`1220×780` 浏览器检查 |
| Figma | Page `71:2` 保存 CP7 version 后原位覆写，五档与关键状态齐全，bounds/font 审计通过 | 第二套活动母版、旧双 Shell、节点溢出或字体角色漂移 | version-history 保存记录、节点回读、截图、递归 bounds/font 审计 |
| 原生 IME | 实体键盘输入 `baoshi` 时候选窗稳定；选择“暴食”后只查询一次最终中文且无残留 `ba` | 候选窗缺失/被重渲染打断、中间拼音查询、最终值重复提交 | fake Home + synthetic Vault + 绝对路径 debug `.app` 人工记录 |
| 范围 | 只改 Vue 结构/CSS/直接测试与 Figma；数据、运行链、Tauri 几何和依赖不变 | Core、bridge、DTO、Paper/Index/protocol、Rust、依赖或产品能力变化 | diff 审计 + 完整 Python/Vitest/Rust/build/docs |

### 18.6 Gate 与阻断判据

CP8 Gate A–C 的工程候选与 Figma 已完成。开发者于 2026-08-26 在真实 macOS 简体拼音和
实体键盘下完成以下复核：只按 CP8 debug `.app` 绝对路径启动，使用 fake Home 与含
Tag“暴食”的 synthetic Vault，输入 `baoshi`，在提交前观察稳定候选窗，手动选择“暴食”，
并确认输入框只保留最终中文、结果只刷新一次。

候选窗未出现、选择前被重渲染打断、出现中间拼音查询或最终值重复提交，任一项均为 P1，
阻断 CP8 Gate D。上述四类阻断均未出现，开发者明确判断“全部通过，没有异常”。自动化
composition、截图、Figma、full gate 或 debug bundle 构建仍不能替代该人工证据；详细的
synthetic、build/OS/input-source 记录见 CP8 acceptance report。

CP8 Gate D 已通过；最终 checkpoint 为 `2f03aee`，Road snapshot 已作为其后的独立文档
closeout 创建。该 Git 收口不授权 push、tag、进一步真实 Vault 操作、签名、打包或发布；
这些动作在收口阶段均未执行。
