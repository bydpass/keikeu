> **ARCHIVED — READ ONLY.** Road v0.1 contract; current product authority is [`docs/SPEC.md`](../../SPEC.md).

# keikeu Road v0.1 执行 Spec

> 状态：经 Manager QA 定案（2026-07-04）
> 地位：appdesign.md 仍是产品真理。本 spec 只规定 Road v0.1 剩余工作 + Library 补齐。
> 与 appdesign.md 冲突时以 appdesign.md 为准，**除本 spec「明文修订」条目外**。
> 配套执行手册：planbook_road_v0_1.md

## 0. QA 决议记录

| 议题 | 决议 |
|---|---|
| 覆盖范围 | Road v0.1 剩余五项 + Library 补齐（打开文件 / 文件夹显示） |
| §6 Ending Type | 正文写入结局字样，frontmatter 仍是机读真值 |
| 冒号 | **半角 `: `**（明文修订：appdesign §5.1 示例中的全角冒号视为排版，不是规范） |
| §7 关系格式 | 三行标签块，多条间空行分隔 |
| 旧格式文件 | **不兼容**。只认新格式；pre-alpha 阶段旧文件由人工处置 |
| 导出交互 | 系统保存对话框（Flet FilePicker.save_file） |
| Archive 去重合 | status 变只读，状态完全由动作驱动 |
| 视觉规范来源 | `memory/specs/keikeu-ui-prototype.html` 为视觉权威（落 tokens，非像素复刻） |
| UI 文案 | 全面中文化，按原型文案 |
| 回收站 | 软删除进 `.trash/`，MVP 不做应用内恢复 UI |
| Library 打开语义 | 行点击 = 应用内编辑器；行尾两钮 = 系统打开 + 文件夹显示 |

## 1. 通用约束（每个工作项都适用）

1. `keikeu_core` 不得 import Flet；序列化只存在于 `markdown_io.py`。
2. 产品不变量 1–5（见 CLAUDE.md）不可违反；原始灵感逐字保留。
3. 索引可弃可重建；任何操作不得删除或改写用户 Markdown 资产（软删除仅移动）。
4. 不新增第三方依赖（stdlib 优先；Flet 自带能力可用）。
5. 空字段永远允许；任何检查只提示、不阻塞保存。

---

## WI-1 Outline schema 收尾（P0-001）

### 行为规范

**§3（不变，明文定案）**：保持半角冒号 `- Fandom: ` `- 人物: ` `- CP: `。

**§4 观前提醒（改）**：由自由文本改为三行结构：

```markdown
## 4. 观前提醒

- 原作 / AU / IF / PA: 
- CP 结构: 
- 情节元素: 
```

- `models.Outline.content_warnings: str` 拆为三个 str 字段：`warning_setting`（原作/AU/IF/PA）、`warning_cp_structure`、`warning_elements`，默认皆 `""`。
- GUI 编辑时该区块标签显示为「内容要素」（appdesign §5.2：导出用同人语境熟词，编辑时避免发布语境）。
- 值为空时该行仍写出（保留标签行，值留白）。

**§6 Ending Type（改）**：正文写入结局字样：

- `ending_type` 为 HE/BE/OE 时，§6 正文写对应字样一行（`HE` / `BE` / `OE`）。
- 为 custom 时，§6 正文写 `custom_ending` 原文（逐字）。
- 读取规则：frontmatter `ending_type` 是唯一机读真值；非 custom 时忽略 §6 正文（`custom_ending = ""`）；custom 时 §6 正文即 `custom_ending`。

**§7 逻辑关联（改）**：每条关系写三行标签块，多条之间以一个空行分隔：

```markdown
## 7. 与其他灵感的逻辑关联（Optional）

- 关系: 续作
- 关联对象: outlines/2026-06-19-xxxx-阿德琳等着姐姐.md
- 说明: 同一车站，三年后

- 关系: IF
- 关联对象: cache/2026-06-20-xxxx-琴房雨声.md
- 说明: 
```

