> **ARCHIVED — READ ONLY.** Superseded by [`docs/SPEC.md`](../SPEC.md). Do not update or use for a cold start.

# keikeu APPDESIGN.md

> slogan：存住一瞬的灵光  
> 当前阶段：Road v0.2 · macOS Paper–Flashcard Core  
> 设计原则：本地优先、创作者资产优先、MVP 极简、无 AI 代写

---

## 0. 本文用途

本文是 keikeu 当前产品行为的唯一事实来源。

它定义目标用户、核心内容模型、页面职责、资产边界和 MVP 验收标准。Road 规格负责把这些要求拆成可执行阶段；历史规格只记录当时的实现，不再约束当前产品。

Road v0.1 的 `Cache → 配方票 → Outline` 是已归档旧模型。Road v0.2 以本文的 `Paper → Flashcard` 模型为准。

---

## 1. 产品定义

keikeu 是一个面向私人同人创作的本地优先写前整理与写作聚焦工具。

它服务的时刻是：

> 灵感已经出现，但作者还没有把它稳定地转成正文。

核心链路：

```text
已有的单件灵感
  ↓
纸片 Paper（轻量整理）
  ↓
Flashcard（有限上下文聚焦）
  ↓
外部正文编辑器
```

一句话定义：

> keikeu 把已有灵感整理成耐久的 Markdown 纸片，再把其中的写作锚点逐张举到作者眼前。

keikeu 不负责产生灵感，也不承载正式正文。

---

## 2. 目标用户与作品范围

### 2.1 核心交集

keikeu 优先服务：

```text
本地优先
∩ 单作者
∩ 私密创作
∩ 同人小说
∩ 即兴型为主、混合型为辅
∩ one-shot 与短中篇优先
```

### 2.2 用户特征

- 有能力动笔写作，不需要软件代写。
- 灵感常来自一首歌、一幅画、一个景色、一条梗、一句话或一个动作。
- 片段的初步排列通常在灵感形成时已经发生。
- 真正卡住的是如何把已有片段扩写为正文。
- 不希望为了写作先维护复杂项目、状态和资料库。
- 重视隐私、可迁移性和对文字的最终控制。

### 2.3 次要与非目标用户

- 混合型作者可以使用可选大纲，但不决定 MVP 主链路。
- 长篇能力进入 Advance，不要求当前 MVP 完成。
- 重规划型作者、多人团队、约稿平台、AI 代写用户、社区运营者不是主动争取对象。

---

## 3. 产品立场与边界

### 3.1 作者资产

> 创作者资产属于创作者，不属于软件。

因此：

- Markdown 是耐久资产。
- `keikeu_index.json` 只是可重建索引。
- 用户能用普通文本编辑器打开和修复 Paper。
- keikeu 不自动总结、改写或评价作者文字。
- 作者手动保存的当前 Summary 是权威版本。
- 首次保存的 Summary 同时写入不可变的初稿副本。

### 3.2 正文边界

keikeu 不承担：

- 正文编辑与保存
- 章节和长篇工程管理
- 字数、完成度和写作进度追踪
- 排版、协作、Beta 阅读和发布
- 读取或监控外部编辑器中的正文

作者可以看着 Flashcard，在任意外部编辑器中扩写正文。

### 3.3 网络与同步边界

keikeu 本身不提供账号、云后端、上传 API 或后台同步服务。

用户可以主动把 vault 放在由操作系统暴露的第三方同步目录中，例如 iCloud Drive、Dropbox 或 OneDrive。同步行为、账号、版本冲突与可用性由对应服务负责；keikeu 只读写用户选择的普通文件路径。

这仍属于本地优先：没有网络时，只要文件在设备上可用，核心工作流就必须可运行。

---

## 4. MVP 核心对象：Paper

UI 中统一称为“纸片”；代码与规格中称为 `Paper`。耐久文件继续位于 `cache/*.md`，以兼容 vault 的简单目录语义。

### 4.1 Paper 的单位

> 一张 Paper = 一次准备写成正文的作品单元。

第一件灵感创建 Paper；同一作品在写作前出现的新灵感继续补充到这张 Paper，而不是自动创建项目、合集或跨纸片卡组。

### 4.2 内容模型

Paper 的创作内容只有：

