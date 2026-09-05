# 独立关闭保护修复：报告与代码导读

> 2026-09-04 开始；基线 `17d6a50`，分支 `codex/fix-app-close-guard`。
> 2026-09-05 开发者授权提交此独立修复并从新分支推进 Road；聚焦测试与本机原生窗口验证已执行，开发者于 2026-09-05 完成人工复核，独立关闭保护前置验收通过。
> 这不是 Road v0.8 CP0；代理检查与开发者人工复核分别记录，强制退出不在关闭保护保证内。

## 1. 问题与修复

原先 App 保留未知写入的内存快照，PaperView 却独占窗口关闭监听器。
切换到 Library、Vault 或运行阻塞页时，PaperView 卸载会注销监听器；
监听器又在异步启动读取完成后才安装，启动阶段也存在空档。

- `App.vue` 在开放工作面前安装唯一监听器，页面更换不注销，App 卸载才清理。
- 正在执行的持久请求、Core 重启及 Shell 导航期间拒绝关闭；未知结果与执行中请求分开判断。
- 无未决操作时复用 Paper 的 `confirmDeparture()`；有未知结果时明确说明放弃的是内存草稿或操作记录，不能撤销已经发生的磁盘操作。
- 用户确认后仍保留快照，直到窗口真正销毁；确认失败、取消、状态变化均不放行。
- `bridge.js` 合并同时到来的关闭请求，避免重复弹窗；窗口销毁失败后仍可再次请求关闭。
- 原生验证额外复现 macOS 默认 Quit／`Cmd+Q` 直接终止应用、绕过窗口监听器。
  `lib.rs` 将默认菜单中的 Quit 替换为 `window.close()`，保留其他默认菜单项与快捷键。
  菜单位置与文本按锁定的 Tauri 版本核对，不匹配则启动失败，不静默保留危险的 Quit。

不改变 Paper v4、Index、protocol v2、Python 业务行为、依赖版本或持久草稿策略。

## 2. 如何读懂这次修改

```text
窗口关闭按钮 / 菜单 Quit（Cmd+Q）
  → 请求关闭主窗口
  → App 的监听器先阻止默认关闭
  → 写入仍在执行？保持窗口
  → 结果未知？明确询问是否放弃内存记录
  → 否则询问 Paper 是否允许离开
  → 再检查状态没有改变
  → 允许后销毁窗口，结束 host 与 sidecar
```

**生命周期要一致。** 全应用的数据由 App 保管，保护它的监听器也必须活到 App 结束。
Paper 只需要继续负责自身的 dirty／baseline 判断，不必知道 Library 或 Vault 的操作规则。

**`await` 前后的状态可能不同。** 确认弹窗是异步的，返回“同意”时要重新检查未决操作，
不能把旧问题的答案当成新状态的授权。执行中的请求计数在 `finally` 中释放，成功和异常都不会漏掉。

