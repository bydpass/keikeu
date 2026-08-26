# Road v0.7 CP7 连续编辑流与 Gate D 验收记录

**日期：** 2026-08-25

**分支：** `ui/cp7-v07-continuous-flow`

**进入基线：** preparation/hygiene `528124d`

**Gate：** 开发者明确通过 CP7 Gate D；本报告已进入本地 checkpoint `1e17cea`

## 结论

开发者在两轮 UI/功能整改后明确判定 CP7 Gate D 通过。连续编辑流、默认 `720×900`
窗口、单行 CSV-style Tags、轻量原生 Popover、quiet focus、完整文件夹 Trash 生命周期、
Library composition-safe 查询与 top-layer Paper 预览进入 Road v0.7 已接受产品边界；退出时
没有未解决 P0/P1。

本结论不把自动化 composition 序列冒充 macOS 原生候选窗观察。CP7 当时未完成该观察；
实体键盘与系统简体拼音复核随后在 CP8 通过，但它仍不是补写成已完成的 CP7 证据。

## Gate 记录

| Gate | 结果 |
| --- | --- |
| Gate A · 合同 | 2026-08-24 通过 |
| Gate B · Figma | 2026-08-25 经开发者明确判断通过 |
| Gate C · production / 工程 | 原始实现与两轮整改复核完成 |
| Gate D · 开发者 UI | 2026-08-25 明确通过；无未解决 P0/P1 |

## 实现边界

- Paper 是 context → 页导航 → 当前页 → 动作的连续纵向流；无常驻 dirty 提示。
- Tags 只在 Vue 字段边界使用可逆 CSV-style 表示，Paper v4、DTO 与 Markdown 数组语义不变。
- Paper 详情和 Library 预览使用 native Popover，不进入文档流。
- Library composition 期间不发查询，提交最终中文值时同值去重。
- 普通文件夹删除/恢复原子移动完整目录树；永久删除只在废纸篓二次确认后执行
  identity-pinned、fd-relative、symlink-safe 递归。
- 默认 Tauri 几何为 `720×900`，最小 `720×680`；Core 例外只限既有三个文件夹生命
  周期方法。Paper v4、Index v4、protocol v2、DTO、Rust command 与 sidecar 不变。

## 实际工程证据

- pytest：`283 passed`。
- Vitest：`9` 个文件、`99 passed`。
- Rust：`12 passed`；Cargo fmt 通过。
- Python compileall、sidecar build、Vite production build、debug `.app` bundle、文档检查、
  production bundle marker scan 与 `git diff --check` 通过。
- 真实 Chromium 在 `375×812`、`720×900`、`920×680`、`1220×780` 复核长名称、
  Popover 与 document 无横向溢出。
- 隔离 fake Home / synthetic Vault 的 debug `.app` smoke 通过；未触碰真实 Vault。
- composition 自动化在 `b` / `ba` 阶段零查询，提交“暴食”后只新增一次查询。

本轮 checkpoint closeout 又在同一工作树实际重跑：pytest `284 passed`、Vitest `9` 个
文件 / `100 passed`、Rust `12 passed`、Python compileall、Cargo fmt、sidecar build、Vite
build、debug `.app` bundle、文档检查（`71` active / `15` required）、production bundle
marker scan 与 `git diff --check` 全部通过。应用 smoke 使用前述整改后记录，不复制为本轮
重新启动证据。

## Figma 与文档

- Gate B 母版和 Gate D 后续整改位于同一 Figma Page `71:2`；后续 Section 为 `152:138`。
- CP7 状态已同步到 SPEC、PLAN、PROJECT、详细设计、active maps、README、Planbook 与
  必要手册；过时的“实施中 / 等待复验”文案不再作为当前事实。
- CP8 已先保存 `CP7 Gate D accepted · before CP8 overwrite` 版本历史，再原位覆写该 Page；
  CP7 视觉历史由 Figma version history 保存，未建立第二套活动母版。

## 未执行与剩余风险

- CP7 当时未观察 macOS 原生候选窗；CP8 把候选窗缺失、选择前重渲染、出现中间拼音查询或
  最终值重复提交列为 P1 阻断，并在后续实体键盘 Gate 中确认四类阻断均未出现。
- 未操作真实 Vault、provider 同步或作者内容；未记录 Vault 路径、Paper 名称或正文。
- 永久递归销毁经不可撤销确认后仍可能因权限、ACL 或并发文件系统变化而部分完成；
  预检会阻断已知挂载/身份问题，运行中失败会恢复并报告剩余树，但已销毁 entry 不可回滚。
- 未 push、tag、closeout、签名、公证、DMG 或发布。
- CP7 checkpoint commit 是 `1e17cea`；CP8 checkpoint commit 仍需开发者另行判断。
