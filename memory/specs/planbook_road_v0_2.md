# keikeu Road v0.2 Planbook

> Road：macOS Paper–Flashcard Core  
> 行为规范：[`spec_road_v0_2.md`](spec_road_v0_2.md)  
> 产品真理：[`../../appdesign.md`](../../appdesign.md)  
> 状态：Phase 2 完成，等待 Phase 3（2026-07-14）

当前代码对照与测试基线见 [`audit_v01_to_v02_2026-07-13.md`](audit_v01_to_v02_2026-07-13.md)：`0d3d5fb` 上 `113 passed`。

## 执行纪律

1. 一个 Phase 只完成一个可验收能力组。
2. 每个 Phase 开始前检查工作树，避免混入无关改动。
3. 每个 Phase 优先增加或改写测试，再完成最小实现。
4. `keikeu_core` 零 Flet import；Markdown 只由 core I/O 处理。
5. 迁移和删除属于高风险 Phase，必须使用夹具 vault，禁止直接拿唯一真实 vault 首测。
6. UI 改动必须 smoke test；无法运行时明确报告。
7. 每个 Phase 结束记录：改动文件、行为变化、检查结果、剩余风险。
8. 未经明确确认不 push remote。

## Phase 0 — 文档基线与现状对照

**目标**：确认 Road 文档经开发者审阅，记录当前 v0.1 实现与 v0.2 目标的差距。

检查：

- `appdesign.md`、spec、planbook 无冲突。
- 列出旧 `Cache/Outline/Relation/CacheStatus` 的源码与测试引用。
- 冻结一套包含正常、空字段、损坏 Cache 和 Outline 的 v0.1 迁移夹具。
- 记录当前完整测试基线。

完成条件：开发者批准 Road；没有占位符、隐含数据删除或未定义字段映射。

建议分支：`codex/road-v02-baseline`

## Phase 1 — Paper v2 核心模型与 Markdown

**目标**：在不改 UI 的情况下建立可完整测试的 Paper v2 契约。

主要文件：

- `src/keikeu_core/models.py`
- `src/keikeu_core/markdown_io.py`
- `tests/test_models.py`
- `tests/test_markdown_io.py`

步骤：

1. 添加 `Paper`；移除创作状态依赖。
2. 实现代号验证、Summary 必填、Tags 清理和 Highlights 顺序。
3. 实现 Paper v2 render/read/write/update/rename。
4. 初稿副本只在首次写入时固化。
5. 使用临时文件和安全替换。
6. 增加最小、完整、CJK、多行、空列表、重名和 rename 测试。

完成条件：Paper v2 core 测试全绿，旧 UI 暂时仍可运行或被明确隔离。

建议分支：`codex/paper-v2-core`

## Phase 2 — 一次性迁移器

**目标**：在删除旧 Cache 读取能力前完成并锁定 v0.1 → v0.2 迁移。

建议新增：

- `src/keikeu_core/migration_v01.py`
- `tests/test_migration_v01.py`
- `tests/fixtures/v01-vault/`

步骤：

1. 只读识别 v0.1 vault。
2. 完整复制到 vault 外时间戳备份。
3. 在临时目录按 spec 字段映射转换 Cache。
4. 生成迁移报告并验证所有 Paper。
5. 通过原子目录切换替换活动 Cache。
6. 验证后永久移除活动 Outline。
7. 注入失败点，测试每个阶段都不会留下混合 schema。

完成条件：正常迁移、单 Cache 失败、备份失败、切换失败和重名案例均有测试；真实数据尚不执行。

建议分支：`codex/v01-paper-migration`

## Phase 3 — Vault、Index v2 与恢复

**目标**：让 Paper 成为唯一活动资产，并解决外部删除、损坏隔离与回收站恢复。

主要文件：

- `src/keikeu_core/vault.py`
- `src/keikeu_core/indexer.py`
- `tests/test_vault.py`
- `tests/test_indexer.py`

步骤：

1. 新 vault 只创建 `cache/`、`.trash/cache/` 和 index。
2. Index v2 只索引 Paper，记录 parse errors。
3. 单文件损坏隔离，不中断重建。
4. 外部删除后重建与磁盘一致。
5. 实现回收站列出和恢复，处理代号冲突。

完成条件：index 可丢弃重建；损坏、外删、软删除和恢复均有直接文件系统测试。

建议分支：`codex/paper-vault-index`

## Phase 4 — macOS Paper 编辑器与 Library

**目标**：替换旧 Cache/Outline 主交互，先完成可编辑、可检索的 Paper 闭环。

