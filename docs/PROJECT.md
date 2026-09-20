# keikeu Project Map

> 本文件提供当前坐标和按任务读取的路径。产品契约见 [SPEC](SPEC.md)，工程与 Git 规则见 [RULES](RULES.md)，执行流程见 [AGENTS](../AGENTS.md)。

更新：2026-09-20。当前执行 [Road v09](road-v09.md)，CP2 纯规则核心独立；全计划 YOLO 覆盖 CP0–CP4、本地集成与提交。v08 已中断转交，未获最终接受。

## Current coordinates

| 项目 | 当前状态 | 下一步／依据 |
| --- | --- | --- |
| 最近已接受的产品基线 | Road v0.7 CP8，`2f03aee`，Paper v4／Index v4／JSONL v2 | [完成快照](archive/snapshots/road-v0-7.html)；App-root 关闭保护随后独立接受 |
| 当前执行 | v09 CP2：纯规则 crate 已提取，正在验证 | [批准计划](road-v09.md)；v09.01 原生 iOS 替换后续单独执行 |
| 候选源码与安装 | Mac／iPhone 同产品源码 `83c4f60`；已取得安装及普通界面运行记录 | 后续主题修改已进入 `deaece8`，旧安装包不能证明该 HEAD；本轮不操作旧设备候选 |
| 验收进度 | B01–B13、B15–B16 共 15 组通过；B14 待验；CP5 随 v08 中断转交 | B10 按用户批准的实际 provider 结果验收，原生冲突保全另由 B09／B11 证明 |
| B10 证据边界 | 两轮同编号新建均产生改名 sibling；原生冲突来自已有稿并发编辑 | 保留此区分；同编号新建原生冲突这一组合没有实测证据 |
| 当前外部阻点 | B14 尚缺独立测试设备／账号条件 | [B14 SOP](acceptance/road-v0-8/b14-test-sop.md)；转交 v09.01 重新设计验证；v09 不操作账号或 Drive 设置 |
| 后续架构工作 | 独立桌面功能对等和 Python 产品运行时退役待实施 | [ADR-0009](architecture/decisions/0009-unified-rust-core-transition.md)；外部 Alpha 以该阶段通过为前提 |
| 发行 | 当前是个人开发候选 | 对外签名、公证、TestFlight、推广和发布按后续单独授权执行 |

当前 v09 在独立工作区集成候选 `deaece8`、原工作区手册 `78eb755`、归档清理 `0447e16` 与批准计划 `670142d`；原工作区和旧候选保留。此次工程接续不认定 v08 已接受，有限例外见 [ADR-0010](architecture/decisions/0010-v09-engineering-continuation.md)。

## 下一 Gate

