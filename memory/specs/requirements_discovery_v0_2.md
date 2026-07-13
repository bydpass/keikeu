# keikeu 新需求搜索与 Road v0.2 候选池

日期：2026-07-10  
状态：需求发现已收束；保留为历史证据，不再作为实现规格  
研究对象：同人创作者从零碎灵感到大纲、正文交接的个人工作流  
本地基线：macOS pre-alpha，Road v0.1 已完成；唯一实际用户已提交 O-01～O-05。

## 0. 2026-07-13 产品收束

后续 brainstorming 重新验证了目标用户、内容模型和大纲必要性。本文件中的候选路线已由以下活动文档取代：

- [`../../appdesign.md`](../../appdesign.md)：当前产品事实来源。
- [`spec_road_v0_2.md`](spec_road_v0_2.md)：macOS Paper–Flashcard Core 行为规格。
- [`planbook_road_v0_2.md`](planbook_road_v0_2.md)：Road v0.2 执行顺序。
- [`road_pre_advance.md`](road_pre_advance.md)：可选 Outline 的后置候选池。

新决议：

1. 目标用户收窄为即兴型为主、混合型为辅的私人单作者同人小说作者。
2. one-shot 与短中篇优先；长篇能力后置。
3. 一张 Paper 代表一次准备写成正文的作品单元。
4. 主内容模型为必填 Summary、推荐 Highlights、推荐 Tags；首次保存冻结初稿副本。
5. Flashcard 第一张是 Summary，后续一条 Highlight 对应一张卡，并默认记住每设备上次位置。
6. Outline 不再是强制终点，移入 Pre-Advance。
7. v0.1 Cache 迁移为 Paper v2；旧 Outline 完整备份后从活动 vault 销毁。
8. Road v0.2 从 macOS 开始；三设备未来通过 iCloud Drive 等第三方文件服务传递 vault，keikeu 不自建云服务。

因此，下文 R-01～R-06 和原“推荐路线”只用于追溯当时证据，不得直接转成实施任务。特别是旧 `cache → outline`、iOS-first v0.2 和 CP 专用检索结论已被新产品模型覆盖。

## 1. 研究边界

本轮只寻找与 keikeu 主链路直接相关的重复摩擦：

```text
捕获灵感 → 整理与检索 → 形成大纲 → 交接到正式写作
```

不把竞品功能数量当作需求证据。以下方向预先排除：AI 代写、云同步、账号、社区、实时协作、复杂 wiki、知识图谱和完整长篇写作套件。

证据分为：

- **用户事实**：当前唯一 pre-alpha 用户的实际问题，优先级最高。
- **公开讨论**：创作者对自己的真实工作方式与摩擦的描述。
- **官方事实**：发布平台明确写出的限制。
- **推断**：由多条证据共同指向、但仍需本地用户确认的候选需求。

## 2. 已确认事实

### 2.1 用户事实

当前唯一 pre-alpha 用户已经确认：

- Finder 外部删除或文件损坏后，Library 与磁盘事实不能可靠重新同步。
- 配方票需要条件显示：自定义结局、PA/PARO 细节只在对应选择时出现。
- `.trash` 虽然安全，但目前不可见、不可恢复，是一个黑箱。

这些问题已经记录在
[`Road v0.1 Issue 复盘`](9d033db326295874d1f32f23325e430e0461396d/issue_retrospective_v0_1.md)
的 O-01～O-05，应先于外部候选进入实施排序。

### 2.2 公开工作流证据

1. 创作者经常从混乱的片段、对白、场景和 trope 开始，再逐步拼成故事，而不是先写一份整齐大纲。
2. “废弃但未来可能复用的片段”通常被放入 scratchpad、随机场景文档或独立笔记。
3. 大纲不是一次性产物，而是持续增删、移动、拆分的活文档。
4. 作者常把某章需要的 outline 复制进正文文档，并在写完后逐条删除或消费这些提示。
5. 当点子达到几十或上百条时，作者会自行发明编号、标题层级、按 CP/人物分组和搜索代码。
6. 很多作者只想保持简单；有人明确表示，整理过程本身会分散写作注意力，复杂工具反而让混乱更严重。
7. 手机快速记录与跨设备访问被频繁提及，但不少人仍接受本地文件、普通文本和手工同步。
8. Beta 阅读主要依赖 Google Docs、Word 或文件往返，其核心价值是评论/修订协作，不是大纲管理。

### 2.3 官方平台事实

