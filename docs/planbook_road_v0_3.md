# keikeu Road v0.3 Planbook

> Road：macOS Paper Library / Retrieval Quality  
> 状态：**APPROVED — Phase 6 complete / Phase 7 next**
> 基线：`d0feac0269a5619f5dbf27c04347ba69c5665b42`（Road v0.2 已验收，local annotated tag `v0.2.0`）  
> 当前 checkpoint：**CP4 complete / Phase 6 engineering complete / CP5 pending**
> 日期：2026-07-22
> 权限：本文件是 Road v0.3 的已批准执行计划。[`SPEC.md`](SPEC.md)、[`RULES.md`](RULES.md) 与三个 HTML map 描述 v0.3 目标；当前实现进度与 v0.2 runtime 事实分别见 [`PROJECT.md`](PROJECT.md)、`src/` 和 `tests/`。

## 1. 核心判断

Road v0.3 应继续使用现有的**模块化单体**：一个 Flet 应用进程、一个纯 Python core、作者拥有的 Markdown、一个可重建 JSON index。当前架构没有扩容、协作或远程服务问题；重写、数据库、微服务、Repository/Service 层、事件总线和文件监听器都会制造比需求更大的系统。

真正需要改变的只有四个接缝：

1. 所有 Vault 与 Paper 路径由 `keikeu_core.vault` 统一验证、枚举和移动；页面不再假设 `cache/<code>.md`。
2. Paper 升级为 schema v3：增加 Paper 名称，并将 Highlight 从字符串升级为“名称 + 内容”。
3. App 在页面之间传递 vault-relative Paper path；系统编号继续是不可变内容标识，不再承担路径定位。
4. 删除、合并、恢复和永久删除都按明确 Paper 文件逐项执行；只在已验证为空时 `rmdir`，禁止递归删除。

这是 Ponytail 路径：保留已经工作的边界，只在根因位置加最小能力。

## 2. 架构判断方法

