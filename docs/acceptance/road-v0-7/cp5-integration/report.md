# Road v0.7 CP5：跨栈集成与安全 Gate 证据

> 状态：CP5 全量自动检查、当前源码 Tauri 合成 Vault 主链与故障恢复证据已完成；开发者以 advance YOLO 通过退出 Gate。本报告已随 checkpoint commit `3259c42` 提交，该 commit 是 `test/cp5-v07-integration` 的 HEAD。

## 基线与边界

- 日期：2026-08-21
- CP4 checkpoint：`6f69310`
- 分支：`test/cp5-v07-integration`
- 进入时工作树：clean
- production：仍是 Vue 3 → Tauri/Rust → JSONL v2 → Python service/core → Paper v4 / Index v4；CP5 未修改产品代码、schema、DTO、protocol、依赖或 capability
- 数据：Tauri smoke 的配置、状态、Vault 与 fault audit 写入只进入仓库已忽略的 `tests/test-vault/cp5-v07.D0gTO2/`；host 使用该目录内的隔离 `HOME` 与 `TMPDIR`。标准 build 产物仍进入仓库既有 ignored build 路径
- 未选择、读取、迁移或修改真实 Vault、真实 selected-Vault 配置、作者内容、provider 目录或远端状态

## 结论

当前 CP4 源码候选通过完整 Python、Vue、Rust、sidecar 与文档基线。真实 Tauri 窗口完成启动、Vault 初始化、两页 Paper 创建与保存、Library 找回、Vault 往返、原生 dirty departure 两分支、`920×680`、Index degraded/rebuild、普通 repair/recheck、`commit_unknown` 阻塞及重启后只读恢复。临时 fault sidecar 只在 `library.branch` 已落盘后改错一次响应 ID；审计确认原 mutation 没有 replay。

本 checkpoint 未发现未解决 P0/P1，也未发现 scope drift。CP5 只证明本机 synthetic 工程与平台 Gate；不证明真实 provider、真实作者流程、CP6 或产品接受。

## 全量自动检查

| Command | Result |
| --- | --- |
| `.venv/bin/python -m pytest` | pass：`265 passed in 1.58s` |
| `.venv/bin/python -m compileall -q src` | pass |
| `.venv/bin/python scripts/build_sidecar.py` | pass：arm64 Mach-O；最终复跑产物 SHA-256 `175ce674c37db0f91ecee897ac636fa0359e58650eb3641fe38b8e3f1f1f0bd2` |
| `npm --prefix frontend run test` | pass：`77 passed` in 8 files |
| `npm --prefix frontend run build` | pass：32 modules transformed |
| `cargo test --manifest-path frontend/src-tauri/Cargo.toml` | pass：`12 passed` |
| `cargo fmt --manifest-path frontend/src-tauri/Cargo.toml --check` | pass |
| production bundle scan for CP1 prototype-only text and selectors | pass：no match |
| `.venv/bin/python scripts/check_docs.py` | pass：active/required files and local links valid |
| `git diff --check` | pass |

PyInstaller 只报告冻结导入占位、`collections.abc` 解析提示和 Windows-only 模块提示；当前 arm64 构建未被阻断。

## 当前源码 Tauri synthetic smoke

### 正常 sidecar 主链

实际启动当前 Vue、Rust host、JSONL v2 与本次重新构建的 Python sidecar，并在隔离 blank Home 内完成：

```text
startup picker → inspect empty path → initialize synthetic Vault
→ 创建并命名 Paper → 填写 Tags → 两页与一种 page type → Cmd+S
→ parser 只读核对两页 → Library 找回并打开整份 Paper
→ quiet Vault context → 显式维护入口 → 取消并返回同一 Paper
→ dirty 后去 Library：继续编辑 → draft 保留
→ 再次去 Library：放弃更改 → 磁盘仍是已保存版本
```

- Parser 核对为 1 份 Paper、2 页、2 个 Tags、两页正文非空，type 为 `null / summary`；报告不保留合成正文。
- 原生 macOS sheet 的“继续编辑”和“放弃更改”均由 System Events 找到具名按钮并实际点击；取消后仍在同一 Paper 且 draft 保留，focus 返回发起动作 `AXButton / Library`；确认后只离开一次，未保存尾注未进入磁盘。
- 已保存 Paper 经 Vault context、维护入口与“取消并返回”后仍保持同一名称和 2 页。
- 默认窗口实际返回 `1220×780`；经 AX resize 后实际返回 `920×680`，Paper、Library、新 Paper、Vault、正文与三个底部动作仍在可访问性树中。

