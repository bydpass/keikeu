# Road v0.4 CP14 — Flet retirement and final audit

> 状态：**开发者已验收；Road v0.4 完成**
> 日期：2026-07-26
> 基线：CP13 acceptance `4d510cca7b0c8d3800008506f086f07360753219`
> 分支：`codex/road-v04-cp14`

## 现在发生了什么

Gate A、Gate B、产品验收和 macOS 15.7+ 兼容性先后通过后，CP14 删除了
Flet 壳、Flet-only tests、`flet` dependency 和旧 Python GUI entry。
最终用户入口只剩 Tauri `.app`；Python Core、Markdown、Index 和 Vault
格式没有改变。

同时删除 `KeikeuService.active_vault` 与 `activate_existing_vault()` 两个
仅供 Flet adapter 使用、且退场后没有调用者的公开入口。设备每日卡状态仍由
`keikeu_bridge.local_state` 提供，原测试改为直接导入该真实模块。

## 数据怎么走

```text
用户动作
→ Vue 可见状态
→ 窄 Tauri/Rust command
→ 串行 JSONL request
→ Python Application Service
→ Python Core
→ Paper Markdown / rebuildable Index / Home-contained Vault
```

Vue 不读取或写入作者文件；Rust 不实现产品规则；mutation 不自动重试。

## 删除与保留

- 删除：`src/keikeu_app/` 的 10 个 tracked 文件。
- 删除：`tests/conftest.py`、`tests/test_app_pages.py`、
  `tests/test_migration_page.py`。
- 删除：Python project 的 `flet` dependency、`keikeu` GUI script 和
  `keikeu_app` wheel package。
- 保留：全部 Core、Bridge、JSONL、Vue 与 Rust 实现及其测试。
- 保留：Core 纯度测试中把 `flet` 列为禁止依赖的 4 个 intentional 字符串。
- 不改：依赖锁、权限、协议、Paper schema、Vault layout 或业务规则。

## 自动检查

| 命令 / 项目 | 结果 |
| --- | --- |
| 锁定工具链 | Node/npm `22.23.1`/`10.9.8`; Rust/Cargo `1.88.0`; Python/PyInstaller `3.13.14`/`6.21.0` |
| `npm --prefix frontend ci` | Pass — exact lock 安装；159 packages |
| `.venv/bin/python -m pytest -q` | Pass — `234 passed` |
| `.venv/bin/python -m compileall -q src` | Pass |
| `npm --prefix frontend run test` | Pass — `48 passed` |
| `npm --prefix frontend run build` | Pass |
| `cargo test --manifest-path frontend/src-tauri/Cargo.toml` | Pass — `10 passed` |
| `.venv/bin/python scripts/build_sidecar.py` | Pass — arm64 frozen sidecar |
| frozen sidecar `system.hello` | Pass — protocol v1, `paper-v3/index-v3` |
| `npm --prefix frontend run tauri:build` | Pass — no override |
| `.venv/bin/python scripts/check_docs.py` | Pass |
| `git diff --check` | Pass |
| `npm --prefix frontend audit --omit=dev` | Pass — 0 production vulnerabilities |

Python 测试由 CP13 的 `321` 降为 `234`，差额 `87` 正是删除的 Flet
builder/migration tests；Core、Bridge 和 fixture tests 没有删除。`npm ci`
仍报告 approved dev/test chain 的 6 个 high advisories，production tree 为 0。

## 本机 beta 工程证据

ADR-0005 的原 beta 工程例外在 CP13 开始时过期。开发者于 2026-07-26
窄批准一次性 CP14 延长，仅用于 Flet 退役后的最终工程 build 与隔离
launch/relaunch smoke。授权后的复验已通过，该一次性延长随证据记录而到期；
结果不替代或扩大 CP13 的稳定 macOS 15.7+ 兼容性结论。

本机无 override build 生成：

```text
frontend/src-tauri/target/release/bundle/macos/keikeu.app
```

- bundle id：`app.keikeu.desktop`
- `LSMinimumSystemVersion`：`15.7`
- main / sidecar：Mach-O arm64
- main `minos`：`15.7`
- frozen sidecar archive：没有 Flet entry
- main SHA-256：
  `90e427077a21053c0636fd37040f24d4e4ae7722aa4acb138e33d064cb9cfeb7`
- sidecar SHA-256：
  `b061c5be5ea2ec679b731bd89fa11cc16e195b6cf235a34618f60adbde70c519`

隔离 smoke 使用 fresh fake Home 与
`tests/fixtures/v03-vault/mixed-vault` 的副本：

1. startup handshake 解除阻塞；
2. Vault preview 识别 3 个活动 Paper；
3. 每日卡显示一次后进入 Paper，Core 报告 `paper-v3/index-v3`；
4. Flashcard 为 Summary-first、page 1、3 cards；
5. Library 显示 3 项、folder scope、Trash 和 1 个故意损坏的深层路径；
6. `Cmd+Q` 后 host/sidecar 无残留；
7. 同一 `.app` 与 fake Home 重启后直接恢复 Vault，每日卡不重复；
8. 再次退出无残留，6 个 fixture Markdown SHA-256 全部未变。

临时 Home 只产生 `.keikeu_config.json`、`.keikeu_state.json` 和 copied
Vault；精确临时根目录在退出检查后删除。真实 Home、配置和 Vault 未参与。

## 出错怎么查

1. `.app` 不解除启动闸门：先查 Rust host 与 `system.hello`。
2. method 有响应但页面失败：按 `error.layer` 查 JSONL、Service 或 Core。
3. Paper/Library 数据异常：只在 synthetic/copied Vault 复现并比较 Markdown。
4. 打包异常：先独立运行 frozen sidecar hello，再查 Tauri external binary。

## 怎么撤销

CP14 checkpoint 的回滚点是 CP13 `4d510cc`。撤销范围只包括本记录列出的
Flet 删除、两个 dead service 入口、Python metadata、测试 import 和活跃文档；
不需要转换或恢复 Vault。

## 下一步依赖什么

开发者于 2026-07-26 验收 CP14，Road v0.4 完成。CP14 push、tag、archive、
签名、公证、DMG、App Sandbox 和发布仍需各自授权。