1. **Summary**：必填；作者当前对作品火种的表达。
2. **Highlights**：可选但推荐；有序的写作锚点。
3. **Tags**：可选但推荐；平面检索标签。

另外保存：

- **代号**：必填；Paper 的稳定标识。
- **初稿副本**：首次保存时冻结的 Summary，只读保存，不参与日常编辑。
- **创建/更新时间**：文件元数据，不是创作进度。
- **legacy_title**：仅旧 Cache 迁移时存在的保全元数据；普通 Paper 不生成，后续保存不得丢失。

Paper 不包含：

- 标题字段
- 临时备注字段
- `raw / drafting / outlined / archived` 等创作状态
- `linked_outline`
- 固定 Fandom、CP、Ending Type、流水账或逻辑关系表单

这些信息需要时可以成为 Tags、Highlights 或未来可选 Outline 的内容，但不进入 Paper 的固定模型。

### 4.3 代号

- 新 Paper 自动生成中性代号，例如 `K-20260713-001`。
- 代号不得从 Summary 自动推导，避免在文件名泄露创作内容。
- 首次保存前允许作者修改。
- 首次保存后修改代号属于显式重命名，同时更新文件名和索引。
- 文件名使用 `<代号>.md`。

### 4.4 Summary 与初稿副本

- Summary 不能为空；为空时阻止保存，并保留磁盘上的上一版本。
- keikeu 不自动摘要、不润色、不补写 Summary。
- 作者可以自由修改当前 Summary。
- 第一次成功保存时，将 Summary 同时复制到“初稿副本”。
- 初稿副本随后只读；普通保存和重命名不得修改它。
- Flashcard 的第一页始终显示当前 Summary，不显示初稿副本。

“保留原始灵感”在新模型中的含义是：软件不改写作者输入，并保留首次保存的初稿副本；它不要求当前 Summary 永远不可编辑。

### 4.5 Highlights

- 一个 Highlight 是一个可独立扩写的写作锚点，例如场景、动作、对白、转折或意象。
- Highlights 保持作者指定的顺序。
- 一条 Highlight 对应一张 Flashcard。
- 建议短小，通常一至三句，但不设硬字符数或句数限制。
- Highlights 为空仍允许保存；界面温和建议添加，不显示错误。
- MVP 不提供跨 Paper 聚合、画布或复杂场景数据库。

### 4.6 Tags

- Tags 是可选、自由、平面的 Markdown 标签。
- 已有 Tags 可以作为输入建议复用。
- 保存时只清理首尾空格，并删除同一 Paper 内完全相同的重复项。
- 不自动合并同义词，不区分层级，不分配颜色，不建设 Tag Manager。
- Tags 为空仍允许保存；界面温和建议添加。

### 4.7 Markdown 参考格式

```markdown
---
type: paper
schema_version: 2
code: K-20260713-001
created: 2026-07-13 17:30
updated: 2026-07-13 17:45
---

# K-20260713-001

## 初稿副本

深夜的末班公交上，两个人隔着一个空位假装睡着。

## Summary

深夜的末班公交上，两个人隔着一个空位假装睡着。A 明早要离开，B 已经知道。

## Highlights

1. 末班车几乎空了；两个人都闭着眼，却都没有睡。
2. 公交驶过 B 平时下车的站。A 看见了，但没有问。
3. B 把旧打火机塞回 A 手里：“只是这个你忘了。”

## Tags

- 末班车
- 离别
- 暧昧
```

Highlights 或 Tags 为空时保留对应标题和空正文，以保持格式简单、稳定、可手工修复。

UI 不提供原始 Markdown 预览；需要查看资产时交给系统文件管理器或外部文本编辑器。

---

## 5. Flashcard

Flashcard 是 Paper 的只读聚焦视图，不是第三份耐久资产。

### 5.1 卡片顺序

```text
第 1 张：当前 Summary
第 2 张起：各条 Highlight，保持 Paper 顺序
```

因此，没有 Highlight 的 Paper 仍然拥有一张可用的 Summary 卡。

### 5.2 有限上下文

Flashcard 只提供：

- 当前卡片正文
- `x / n`
- 上一张 / 下一张
- Highlight 页上的临时 Summary 查看
- 返回 Paper 修改