### Index degraded 与 repair

- 将 synthetic Vault 的 `keikeu_index.json` 精确移动到本次 smoke root 作为可恢复备份后，重新进入 Library，实际显示“Index 可能过期；Paper 内容仍可用”与“显式重建 Index”；Paper 仍可找回。
- 实际点击显式重建后，`verify_index_v4()` 返回 `True`，新的 Index 为 current。
- 对 synthetic Paper 做逐字节备份，只把第 2 页 type 从 `summary` 临时改为 `invalid`。Library 打开后实际进入 `REPAIR REQUIRED`，显示 `cache/K-20260821-001.md`、第 2 页、Finder 与重新检查动作。
- 恢复唯一字段后 SHA-256 与备份一致；实际点击“重新检查”回到同一 2 页 Paper。App 没有自动改写损坏文件。

### `commit_unknown` 与 no-replay

只在本次 ignored debug 副本上临时运行基于当前 `KeikeuService` / `JsonlDispatcher` 的 fault sidecar。它不记录 params 或内容，只统计 method 名；第一次成功执行 `library.branch` 后把 response ID 改错一次，后续重启不再注入。

```text
Library → Branch 落盘一次 → 错误 response ID
→ App 显示 commit_unknown blocker
→ 重启本地 Core → startup.load → verified Library query
→ 两份 Paper 可见；上次操作只读核对提示可见
```

- 阻塞页实际显示 `commit_unknown / tauri_host / restart_then_reload`，说明磁盘结果未知、不继续改写且不会自动重放。
- 去内容化审计为 `library.branch=1`、`startup.load=2`、`library.query=2`；磁盘 Paper 数从 1 变为 2，没有第三份 Branch。
- fault 后将 smoke 启动前备份的正常 debug sidecar 按 SHA-256 `5d70d85f51a357b0be2fa7d9f266e5304fda367b9d6af40ae4092034bacf5c21` 原样恢复；随后用正常 sidecar 再启动一次，Library 实际显示两份 Paper并正常退出。最终门禁又执行了一次 PyInstaller 构建，因此上表的最终 ignored 构建产物有不同 SHA；两者不被表述为可复现构建。
- 该注入只证明当前 App/Rust host 对响应丢失的阻塞、重启与 no-replay 行为；不声称 production sidecar 自发故障，也不替代完整自动故障矩阵。

## 生命周期与观测边界

- 正常主链、fault-injected 主链和恢复后的正常启动均通过 App 的正常退出路径结束。每次记录的 host、sidecar、Vite 与父进程 PID 均在退出后 `kill -0` 失败，端口 `1420` 无 listener。
- Tauri/Vite PTY 未报告 runtime/build error；仅正常主链退出时出现 npm 新版本提示。
- 没有单独保存 WebView console，也无法从 Rust host 取得 sidecar stderr 内容，因此不声称“WebView console 为零”或“sidecar stderr 为零”。此前 production-browser console 证据仍只属于 CP2–CP4 各自报告。
- synthetic root、临时 fault source、audit、备份和 npm cache 在记录完成后精确移入 macOS 废纸篓；仓库路径已不存在，废纸篓清空前仍可恢复。没有清理或读取 `tests/test-vault/` 的其他历史目录。

## 未执行与剩余风险

- 未使用真实 Vault、真实作者内容、iCloud/provider service、外部正文编辑器、真实迁移、签名、公证、DMG、Intel Mac、移动端或 Windows。
- synthetic Home 与本机普通目录不证明 provider 占位文件、跨设备时序、外部卷或真实作者舒适度。
- 未单独重跑 macOS 原生中文输入法 composition；CP3 的 composition 与字段行为仍是 production-browser/直接测试证据，不在本报告冒充原生 IME 结果。
- CP6 一号作者 Gate 仍需要单独的真实 Vault 授权与去标识化完成记录。push、tag、closeout 与发布仍未授权。

## Exit

§3.2 全量检查、production bundle 隔离、当前源码 synthetic Tauri 主链、原生 dirty 双分支、两尺寸、Index/repair、fault-injected `commit_unknown` no-replay、sidecar 恢复和子进程清理均有本次证据。独立复核未发现未解决 P0/P1。开发者 advance YOLO 覆盖 CP5 退出判断与本地 checkpoint commit，因此 CP5 通过；CP6 可从该 checkpoint 线性开始，但不能在未获真实 Vault 授权时伪报完成。
