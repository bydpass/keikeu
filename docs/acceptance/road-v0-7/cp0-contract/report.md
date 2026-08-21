# Road v0.7 CP0：合同与基线证据

> 状态：CP0 文档与自动证据已完成；开发者于 2026-08-20 以 advance YOLO 通过退出 Gate 并授权本地 checkpoint commit。本报告随该 commit 成为 `docs/cp0-v07-contract` 的 HEAD。

## 基线

- 日期：2026-08-20
- 批准目标与计划 commit：`d8aca4a`
- CP0 分支基线：`558202b`
- 分支：`docs/cp0-v07-contract`
- 进入时工作树：clean
- current production：已接受的 Road v0.6 Paper v4 / Index v4 / protocol v2
- approved target：Road v0.7 App Shell 与信息层级；尚未实现

## 范围结果

- `SPEC` 现区分 current v0.6 与 target v0.7；Paper、Index、Vault、protocol、Python 与 Rust 合同不变。
- `PROJECT` 现记录 current、target、CP0 状态与下一 Gate；源码和测试仍是 runtime 事实。
- Design、Interaction 与 Architecture 三张 active map 保留 v0.6 current，并单独标出尚未实现的 v0.7 target。
- 已批准设计拥有唯一详细验收矩阵，冻结 App Shell、Paper、Library、Vault/阻塞恢复、窗口与可访问性判据。
- 冷启动入口、计划索引和仍自称 current 的旧手册已同步；archive、generated 与明确历史证据保持不动。
- CP0 未修改 production source、DTO、schema、依赖、Vault 或持久配置。

## Python 基线失败与修复

第一次运行 `.venv/bin/python -m pytest` 在收集阶段失败：`tests/test-vault/` 中保留的合成安全 fixture 含一个指向 `/private/tmp` 的目录 symlink，pytest 递归进入其中的仓库副本并报告 11 个同名 module import mismatch；0 个测试执行。

根因是 `.gitignore` 只约束 Git，不约束 pytest collection。安全测试故意保留该 symlink 来证明越界备份会被拒绝，fixture 本身不应被删除或改写。`pyproject.toml` 因此在既有 `--basetemp` 后增加 `--ignore=tests/test-vault`，只排除规则已定义为合成临时数据的目录。原命令随后收集并通过 265 个 tracked 测试；精确 symlink 越界测试也单独通过。

## 自动检查

| Command | Result |
| --- | --- |
| `.venv/bin/python -m pytest` | 首次 fail：收集污染、11 个 import mismatch、0 tests；修复后 pass：`265 passed` |
| `.venv/bin/python -m pytest tests/test_migration_v01.py::test_backup_root_symlink_escape_is_rejected_before_writing -q` | pass：`1 passed` |
| `.venv/bin/python -m compileall -q src` | pass |
| `.venv/bin/python scripts/build_sidecar.py` | pass：PyInstaller 6.21.0 生成 ignored arm64 sidecar |
| `npm --prefix frontend run test` | pass：`63 passed` in 8 files |
| `npm --prefix frontend run build` | pass：31 modules transformed |
| `cargo test --manifest-path frontend/src-tauri/Cargo.toml` | pass：`12 passed` |
| `cargo fmt --manifest-path frontend/src-tauri/Cargo.toml --check` | pass |
| `.venv/bin/python scripts/check_docs.py` | pass：`63 active files, 15 required files` |
| `git diff --check` | pass |

## HTML map QA

使用隔离本地 Chromium 直接打开 Design、Interaction 与 Architecture 三张 active map，并在 `1220×780` 与 `920×680` 各检查一次：

- 六种组合的 `scrollWidth` 均等于 viewport width，无横向溢出；
- 每页标题与正文都同时包含 current 和 target 标签；
- 三页均保留 `data-doc-search` 与 `data-theme-toggle` marker；
- 浏览器 task space 已在检查后关闭，未保留页面或截图。

## 未运行与边界

- 未运行 Tauri 应用 smoke：CP0 不改 application source、bridge contract 或 lifecycle；该 smoke 属于后续实现/集成 Gate。
- 未连接、读取或修改真实 Vault、selected-Vault config、持久应用状态或作者内容。
- 未执行迁移、删除、恢复实验、provider-folder 操作、外部编辑器 handoff、签名、公证、DMG、发布、push、tag 或 closeout。
- 自动检查与 map QA 是 CP0 工程证据；开发者退出判断由 advance YOLO 单独提供。它们不证明 CP1 原型、production 实现、平台流程或产品接受。

## Exit

当前没有未解释的基线失败或发现的 P0/P1。开发者 advance YOLO 已覆盖 CP0 退出判断与本地 checkpoint commit，因此 CP0 通过；CP1 可从该 checkpoint commit 线性开始。真实 Vault、production 实现、平台流程与产品接受仍未由 CP0 证明。
