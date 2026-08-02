# Road v0.6 CP3 Vue v4 预备层证据

**日期：** 2026-08-02

**分支：** `ui/cp3-paper-v4-development`

**Gate：** advance YOLO 通过；本报告随 checkpoint commit 提交

## 结论

CP3 在既有 `?prototype=1` development-only 入口完成可供 CP4 直接接线的
`PaperV4Workbench` 与 `LibraryV4Projection`。两个候选组件只通过 props/emits 接收
数据和意图，不 import bridge、不写文件；原型只使用内存合成 DTO，并醒目标明不连接
Vault。production 默认路径、Paper v3、protocol v1 与 Flashcard 仍保持活动。

浏览器 QA 首次发现 Library 搜索后详情仍指向未过滤 Paper；已在详情投影根因处修正并
加入回归测试。最终未发现未解决 P0/P1，CP4 可直接接线而不复制第二套卡页或 Library UI。

## 已验证交互

- Paper 名称与页标题始终可编辑；Tags 每行一个，逗号保持普通字符。
- 卡页支持基础/进一步模式、`null`/总结/高光/碎碎念，隐藏模式不清除类型；已有总结时
  其他页仍显示但禁用“总结”。
- 页码为真实按钮；加页覆盖光标首/中/尾、选区与从未聚焦时末尾截断，新页名称/类型为
  null 并聚焦标题。删除覆盖普通页与唯一页替换；确认框初始聚焦取消，`Escape` 返回
  删除按钮。底部动作严格为保存、删除本页、加一页。
- draft/baseline、dirty、合成整体保存、离开保护和 `Cmd+S` 已验证；`ui_key` 不进入 DTO。
- Library 展示第一页预览、页数、所有页标题、Tags、folder 与时间；搜索覆盖全部投影字段，
  详情始终跟随过滤结果，打开整份 Paper 的第一页而非单页 deep-link。
- stale、`repair_required`、`index_degraded` 与 `commit_unknown` 有独立状态；阻塞状态禁止保存，
  degraded 只显示显式 rebuild 意图。
- 200/201 个 astral emoji 证明名称按 Unicode code point 计数；输入没有 `maxlength`。

## 实际检查

| 检查 | 结果 |
| --- | --- |
| CP3 聚焦 Vitest | `32 passed` |
| 全量 Vitest | `83 passed` |
| Vite production build | 通过；`29 modules` |
| Cargo tests | `10 passed` |
| 文档检查 | `49 active files`，通过 |
| `git diff --check` | 通过 |

浏览器实测 `1220×780`、`920×680` 与 `920×680` 的 200% 文本缩放均无水平溢出；
已核对 Tab 顺序、Enter/Space、`Cmd+S`、原生类型选择、分页、截断、加删页焦点和确认框
`Escape`。所有可见 form control 均有 label 或可访问名称；共享 `:focus-visible` 规则仍在。
抽查的主要文本色对比为 `5.60:1`–`15.78:1`。没有历史截图 baseline，因此自动视觉回归
结论为“不确定”；人工检查本次截图未发现阻塞性视觉问题。

去内容截图：

- [`paper-1220x780.png`](screenshots/paper-1220x780.png)
- [`paper-920x680.png`](screenshots/paper-920x680.png)
- [`paper-text-200.png`](screenshots/paper-text-200.png)
- [`library-920x680.png`](screenshots/library-920x680.png)
- [`tauri-default-v3.png`](screenshots/tauri-default-v3.png)

production build 中搜索不到 CP3 原型标题、声明或 CSS 文案。默认 URL 的 Tauri 窗口在
逻辑 `1220×780` 下使用临时合成 protocol-v1 sidecar 启动，画面实际显示
`ROAD v0.5 · PAPER`、`paper-v3/index-v3`、Summary/Highlights 与 Flash 导航。
操作系统拒绝自动点击原生窗口内的 Flash 导航，因此该原生点击未声称通过；聚焦 App
测试实际触发并验证 Flashcard route。CP2 已另以真实打包 sidecar 验证 protocol-v1 hello。

临时合成 sidecar 没有读取配置或 Vault；结束后原 Mach-O 已恢复，恢复后 SHA-256 与替换前
一致。未改 `HOME`、selected Vault、持久应用状态、真实作者内容或真实路径。

## 边界与剩余风险

- CP3 组件尚未接 production bridge；protocol v2、locator、pending intent、迁移 Gate 和
  durable mutation 由 CP4 完成。
- 本 Gate 没有真实或复制 Vault，没有真实迁移、Index 写入、作者接受、设备兼容、签名、
  公证、打包发布、push 或 tag。
- 原生 Tauri Flashcard 点击缺少平台自动化证据；当前证据由可见活动导航与 App 路由测试
  组合构成。CP4 的合成/复制 Vault Tauri smoke 必须覆盖实际导航与完整生产主流程。