**同意关闭不等于已经关闭。** 窗口销毁也可能失败，因此确认时不提前清空唯一草稿快照。
Tauri 的 [`close()` 与 `destroy()`](https://v2.tauri.app/reference/javascript/api/namespacewindow/)
分别对应可拦截的关闭请求与实际销毁；本次复用既有边界，不自动保存或重发业务请求。

阅读顺序：[App](../../frontend/src/App.vue) → [PaperView](../../frontend/src/PaperView.vue) →
[bridge](../../frontend/src/bridge.js) → [Rust 菜单](../../frontend/src-tauri/src/lib.rs) →
[App 回归测试](../../frontend/src/App.test.js)。

## 3. 自动检查

新增 App 场景先在旧实现上运行：7 项失败，另有监听器注册失败导致的未处理异常；
错误包含页面注销监听器、Library／Vault 写入时错误放行以及阻塞页缺少监听器。

| 检查 | 实际结果 |
| --- | --- |
| 聚焦 App／Paper／bridge 测试，第一轮修复后 | 42 通过 |
| 全量 `npm --prefix frontend run test`，包含新增并发关闭测试 | 128 通过，9 个文件 |
| `npm --prefix frontend run build` | 通过，33 个模块 |
| `cargo build --offline --manifest-path frontend/src-tauri/Cargo.toml` | 通过，原生候选已重建 |
| `cargo test --offline --manifest-path frontend/src-tauri/Cargo.toml` | 12 通过；不把现有 Rust 单元测试算作菜单交互证据 |
| `cargo fmt --manifest-path frontend/src-tauri/Cargo.toml --check` | 通过 |
| `.venv/bin/python scripts/build_sidecar.py` | 通过，使用现有 PyInstaller；未使用 Developer ID 身份 |
| `.venv/bin/python scripts/check_docs.py` 与 `git diff --check` | 通过；72 个活动文档及本地链接有效 |

全量前端检查使用现有 Node `22.23.2`；最初红灯及第一轮聚焦检查使用默认 Node `26.8.1`。
Rust `1.88.0`，Python `3.13.15`，macOS `27.0 (26A5425a)`，Xcode `27.0 (27A5194q)`。
这是本机工程环境证据，不能替代稳定系统兼容性、签名分发或实体 iPhone 验证。
Python 业务未改，本轮未重跑 Python 全量测试。

## 4. 原生窗口与故障验证

候选使用本次重建的 Rust host、当前 Vue 开发入口及重建的正常 sidecar。
合成 Vault、临时 Home、临时应用、故障适配器和方法计数保留在本次
`tests/test-vault/close-guard.*` 隔离目录；临时应用并非分发包。
故障适配器调用当前 Python dispatcher，只控制指定合成请求的响应时机／ID，不记录参数或正文。

| 场景 | 观察结果 |
| --- | --- |
| Paper dirty → 关闭按钮 → 继续编辑 | 原生确认出现，取消后正文完整保留 |
| Paper dirty → Cmd+Q | 先复现旧菜单绕过；修复后的原生候选弹出同一确认，取消后正文保留 |
| 正常保存 → Library → 关闭按钮 | 正常退出；随后发生下节记录的工具自动重启事件 |
| Paper 保存已落盘但响应 ID 错误 | 进入 `commit_unknown`，Paper 卸载；关闭仍弹出“放弃草稿并关闭／留下核对” |
| 未知保存 → 留下核对 → 重启 Core | 正文恢复，显示已确认上次保存落盘；未重发保存 |
| Library Branch 请求等待期间 → 关闭按钮 | 窗口保持，写入返回后显示一次成功 |
| Vault open 请求等待期间 → Cmd+Q | 窗口保持，返回后进入正常工作面 |
| Library Branch 响应丢失 → Cmd+Q | 明确提示放弃操作记录不会撤销磁盘操作；确认后 host 与 sidecar 均退出 |

故障运行日志：`paper.save=1`、`paper.reconcile_save=1`、`library.branch=2`、`vault.open=1`。
两次 Branch 均由人工操作触发；合成 Paper 最终 4 份，未出现自动重发生成的额外副本。

## 5. 工具意外重启与数据边界

界面检查工具在一次正常关闭后自动重新启动临时应用，新进程没有继承启动命令的隔离 Home。
确认此事后停止该进程及其 sidecar。该次启动可能按正常流程读取正式配置／Vault；
实际观察到正式 `.keikeu_state.json` 的 `last_daily_card_date` 状态文件更新。
因此本轮不能声称“未读取真实 Vault”或“正式本机状态完全未变”。

没有在额外进程中执行编辑、保存、删除、迁移或资料管理动作；正式 Vault 选择配置的修改时间未变。
没有事前的设备状态副本，所以未猜测旧值、未自动回写。此事件已即时向开发者披露。
后续测试改用独立应用标识、固定 Home 的启动环境及 `LSEnvironment`，并实际核对进程 Home；
允许退出后只检查进程，不再向已退出的应用请求界面状态。

## 6. 开发者人工复核与验收

2026-09-05，开发者在本任务中确认：

> 经人工复核，除强制退出外，所有常规退出入口受到保护

据此，独立关闭保护前置验收通过。此项属于开发者人工复核证据；§4 保留代理实际执行的场景，
不补造逐入口步骤、设备或构建信息，也不将人工结论记作新增自动测试。
本次确认不批准软件 CP0 seed，不授予提交、推送或真实 Vault 操作权限。

## 7. 剩余边界与下一步

- 代理原生检查仅覆盖 §4 所列路径；常规退出入口的整体通过结论来自 §6 的开发者人工复核。WebView 崩溃不属于常规退出，本次未验证。
- 强制退出、断电仍可能丢失内存草稿；本次不增加持久恢复区，也不扩大已有保证。
- 未执行真实 provider、外部编辑器、iPhone／iCloud、稳定系统发布构建或完整产品作者验收；关闭保护的专项人工验收见 §6。
- 开发者随后授权本地提交及独立分支实施，并提供 CP0–CP5 YOLO；阶段仍须具备实际证据。下一步从此修复提交建立 CP0 分支。
- 本报告随独立关闭修复提交；精确 checkpoint 由 Git 记录。未推送；原工作树 AGENTS、CLAUDE 与 keikeu-routine 修改保留。

[返回证据索引](README.md)
