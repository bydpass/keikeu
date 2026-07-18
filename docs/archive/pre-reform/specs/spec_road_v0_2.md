> **ARCHIVED — READ ONLY.** Superseded by [`docs/SPEC.md`](../../SPEC.md); retain only for Road history.

# keikeu Road v0.2 行为 Spec

> Road：macOS Paper–Flashcard Core  
> 状态：已审阅，Phase 7 完成（2026-07-15）
> 产品真理：[`../../appdesign.md`](../../appdesign.md)  
> 配套执行手册：[`planbook_road_v0_2.md`](planbook_road_v0_2.md)

## 0. Road 目标

Road v0.2 将当前 macOS pre-alpha 从旧 `Cache → Outline` 模型迁移到：

```text
Paper Markdown → Flashcard → 外部正文编辑器
```

完成后，macOS 应具备可独立验收的 Paper 创建、编辑、检索、聚焦、迁移和本地资产恢复闭环。Outline 不属于本 Road 的主功能。

## 1. 已定案决议

| 议题 | 决议 |
|---|---|
| Paper 单位 | 一张 Paper = 一次准备写成正文的作品单元 |
| 主资产目录 | 继续使用 `cache/*.md` |
| 代号 | 自动生成中性代号；首次保存前可改，之后显式重命名 |
| Summary | 必填；Flashcard 第一张 |
| 初稿副本 | 首次保存时冻结在同一份 Markdown 中 |
| Highlights | 可选但推荐；有序；每条一张 Flashcard |
| Tags | 可选但推荐；自由平面标签 |
| 创作状态 | 删除 `raw/drafting/outlined/archived` |
| Flashcard 位置 | 默认记住；每设备本地可丢弃状态 |
| Outline | 移出 MVP，进入 Pre-Advance Road |
| 旧 Cache | 自动重写为 Paper v2 |
| 旧 Outline | 完整备份后从活动 vault 永久移除，不迁移 |
| 同步 | 用户选择 iCloud Drive 等系统文件服务目录；keikeu 不建云后端 |
| 平台 | 本 Road 只实现并验收 macOS |

## 2. 全局工程约束

1. `keikeu_core` 不得 import Flet 或 GUI 包。
2. Markdown 解析与序列化只存在于 `src/keikeu_core/markdown_io.py`；迁移期旧格式读取可以隔离到纯 Python legacy 模块。
3. Paper Markdown 是创作事实；索引与 Flashcard 位置均可丢弃。
4. 不新增数据库、网络 API、账号、遥测或后台进程。
5. 不新增第三方运行时依赖，除非开发者另行批准。
6. keikeu 不自动改写 Summary、初稿副本或 Highlights。
7. 任何迁移失败都不得留下半转换的活动 vault。
8. UI 不显示原始 Markdown 预览，不承载正文输入。

## 3. Paper v2 行为

### 3.1 模型

建议纯 Python 模型：

```python
@dataclass
class Paper:
    code: str
    initial_summary: str
    summary: str
    highlights: list[str]
    tags: list[str]
    created: datetime
    updated: datetime
    legacy_title: str | None = None
```

行为要求：

- `summary.strip()` 不能为空。
- `initial_summary` 在第一次成功保存后不可由普通更新 API 修改。
- Highlights 保持顺序；空字符串条目保存前去除。
- Tags 只做首尾空格清理和完全重复去除，保持首次出现顺序。
- 模型无创作状态、标题、临时备注或 Outline 关联。
- `legacy_title` 只用于保全旧 Cache 标题；普通新建为 `None`，后续保存必须原样保留。

### 3.2 代号与文件名

- 默认格式：`K-YYYYMMDD-NNN`。
- 同日序号根据 vault 中现有代号取下一个可用值。
- 文件名：`cache/<code>.md`。
- 重名时不得覆盖；自动生成过程继续寻找可用序号。
- 首次保存后修改代号必须调用显式 rename 行为。
- rename 成功前旧文件保持不变；成功后重建索引和 Flashcard 本地状态键。

### 3.3 保存规则

- 新 Paper：Summary 非空 → 固化 `initial_summary = summary` → 写入新文件。
- 已存在 Paper：Summary 非空 → 保持旧 `initial_summary` → 更新其余字段。
- Summary 为空：报告可解释错误，不写磁盘。
- Highlights/Tags 为空：保存成功，UI 给非阻塞建议。
- 写入应使用同目录临时文件 + 原子替换，避免同步或崩溃产生截断文件。

### 3.4 Markdown