- `RelationType` 枚举 backing value 改为中文：`前作` / `续作` / `IF` / `外传` / `同系列`（枚举成员名不变；中文值直接写入正文，消灭翻译表）。
- `关联对象` 为 vault 相对路径；`说明` 可空但标签行保留。

**兼容性（定案）**：不兼容旧格式。`read_outline` 只解析新格式；解析不到的字段落空值，不崩溃。`tests/test-vault/` 内旧格式文件重写为新格式（测试夹具不是用户资产）。

### 验收标准

- [ ] 一份各字段全填的 outline 写出的 Markdown 与本节示例逐行一致（含空值行为）
- [ ] round-trip：write → read → write，字节一致；自由文本字段逐字保留
- [ ] 非 custom 结局的文件正文 §6 可见结局字样；custom 结局正文可见自定义文本
- [ ] 全部 core 测试绿

---

## WI-2 导出 Markdown

### 行为规范

- outline 编辑器新增「导出 Markdown」按钮。
- 点击时先弹出系统保存对话框（`ft.FilePicker.save_file`）；已有 vault 文件时，默认文件名 = vault 内文件名；未保存草稿按当前标题生成默认 `.md` 文件名。
- 用户确认目标后：若该 outline 尚未保存过（无 vault 内路径），先按正常保存流程存入 vault，再继续导出。
- 将 vault 内 `.md` **字节一致**复制到目标位置（`shutil.copy2`，app 层执行；不经过重新序列化）。
- 用户取消对话框：无操作、无报错。
- 第一版只支持 Markdown（无 PDF/DOCX/HTML）。

### 验收标准

- [ ] 导出文件与 vault 内源文件字节一致
- [ ] 未保存草稿点导出 → 自动落盘 vault 后导出成功
- [ ] 取消不报错；未保存草稿不落盘，vault 状态不变

---

## WI-3 软删除 + Archive 去重合

### 行为规范

**vault 布局**：新增 `.trash/cache/` 与 `.trash/outlines/`。`init_vault` 创建之；`is_vault` **不**要求其存在（旧 vault 首次删除时按需创建）。

**core 新函数**（`vault.py` 或独立函数，纯 Python）：

- `soft_delete(vault: Path, rel_path: str) -> Path`：把 `cache/x.md` 或 `outlines/x.md` 移入 `.trash/` 对应子目录并返回新路径；目标重名时在文件名后附加短随机后缀；只移动，永不删除字节。
- `rebuild_index` 保持只扫 `cache/*.md` 与 `outlines/*.md`（确认 `.trash/` 天然不入索引，加测试钉死）。

**GUI**：

- cache 编辑器与 outline 编辑器各加「删除」按钮；Library 每行行尾加删除小钮。
- 删除后：文件移入 `.trash/` → 重建索引 → snackbar「已移入回收站」→ 回到 Library。
- 无确认弹窗（软删除本身即保险）；MVP 无应用内恢复（恢复 = 用户在文件管理器把文件移回）。

**status 只读（去重合）**：

- cache 页 status 下拉**移除**，改为只读徽章，显示 `raw — 刚存，未处理` 等中文说明（文案见原型）。
- 状态只由动作驱动：保存不改状态；「炼成大纲」→ drafting（保存大纲后 → outlined）；「封存」→ archived。
- 已 archived 的 cache 仍可打开、编辑、保存（状态保持 archived）；MVP 不做「解除封存」。

### 验收标准

- [ ] 删除后原文件字节原样存在于 `.trash/` 下；索引与列表不再出现
- [ ] 同名二次删除不覆盖（后缀避让）
- [ ] UI 上不存在任何可手选 `archived` 的控件
- [ ] core 测试覆盖 soft_delete 与索引排除

---

## WI-4 逻辑关系 picker

### 行为规范

- outline 编辑器「+ 添加关联」打开对话框，流程：
  1. 搜索框 + 本地资产列表（来自 index：caches + outlines，显示标题/类型/更新时间）；
  2. 点选目标；
  3. 五择一关系类型：前作 / 续作 / IF / 外传 / 同系列；
  4. 可选「说明」一行；
  5. 确认 → 关系加入。