按 [v09 检查点](road-v09.md#检查点与退出条件) 依次完成基线、目录、纯规则核心、工具与文档、整体验证。移动端采用原生组件并尽可能保留 Rust；Mac 日后重构，Windows 保留现有技术结构。本轮不含新原生界面、Windows 包、Python 退役或外部 Alpha。

截至既有记录，前端全量 142 项、Rust 21 项、Python 301 项曾分别通过；精确适用状态见各验收记录。这些是历史结果，新变更按影响面验证。

## 共享纯规则

`crates/keikeu-core/` 独立提供 Paper/Page、解析、渲染、校验、编号、Unicode 比较和错误类型。没有 Tauri、Apple SDK 或文件访问依赖；宿主 `paper::store` 继续负责文件，保存恢复及云协调仍在宿主。Rust crate 与 Python `keikeu_core` 是不同语言的包，桌面对等退役尚未实施。根 `Cargo.lock` 统一锁定，`cargo test -p keikeu-core --locked` 可单独验证规则。

## 当前后端路由

| 环境 | 实际后端 | 入口 |
| --- | --- | --- |
| Mac 本地 Vault | Python service/core，经 JSONL v2 | `PaperView.vue`、`apps/desktop/python/keikeu_bridge/` |
| Mac iCloud Vault | 进程内 Rust Paper Core＋Apple 原生协调 | `CoreWorkspace.vue`、`apps/desktop/src-tauri/src/host/` |
| iPhone 本地 Vault | 同一 Rust Paper Core | `CoreWorkspace.vue`、宿主私有状态与 app sandbox |
| iPhone iCloud Vault | Rust Paper Core＋Apple 原生协调 | `platforms/apple/Cloud.swift` |

桌面本地保留 Index、文件夹、Trash、迁移及外部编辑器能力。移动／云端候选按较窄的 Paper 能力集工作。当前路由由 [`router.rs`](../apps/desktop/src-tauri/src/host/router.rs) 与 [`bridge.rs`](../apps/desktop/src-tauri/src/bridge.rs) 确定。

## Current runtime map (Paper v4 + protocol v2)

下表前半为保留的 Mac 本地能力，末尾补充双端宿主；从受影响模块进入调用链。

| Area | Responsibility | Source | Direct evidence |
| --- | --- | --- | --- |
| Domain model | Paper v4/CardPage validation; frozen legacy model exists only in the migration module | [`models.py`](../apps/desktop/python/keikeu_core/models.py), [`legacy_v3.py`](../apps/desktop/python/keikeu_core/legacy_v3.py) | [`test_models_v4.py`](../tests/test_models_v4.py), [`test_migration_v4.py`](../tests/test_migration_v4.py) |
| Markdown | Strict Paper v4 parse/render, exact create/CAS/Branch, plus frozen legacy readers for migration | [`markdown_io.py`](../apps/desktop/python/keikeu_core/markdown_io.py), [`legacy_v3.py`](../apps/desktop/python/keikeu_core/legacy_v3.py) | [`test_markdown_v4.py`](../tests/test_markdown_v4.py) |
| Vault | Home/path validation, one-level active/Trash enumeration, global code allocation, per-Paper lifecycle, crash-visible whole-folder atomic Trash/restore, identity-pinned fd-relative permanent folder deletion, copy verification, atomic config | [`vault.py`](../apps/desktop/python/keikeu_core/vault.py) | [`test_vault.py`](../tests/test_vault.py) |
| Index | rebuildable Index v4, all-page search, first-page preview, page titles, folder/Trash projection and isolated errors | [`indexer.py`](../apps/desktop/python/keikeu_core/indexer.py) | [`test_indexer_v4.py`](../tests/test_indexer_v4.py) |
| Migration | explicit v0.1→v3 then v2/v3→v4 preflight, verified backup, loss audit, safe replacement and resume | [`migration_v01.py`](../apps/desktop/python/keikeu_core/migration_v01.py), [`migration_v4.py`](../apps/desktop/python/keikeu_core/migration_v4.py) | [`test_migration_v01.py`](../tests/test_migration_v01.py), [`test_migration_v4.py`](../tests/test_migration_v4.py) |
| Application service | startup schema Gate, Paper v4 save/reconcile, locator, Library v4, migration, structured errors and validated system targets | [`service.py`](../apps/desktop/python/keikeu_bridge/service.py), [`dto.py`](../apps/desktop/python/keikeu_bridge/dto.py) | [`test_bridge_service.py`](../tests/test_bridge_service.py) |
| JSONL sidecar | protocol v2 strict DTO/method classification, session-bound tokens, stdin/stdout isolation and one-shot mutations | [`protocol.py`](../apps/desktop/python/keikeu_bridge/protocol.py), [`sidecar.py`](../apps/desktop/python/keikeu_bridge/sidecar.py) | [`test_bridge_protocol.py`](../tests/test_bridge_protocol.py) |
| Tauri/Rust host | one sidecar, serialized requests, lifecycle cleanup, native directory picker/confirmation, and validated open/reveal | [`lib.rs`](../apps/desktop/src-tauri/src/lib.rs), [`commands.rs`](../apps/desktop/src-tauri/src/commands.rs), [`bridge.rs`](../apps/desktop/src-tauri/src/bridge.rs) | Cargo tests in `bridge.rs`; cargo build checks host/command wiring |
| Vue app shell | startup/Vault/migration gates, App-root pending durable intent and restart ownership; accepted CP8 one-row `56px` Shell. App owns the accepted Tauri close guard; Paper retains dirty/departure checks; see the independent evidence above | [`App.vue`](../apps/desktop/src/App.vue), [`bridge.js`](../apps/desktop/src/bridge.js), [`PaperView.vue`](../apps/desktop/src/PaperView.vue) | [`App.test.js`](../apps/desktop/src/App.test.js), [`bridge.test.js`](../apps/desktop/src/bridge.test.js), [`PaperView.test.js`](../apps/desktop/src/PaperView.test.js) |
| Vue Paper slice | accepted CP7 continuous Paper flow plus accepted CP8 all-page horizontal roller, portrait bounded Markdown field and bottom action Anchor; CSV-style Tags, native details, whole-Paper save, saving lock and dirty departure remain unchanged | [`PaperView.vue`](../apps/desktop/src/PaperView.vue), [`PaperV4Workbench.vue`](../apps/desktop/src/PaperV4Workbench.vue), [`tagsCsv.js`](../apps/desktop/src/tagsCsv.js) | [`PaperView.test.js`](../apps/desktop/src/PaperView.test.js), [`PaperV4Workbench.test.js`](../apps/desktop/src/PaperV4Workbench.test.js), [`tagsCsv.test.js`](../apps/desktop/src/tagsCsv.test.js) |
| Vue Library slice | CP7 composition-safe query/top-layer Paper preview plus accepted CP8 portrait `范围 / 排序` and `新文件夹` sticky Anchors with native Popovers; landscape sidebar, sort and inline creation remain | [`LibraryView.vue`](../apps/desktop/src/LibraryView.vue), [`LibraryV4Projection.vue`](../apps/desktop/src/LibraryV4Projection.vue) | [`LibraryView.test.js`](../apps/desktop/src/LibraryView.test.js), [`LibraryV4Projection.test.js`](../apps/desktop/src/LibraryV4Projection.test.js) |
| Vue Vault/migration slice | Road v0.7 quiet normal context, explicit maintenance entry, native directory intent, candidate locator, relocation/two-stage migration and restart readback | [`VaultView.vue`](../apps/desktop/src/VaultView.vue), [`bridge.js`](../apps/desktop/src/bridge.js) | [`VaultView.test.js`](../apps/desktop/src/VaultView.test.js), [`bridge.test.js`](../apps/desktop/src/bridge.test.js) |
| Device state | disposable once-per-local-day start-card claim; no page position | [`local_state.py`](../apps/desktop/python/keikeu_bridge/local_state.py) | [`test_local_state.py`](../tests/test_local_state.py) |
| 双端宿主及恢复 | 存储路由、私有草稿、冲突原字节保全、未知结果核对 | [`host/router.rs`](../apps/desktop/src-tauri/src/host/router.rs)、[`host/mod.rs`](../apps/desktop/src-tauri/src/host/mod.rs)、[`host/conflicts.rs`](../apps/desktop/src-tauri/src/host/conflicts.rs) | 同模块 Rust 测试及 CP3–CP5 验收 |
| Apple 云文件适配 | 身份、容器、下载、协调和原生版本 | [`Cloud.swift`](../platforms/apple/Cloud.swift)、[`AppleFiles.swift`](../platforms/apple/AppleFiles.swift) | CP1、CP4 和 CP5 真实 provider 记录 |
| 移动／云端工作面 | Paper 编辑、草稿、恢复与导出 | [`CoreWorkspace.vue`](../apps/desktop/src/CoreWorkspace.vue) | [`CoreWorkspace.test.js`](../apps/desktop/src/CoreWorkspace.test.js) 和候选原生检查 |

## Documentation map

- 产品与格式：[SPEC](SPEC.md)、[Paper v4 设计](design/road-v0-6-paper-v4-design.md)、[v0.8 宿主契约](design/road-v0-8-host-contract.md)。
- 当前工程：[Road v0.8](../PLAN_road_v0_8.md)、[变更图](architecture/road-v0-8-changes.html)、[CP0 宿主契约](design/road-v0-8-host-contract.md)、[CP1](acceptance/road-v0-8/cp1-apple.md)、[CP2](acceptance/road-v0-8/cp2-core.md)、[CP3](acceptance/road-v0-8/cp3-local.md)、[CP4](acceptance/road-v0-8/cp4-cloud.md)、[CP5](acceptance/road-v0-8/cp5-candidate.md)。
- 已接受的桌面界面：[App Shell](design/road-v0-7-app-shell-design.md)、[设计](design/design.html)、[交互](design/interaction.html)。[架构页](architecture/architecture.html) 与 [v0.7 交互计划](design/road-v0-7-planbook.html) 用于理解桌面基线，当前双后端按上表及源码核对。
- 决策：[文档归属](architecture/decisions/0001-document-authority.md)、[整树回收](architecture/decisions/0008-whole-folder-trash-lifecycle.md)、[Rust 收敛](architecture/decisions/0009-unified-rust-core-transition.md)。
- 工具链历史例外：[ADR-0005](architecture/decisions/0005-beta-toolchain-engineering-exception.md)，按其原适用阶段解释。
- 历史证据：[验收索引](acceptance/README.md)、[归档索引](archive/snapshots/)、[v0.5](archive/snapshots/road-v0-5.html)／[v0.6](archive/snapshots/road-v0-6.html)／[v0.7](archive/snapshots/road-v0-7.html) 快照；旧 Gate 的完整记录按需读取。
- 人类说明：[手册](manual/README.md)。Agent 交接：由现有构建器生成的忽略文件 `CONTEXT.md`，包含选定文件的当前工作树文本。
- 独立前置项：[关闭保护验收](acceptance/close-guard-2026-09-04.md)，2026-09-05 开发者确认普通退出保护；强制退出按实际已落盘草稿恢复。

## Commands

从当前 worktree 根目录运行；先使用现有兼容环境。Python 范围为 `>=3.11,<3.14`。隔离 worktree 若缺少 `.venv`，使用已核验的共享项目解释器。

```bash
./dev
.venv/bin/python -m pytest
.venv/bin/python -m compileall -q apps/desktop/python
.venv/bin/python scripts/build_sidecar.py
npm --prefix apps/desktop run test
npm --prefix apps/desktop run build
cargo test --manifest-path apps/desktop/src-tauri/Cargo.toml
npm --prefix apps/desktop run tauri:build
.venv/bin/python scripts/check_docs.py
git diff --check
```

按任务选对应命令；签名、安装和真实 provider 测试先读对应 SOP 与授权范围。