- 格式以 `appdesign.md §4.7` 为准。
- `schema_version: 2` 必须存在。
- 自由文本逐字往返，除 Markdown 结构本身要求的最小换行规范外不得 normalize。
- 空 Highlights/Tags 仍写出对应二级标题。
- 初稿副本、Summary、Highlights、Tags 必须能 write → read → write 稳定往返。
- 未知 frontmatter 字段在可行时保留；至少不得导致解析崩溃。

### 3.5 验收

- [ ] Summary 为空无法写入或覆盖文件
- [ ] 首次保存同时写入相同的初稿副本和当前 Summary
- [ ] 二次修改 Summary 后初稿副本字节不变
- [ ] Highlights 顺序往返一致
- [ ] Tags 按规则清理，不做同义词或大小写合并
- [ ] 代号生成和显式 rename 不覆盖现有文件
- [ ] 完整、最小和 CJK/换行案例均可 round-trip
- [ ] 迁移 Paper 的 `legacy_title` 在普通编辑与重写后仍保留

## 4. Vault 与索引

### 4.1 目标布局

```text
vault/
  cache/*.md
  .trash/cache/*.md
  keikeu_index.json
```

- 新 vault 不创建 `outlines/` 或 `.trash/outlines/`。
- 旧 vault 在迁移完成后删除活动 `outlines/` 与 `.trash/outlines/`。
- `is_vault` 只要求 `cache/` 和 index 所需的最小条件。

### 4.2 Index v2

建议结构：

```json
{
  "version": 2,
  "papers": [
    {
      "code": "K-20260713-001",
      "path": "cache/K-20260713-001.md",
      "summary": "...",
      "tags": ["末班车", "离别"],
      "created": "...",
      "updated": "..."
    }
  ],
  "errors": []
}
```

- Index 不包含初稿副本全文和 Flashcard 位置。
- Index 不包含创作状态或 Outline 列表。
- Summary 可进入索引以支持本地搜索；索引依然可删除重建。
- 单个 Paper 解析失败时，加入 `errors`，继续索引其他文件。
- 外部删除后重建应移除失效条目。

### 4.3 软删除与恢复

- Paper 删除继续移动到 `.trash/cache/`，不立即删除字节。
- 同名避让，不覆盖既有回收站文件。
- Library 提供回收站查看和恢复；恢复重名时要求用户选择新代号或取消。
- 创作状态与资产健康/回收站状态必须分离。

### 4.4 验收

- [ ] 删除 index 后能从 Paper 重建 v2 index
- [ ] 一个损坏 Paper 不阻塞其他 Paper
- [ ] 外部删除后显式刷新与磁盘事实一致
- [ ] 软删除和恢复保持文件字节
- [ ] 新 vault 不依赖 `outlines/`

## 5. Paper 编辑器

macOS Paper 页面必须提供：

- 代号编辑或显式重命名入口
- 当前 Summary 必填编辑区
- 初稿副本只读查看区，默认折叠或渐进披露
- Highlights 增加、删除、编辑和排序
- Tags 自由输入与已有标签提示
- 保存、删除、打开 Flashcard、返回 Library

不提供：

- 独立极简输入页
- Markdown 资产预览
- 创作状态选择器
- “转成大纲”按钮
- 正文输入框

保存反馈必须区分：Summary 缺失、代号冲突、文件不可写和文件已被外部修改。

## 6. Flashcard

### 6.1 卡组投影

```text
cards = [paper.summary] + paper.highlights
```

- Summary 永远是第一张。
- 一条 Highlight 对应一张卡。
- 卡片只读。
- 有限上下文：当前卡、`x/n`、上一张、下一张、临时 Summary、返回 Paper。

### 6.2 上次位置

- 每台 macOS 设备在 vault 外保存 `paper.code → card_index`。
- 建议文件：`~/.keikeu_state.json`。
- 不同步、不进入 Markdown、不进入 index。
- 位置缺失或非法时使用 0。
- Paper rename 时迁移状态键。
- Highlights 变化后将越界位置夹到最后一张。

### 6.3 验收

- [ ] Summary-only Paper 产生一张卡
- [ ] N 条 Highlights 产生 N+1 张卡
- [ ] 关闭并重开应用后恢复上次位置
- [ ] 删除本地状态文件后从 Summary 开始，Paper 不受影响
- [ ] 卡片无编辑、完成、跳过或正文输入能力

## 7. Library

- 单一搜索框同时匹配代号、Summary 和 Tags。
- 列表不显示创作状态和 Outline 存在状态。
- 行入口支持编辑 Paper 和打开 Flashcard。
- 保留系统默认程序打开、Finder 定位和 vault 路径入口。
- 搜索与标签提示只使用本地 v2 index。
- 不增加筛选器矩阵、CP 专用字段或查询语言。