AO3 官方 FAQ 明确说明：未发布草稿会在创建一个月后删除，且编辑不会重置这一期限。因此 AO3 草稿不能被视为长期创作存储；keikeu 坚持本地资产和显式导出是正确方向。

## 3. 候选需求

### R-01 — CP 优先的 Library 检索

- **证据强度**：高
- **痛点**：资产变多后，只按标题和 cache status 搜索不够；当前用户无法预估触发条数，但明确表示找不到资产时会优先按 CP 查找，且 CP 需求远高于 fandom。
- **最小候选**：把 outline 的 CP 加入可重建索引，让现有搜索框同时匹配标题与 CP；fandom、characters 暂不增加独立筛选器。
- **为什么适合 keikeu**：复用已有字段，不引入标签系统、文件夹系统或外部数据库。
- **风险**：筛选 UI 容易膨胀；第一版应保持一个搜索框，不建立复杂查询语言。
- **建议**：需求已确认；实现前只需确定 cache 没有 CP 字段时的搜索展示规则。

### R-02 — Cache 的“待安置片段”子栏目

- **证据强度**：中高
- **痛点**：对白、未来场景和被删片段不一定属于当前流水账，但作者不愿丢弃。
- **用户决策**：不在 outline 内新增碎片区，而是在 cache 下新增一个子栏目。
- **最小候选**：为 cache 增加一个轻量类别，用来区分普通灵感与待安置对白/场景片段；仍使用 Markdown 文件和同一 Library，不建设 scene database 或卡片画布。
- **为什么适合 keikeu**：cache 本来就是临时收容层，新子栏目延伸现有职责，不污染 outline schema。
- **风险**：需要明确类别写入 frontmatter 的方式，并保证旧 cache 默认仍属于普通灵感。
- **建议**：需求已确认；子栏目名称与数据枚举留给 spec 定案。

### R-03 — 从大纲生成独立写作交接文件

- **证据强度**：中高
- **痛点**：作者经常手工复制 chapter/scene outline 到正文文档，再边写边消费提示。
- **用户工作流**：以流水账为骨架，沿着已有内容逐步扩写，而不是先拆成完整章节系统。
- **最小候选**：基于现有 outline 生成一份新的本地 Markdown 写作文件，保留来源链接，并把流水账作为扩写起点；不强制章节模型，不在本轮建设完整正文编辑器。
- **为什么适合 keikeu**：补齐“可继续写作”的最后一米，同时保持 Markdown 和作者控制。
- **风险**：容易滑向完整写作软件；必须把范围锁在“生成交接文件”，正文继续交给用户选择的编辑器。
- **建议**：工作流需求已确认；仍需在实现规格中决定写作文件是否进入 keikeu Library。

### R-04 — iOS 完整复刻稳定版 macOS 功能

- **证据强度**：中
- **用户决策**：手机端不做快速捕获 companion；在尚未引入 advanced 功能的阶段，应复刻稳定版 macOS 的完整功能。
- **最小候选**：cache、outline、Library、关系、导出、回收站与恢复等稳定核心能力在 iOS 可完成同等用户目标；系统打开、Finder 定位等平台动作允许使用 iOS 等价交互。
- **为什么适合 keikeu**：避免形成两个产品，也符合 macOS 先稳定、iOS 后复制的 release route。
- **风险**：iOS sandbox、文件选择/共享、vault 持久授权和 Flet 生命周期需要单独技术验证；“功能等价”不能理解为逐控件像素复刻。
- **建议**：需求已确认；Road v0.2 开始前先做技术 spike，但 spike 只决定实现方式，不再决定是否做完整对齐。

### R-05 — Vault 健康检查与可解释恢复

- **证据强度**：高，但与 O-01/O-02/O-05 相邻
- **痛点**：用户需要知道哪些文件健康、损坏、已外部删除或在回收站，而不是只看到一次刷新失败。
- **最小候选**：在完成 O-01/O-02/O-05 后，提供一次显式“检查本地资产”动作和结果摘要。
- **为什么适合 keikeu**：强化本地优先与资产可修复性。
- **风险**：不能自动修复或重写原文；第一版只检测、解释和提供安全动作。
- **建议**：作为稳定化工作的收尾，不单独扩张成维护中心。

### R-06 — AO3 友好交付

- **证据强度**：中低
- **痛点**：作者会在本地/Google Docs 写作后复制到 AO3，格式转换可能产生摩擦；AO3 草稿又不是可靠存储。
- **最小候选**：未来评估 HTML copy/export，而不是登录 AO3 或自动发布。
- **为什么暂缓**：keikeu 当前产物是大纲，不是最终正文；现在加入发布格式优化过早。
- **建议**：不进入下一开发周期。