Flashcard 不提供：

- 相邻 Highlight 正文预览
- 卡片内编辑
- 完成、跳过、消费或写作进度状态
- 正文输入框

### 5.3 记住位置

- 默认记住每张 Paper 上次停留的卡片位置。
- 位置是每台设备自己的可丢弃 UI 状态，不写进 Paper Markdown，也不通过 vault 同步。
- 建议保存在应用层本地状态文件，例如 `~/.keikeu_state.json`。
- 状态文件丢失时从 Summary 第一张开始，不影响任何创作资产。
- Highlights 变少导致旧位置越界时，落到当前最后一张。

---

## 6. Library

Library 是 Paper 的轻量检索入口，不是项目管理器。

MVP 支持：

- 按代号搜索
- 按 Summary 全文搜索
- 按 Tags 搜索
- 打开 Paper 编辑
- 打开 Flashcard
- 用系统默认程序打开 Markdown
- 在 Finder 中显示文件或 vault
- 显示资产健康、损坏与回收站结果

Library 不支持：

- 创作状态筛选
- 看板、任务、完成度或截止日期
- 复杂查询语言
- 项目层级、图谱和世界观数据库

`keikeu_index.json` 可随时从 `cache/*.md` 重建。单个损坏 Paper 应被隔离并报告，不得让其余 Library 失效。

---

## 7. Outline 的新位置

Outline 不进入 Road v0.2 的 MVP 主链路。

- 当前 Paper 保存、Library 和 Flashcard 均不得依赖 Outline。
- 当前主导航不显示 Outline 编辑器。
- 新 vault 不必创建 `outlines/`。
- Outline 作为混合型作者和长篇需求的可选产物，进入独立的 Pre-Advance Road。
- 未来生成 Outline 时，它是独立 `outlines/*.md` 资产；生成行为不改变 Paper 状态。
- 旧七字段 Outline schema 不自动成为未来 schema，必须在 Pre-Advance 阶段重新验证。

---

## 8. 正式写作交接

keikeu 的交接方式不是生成正文文件，而是让作者在外部编辑器旁查看 Flashcard。

- macOS：keikeu 窗口与外部编辑器并列。
- iPadOS：Flashcard 与外部编辑器使用系统分屏。
- iPhone：全屏 Flashcard，必要时切换外部编辑器。

keikeu 不追踪作者在外部编辑器中写了什么、写了多少或是否完成。

---

## 9. 三设备产品架构

三端读取同一种 Paper 模型，但按设备能力分配任务。

### 9.1 macOS

- Road v0.2 首发平台。
- 完成 Paper 编辑、Library 检索与整理、Flashcard、迁移和资产恢复。
- 验证用户选择普通本地目录或 iCloud Drive 等系统同步目录作为 vault。

### 9.2 iPhone

- 捕获或编辑 Paper。
- 全屏查看 Flashcard。
- 不提供 keikeu 内正文输入。

### 9.3 iPad

- Paper 编辑与 Library。
- Flashcard 与外部编辑器系统分屏。
- 不读取外部正文内容。

三设备使用第三方文件服务传递 vault；keikeu 不承诺实时同步、无冲突合并或自己的云服务。iOS/iPadOS 持久目录权限必须在后续平台 Road 中单独验证。

### 9.4 正式原型交付规则

今后的正式产品原型必须同时包含：

1. 软件架构图
2. 手机 UI
3. 电脑 UI
4. 平板 UI

为亲友分享而裁切的派生副本可以只保留指定页面，但不得冒充新的正式原型。

---

## 10. Vault 与本地状态

Road v0.2 目标布局：

```text
keikeu-vault/
  cache/
    K-20260713-001.md
  .trash/
    cache/
  keikeu_index.json

设备本地、vault 外：
  ~/.keikeu_config.json   # 当前 vault 路径
  ~/.keikeu_state.json    # Flashcard 上次位置等可丢弃 UI 状态
```

原则：

> Paper Markdown 是创作事实；索引和 UI 状态都可以丢失后重建或重置。

---

## 11. Road v0.1 资产迁移

旧数据迁移是 Road v0.2 的一次性、显式、可回滚操作。

### 11.1 安全边界

