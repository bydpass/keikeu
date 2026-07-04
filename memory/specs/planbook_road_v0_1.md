# keikeu Road v0.1 Planbook（Codex 执行手册）

> 配套规范：spec_road_v0_1.md（验收标准以 spec 为准，本手册只管怎么切）
> 执行纪律：一个 phase = 一个分支 = 一个行为 = 一组测试 = 一个 commit
> 必读：CLAUDE.md、gitagent.md（Git 仪式与红线）、spec_road_v0_1.md

## 执行者须知

1. **开工仪式**（每个 phase 开始前）：`git status` 必须干净。不干净就停下报告，不许混提交。
2. 每 phase 从 `main` 开任务分支（命名见各 phase），完成后合回。
3. 测试命令：仓库根目录 `python -m pytest`（venv：`source .venv/bin/activate`）。全绿才许 commit。
4. UI 改动尽力 `flet run src/keikeu_app/main.py` 目验；不能跑就在报告里说明原因。
5. 红线：`keikeu_core` 零 Flet import；序列化只在 `markdown_io.py`；不加依赖；不改 appdesign.md / techpolicy.md / gitspec.md / gitagent.md；不碰范围外文件。
6. 每 phase 结束报告：改了什么文件、行为变化、跑了什么测试、已知风险。
7. P0-001 之后，outline schema 改动必须带 migration 或明确版本号。

## 前置检查（Phase 0，人工确认项）

开发者负责把当前未提交的文档态收进一个 commit（或明确弃置）。Codex 开工时若工作树不干净：**停，报告，等指令**。

---

## Phase 1 — Outline schema 收尾（P0-001）

- 分支：`feature/outline-schema-v01`
- 规范：spec WI-1
- 触碰：`src/keikeu_core/models.py`、`src/keikeu_core/markdown_io.py`、`tests/test_models.py`、`tests/test_markdown_io.py`、`tests/test_indexer.py`（若夹具受影响）、`tests/test-vault/outlines/*.md`（重写为新格式）

步骤：

1. `models.py`：`Outline.content_warnings` 拆为 `warning_setting` / `warning_cp_structure` / `warning_elements`（皆 str，默认 `""`）；`RelationType` backing value 改中文（`前作`/`续作`/`IF`/`外传`/`同系列`）。
2. `markdown_io.py`：`_render_outline` 按 spec WI-1 改 §4（三标签行）、§6（写结局字样或 custom 文本）、§7（三行标签块 + 空行分隔）；`read_outline` 对应改解析（§6 读取规则见 spec；解析不到的字段落空值不崩）。
3. 更新测试：round-trip、逐行对照 spec 示例、空字段行为、§6 双向规则、§7 多条关系。
4. 重写 `tests/test-vault/` 内旧格式 outline 夹具。
5. 全测绿 → commit。

- Commit：`feat: finalize outline markdown schema (P0-001)`

## Phase 2 — 导出 Markdown

- 分支：`feature/export-markdown`
- 规范：spec WI-2
- 触碰：`src/keikeu_app/pages/outline_editor_page.py`（FilePicker 挂接 `page.overlay`）；core 无改动（导出是字节复制，app 层 `shutil.copy2`）

步骤：

1. 编辑器加「导出 Markdown」按钮；未保存草稿先走既有保存流程。
2. `ft.FilePicker.save_file`，默认文件名 = vault 内文件名；确认后 copy2；取消则无操作。
3. 注意 Flet 0.85 FilePicker 的事件模型（回调/async），照现版 API 写。
4. GUI 层为主，逻辑尽量薄；`flet run` 目验导出与取消两条路。

- Commit：`feat: export outline as markdown`

## Phase 3 — 软删除 + Archive 去重合

- 分支：`fix/soft-delete-archive`
- 规范：spec WI-3
- 触碰：`src/keikeu_core/vault.py`（`.trash/` 布局 + `soft_delete`）、`src/keikeu_core/indexer.py`（仅确认排除，加钉死测试）、三个 page 文件、`tests/test_vault.py`、`tests/test_indexer.py`

步骤：

1. core：`init_vault` 增建 `.trash/cache/`、`.trash/outlines/`（`is_vault` 不要求）；实现 `soft_delete`（重名后缀避让，只移动）。
2. 测试：soft_delete 移动/避让/内容字节不变；`.trash` 不入索引。
3. GUI：两编辑器加「删除」，Library 行尾加删除钮；删除 → 移入 → 重建索引 → snackbar「已移入回收站」→ 回 Library；无确认弹窗。
4. cache 页 status 下拉换只读徽章（中文说明文案见 spec WI-6）；状态只由动作驱动；「封存」→ archived。
5. 全测绿 + `flet run` 目验 → commit。

- Commit：`fix: simplify archive and add soft delete`

## Phase 4 — 逻辑关系 picker

- 分支：`feature/relation-picker`
- 规范：spec WI-4
- 触碰：`src/keikeu_app/pages/outline_editor_page.py`（或抽 `widgets/` 小件）、`tests/test_app_pages.py`（可测部分）

步骤：

1. 移除手输 `target path` 的关系行编辑器。
2. 对话框：搜索 + index 资产列表 → 选目标 → 五择一关系 → 可选说明 → 确认。
3. 已有关系显示为只读行（类型徽章 + 标题反查 + 说明 + 移除）；目标丢失时降级显示路径。
4. 保存后 §7 输出正确（Phase 1 的序列化不动，picker 只生产 `Relation` 对象）。

- Commit：`feat: add local relation picker`

## Phase 5 — Library 补齐

- 分支：`feature/library-open-reveal`
- 规范：spec WI-5
- 触碰：`src/keikeu_app/pages/library_page.py`

步骤：

1. 行尾「打开」（`open <file>`）与「在文件夹中显示」（`open -R <file>`），stdlib subprocess，非 macOS 降级不崩。
2. 页底 vault 路径行 + 定位钮。

- Commit：`feat: open file and reveal in folder from library`

## Phase 6 — 视觉气质 + 文案中文化

- 分支：`style/app-shell-visual`
- 规范：spec WI-6（tokens 表 + 文案表 + 两条记录性偏差）
- 触碰：`src/keikeu_app/`（main、三 page、widgets）；建议新增 `src/keikeu_app/theme.py` 集中 tokens，避免散落

步骤：

1. `theme.py`：色板/字号/圆角常量，一处定义。
2. 壳与三页面按 tokens 换肤：轻 sidebar、去重阴影、加留白、降 icon 存在感。
3. 全部用户可见文案按 spec 文案表中文化（注意「先放着」不做、status 只读两条定案）。
4. `flet run` 目验：三分钟链路走通（口嗨 → cache → 炼成 → 大纲 → 导出）。
5. 测试若断言英文文案需同步更新。

- Commit：`style: soften app shell visual language`

---

## 完工定义（对照 review 验收）

```text
用户输入一段混乱口嗨，能在 3 分钟内得到一份
可保存、可编辑、可导出、可继续写作的本地 Markdown 大纲；
误删有 .trash 兜底；界面不再是 Material demo。
```

六个 phase 全部合入后，通知 Manager 做整体验收与 tag。