## 4. 明确拒绝或暂缓

| 方向 | 判断 | 理由 |
|---|---|---|
| 复杂 wiki / 人物百科 | 拒绝 | 只在部分超长篇中有价值，会把 keikeu 变成 Obsidian 替代品 |
| 图谱、时间线、画布和 scene board | 暂缓 | 有需求证据，但复杂度高于当前唯一用户验证强度 |
| 内置正文编辑器 | 拒绝当前版本 | 会吞掉产品边界；R-03 的交接文件足够验证需求 |
| 内置 Beta 协作与评论 | 拒绝 | 需要账号、共享和权限系统；现有通用文档工具已经覆盖 |
| 云同步 | 拒绝 | 与当前隐私、本地优先和 pre-alpha 规模不符 |
| AI 大纲或续写 | 拒绝 | 违反作者控制与非必要 AI 原则 |
| 自动发布 AO3 | 拒绝 | appdesign 已明确不做自动发布，也会引入账户和网络风险 |

## 5. 推荐路线

### Road v0.1.1 — macOS 稳定化

1. O-01 + O-02：索引与磁盘事实重新同步，损坏文件逐项隔离。
2. O-05：回收站查看与恢复。
3. O-03 + O-04：配方票渐进披露。
4. R-05：在上述能力上增加简短的 vault 健康结果。

完成定义：外部删除、单文件损坏、软删除恢复均不会让用户离开 keikeu 才能理解或处理；配方票只在需要时显示附加输入。

### Road v0.2 — iOS 完整功能对齐

1. 冻结 v0.1.1 的稳定 macOS 行为作为 parity baseline。
2. 技术 spike：验证 iOS vault 目录、持久访问、文件导入/导出、分享和 Flet 页面生命周期。
3. 按用户目标对齐完整核心链路：cache → outline → Library → 导出/删除/恢复。
4. macOS 的 Finder/默认应用动作在 iOS 使用平台等价动作，不要求控件或系统命令一致。
5. iOS 验收通过前，不在任一端加入只存在单端的 advanced 功能，避免 parity baseline 持续移动。

完成定义：同一个本地 vault 工作流在 macOS 与 iOS 都能完成现阶段全部核心任务；平台差异不造成用户资产或功能缺口。

### Road v0.2.x — Mac-first 产品增强，再同步 iOS

平台对齐稳定后，产品候选顺序为：

1. R-01：CP 优先的 Library 检索。
2. R-02：Cache 的待安置片段子栏目。
3. R-03：以流水账为起点生成独立写作 Markdown。

每项仍按 macOS 先实现和验收，再同步到 iOS；不在两个平台同时探索尚未稳定的产品行为。

## 6. 本地验证结论

当前唯一用户已回答本轮四个验证问题：

1. 无法预估搜索失效的具体资产数量；查找优先级为 CP，显著高于 fandom。
2. 未安置对白或场景应进入新的 cache 子栏目。
3. 正文写作沿流水账逐步扩写。
4. iOS 应复刻当前稳定版 macOS 的完整功能，而不是只做快速捕获。

据此，R-01～R-04 均完成方向验证。下一步不再继续泛化搜索，而应先为 Road v0.1.1 和 iOS parity baseline 写正式行为规格。

## 7. 公开证据来源

- [Reddit：写作时如何组织 notes](https://www.reddit.com/r/FanFiction/comments/1d52oh2/how_do_you_format_your_notes_while_writing_a_fic/)
- [Reddit：如何组织大量 ideas documents](https://www.reddit.com/r/FanFiction/comments/1cqp0y8/how_do_you_organize_your_ideas_documents_if_you/)
- [Reddit：2025 年同人作者如何做 outline](https://www.reddit.com/r/FanFiction/comments/1pxbyd0/how_do_you_guys_outline_your_fics/)
- [Reddit：Google Docs 替代品、隐私与移动端讨论](https://www.reddit.com/r/FanFiction/comments/1tl2zma/google_docs_replacement/)
- [Reddit：Beta reader 的文档交接方式](https://www.reddit.com/r/FanFiction/comments/12eqwfp/how_does_beta_reader_work_exactly/)
- [AO3 官方 Posting and Editing FAQ](https://archiveofourown.gay/faq/posting-and-editing?language_id=en)