- **全程禁止出现路径输入框**；`target_path` 由所选条目的 index 相对路径自动填入。
- 已添加关系显示为只读行：关系类型徽章 + 目标标题（按路径从 index 反查；查不到时显示相对路径）+ 说明 + 移除钮。
- 不做图谱、不做反向链接、不做跨 vault。

### 验收标准

- [ ] 添加关系全流程无手输路径
- [ ] 保存后 Markdown §7 出现正确三行标签块
- [ ] 目标文件已被删除（在 .trash）时，关系行降级显示路径而不崩

---

## WI-5 Library 补齐

### 行为规范

- 行点击（现状）：在 keikeu 内打开对应编辑器。
- 行尾新增两个小钮：
  - 「打开」：系统默认程序打开该 `.md`（macOS `open <file>`；用 `subprocess`，app 层）；
  - 「在文件夹中显示」：Finder 定位该文件（macOS `open -R <file>`；非 macOS 降级为打开所在目录）。
- 页面底部显示 vault 路径 + 「在文件夹中显示」（对 vault 目录本身；原型底部样式）。

### 验收标准

- [ ] macOS 上两钮行为正确；非 macOS 不崩（降级或禁用）
- [ ] 不新增依赖（stdlib subprocess）

---

## WI-6 视觉气质 + 文案中文化

### 行为规范

视觉权威：`memory/specs/keikeu-ui-prototype.html`。落 tokens 与气质，**不要求像素级复刻**。

**Design tokens（从原型提取）**：

| Token | 值 |
|---|---|
| bg / surface / surface-warm | `#fbf6ee` / `#fffdf8` / `#f1e3cf` |
| fg / muted | `#201914` / `#7a6d63` |
| accent（及 meta） | `#9b5b32`，白字 `#ffffff` |
| border / border-soft | `#ded2c3` / `#eee4d7` |
| success / warn / danger | `#4f8a4f` / `#c9822f` / `#b33a3a` |
| 字体 | 标题 serif（Georgia 系）；正文系统 sans；正文 17px，sm 14px，xs 12px |
| 圆角 | sm 10 / md 16 / lg 24 |
| 阴影 | 基本无；以 1px 边框环代替（去塑料感） |
| sidebar | 宽约 220，轻底色，非 Material NavigationRail 重态 |

**气质要求**（review Phase 5）：降 Material icon 存在感（文字为主）、减塑料感圆角阴影、多留白、本地小册子/灵感票夹感。

**文案（按原型，全面替换英文）**：

- 导航：`灵感缓存` / `配方票编辑` / `本地文件库`；slogan `存住一瞬的灵光`。
- cache 页：`新灵感`；按钮 `保存` / `炼成大纲` / `封存`；提示 `原文保留，不会被整理改写`；状态徽章 `raw — 刚存，未处理` 等四条。
- outline 页：`保存大纲` / `导出 Markdown` / `检查缺什么` / `+ 添加关联`；缺失提示样式 `Optional，还有空白字段：整理后摘要 · 流水账`。
- library 页：`搜索标题` / `状态筛选` / `刷新` / `打开` / `在文件夹中显示`；底部 vault 行。
- 「检查缺什么」：保留现有自动 hint，另加按钮触发同一检查，以 snackbar 温和列出空白字段；永不阻塞保存。

**与原型的记录性偏差（定案）**：

1. 原型 cache 页第三钮「先放着」不实现——其语义属 post-MVP「灵光回潮」；本版第三钮为「封存」。
2. 原型的 status 下拉改为只读徽章（WI-3 决议）。

### 验收标准

- [ ] 三页面色板/字体/留白符合 tokens；无 Material 默认蓝
- [ ] 全部用户可见文案为中文（按上表）
- [ ] `flet run` 可启动，三页面可走通「输入口嗨 → 3 分钟得到可编辑本地 Markdown 大纲」
