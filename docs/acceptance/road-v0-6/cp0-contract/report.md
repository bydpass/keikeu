# Road v0.6 CP0：契约与基线证据

> 状态：工程证据完成，advance YOLO exit Gate 通过；checkpoint commit 由“全部 YOLO”预先授权并以本分支 HEAD 为准。

## 基线

- 日期：2026-08-02
- 规划批准 commit：`9bb722a`
- 分支：`docs/cp0-v06-contract-baseline`
- 进入时工作树：clean
- 当前 production：Road v0.5、Paper v3、protocol v1、活动独立 Flashcard
- target：Paper v4、protocol v2、Paper 卡页；CP4 前不激活

## 范围结果

- `SPEC` 已从 v0.5 稳定边界校准为已批准 Road v0.6 target，并显式保留 current/target 分期。
- `RULES` 已校准作者字段、Paper v4 保存不变量、Flashcard 退役边界与平台矩阵。
- Architecture、Design、Interaction 三张 active HTML map 同时显示 current v0.5 与 target v0.6，不把 CP0 文档声明成已实现代码。
- Node/npm manifest lock 已从 `22.23.1`/`10.9.8` 改为 `22.23.2`/`10.9.8`；依赖版本未变化。
- ADR-0006 锁定 macOS/Xcode 27 beta 的 Road v0.6 工程例外、稳定版到期条件和后续 beta 不继承规则。
- ADR-0007 锁定 Paper v4 页模型、`initial_summary` 唯一迁移丢弃、legacy Tag 阻塞、完整备份和复核边界。
- README、PROJECT、计划和已批准设计已同步 target/current、工具链与“全部 YOLO”范围。

## 工具链观察

| Tool | Observed | Judgment |
| --- | --- | --- |
| Node / npm | `22.23.2` / `10.9.8` | exact Road v0.6 lock |
| Rust / Cargo | `1.88.0` / `1.88.0` | exact lock; `aarch64-apple-darwin` |
| Python | `3.13.14` | inside `>=3.11,<3.14` |
| macOS | `27.0 (26A5388g)`, Apple Silicon | ADR-0006 engineering only |
| Xcode | `27.0 (27A5194q)` | ADR-0006 engineering only |

## Current/target source audit

- Python 与 Rust 的 active `PROTOCOL_VERSION` 都是 `1`。
- `flashcard.open` 仍在 Python/Rust allowlist 与 active Vue caller 中，符合 CP0–CP3 production 边界。
- `CardPageV4`、`PaperV4`、v4 parser/renderer 尚未进入 `src/` 或 active tests；搜索到的 protocol `2` 仅是既有 mismatch test fixture。
- CP0 未改 Core、Service、Vue 业务调用方或 Rust policy；未写 Paper v4、未迁移数据。

## 自动检查

| Command | Result |
| --- | --- |
| `.venv/bin/python -m pytest` | pass — `235 passed` |
| `.venv/bin/python -m compileall -q src` | pass |
| `.venv/bin/python scripts/build_sidecar.py` | pass — arm64 sidecar built |
| `npm --prefix frontend run test` | pass — `64 passed` in 6 files |
| `npm --prefix frontend run build` | pass |
| `cargo test --manifest-path frontend/src-tauri/Cargo.toml` | pass — `10 passed` |
| `.venv/bin/python scripts/check_docs.py` | pass — 47 active files, 15 required files |
| `git diff --check` | pass |

第一次文档检查在重写 architecture map 后正确拦截了失去入口的 ADR-0004；恢复链接后通过。该失败没有涉及应用代码或作者数据。

## HTML map QA

使用隔离本地浏览器直接打开三张 active HTML map，并在 `1220×780` 与 `920×680` 各检查一次：

- 六种组合的 `scrollWidth` 均等于 viewport width，无横向溢出；
- 标题、current/target 状态、导航和正文均可见；
- Architecture 的 v1/v2 双轨、Design 的中央大卡页与三个底部动作、Interaction 的分页/整体保存/恢复约束均正确呈现；
- 截图只存于临时目录用于当次检查，未加入仓库。

## 未运行与边界

- 未运行 Tauri 应用 smoke：CP0 不改 application source、bridge contract 或 lifecycle；完整 Python/Vue/Rust checks 与 sidecar/Vite build 已运行。
- 未连接、读取或修改真实 Vault、selected-Vault config、持久应用状态或作者内容。
- 未执行迁移、删除、修复、签名、公证、DMG、发布、push、tag 或 closeout。
- CP0 不证明 Paper v4 已实现；下一 Gate 是 additive CP1 Core。

## Exit

本报告进入 active documentation graph 后，文档检查与 `git diff --check` 再次通过；最终 source/current audit 未发现 protocol v2 提前激活或 Paper v4 实现混入。无 P0/P1，CP0 由 advance YOLO 通过，checkpoint commit 以本分支 HEAD 为准。下一 Gate 是从该提交建立 `core/cp1-paper-v4-core`。
