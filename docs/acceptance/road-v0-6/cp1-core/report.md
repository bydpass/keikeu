# Road v0.6 CP1 Paper v4 Core 证据

**日期：** 2026-08-02

**分支：** `core/cp1-paper-v4-core`

**Gate：** advance YOLO 通过；本报告随 checkpoint commit 提交

## 结论

CP1 以独立符号加入 `CardPageV4`、`PaperV4`、`parse_paper_v4_bytes` 与
`render_paper_v4_bytes`。production 的 `Paper`、`Highlight`、v3 codec、Service、Index
和 startup 调用保持原样，当前应用仍是 Paper v3 / Index v3 / protocol v1。

未发现未解决 P0/P1。CP2 可以从本 checkpoint 建立 additive 迁移与 Index v4 分支。

## 已验证契约

- 至少一页、精确空白保存谓词、名称 200 Unicode code point、非法字符、四种类型值、
  最多一个 Summary，以及 Tags 的修剪、丢空、首次去重和逗号普通字符语义。
- 无 BOM UTF-8、一致 LF/CRLF、严格 frontmatter、精确外层结构、page marker JSON、
  名称连字符转义、正文 marker 任意前置反斜线可逆和唯一末尾 Tags 区。
- renderer 固定输出 canonical LF 与一个文件末尾换行；parser 失败只抛出结构化类别与
  可确定的页序号，纯 codec 不进行文件系统写入。
- 正文首尾空行、Markdown、作者空格、未知 frontmatter 解码值及首次顺序均完成
  render→parse 和 parse→render→parse 保真验证。
- production import graph 仍引用 `Paper`、`Highlight`、`parse_paper_bytes` 与
  `render_paper_bytes`；v4 API 尚未接入 Service、Index 或 startup。

## 实际检查

| 检查 | 结果 |
| --- | --- |
| v4 model/codec focused pytest | `57 passed` |
| 全量 Python pytest | `292 passed` |
| Python compileall | 通过 |
| arm64 sidecar build | 通过 |
| 文档检查 | `47 active files`，通过 |
| `git diff --check` | 通过 |

当前源码的 Tauri dev host 使用 development-only 原型入口启动并干净退出。该入口不调用
`startup.load`，因此烟测没有打开 Vault 或触发设备状态 claim；Rust host 的启动路径仍
强制完成 `system.hello`。另一次源码 sidecar hello 实际返回 `protocol_version: 1` 与
`core_version: paper-v3/index-v3`。单独在受限 sandbox 内直接执行 PyInstaller binary
因系统 semaphore 权限失败；同一 binary 由已授权的 Tauri host 成功启动，因此该失败不
作为产品故障或独立 binary smoke 通过证据。

本 checkpoint 未运行 Vitest、Vite production build 或 Cargo tests；它们不属于 CP1
规定检查，且 Vue/Rust 源码未改。未使用真实或复制 Vault，未运行迁移、Index v4、设备
兼容、签名、公证、打包发布、作者接受、push 或 tag。

## 边界与剩余风险

- v4 Core 目前只由测试调用；production cutover 在 CP4 前保持禁止。
- CP2 尚未实现 legacy raw loss-audit、迁移事务、schema scan、Index v4、Trash 临时投影
  或 v4 Branch。
- 当前 Tauri smoke 证明现有 host/sidecar 能启动并保持 v1，不是 v4 UI、迁移或真实 Vault
  的平台证据。
