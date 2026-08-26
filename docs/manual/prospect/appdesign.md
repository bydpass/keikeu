> **HUMAN MANUAL — NON-NORMATIVE.** 本文用人话解释 Road v0.6 建立、已完工 Road v0.7 继续使用的 Paper v4 产品模型。当前产品边界以 [`docs/SPEC.md`](../../SPEC.md) 为准，当前坐标以 [`docs/PROJECT.md`](../../PROJECT.md) 为准；Road v0.7 complete / Git closeout pending 见 [Road v0.7 书面设计](../../design/road-v0-7-app-shell-design.md)。

# keikeu APPDESIGN.md

> slogan：存住一瞬的灵光
>
> 记录范围：Road v0.7 product complete / Git closeout pending · Paper v4；CP8 不改变数据合同
>
> 设计原则：本地优先、作者控制、直接编辑 Paper、无 AI 代写

---

## 0. 先分清数据基线与当前组合层

本文解释当前已接受的 Paper v4 产品模型，但不替代规范或运行证据。Road v0.7 已接受的 App Shell 只调整信息层级与响应式布局，不改变本文的数据与保存合同。

| | 数据与运行合同 | 当前组合层 |
| --- | --- | --- |
| 产品版本 | Road v0.6 建立并归档的 runtime | 已完工 Road v0.7 的 CP8 响应式 App Shell |
| 内容模型 | Paper v4：一份 Paper 由有序卡页组成 | 不改变 Paper v4 / Index v4 / protocol v2 |
| 聚焦方式 | Paper 本身可编辑、可翻页并整体保存 | Paper / Library 是日常位置，Vault 是环境入口 |
| 实现状态 | 已实现、验收并归档 | Road v0.7 产品与实施正式完工；HEAD 仍为 CP7 `1e17cea`，CP8 checkpoint / Road snapshot 尚未创建 |

判断“现在已经运行什么”时，以 `SPEC`、实际代码和测试为准；判断后续 target 与 Gate 时，以当前计划和 `PROJECT` 为准。本文不覆盖其中任何一侧，也不授予实施或迁移权限。

---

## 1. 产品变化：不再“生成 Flashcard”

Road v0.5 的核心链路是：

```text
灵感 → 编辑并保存 Paper → 另行打开只读 Flashcard → 离开 keikeu
```

Road v0.6 已接受的当前链路是：

```text
灵感 → 直接编辑由卡页组成的 Paper → 保存 → 带着 Paper 离开
```

一句话定义：

> 以前，用户带着灵感进入 keikeu，编辑 Paper，最终带着 Flashcard 离开；现在，用户带着灵感进入 keikeu，编辑 Paper，带着 Paper 离开。

Flashcard 不再是单独视图、投影或资产；旧调用方已清零并从活动产品模型退役。

这不是把 keikeu 扩张成正文编辑器。keikeu 仍负责把松散灵感整理成可继续写作的耐久 Paper；正式正文仍可在作者选择的外部编辑器中完成。

---

## 2. 用户、价值与边界

Road v0.6 优先服务一号用户：使用 Apple Silicon Mac、单人私密创作、重视本地文件和文字控制的作者。

keikeu 提供：

- 快速接住已有灵感；
- 把灵感拆成可翻阅的卡页；
- 用命名、类型和 Tags 帮助找回；
- 用普通 Markdown 保存作者资产；
- 在保存冲突、文件损坏或运行时异常中优先防止覆盖。

keikeu 不提供：

- 自动写作、摘要、润色或评价；
- 账号、云后端、遥测或隐藏上传；
- 社区、约稿、协作或发布平台；
- Road v0.6 内的 Outline 编辑或生成；
- 长篇正文工程、章节进度或 Notion 式通用数据库。

二号用户只有 iOS 设备，因此不参加 v0.x 测试。其需求最早在同时具备 iOS 与 Android 客户端的 v1.0 重新设计，不能反向扩大 Road v0.6。

---

## 3. Paper v4：一个对象，两层命名，多张卡页

当前已接受的数据模型：

```text
Paper
├── code                 稳定代号
├── display_name         整份 Paper 的可选名称
├── tags[]               平面标签
├── created / updated
├── legacy_title         兼容保全字段
├── extra_frontmatter    未知 frontmatter 的保全区
└── pages[]              至少一页，顺序即作者顺序
    └── CardPage
        ├── name         当前页的可选标题
        ├── content      当前页正文
        └── type         null / summary / snapshot / whisper
```

两层命名不能混用：

- `display_name` 命名整份 Paper，用于 Library 与工作台外层标题；
- `name` 命名当前卡页，在基础模式和进一步模式中始终可编辑。