本 Road 参考 [study8677/awesome-architecture](https://github.com/study8677/awesome-architecture) 的方法，但不照搬其中为分布式系统准备的组件：

- 先走“需求 → 约束 → 质量属性 → 候选方案 → 取舍 → 决策”，见[架构师的思考框架](https://github.com/study8677/awesome-architecture/blob/main/tutorial/02-%E6%9E%B6%E6%9E%84%E5%B8%88%E7%9A%84%E6%80%9D%E8%80%83%E6%A1%86%E6%9E%B6.md)。
- 架构图保持单一抽象层级、箭头标明方向与含义，见 [C4 图示原则](https://github.com/study8677/awesome-architecture/blob/main/tutorial/03-%E8%AF%BB%E6%87%82%E4%B8%8E%E7%94%BB%E5%A5%BD%E6%9E%B6%E6%9E%84%E5%9B%BE.md)。
- 先确定状态和事实源，再写业务逻辑，见[数据与状态](https://github.com/study8677/awesome-architecture/blob/main/tutorial/05-%E6%95%B0%E6%8D%AE%E4%B8%8E%E7%8A%B6%E6%80%81.md)。
- 只在真实质量属性被卡住时升级架构，并记录为什么，见[架构决策与演进](https://github.com/study8677/awesome-architecture/blob/main/tutorial/08-%E6%9E%B6%E6%9E%84%E5%86%B3%E7%AD%95%E8%AE%B0%E5%BD%95%E4%B8%8E%E6%BC%94%E8%BF%9B.md)。
- 不复制大系统的答案而忽略自己的约束，见[架构品味](https://github.com/study8677/awesome-architecture/blob/main/tutorial/09-%E6%9E%B6%E6%9E%84%E5%93%81%E5%91%B3.md)。
- 关键约束必须落入持久规范与自动检查，见[规格即架构](https://github.com/study8677/awesome-architecture/blob/main/tutorial/23-%E8%A7%84%E6%A0%BC%E5%8D%B3%E6%9E%B6%E6%9E%84%E7%BA%A6%E6%9D%9F%E6%80%8E%E4%B9%88%E5%86%99%E7%BB%99AI.md)。

## 3. Road 边界

### 3.1 已冻结功能

| 能力组 | Road v0.3 结果 |
| --- | --- |
| Paper 标识 | `K-YYYYMMDD-NNN` 自动生成、全 Vault 唯一、不可修改；新增可选显示名称 |
| Highlight | 每项包含 required `content` 与 optional `display_name`；拖放排序；空内容保存时删除该项 |
| Library | 高密度列表；名称/编号/Summary/Tags/Highlight 名称检索；名称、更新时间、创建时间排序 |
| Paper 文件夹 | `cache/` 下真实一层目录；侧栏导航；单个拖放、菜单移动、勾选批量移动、复制分支 |
| Flashcard | 列表点击；Paper 直接切换；左右方向键；页码跳转；每次从第 1 页开始 |
| Trash | 固定可达；Paper/文件夹恢复；安全永久删除；批量操作逐项报告 |
| Vault | 当前用户 Home 白名单；安全切换；不安全旧 Vault 复制验证后切换并保留原件 |
| 启动 | 每台设备每天首次启动显示一次独立鼓励卡，3 秒后进入空白 Paper |
| 键盘 | `Cmd+S`、`Cmd+F`、Flashcard 左右键、`Esc`、标准 Tab/Enter/Space |

### 3.2 Track 边界

- Road v0.2 已完成，不回填或重开其 Phase 8。
- Phase 7.5 是独立轻量 iOS 快速测试版，不是本 Road 的合入或验收门槛。
- Phase 8.5 是 Road v0.3 与下一版 macOS 的前体。
- iOS Flashcard 字号属于 Phase 7.5，不进入本 Planbook。
- Apple App Sandbox 暂不作为 Road v0.3 正式 build 的硬门槛；应用必须明确说明这一点，不能宣称获得 OS sandbox 保护。

### 3.3 明确不做

- 数据库、云同步、账户、网络 API、遥测或后台服务
- Home/Dashboard、Settings 页面、Pin/Favorite、进度管理
- AI 生成、摘要、重写、评价或外部语料
- 多层文件夹、别名、符号链接资产、外部 `/Volumes` Vault
- 文件夹手工排序、Finder 全功能复制、跨目录剪贴板、文件监听器
- Flashcard 快捷键自定义、完成状态或独立 Flashcard 文件
- 插件架构、Repository/Service 接口层、事件总线、事务框架

## 4. 约束与质量属性

优先级从高到低：

| 属性 | Road v0.3 判定标准 | 取舍 |
| --- | --- | --- |
| 数据安全 | 不在白名单外写入；不静默覆盖外部修改；永久删除只处理明确文件 | 拒绝一部分 Finder 自由度 |
| 本地持久性 | Paper Markdown 是唯一作者事实；index 与设备状态可删除重建 | 接受线性扫描和简单 JSON |
| 可解释性 | 当前 Vault、Paper 所在文件夹、失败项和恢复结果都可见 | UI 会比 v0.2 多少量状态提示 |
| 作者控制 | 合并、删除、迁移和 Vault 切换都有明确确认与保留路径 | 不做自动冲突合并 |
| 可维护性 | 保持 app/core 两层；无新增 runtime dependency；路径规则集中一处 | 不抽象成通用文件管理框架 |
| 流程速度 | Paper 可直接检索、分组、选择 Flashcard 和跳页 | 不为未知规模做增量数据库索引 |
| 可访问性 | 所有拖放操作都有菜单等价路径；焦点与键盘可完成核心动作 | 不复制 Finder 的全部快捷键 |

性能只做有记录的探针，不先建缓存体系：使用 1,000 个合成 Paper 测量 index rebuild、Library 打开与搜索；若实际体验出现可重复阻塞，再按测量结果优化。

## 5. 实施前后架构比对

### 5.1 不变的系统边界

```text
Author
  → keikeu_app / Flet UI
  → keikeu_core / pure Python
  → author-owned Markdown + rebuildable JSON
  → OS / Finder / external editor
```

没有新增进程、服务、数据库或网络边界。

### 5.2 Component 级比对

| 责任 | 实施前（Road v0.2） | 实施后（Road v0.3） | 评判 |
| --- | --- | --- | --- |
| Domain model | `Paper.highlights: list[str]`；无显示名称 | `Paper.display_name`；`Highlight(display_name, content)` | 必需的数据结构升级 |
| Markdown | 只读写 schema v2；路径固定在 `cache/<code>.md` | 读 v2/v3，写 v3；只负责序列化，不决定文件夹 | 保住单一 I/O 所有者 |
| Paper addressing | code 同时是标识和路径定位 | code 只做不可变标识；页面传递 vault-relative path | 消除文件夹后的路径重复假设 |
| Vault | 只接受直接 `cache/*.md` 与平铺 Trash | 统一路径白名单、一层枚举、文件夹、逐文件 move/restore/delete | 路径与破坏性操作集中化 |
| Index | `cache/*.md` 线性重建；code/Summary/Tags | 一层目录线性重建；加入名称、Highlight 名称和 folder | 继续是可删除 read model |
| Library UI | 平铺结果 + 恢复区 | 侧栏文件夹、范围搜索、排序、选择、批量操作和固定 Trash | UI 复杂度只留在 app 层 |
| Flashcard | 通过 code 猜固定路径；持久化最后位置 | 使用 index path；每次 page 1；Paper 选择与页码跳转 | 删除不再需要的状态 |
| Device state | `paper.code → card_index` | 仅保留每日启动卡日期 | 状态减少而不是扩张 |
| Config | 接受任意用户输入路径 | Home 子树白名单；验证成功后原子切换 | 安全边界硬化 |

### 5.3 根因接缝

实施前，固定路径假设分散在：

- `markdown_io._paper_path()`
- `markdown_io.next_paper_code()`
- `indexer.rebuild_index()`
- `vault._direct_asset_path()`
- `flashcard_page._paper_path()`

Road v0.3 不在五处各补一个 `glob`。`vault.py` 提供经过验证的 active/trash Paper 枚举与相对路径解析；其余模块只消费结果。这样文件夹、编号扫描、Trash 和路径白名单共享同一事实。

### 5.4 明确拒绝的候选架构

| 候选 | 拒绝原因 | 何时才重审 |
| --- | --- | --- |
| SQLite / ORM | Markdown 已是事实源；引入双写与迁移 | 线性 index 在真实规模持续无法满足检索 |
| Repository/Service 层 | 当前只有文件系统一种实现；会产生单实现接口 | 出现第二个真实存储后端且已获产品批准 |
| 文件监听器 / `watchdog` | 新依赖、并发和 provider 语义复杂；Refresh 足够 | 明确观察到外部编辑后的刷新成本阻塞主流程 |
| 事务/事件框架 | 单机逐文件操作已有清晰失败边界 | 出现跨进程写入或必须原子完成的大批事务 |
| Finder clone | 产品只需要 Paper 组织，不需要通用文件管理器 | 用户需求已超出 Paper 组织且另立 Road |

## 6. Durable data contract

### 6.1 Paper schema v3

```markdown
---
type: paper
schema_version: 3
code: K-20260721-001
display_name: 雪中的无人车
created: 2026-07-21T10:30:00
updated: 2026-07-21T10:45:00
---

# K-20260721-001

## 初稿副本

[first saved Summary]

## Summary

[current Summary]

## Highlights

1. 名称：车轮痕迹
   内容：
   旧打火机被塞回手里。
   谁也没有解释。

2. 名称：
   内容：
   [unnamed content]

## Tags

- [tag]
```

Rules：

- `code` 继续使用 `K-YYYYMMDD-NNN`，生成后不可修改。
- `display_name` 可选；外层空白去除，空白为 `None`；非空值必须是单行、不得含控制字符，上限 200 个 Unicode code point；允许 Unicode、emoji、标点和重复。
- 名称保存作者 trim 后原文；排序和相等比较只使用 `unicodedata.normalize("NFC", value).casefold()`，不静默规范化磁盘文字。
- `display_name` 为 `None` 时不写该 frontmatter key；读取缺失 key 得到 `None`。
- 系统文件名始终是 `<code>.md`；Markdown 一级标题继续使用 code，便于手工识别。
- `Highlight.content` required；保存时空白 content 删除整项，包括已填写的名称。
- `Highlight.display_name` 完整复用 Paper 名称规则。
- Highlight 没有永久 ID；`Highlight n` 是当前位置标签，排序后重新编号。
- 每个 Highlight 以顶层编号行开始；renderer 给 `内容：` 后的每一行增加一层结构缩进，reader 只移除这层缩进。内容自身的换行、空行和编号文本不得被误判为下一项。
- schema v2 Paper 继续可读，读取时转换为无名称 Highlight；下一次成功保存写成 schema v3。
- 混合 v2/v3 Vault 是受支持的兼容状态，不进行全 Vault 自动重写。
- 未知 frontmatter 在更新既有 Paper 时尽力保留；复制分支只复制已定义的创作字段。

### 6.2 Vault layout

```text
vault/
  cache/
    K-20260721-001.md             # 未归类
    夜行列车/
      K-20260718-004.md
  .trash/
    cache/
      K-20260710-002.md           # 原本未归类
      夜行列车/
        K-20260717-002.md
  keikeu_index.json               # disposable

device-local, under current user's Home:
  config                           # selected Vault
  state                            # last_daily_card_date only
```

Folder rules：

- 仅允许 `cache/` 下零层或一层 Paper；更深目录和 symlink 进入 error 状态，keikeu 不写入。
- 名称 trim 后为单行 1–200 个 Unicode code point；禁止 `/`、`:`、控制字符、`.`、`..`、前导 `.`，以及 NFC+casefold 后等于 `cache`、`.trash`、`keikeu_index.json`、`全部 Paper`、`未归类` 或 `Trash` 的名称。
- 比较重名与排序时使用 `unicodedata.normalize("NFC", value).casefold()`；磁盘保存作者输入的 trim 后原文，不静默改写名称。
- “全部 Paper”和“未归类”是 UI scope，不是磁盘目录。
- 文件夹可为空；删除空文件夹也进入 Trash 并可恢复。
- Paper code 在 active 与 Trash 的全部支持路径中全局唯一；新编号扫描两边。
- 外部或旧版本留下的重复 code 不自动改写：全部保留并显示 error，涉及冲突资产的 move/restore/delete/branch 等 mutation 在作者处理前阻断。

### 6.3 Index v3

Index entry 至少包含：

```text
code, display_name, path, folder,
summary, tags, highlight_names,
created, updated
```

- `path` 是 Vault-relative path；GUI 通过它打开 Paper。
- 名称排序使用 `display_name or code` 的 NFC+casefold key，再以 code 和 path 作稳定 tie-breaker。
- 搜索字段：Paper 名称、code、Summary、Tags、Highlight 名称。
- 不索引 Highlight content 或初稿副本。
- 单 Paper 损坏、非法深层路径和 symlink 进入 `errors[]`，不隐藏其余 Paper。
- Index 丢失或损坏仍从 Markdown 重建。

### 6.4 Device state

- 删除所有 Flashcard position 读写与 code rename state migration。
- 设备状态只记录本地日期 `last_daily_card_date`。
- 状态缺失或损坏视为“今天尚未显示”；不得影响 Vault 或 Paper。
- 状态文件继续原子替换。

## 7. Interaction contract

### 7.1 Daily start card

- 每台设备、按本地日历日期、当日首次启动显示一次独立启动卡。
- 3 秒后自动进入空白新 Paper；点击“开始写”或按 Enter 立即进入。
- 当日再次启动直接进入空白新 Paper。
- 测试文案：

  > 玛格丽特·阿特伍德（意译）  
  > 写作像走迷宫。撞墙时，退回走错的路口，换一条路。

- Road v0.3 只内置这一条文案；无列表轮换、网络、AI、设置或用户自定义。
- 判定当日尚未显示后，先原子写入当天本地日期，再显示卡片；这样崩溃或快速重启不会重复出现。

### 7.2 Paper editor

- 显示只读系统编号；移除 Road v0.2 的 code rename 入口。
- Paper 名称输入位于“保存”操作上方；空白时 Library 显示 code。
- Highlight row 包含可选“命名”和 required“内容”；外框高度随文本框。
- 每行显示 drag handle；同一行的键盘可达菜单提供“上移/下移”完全等价路径，不显示“顺序已更新”提示。
- 保存把空 content 的 Highlight 当作删除。
- `Cmd+S` 保存；外部移动、删除或修改继续阻止覆盖并保留表单输入。

### 7.3 Library and folders

- 现有全局侧栏扩展为：主导航 + `全部 Paper` + `未归类` + 一层文件夹 + `新建文件夹`。
- 文件夹按名称排序；前两项固定。
- 主区域继续使用高密度 Paper 行，不改为 Dashboard 卡片。
- 搜索限制在当前 scope；“全部 Paper”跨全部文件夹。
- 默认“最近更新”；可切换按名称、创建时间新→旧、创建时间旧→新。
- Paper 支持单个拖放到文件夹；`移动到…` 菜单是同等、可键盘完成的入口。
- 勾选多个 Paper 后可批量移动；拖放仍一次移动一个。
- 提供“全选当前”与“取消全选”。切换 scope 会清空选择并显示 2 秒行内提醒：`已取消选择的 n 个 Paper`。
- 文件夹 `•••` 菜单提供重命名和移至 Trash；右键打开同一菜单，但不是唯一入口。
- 重命名为既有名称时先确认再合并；无冲突 Paper 成功移动，冲突项留在原文件夹并逐项报告。
- Finder 中的外部变更在进入 Library 或显式 Refresh 时重建 index；不运行后台 watcher。

### 7.4 Copy branch

- 入口只在 Library Paper 行的 `•••` / 同一右键菜单。
- 读取磁盘中已保存的版本；不复制编辑页未保存状态。
- 副本留在原文件夹，生成新 code、created、updated。
- 复制 Paper display name、当前 Summary、Highlights 与 Tags；新 Paper 的初稿副本等于复制时 Summary。
- 有名称时副本名称为 `原名称 · 分支`；原 Paper 名称为 `None` 时，副本也为 `None`。
- 名称允许重复，code 负责区分；不生成“分支 2”。

### 7.5 Flashcard

- 仍是 `[current Summary] + Highlights` 的只读投影；Summary 是第 1 页，Highlights 是第 2..N 页。
- 列表点击选择；单卡页左右方向键切换，不循环。
- 第一/最后一张再次移动时显示 2 秒非模态提示，不抢焦点。
- 顶部 Paper selector 显示 `display_name (code)`，无名称时显示 code；切换 Paper 从第 1 页开始。
- 每次从 Library 打开、跨 Paper、重新启动都从第 1 页开始，不保存位置。
- 提供 `第 [数字] 页` + `跳转`；只接受 `1..N` 整数，非法输入不移动并显示范围。
- Highlight 有名称时用其名称作为卡片标题；无名称时显示当前位置 `Highlight n`。
- 不增加其它快捷键或快捷键自定义。

### 7.6 Trash and permanent delete

- Trash 固定在顶栏并显示数量，包括 0。
- Trash 中的文件夹可展开；可整体恢复/永久删除，也可单独处理 Paper。
- 整体恢复遇到同名 active 文件夹时自动合并；非冲突项成功，冲突项留在 Trash 并逐项报告。
- 单独恢复文件夹内 Paper 时回到原文件夹；原文件夹不存在则重建，已存在则合并。
- active code 冲突时阻止恢复；不改历史 code，不提供“新 code”恢复。
- 永久删除 1–3 个 Paper：确认窗口；4 个以上：必须输入 trim 后完全等于小写 `execute`。
- 文件夹永久删除门槛按其中 Paper 数；空文件夹只有确认窗口。
- 单 Paper 确认显示 display name + code，并说明不可恢复；危险按钮不是默认 Enter 动作。
- “清空 Trash”按全部实际 Paper 数使用同一门槛。
- 永久删除只接受已解析、已验证的明确 `.md` 路径列表；逐个 `unlink` 后只对确认为空的目录调用 `rmdir`。

### 7.7 Vault switching and keyboard

- Library header 始终显示当前 Vault path 与“更换 Vault…”；不创建 Settings 页面。
- 有效 Vault：显示 Paper 数量预览后确认；空目录：询问是否初始化；非空非 Vault：拒绝且不修改。
- `Esc` 关闭 dialog/menu；标准 Tab/Shift+Tab/Enter/Space 保持可用；`Cmd+F` 聚焦 Library 搜索。

## 8. Path and failure contract

### 8.1 Allowed writes

- Durable Vault、config、device state 和交互式 smoke artifacts 必须位于当前用户 `Path.home()` 或后代路径。
- `/Applications/keikeu.app` 只作为安装/运行包读取，不保存 Vault 或用户状态。
- 禁止 durable writes：`/tmp`、`/private/tmp`、`/var/folders`、其他用户 Home、app bundle、`/Volumes`。
- 使用 `Path.resolve()` 后检查相对关系，防止 symlink 逃逸。
- 自动化测试 basetemp 放在仓库已忽略的 `tests/test-vault/`；macOS smoke 放在可见的 `~/Documents/keikeu-test-vaults/<run-id>`，记录准确路径并清理。

### 8.2 Existing unsafe Vault

若配置指向白名单外：

1. 立即停止对该 Vault 的写入，先以只读方式分类来源和全部目录项；不跟随或解引 symlink。
2. 任何 symlink 或不支持的 special entry 都报错并中止搬迁，不改来源与 config。
3. 明确显示当前路径和原因；用户选择 Home 下全新安全位置。
4. 仅复制普通目录和 regular files，比对来源与副本的 regular-file manifest 和逐文件 bytes。
5. v2/v3 副本额外逐 Paper 解析并重建/验证 index；全部成功后才原子更新 config。
6. v0.1 副本不得先按 v2/v3 Paper 解析；在副本上运行现有 v0.1 只读 preflight/manifest validation，通过后原子切换 config，再只对该安全副本进入现有显式 migration gate；取消或迁移失败仍选择未改写的安全副本。
7. 原 Vault 保留且永不写入或自动删除；任何搬迁或切换前验证失败都不更新 config。

### 8.3 Partial operations

- 批量 move、folder merge、folder restore 和 permanent delete 均报告每个失败项。
- 已成功项不回滚；失败项留在原位置。UI 不得宣称“全部成功”。
- 包含未知文件、深层目录或 symlink 的文件夹不能整体删除或合并；先报告并由作者在 Finder 中处理。
- 外部 provider conflict copy 是未知文件；不自动合并或改写。
- 外部或历史状态中的重复 code 全部保留并进入 errors；不得自动换号，涉及这些资产的 mutation 先阻断。
- 禁止 `rmtree` 适用于 active/Trash 与永久删除；keikeu 自己创建、与作者资产隔离且尚未切换为 active 的 migration staging 可在失败清理时递归删除。

## 9. Phase plan

每个 Phase 开始前应用 Git gate；在独立分支或明确接受的现有工作树上完成。每个 Phase 必须保持测试可运行，不提交半个 schema 或无法打开的 UI。

交付节奏采用开发者选择的 **B**：每个 Phase 通过本 Phase gate 与独立复核后形成一个 focused local commit；不得把后续 Phase 混入，不自动 push 或 tag。

### Phase 0 — Authority and fixtures

**目标**：把已冻结决策写进当前权威，消除 v0.2 与 v0.3 的主动冲突。

主要文件：

- `docs/SPEC.md`
- `docs/PROJECT.md`
- `docs/RULES.md`
- `docs/design/design.html`
- `docs/design/interaction.html`
- `docs/architecture/architecture.html`
- `docs/architecture/decisions/`
- `tests/fixtures/v03-vault/`
- `pyproject.toml`

步骤：

1. SPEC 升级 Paper/Highlight、folder、Flashcard、Trash、Vault 与 acceptance 契约。
2. 显式撤销 code rename、Flashcard position persistence、restore-with-new-code。
3. 写两个轻量 ADR：Home 写入白名单/App Sandbox 延后；Paper v3 + 一层真实文件夹。
4. architecture/design/interaction 在 Phase 0 改为明确标注的 **Road v0.3 target**；`PROJECT.md` 单独记录当前 runtime 仍为 v0.2 与下一收敛 gate。
5. 建立 v2/v3、folder、Trash、非法深层目录、运行时 symlink 和不安全路径模拟 fixture；冻结文件不被测试原地修改。
6. pytest 默认 basetemp 固定到已忽略的 `tests/test-vault/pytest`，所有自动测试写入仓库内合成区域。

Gate：权威无冲突、无 TBD；fixture validation、`scripts/check_docs.py` 与 `git diff --check` 通过；应用测试未因 docs-only authority 更新而冒充运行时 v0.3 证据。

### Phase 1 — Path safety and Vault switch

**目标**：先关闭 `/private/tmp` 类不安全写入，再继续任何功能扩展。

主要文件：

- `src/keikeu_core/vault.py`
- `src/keikeu_app/main.py`
- `src/keikeu_app/pages/library_page.py`
- `tests/test_vault.py`
- `tests/test_app_pages.py`

最小实现：

1. 在 `vault.py` 集中 Home 白名单、symlink-resolved path 和 folder-name 验证。
2. `set_vault()` 使用临时文件 + `os.replace()`；验证完成前不改 config。
3. 增加 valid / empty / non-empty non-Vault 三种切换路径。
4. 增加 unsafe Vault 的 read-only classify → no-follow regular-file copy/byte verify → format-specific validate → atomic switch；v2/v3 重建 index，v0.1 只在安全副本上跑现有 preflight 与 migration gate。
5. UI 公告真实保护边界，不声称 Apple App Sandbox 已启用。

Gate：所有白名单与迁移失败测试证明无外部写入、无配置提前切换；复制 Vault smoke 只使用副本。

**完成证据（2026-07-22）**：Home 白名单、全路径 no-follow、原子 config 切换、unsafe Vault 复制验证、v0.1 安全副本迁移入口和 App Sandbox 边界公告已接通；203 项自动测试、compile、文档检查与 diff 检查通过。当前 relocation 支持 v0.1/v2；v3 要等 Phase 2 reader/index 升级后启用。原子目录交换使用 Darwin/Linux 原生能力，不支持的平台在破坏性 mutation 前失败。`architecture.html` 继续保留 Road v0.3 target 标记，按已批准 option A 在 Phase 7 依据最终代码校准。

### Phase 2 — Paper v3 naming vertical slice

**目标**：让 schema v2/v3 共存可读，并完整接通 Paper/Highlight 名称。

主要文件：

- `src/keikeu_core/models.py`
- `src/keikeu_core/markdown_io.py`
- `src/keikeu_core/indexer.py`
- `src/keikeu_core/migration_v01.py`
- `src/keikeu_app/pages/paper_page.py`
- `src/keikeu_app/pages/flashcard_page.py`
- `tests/test_models.py`
- `tests/test_markdown_io.py`
- `tests/test_indexer.py`
- `tests/test_migration_v01.py`
- `tests/test_app_pages.py`

最小实现：

1. 新增一个 `Highlight` dataclass；不建立 ID、基类或通用 content hierarchy。
2. `Paper` 增加 optional `display_name` 与 `list[Highlight]`。
3. Reader 接受 schema 2/3；renderer 只写 schema 3。
4. Index 增加 Paper/Highlight 名称；搜索不加入 Highlight content。
5. v0.1 migration 与所有 index 生产者同步构造 v3 Highlight/index shape，不能留下 `list[str]` 或 index v2 常量。
6. Paper UI 增加名称与 paired Highlight fields；删除 code rename UI。
7. Flashcard 投影适配 `Highlight.content` 与名称标题，仍暂时保持现有导航可用。

Gate：v2→read→save v3、200 字符边界、Unicode、重复名称、多行内容、空内容删除、未知 frontmatter、CJK round trip 全部有直接测试。

**完成证据（2026-07-22）**：Paper/Highlight 名称、v2/v3 双读与 v3 单写、index v3、v0.1→Paper v3 migration、不可变 code UI 与 Flashcard 名称投影已接通；unsafe v3 relocation 也已解除 Phase 1 的临时阻断。独立复核额外发现并修复未知 frontmatter 反斜杠静默丢失和空白 legacy notes 阻断迁移两项问题。最终 212 项自动测试、compile、文档检查与 diff 检查通过；未运行手动 Flet smoke。`architecture.html` 继续保留 Road v0.3 target 标记，等待 Phase 7 按最终代码校准。

### Phase 3 — Folder-aware filesystem core

**目标**：在不先堆 UI 的情况下建立一层真实目录与全局 code 规则。

主要文件：

- `src/keikeu_core/vault.py`
- `src/keikeu_core/markdown_io.py`
- `src/keikeu_core/indexer.py`
- `tests/test_vault.py`
- `tests/test_markdown_io.py`
- `tests/test_indexer.py`

最小实现：

1. `vault.py` 提供 active/trash Paper 的受限枚举与路径解析。
2. `markdown_io` 接受已验证 destination path，不再决定 folder；序列化责任不变。
3. `next_paper_code()` 检查 active + Trash 全部支持路径。
4. Index entry 保存 vault-relative path/folder；非法深层和 symlink 进入 errors。
5. `AppContext.open_flashcards`、Paper/Library callers 与 Flashcard page 都改传已验证的 vault-relative path；不得通过 code 猜路径。

Gate：root/folder/trash 全局 code、外部移动、深层目录、symlink、损坏 Paper 和 deterministic index 有直接测试。

**完成证据（2026-07-22）**：`vault.py` 已统一一层 active/Trash 枚举、受限路径解析与跨支持路径编号分配；Markdown 写入接收准确 destination，index 保存准确相对 path/folder，App 页面之间只传经过验证的 vault-relative path。外部移动、深层目录、symlink、损坏 Paper、legacy/provider 重复 code、普通目录替换与并发创建回滚均有直接回归。最终 229 项自动测试、compile、文档检查与 diff 检查通过；未运行手动 Flet smoke。`architecture.html` 继续保留 Road v0.3 target 标记，等待 Phase 7 按最终代码校准。

### Phase 4 — Folder, Trash and branch operations

**目标**：先把所有破坏性与批量操作做成可单测 core API。

主要文件：

- `src/keikeu_core/vault.py`
- `src/keikeu_core/markdown_io.py`
- `tests/test_vault.py`
- `tests/test_markdown_io.py`

最小实现：

1. create/rename/merge folder；move one/many Paper；结果逐项记录。
2. soft-delete Paper/folder；restore whole/one；同名 folder merge；active code conflict block。
3. permanent-delete 明确 path list；禁止 `rmtree` 与 glob-delete。
4. branch copy 使用新 code/timestamps/current Summary，不复制历史系统字段。
5. 删除仅为 code rename 服务的 core 路径；保留 v0.1 migration 真正仍使用的 helper。

Gate：注入单项 move/unlink 失败，证明其余项结果准确、失败项保留、未知文件不受影响。

**完成证据（2026-07-22）**：一层 folder create/rename/merge、单个与批量 move、Paper/folder soft-delete 与 restore、明确 Paper path 永久删除、空 Trash folder 永久删除，以及保持原文件夹的新 code branch copy 已接通。移动与删除使用原子 no-replace rename 或隔离后验证，目录批量操作持续绑定 source/destination descriptor；未知项先阻断整文件夹结构操作，损坏 Paper 逐项失败且其余项继续。NFC+casefold 重名、最后一步替换、目录 replacement、单项失败、历史 code 不改写与 branch 字段边界均有直接回归。独立复核通过；最终 247 项自动测试、compile、文档检查与 diff 检查通过，未运行手动 Flet smoke。CP3 完成；`architecture.html` 继续保留 Road v0.3 target 标记，等待 Phase 7 按最终代码校准。

### Phase 5 — Paper and Library interaction

**目标**：接通已确认视觉布局与安全操作，不建立全局状态框架。

主要文件：

- `src/keikeu_app/main.py`
- `src/keikeu_app/pages/paper_page.py`
- `src/keikeu_app/pages/library_page.py`
- `src/keikeu_app/widgets/`（只有第二个真实复用点才增加 helper）
- `tests/test_app_pages.py`

最小实现：

1. 将固定 `NavigationRail` 改为同一自定义侧栏，加入 Library folder scope；状态保持在现有 builder closure。
2. 高密度 Paper rows、scope search、sort、全选/取消、切换清选提示。
3. 使用当前 Flet 已安装的 `Draggable` / `DragTarget`；菜单是可访问的可靠路径，不加 drag dependency。
4. 接通 folder menus、batch move、branch copy、固定 Trash、永久删除 threshold。
5. Highlight 保留 drag handle，并在键盘可达 row menu 提供上移/下移；移除 reorder Toast。

Gate：builder tests 覆盖默认、empty、selection、merge、partial error、confirmation threshold 与 focus；macOS Flet smoke 验证实际拖放和菜单。

**完成证据（2026-07-22）**：固定 `NavigationRail` 已替换为自定义全局侧栏并挂载全部/未归类/一层文件夹/Trash scope；当前 scope 搜索与排序、选择/批量移动、原生拖放与菜单等价路径、文件夹菜单与右键、同目录分支、可展开 Trash、永久删除门槛，以及 Highlight 拖放/键盘菜单已接通。macOS synthetic Flet smoke 在隔离 Vault 中实际完成菜单移动与 Paper 拖放，磁盘路径核对正确；后续复验发现并修复右键 `ContextMenu` 与 drop 的事件冲突，但最终重启时 Flet 客户端只有进程、没有可连接窗口，未伪报重复 smoke 通过。最终代码由 265 项全量自动测试、156 项独立聚焦复核、compile、文档与 diff 检查覆盖，复核未发现 P0/P1/P2；完整候选原生 smoke 仍由 Phase 7 重跑。`architecture.html` 按批准的 option A 继续等待 Phase 7 依据最终代码校准。

### Phase 6 — Flashcard, daily card and keyboard

**目标**：完成检索后的聚焦流，并删除不再需要的持久状态。

主要文件：

- `src/keikeu_app/pages/flashcard_page.py`
- `src/keikeu_app/local_state.py`
- `src/keikeu_app/main.py`
- `tests/test_app_pages.py`
- `tests/test_local_state.py`

最小实现：

1. 删除 card position APIs 与测试；每次 index = 0。
2. Paper selector、卡片列表点击、左右键、边界提示和页码跳转。
3. local state 只保存 daily local date；实现 3 秒卡与 Enter。
4. 接通 `Cmd+S`、`Cmd+F`、`Esc` 和标准焦点行为；不建 shortcut registry。

Gate：无位置 persistence、跨 Paper reset、非法跳页、same-day once、next-day replay、corrupt state 与键盘/focus 有直接测试和 macOS smoke。

**完成证据（2026-07-22）**：旧 Flashcard position API、code 迁移与读写已删除；Flashcard 通过重建后的准确 index path 提供 Paper selector、卡片列表、无 wrap 左右键、页码跳转与短时边界提示，每次打开和跨 Paper 切换都从第 1 页开始。设备状态只原子保存最后展示的本地日期，缺失、损坏和旧 position state 都按今日未展示处理；启动卡在记录日期后显示，并由 3 秒、Enter 或“开始写”幂等进入空白 Paper。`Cmd+S`、`Cmd+F` 与 `Esc` 使用页面局部 handler，没有 shortcut registry。macOS synthetic Flet smoke 实际验证了 3 秒进入、date-only state、Paper 选择/复位、有效与非法跳页、方向键、边界不循环和 2 秒提示清除；Enter、same-day once、next-day replay 与 corrupt state 由直接测试覆盖。最终 274 项全量自动测试、compile、文档与 diff 检查通过。CP4 完成；`architecture.html` 仍未提前修改，按批准的 option A 留给 Phase 7 依据最终代码校准。

### Phase 7 — Documentation, smoke and acceptance

**目标**：把“代码完成”“macOS workflow 完成”“产品接受”分开证明。

步骤：

1. 将 Phase 0 的 target `docs/architecture/architecture.html` 按已验证代码重新校准为实际 Road v0.3 模块和 lifecycle，移除 target/current 过渡声明。
2. 更新 design/interaction 页面中的最终状态；不把临时 prototype 当 authority。
3. 使用可见 synthetic Vault 完成新建/命名/文件夹/复制/Flashcard/Trash/Vault switch 全流。
4. 使用复制的真实 Vault 验证 v2 lazy upgrade、Finder 外部移动和 unsafe Vault relocation；永不首测唯一真实 Vault。
5. 跑全测、compile、docs、diff checks；记录实际命令与结果。
6. 开始 Road v0.3 产品验收；tag/归档仍由开发者单独决定。

Gate：没有 P0/P1；所有高风险文件操作有证据；未验证项明确列出。

## 10. Checkpoints

| Checkpoint | 含义 | 当前状态 |
| --- | --- | --- |
| CP0 | 范围冻结、Planbook approved | **Complete** |
| CP1 | Authority + path safety 合入 | **Complete** |
| CP2 | Paper v3 与 mixed-schema round trip | **Complete** |
| CP3 | Folder/Trash core 完成，UI 尚未成为证据 | Complete |
| CP4 | Paper/Library/Flashcard UI engineering complete | **Complete** |
| CP5 | macOS candidate smoke complete | Pending |
| CP6 | Road v0.3 product accepted；是否 tag 另行决定 | Pending |

任何 checkpoint 都不能用旧测试数字、prototype 或上一 Road 的 smoke 代替当前证据。

## 11. Verification matrix

| Area | Minimum automated evidence | Manual evidence |
| --- | --- | --- |
| Names/schema | v2/v3 round trip、200 char、Unicode、None、duplicates | Markdown 在普通编辑器中可读可修 |
| Paths | Home allow、outside reject、symlink escape、config atomic | 显示真实 Vault path 与边界公告 |
| Folders | one-level enumerate、merge、global code、deep error | Finder 创建/rename/move 后 Refresh |
| Batch/Trash | partial failure、count threshold、explicit paths | 1–3 与 4+ dialog、folder expand |
| Flashcard | page 1 reset、selector、jump、edge | arrows、focus、no wrap |
| Daily state | once/day、next day、corrupt/missing | relaunch twice same local day |
| External change | edit/delete/move refusal | external editor + Finder smoke |
| Full repo | pytest、compileall、docs、diff | macOS candidate launch/relaunch |

Candidate commands：

```bash
.venv/bin/python -m pytest --basetemp=tests/test-vault/pytest
.venv/bin/python -m compileall -q src
.venv/bin/python scripts/check_docs.py
git diff --check
flet run src/keikeu_app/main.py
```

## 12. Development advice

已验证的 installed Flet 0.85.3 路径限于 `Draggable` / `DragTarget`、`ContextMenu` / `PopupMenuButton`、`Page.on_keyboard_event`、`Page.run_task` 与 `TextField.on_submit`。不使用不存在的 `ft.Timer`，不加 drag dependency、shortcut registry 或新状态框架。

1. **先修路径，再碰文件夹。** 当前最大风险不是 UI，而是五处固定路径假设和任意 Vault config；Phase 1/3 不可倒序。
2. **传 path，不重新找 code。** Library/index 已知道准确文件；页面之间传相对 path，避免全盘扫描和错误命中。
3. **混合 schema 要被设计，不要偷偷全量迁移。** v2 reader + v3 writer 足够；任何批量改写都另立迁移契约。
4. **拖放不是安全路径。** 使用 Flet 原生 drag；菜单必须完成同一操作并承担 keyboard/accessibility acceptance。
5. **批量操作不要伪事务。** 本地文件系统没有跨文件原子事务；逐项成功、逐项报告比手写 rollback 更可靠。
6. **删除旧状态。** Flashcard position、code rename UI 与相应 state migration 在新规则下没有存在理由。
7. **不监听文件系统。** 进入 Library 与显式 Refresh 重建 index；真实延迟证明不足前不加 watcher。
8. **不为目录写通用框架。** 一层 `Path` + stdlib 已覆盖；多层目录若有真实需求再设计。
9. **先在 copied/synthetic Vault 失败。** 删除、合并、恢复、迁移和 provider 场景禁止拿唯一真实 Vault 首测。
10. **每个 Phase 留一个可解释 diff。** 数据模型、路径安全、破坏性操作和 UI 不混成一个不可 review 的 mega-commit。

## 13. Known risks and revisit triggers

| Risk | Current handling | Revisit trigger |
| --- | --- | --- |
| Flet drag 在 macOS 行为不稳定 | 菜单是完整 fallback；smoke 实测 | drag 经常失败或无障碍不可用 |
| 线性 index rebuild 变慢 | 继续简单扫描；1,000 Paper probe | 真实 Vault 可重复阻塞主流程 |
| Provider 同步时移动部分失败 | 逐项结果、保留原件、不自动合并 | 有稳定复现且 OS/provider 文档给出可控语义 |
| Mixed v2/v3 长期存在 | reader 双版本，writer 单版本 | 兼容代码成为维护瓶颈时另立迁移 Road |
| Apple App Sandbox 尚未启用 | 白名单 + 公告 + app-level guard | 正式分发、安全审查或平台要求变化 |
| 一层目录不足 | 深层只报错不写入 | 真实工作流反复需要层级而非偏好 |
| Home-only 阻止外部卷 | 明确不支持 | 用户有必要的外置存储工作流并愿意接受权限设计 |

## 14. Approved review decisions

2026-07-22，开发者批准本 Planbook 与以下执行选择：

- architecture option A：Phase 0 先写 Road v0.3 target，并在 Road 完成后按实际实现再校准；
- Highlight ordering option A：drag handle + 键盘可达的上移/下移菜单，无 reorder toast；
- delivery cadence B：每个 verified Phase 一个 focused local commit，不自动 push/tag；
- legacy duplicate code 保留、报告并阻断 mutation，不自动改号；以及
- unsafe Vault 先只读分类，不跟随 symlink，仅将普通目录/regular files byte-copy/verify 到 Home；v2/v3 再解析并重建 index，v0.1 改走安全副本上的现有 preflight 与 migration gate，不写原件也不以真实唯一 Vault 首测。

Phase 0 权威/fixture 到 Phase 6 Flashcard/daily card/keyboard engineering 已完成，CP4 关闭；下一步是 Phase 7 按最终代码校准三张 HTML map、完成 macOS candidate workflow，并将工程、平台 smoke 与产品验收分开记录。