主要文件：

- `src/keikeu_app/main.py`
- `src/keikeu_app/pages/cache_page.py`（建议重命名为 `paper_page.py`）
- `src/keikeu_app/pages/library_page.py`
- `tests/test_app_pages.py`

步骤：

1. 主导航改为纸片、Flashcard、本地文件库。
2. Paper 页面实现代号、Summary、初稿副本、Highlights 和 Tags。
3. Summary 缺失阻止保存；Highlights/Tags 使用温和建议。
4. 显式 rename，不允许编辑路径。
5. Library 单框搜索代号、Summary 和 Tags。
6. 增加损坏摘要、回收站查看/恢复、默认程序打开和 Finder 定位。
7. 去除极简输入、Markdown 预览、状态和转大纲入口。

完成条件：macOS 可走通新建、保存、重开、修改、rename、搜索、删除与恢复。

建议分支：`codex/macos-paper-library`

## Phase 5 — Flashcard 与设备本地状态

**目标**：完成产品差异核心。

建议新增：

- `src/keikeu_app/pages/flashcard_page.py`
- `src/keikeu_app/local_state.py`
- 对应测试

步骤：

1. 将 Paper 投影为 Summary-first 卡组。
2. 实现当前卡、位置、前后切换、临时 Summary 和返回 Paper。
3. 保存 `paper.code → card_index` 到 vault 外本地状态。
4. 处理状态丢失、损坏、rename 和 Highlights 数量变化。
5. 验证无卡内编辑、正文输入和完成状态。

完成条件：重启应用恢复上次位置；删除状态文件只重置视图，不影响资产。

建议分支：`codex/macos-flashcard`

## Phase 6 — Outline 退休与迁移 UI

**目标**：让正常运行路径彻底脱离旧 Outline，同时提供显式安全升级入口。

步骤：

1. 启动时识别旧 vault，展示迁移预检和不可逆说明。
2. 用户确认后调用 core 迁移器，展示备份位置和报告。
3. 用户取消时保持只读或退出选择，不让 v2 写入旧 vault。
4. 删除 Outline 导航、页面、关系 picker 和导出入口。
5. 删除或隔离旧 Outline 模型、I/O、index 与测试。
6. 确认运行路径不创建、读取或索引 `outlines/`。

完成条件：fixture 和复制的真实 vault 演练成功；旧 Outline 仅存在于备份；主应用无 Outline 可达入口。

建议分支：`codex/retire-outline-v02`

## Phase 7 — macOS 文件服务与完整 Smoke Test

**目标**：验证普通目录和第三方同步目录中的实际文件行为。

步骤：

1. 使用系统目录选择交互设置 vault，保留可解释 fallback。
2. 普通本地目录执行完整 Paper/Flashcard/恢复流程。
3. iCloud Drive 目录执行同一 smoke test。
4. 模拟外部编辑、外部删除和冲突副本；禁止静默覆盖或自动合并。
5. 验证无网络时本地可用文件仍能工作。
6. 检查应用无第三方 API、账号和后台同步。

完成条件：macOS 两类目录 smoke test 有记录；已知 provider 限制写入风险清单。

建议分支：`codex/macos-file-provider-smoke`

## Phase 8 — 产品验证与 Road 归档

**目标**：区分功能完成与产品好用。

步骤：

1. 用真实 one-shot 走完 Paper → Flashcard → 外部正文。
2. 用真实短中篇场景重复验证。
3. 记录用户是否需要跳出 Flashcard、是否频繁返回 Paper、Summary-first 是否自然。
4. 修复 P0/P1 阻塞问题；非阻塞想法进入下一 Road 候选池。
5. 全测、compile、文档链接、git diff 和 macOS 手工验收。
6. 写 Road 复盘；是否 tag 由开发者决定。

完成条件：spec §11 全部有证据；不能只以测试数量宣称 MVP 好用。

建议分支：`codex/road-v02-acceptance`

## Road 顺序摘要

```text
Phase 0  契约冻结
  ↓
Phase 1  Paper core
  ↓
Phase 2  安全迁移器
  ↓
Phase 3  Vault / Index / Recovery
  ↓
Phase 4  Paper / Library UI
  ↓
Phase 5  Flashcard
  ↓
Phase 6  迁移 UI / Outline 退休
  ↓
Phase 7  macOS 文件服务 smoke
  ↓
Phase 8  真实创作验证与归档
```

不要同时开 iOS、iPadOS 或 Pre-Advance Outline 实现；先让 macOS 核心闭环稳定。