核心不变量：

- 一份 Paper 至少有一页；
- 页面没有持久 ID；界面临时使用的 `ui_key` 不发送、不写盘；
- 每个保存页必须满足 `name is not None or content.strip() != ""`；
- 一份 Paper 最多有一个“总结”页；
- “高光”和“碎碎念”页数量不限；
- 作者正文按原文保存，不自动总结、规范化或修复；
- Road v0.6 不提供页面重排。

---

## 4. 类型是标记，不是三种不同对象

类型变量与界面显示名固定为：

| 保存值 | 显示名 | 用途 |
| --- | --- | --- |
| `summary` | 总结 | 对整份灵感的收束；每份 Paper 最多一页 |
| `snapshot` | 高光 | 场景、动作、对白、转折或意象 |
| `whisper` | 碎碎念 | 尚未整理、但值得留下的旁白或念头 |
| `null` | 不显示标签 | 暂不分类 |

基础模式与进一步模式只是同一份数据的两种界面密度：

- 基础模式：编辑页面标题与正文，不显示类型控件；
- 进一步模式：仍可编辑标题与正文，并额外设置类型；
- 切换模式不创建副本，也不清除已经设置的类型。

“命名”不属于进一步模式专有能力。基础模式下，它就是卡页顶部的可编辑标题输入栏。

---

## 5. Paper 工作台（CP6 历史；CP7/CP8 accepted）

下列图与“每行一个”描述保留 CP6 已接受历史。CP7 accepted override 已把展示替换为连续
纵向编辑流和单行可逆 comma/CSV Tags 字段；底层有序 `string[]` 与 Paper v4 Markdown
合同不变。新建 Paper 默认只有一张空白、未标记的页，
不会把第一页预设成“总结”。正文引导只推荐“写任何想写的文字”，不把总结变成默认值
或必填项。

```text
┌─ Paper 元数据栏 ─────────────────────────────────────┐
│ 代号（只读）   Paper 名称（可编辑）   Tags（每行一个；CP6 历史） │
└───────────────────────────────────────────────────────┘

                 1 / 3      ‹      ›
        ┌───────────────────────────────┐
        │ 页面标题（始终可编辑）          │
        │ [进一步模式下显示类型标记]       │
        │                               │
        │          页面正文             │
        │                               │
        │ 保存      删除本页      加一页  │
        └───────────────────────────────┘
```

边界如下：

- 卡页底端只有三个主操作：保存、删除本页、加一页；
- 页码和前后翻页位于卡片外，不挤入主操作区；
- Paper 名称、代号和 Tags 属于整份 Paper，不随翻页改变；
- CP6 历史 UI 的 Tags 使用原生多行输入框，每行一个 tag；逗号只是普通字符；
- CP6 历史 UI 保存 Tags 时逐行修剪，移除空行，并按首次出现顺序去重；CP7 只在 Vue 字段边界改用可逆 CSV-style 表示；
- `Cmd+S` 与“保存”调用同一个动作。

CP8 不再让页数增长形成第二行：全部页按钮保留在约三槽宽的单行局部滚轮中，只有该轨道
显示细横向滚动条，并在载入、点选、加页与删页后把活动页滚至中部。竖版 Markdown 在
`clamp(220px, 34dvh, 300px)` 内部滚动，三项动作成为 safe-area-aware 底部 Anchor；横版
继续允许 textarea 纵向 resize。这些都是呈现和可达性调整，不改变 pages[] 或保存合同。

### 5.1 加一页

“加一页”在当前光标处截断正文：

1. 当前页保留光标前的正文；
2. 若选中了文字，选区和其后的正文一起移动到新页；
3. 当前页保留原来的标题与类型；
4. 新页标题和类型均为 `null`；
5. 新页插入当前页之后，立即成为活动页，焦点进入标题；
6. 这一步只改内存草稿，不写磁盘。

在开头或末尾截断可以临时产生空白页，但最终保存仍须满足页面有效性规则。

### 5.2 删除本页

- 删除前必须确认；
- 多页 Paper 删除当前页后，选择相邻页继续编辑；
- 若只剩一页，则以一张空白页替代，保证 Paper 永远至少一页；
- 页删除只有在下一次整体保存成功后才持久化；
- 整份 Paper 的删除仍由 Library 的软删除能力负责，不借用“删除本页”。

### 5.3 保存与离开

Save 是唯一持久化边界。标题、正文、类型、Tags、加页和删页在保存前都只是本地草稿。