## 8. v0.1 → v0.2 迁移

### 8.1 触发

- 检测到旧 `type: cache`、旧 index version 或 `outlines/` 时进入迁移前检查。
- 不允许在后台静默迁移。
- UI 显示将发生的动作：完整备份、Cache 重写、活动 Outline 永久移除。
- 用户确认后才执行；取消则保持旧 vault 原样，并阻止 v0.2 对其写入。

### 8.2 原子迁移

1. 创建 vault 外的时间戳备份目录并字节复制整个旧 vault。
2. 在 vault 外临时目录转换全部旧 Cache。
3. 逐个读取临时 Paper，验证数量、Summary 和初稿副本。
4. 生成迁移报告。
5. 只有全部 Cache 验证成功后，切换活动 `cache/`。
6. 永久移除活动 `outlines/` 和 `.trash/outlines/`。
7. 写入 v2 index。
8. 任一步失败时恢复或保留旧活动 vault，不产生混合 schema。

### 8.3 字段映射

| 旧 Cache | Paper v2 |
|---|---|
| title | `legacy_title` frontmatter |
| raw inspiration | 初稿副本 + 当前 Summary |
| temporary notes | 非空时作为第一条 Highlight |
| created / updated | 原值 |
| status | 不迁移；写入报告 |
| linked_outline | 不迁移；写入报告 |

Tags 为空。不得根据旧标题、CP 或文本自动猜标签。

旧 raw inspiration 为空时，该 Cache 不能自动迁移：预检必须列出它，并要求用户在旧版中补写或删除。不得用旧标题或 temporary notes 自动代替必填 Summary。

### 8.4 Outline 销毁

- 不解析、不转换、不展示旧 Outline。
- 活动 Outline 只在 Cache 转换验证全部通过后永久删除。
- 回滚来源只有迁移前完整备份；应用不提供旧 Outline 恢复 UI。

### 8.5 验收

- [ ] 迁移前备份与旧 vault 文件逐字节一致
- [ ] 迁移后 Paper 数量等于成功读取的旧 Cache 数量
- [ ] 旧原始灵感同时存在于初稿副本和 Summary
- [ ] 旧临时备注非空时成为第一条 Highlight
- [ ] 任一 Cache 失败时活动 vault 不切换
- [ ] 成功后活动 vault 无旧 Outline，备份仍存在
- [ ] 报告列出映射、销毁和失败情况

## 9. 第三方文件同步目录

macOS Road 只实现普通目录语义：

- vault picker 允许选择本地目录或系统可访问的 iCloud Drive/Dropbox/OneDrive 目录。
- keikeu 不调用服务商 API，不读取账号，不承诺同步时机。
- 保存必须使用安全替换，减少同步中途读取半文件的风险。
- 检测到外部修改时不得静默覆盖；应提示重新载入或另存。
- provider 产生的冲突副本按普通未知文件处理，不自动合并创作文本。

macOS MVP 至少对普通本地目录和一个 iCloud Drive vault 进行真实 smoke test。跨设备同步验收不属于本 Road。

## 10. Outline 退休

- 主导航移除 Outline 编辑器。
- 删除“从 Cache 炼成大纲”、Outline 导出和关系 picker 的可达入口。
- 当前代码中的 Outline 模型、I/O、index 与页面在迁移能力稳定后删除或隔离为不可达 legacy 代码。
- Road 完成时，正常运行路径不得创建、读取或索引 `outlines/*.md`。
- 未来 Outline 依据 [`road_pre_advance.md`](road_pre_advance.md) 重新设计，不复活旧七字段作为默认答案。

## 11. macOS Road 完成定义

Road v0.2 只有同时满足以下条件才可归档：

- appdesign、Road spec、实现和测试使用同一 Paper v2 契约。
- macOS 完整走通 Library → Paper → Flashcard → 返回 Paper。
- Summary 必填、初稿冻结、Highlights/Tags 推荐但不阻塞。
- Flashcard Summary-first 且恢复上次位置。
- v2 index 可重建，损坏文件被隔离。
- 删除与恢复行为可解释。
- v0.1 Cache 迁移和 Outline 销毁通过夹具与真实备份演练。
- 普通目录与 iCloud Drive vault 完成 smoke test。
- 应用无 Outline 可达入口、无正文编辑、无 AI 代写、无 keikeu 云服务。
- 完成至少一次真实 one-shot 与一次短中篇工作流验证；结果可以暴露产品问题，但必须有记录。

“功能实现完成”“macOS MVP 可用”和“三设备产品完成”是三个不同结论，不得混写。