- 迁移前对整个旧 vault 做字节一致的时间戳备份。
- 备份位于活动 vault 外，避免被索引或第三方同步冲突处理误认成当前资产。
- 先写入临时目标并完成解析验证，再替换活动文件。
- 任一 Cache 转换失败时停止切换，旧活动 vault 保持不变。
- 迁移产生可读报告，列出重写的 Cache、移除的 Outline 和失败项。

### 11.2 旧 Cache 映射

- 生成新的中性代号与文件名。
- `原始灵感` → `初稿副本`，逐字复制。
- `原始灵感` → 当前 `Summary`，逐字复制。
- 非空 `临时备注` → 第一条 Highlight，逐字复制。
- 旧标题保存在 `legacy_title` frontmatter，避免静默丢失。
- 旧状态和 `linked_outline` 不进入新 Paper；只记录在迁移报告和完整备份中。
- Tags 初始为空，由用户后续补充。
- 旧 `原始灵感` 为空时视为迁移前检查失败；软件不得用标题或临时备注自动替代 Summary。用户需要先补写或删除该旧 Cache。

### 11.3 旧 Outline

- 旧 Outline 不转换为 Paper，也不进入当前产品模型。
- Cache 全部转换并验证成功后，从活动 vault 中永久移除旧 `outlines/` 内容。
- 旧 Outline 只存在于迁移前完整备份中。
- 应用不为旧 Outline 提供读取、浏览或恢复入口。

这实现“旧 Outline 直接销毁”的产品决定，同时保留一次人工回滚能力，避免迁移缺陷造成不可逆的数据事故。

---

## 12. macOS MVP 验收标准

Road v0.2 只在 macOS 上验收以下闭环：

1. 用户能新建 Paper；Summary 为空时不能保存。
2. 第一次保存生成不可变初稿副本。
3. Highlights 和 Tags 为空时可以保存，并得到温和建议。
4. Paper 关闭、重开、修改和显式重命名后内容正确。
5. Markdown 可由普通文本编辑器读取和手工修复。
6. Library 能按代号、Summary 和 Tags 找到 Paper。
7. 删除或损坏索引后，能从 Paper 重建。
8. 单个损坏 Paper 不阻塞其余资产。
9. Flashcard 第一张是 Summary，后续一条 Highlight 对应一张卡。
10. Flashcard 默认记住每台设备的上次位置；状态丢失不影响 Paper。
11. Flashcard 可随时返回 Paper 修改，不提供正文输入或完成状态。
12. 普通本地目录和至少一个 iCloud Drive vault 完成 macOS smoke test。
13. 旧 Cache 能按迁移规则重写；旧 Outline 从活动 vault 移除；完整备份与报告存在。
14. 主流程不要求 Outline，不使用 AI 代写，不读取外部正文。

产品价值验收仍需真实创作：至少用 one-shot 和短中篇场景验证 Paper → Flashcard 是否确实帮助作者开始写正文。合成案例只能证明模型自洽。

---

## 13. MVP 明确不做

- Outline 编辑与生成
- 长篇章节工程
- 跨 Paper Flashcard 聚合
- AI 总结、改写或续写
- 内置正文编辑器
- keikeu 自建云同步、账号或远程存储
- 实时协作、评论和 Beta 工作流
- 社区、发现流、排行榜和发布
- 外部 fandom / CP / 角色数据库
- 标签层级、颜色、管理器和复杂筛选
- 图谱、时间线、画布和 scene board
- 用户画像、分析和遥测

---

## 14. Pre-Advance

Pre-Advance Road 暂存：

- 可选 Markdown Outline
- Paper → Outline 的显式生成或整理流程
- 面向混合型作者的结构化字段
- Outline 与 Paper 的来源关联
- 长篇开始前的最小组织能力

任何 Pre-Advance 功能都不得阻塞 Paper → Flashcard 主链路，也不得把 Paper 重新变成等待“升级”的临时物。

---

## 15. 总结

keikeu 第一版不是大纲工厂，也不是完整写作平台。

它是一把本地小刀：

> 把已经出现的灵感收成一张纸片，再把当前最值得扩写的内容递到作者眼前。

先让 Paper → Flashcard → 外部正文闭环在 macOS 上真正好用，再扩展平台与 Advance。