- 不自动保存；
- 不逐页保存；
- 翻页时不隐式保存；
- 整份 Paper 一次提交；
- 保存以作者打开时读到的源版本为前提；磁盘已改变就进入 `stale`，不做后写覆盖；
- 只有成功保存才建立新的干净基线；
- 保存失败、外部修改或结果不明时，完整草稿继续留在内存；
- 关闭窗口、切换 Vault、打开别的 Paper 等离开路径共用同一套未保存保护。

---

## 6. Markdown 仍是作者资产

每份 Paper 继续是一份普通 Markdown 文件，Index 只是可删除、可重建的辅助索引。

当前已接受形状示例：

```markdown
---
type: paper
schema_version: 4
code: K-20260802-001
created: 2026-08-02T10:00:00
updated: 2026-08-02T10:30:00
display_name: 夜车上的约定
---
# K-20260802-001

<!-- keikeu:page {"name":null,"type":"summary"} -->
末班公交上，两个人隔着一个空位假装睡着。
<!-- /keikeu:page -->

<!-- keikeu:page {"name":"旧打火机","type":"snapshot"} -->
B 把旧打火机塞回 A 手里。
<!-- /keikeu:page -->

## Tags

- 末班车
- 离别
```

格式选择 HTML comment 作为页边界，是为了让普通 Markdown 阅读器仍主要呈现作者正文。实现必须同时保证：

- 严格解析结构，不从损坏文件拼出半份 Paper；
- 对页名中的 `--` 和正文中的保留 marker 行做可逆转义；
- 尽可能语义保留未知 frontmatter；
- 解析失败时不写“自动修复”，不覆盖原文件；
- 用户可从 Finder 打开文件，并在普通文本编辑器中人工修复。

---

## 7. Library：一行仍是一份 Paper

Paper 变成多页后，Library 不会变成卡页数据库。

每行显示或提供：

- Paper 名称与代号；
- 页数与第一页预览；
- 页标题、Tags、创建与更新时间；
- 文件夹、Branch、Trash 等现有生命周期能力。

搜索覆盖 Paper 名称、代号、Tags、所有页标题、正文和类型，但搜索派生文本只留在 Python/Index 一侧，不发送给 Vue。打开搜索结果时打开整份 Paper 的第一页；Road v0.6 不提供单页 deep-link。

CP7 Gate D 后续整改在不改变 Index/DTO 的前提下增加两条展示约束：中文输入法 composition 期间不发查询，提交后只发送一次最终词；每行 Paper 使用与触发器相邻的 native top-layer Popover 预览，不把详情块插到列表下方或下压文件夹操作。文件夹软删除与恢复则原子移动完整目录树；不可恢复销毁只发生在废纸篓中的二次确认后，详见 ADR-0008。

CP8 竖版 Library 进一步把“范围 / 排序”和“新文件夹”收成 Shell 下方两枚等高 sticky
Anchor；它们分别打开 native Popover，复用既有 select、输入、校验与创建请求。失败保留
输入并继续打开，成功后才关闭；横版 sidebar、排序栏与内联创建保持不变。

Branch 复制已经保存的整份 Paper，包括页序、标题、正文、类型和 Tags，并生成新的代号、路径和时间。未保存草稿不参与 Branch。

Index 失效不能让 Markdown 失去权威。Trash 搜索也不新建第二份持久索引，而是在 Python 内存中计算。

---

## 8. v2 / v3 → v4：允许直接改写，但不允许静默改写

Road v0.6 选择直接把旧 Paper 改写为 v4，不长期维持双 schema 兼容层。简单不等于冒险：迁移必须是显式、一次性、可预检的操作，不能在普通打开或保存时偷偷发生。

| 旧数据 | v4 结果 |
| --- | --- |
| `code`、`display_name`、Tags、路径、时间与未知 frontmatter | 保留 |
| current Summary | 第一页，类型为 `summary` |
| 每条 Highlight | 按原顺序成为 `snapshot` 页，名称与正文保留 |
| `initial_summary` | 按已确认的产品决定丢弃 |
| whisper | 不从旧内容猜测 |

`initial_summary` 是唯一获准丢弃的旧字段。迁移前必须做原始字节归属审计；除它以外，只要有无法证明已映射或明确保留的内容，整份迁移就阻塞并转人工修复。

执行纪律：

- 先在 fixtures 或完整副本上预检和演练；
- 在 Home 下、active Vault 之外生成并逐字节验证完整备份；报告不记录作者正文；
- 旧 Summary 无效，legacy Tags 含多行、控制字符、空项、外围空白或 trim 后重复，
  以及结构重叠等情况阻塞；
