# Road v0.6 CP7 一号真实作者接受证据

**日期：** 2026-08-02

**分支：** `test/cp7-real-author-gate`

**候选基线：** CP6 `02d8ed5`

**Gate：** 实际场景完成；advance YOLO 通过；本报告随 CP7 checkpoint commit 提交

## 结论

一号作者在获准的现有 Paper v4 Vault 中完成真实灵感的创建、命名、分页、类型标记、
删页、整体保存、正常退出、独立重启、Library 找回和继续操作。开发者判断“基本功能
实现良好。经人工检验可以通过”，并在第二段报告“library，连带删除没有问题”。

第二段运行暴露一个 Tauri 确认框 P1：Library 的三个高风险删除入口直接使用
`window.confirm`，运行时连续返回 `dialog.confirm not allowed`。接受随即暂停；修复让
这些入口复用既有异步原生确认边界，并加入直接 Vitest。修复后的取消/确认两路由开发者
在实际 Tauri 中复验，结论为“没有问题”，运行日志未再出现该错误。最终无未解决 P0/P1，
CP7 由 advance YOLO 通过。

## 真实 Vault 边界

- 开发者明确授权使用一个 Home 内、系统文件提供器托管的既有 Vault；报告不记录其路径。
- 写入前只读 inspect 证明它已经是可用 Paper v4，活动区 3 份 Paper，无迁移或 repair
  Gate；selected-Vault 配置已经指向它。
- 因目标已是 v4，没有创建新 Vault、备份、迁移或 selected-Vault 配置切换。
- 两次主场景和一次修复复验后，只读检查为活动区 4 份 Paper、Index v4 与磁盘投影一致；
  设备每日卡状态为当天。新增 Paper 由作者保留。
- 文件提供器可能自行同步该路径的写入；keikeu 未管理、触发、观测或验证同步结果。
- 没有故意损坏真实作品，没有运行 repair，没有读取或记录正文、名称、Tags、相对路径、
  内容截图、稳定设备标识或原始日志。

## 实际作者场景

测试前只说明隐私、停止条件和一条完整任务，不解释按钮位置或操作方法。功能介入次数为
0；作者未报告犹豫点。

1. 第一会话用真实灵感创建 Paper，编辑 Paper 名称、页标题与正文，在真实光标处分割
   新页，设置所需类型，删除一页并确认，然后整体保存。
2. 应用正常退出，Tauri dev 进程返回 `0`；仅出现已知 macOS InputMethodKit 诊断，未见
   内容或 durable-operation 错误。
3. 第二会话独立启动，从 Library 找回并继续操作整份 Paper；作者明确判定 Library 与
   删除没有问题。
4. 运行日志随后暴露确认框 P1。停止接受后，只在 Vue 源码和合成 DTO 测试中修复；未在
   真实 Vault 重复破坏性实验。
5. 修复复验使用未保存的可丢弃草稿：进入 Library 时先取消离开，再确认放弃；两路原生
   确认均正常，草稿未写盘，应用正常退出。

## P1 修复与复验

- 根因：`LibraryView` 的永久删除 Paper、删除文件夹和永久删除文件夹绕过
  `bridge.js` 已有的 Tauri dialog 边界，直接调用被 Tauri 禁止的同步确认框。
- 修复：抽出同文件内的通用 `confirmAction()`，让离开保护和三个 Library 入口共用；
  不增加依赖、权限、Rust command 或产品能力。
- 聚焦 Vitest：2 个文件、21 个测试通过；覆盖任意原生确认 options，以及 Library 永久
  删除不会再直接调用 `window.confirm`。
- 完整 Vitest：8 个文件、63 个测试通过；Vite production build 通过，31 个 modules。
- 实际 Tauri：取消与确认两路通过；没有再次出现 `dialog.confirm not allowed`。

## 最终自动检查

| 检查 | 结果 |
| --- | --- |
| 全量 Python | `265 passed` |
| Python compileall | 通过 |
| arm64 sidecar build | 通过；SHA-256 `3ebaae1dc2525323ce5b6acb0a364db585e954ca01438de63a6393a32a057295` |
| 全量 Vitest | `63 passed`，8 个文件 |
| Vite production build | 通过；`31 modules` |
| Rust host | `12 passed`；`cargo fmt --check` 通过 |
| 文档与 whitespace | 文档 `55 active / 15 required`；`git diff --check` 通过 |

## 未执行与剩余风险

- 本 Gate 只证明一号作者在 macOS Apple Silicon 上接受，不证明二号用户、多用户 MVP、
  移动端、Intel Mac、Windows、Linux、watchOS 或市场匹配。
- 未执行真实旧 schema 迁移；既有 Vault 已是 v4。CP2/CP6 的迁移与 repair 证据仍只来自
  fixture、合成 Vault 或完整副本。
- 未测试或声称文件提供器同步时序、冲突合并、离线下载或跨设备一致性。
- 未使用外部正文编辑器；未签名、公证、staple、打包、tag、push 或发布。
- 本报告随 CP7 checkpoint commit 提交；Road closeout 仍需开发者另行授权。