- mixed-schema Vault 不进入正常工作态；
- 未经单独授权，不操作唯一真实 Vault；
- Road v0.1 数据先按冻结规则迁到 v3，再通过独立 Gate 迁到 v4。

---

## 9. Runtime：设计如何在运行中守住文件

这里的 runtime，指用户打开 App 后，界面、桌面壳、Python 逻辑与本地文件共同工作的实际责任链，而不是一种新的产品功能。

```text
Vue 3 界面
   ↓  用户意图与草稿
Tauri / Rust 桌面壳
   ↓  JSONL protocol v2
Python Application Service + Core
   ↓
Markdown（权威资产） + Index（可重建缓存） + Vault（用户目录）
```

职责保持简单：

- Vue 3 管界面、草稿、活动页和离开保护；
- Tauri/Rust 管进程、请求边界和“结果可能已经落盘”的传输语义；
- Python 管校验、整体保存、迁移、Library 和文件安全；
- GUI 不直接写 Markdown，Core 不依赖 GUI 或 transport。

对作者可见的关键状态：

| 状态 | 意义 | App 行为 |
| --- | --- | --- |
| `stale` | 磁盘文件已在别处改变 | 禁止覆盖，保留草稿，允许查看或明确放弃后重载 |
| `repair_required` | 文件结构无法安全解析 | 不生成半成品，不写修复，指引人工检查 |
| `commit_unknown` | 保存请求结果无法证明 | 冻结写入、绝不重发，只读对账同一个 Vault |
| `index_degraded` | Markdown 已保存，但索引可能过期 | 以保存成功的 Paper 建立基线，单独重建 Index |

`commit_unknown` 不是普通重试错误。重新发送同一次修改可能覆盖已经成功的保存，因此 App 必须在根状态保留提交草稿，只做只读对账。

---

## 10. 平台与发布矩阵

| 平台 | 决定 | Road v0.6 含义 |
| --- | --- | --- |
| macOS Apple Silicon | 主力开发与唯一作者 Gate | 实现、测试和 smoke 的目标平台 |
| Intel Mac | 明确不支持 | 不做 universal、x86_64 或 Rosetta 工作 |
| iOS / iPadOS | 2026 年 8 月方向性目标 | 另行设计移动 runtime |
| Android / HarmonyOS | 2026 Q4 方向性目标 | 另行设计与验收 |
| Windows | 2027 方向性目标 | 不进入本 Road |
| Linux / watchOS | 暂无安排 | 不承诺支持 |

Python sidecar 是桌面子进程；Tauri 能面向移动端，并不意味着当前 runtime 可以自动搬到手机上。

Developer ID 签名、公证、staple、DMG 和人工分发延后至 Road v0.8。Road v0.6 不执行打包发布，也不恢复已经停用的公证凭据。

---

## 11. Road v0.6 已通过的产品 Gate

工程完成不等于产品接受。CP7 已由一号真实作者完成一条真实但不泄露内容的链路：

```text
用真实灵感创建 Paper
  → 命名并添加 Tags
  → 写页、截断加页、设置标记
  → 整体保存
  → 退出并重开
  → 从 Library 搜索并找回
```

验收只记录完成情况、犹豫点、介入次数和脱敏原话，不记录作品正文或敏感路径。故意损坏与修复演练只能使用合成 Paper 或真实 Vault 的完整副本，不能拿唯一真实作品冒险。

Road v0.6 在自动检查、平台 smoke、真实作者链路完成且没有未解决 P0/P1 后获接受。它没有因此自动产生签名包、远端 push、多用户 MVP 或移动端完成声明。

---

## 12. 最终产品表述

Road v0.6 的 keikeu 仍然是一款本地优先的写前整理工具，但它不再要求作者先编辑一种对象，再消费另一种对象。

> Paper 就是作者正在写、正在翻、最终保存并带走的东西。

页面、类型、Tags 和 Library 都围绕这一个对象服务。任何新能力若不能更直接地帮助作者接住灵感、整理成卡页、可靠保存并重新找回，就不进入本 Road。

继续阅读：

- 当前产品权威：[SPEC](../../SPEC.md)
- 当前坐标：[PROJECT](../../PROJECT.md)
- Road v0.6 已接受书面设计：[Paper v4 产品与架构设计](../../design/road-v0-6-paper-v4-design.md)
- Road v0.7 CP8 accepted override：[App Shell、连续编辑流与响应式 Anchor 设计](../../design/road-v0-7-app-shell-design.md)
- 当前架构图：[architecture.html](../../architecture/architecture.html)
- 当前交互图：[interaction.html](../../design/interaction.html)
