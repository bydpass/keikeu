# Road v0.7 CP3：Paper 内容优先工作面证据

> 状态：CP3 production Paper 工作面、自动检查与两尺寸浏览器证据已完成；开发者于 2026-08-20 以 advance YOLO 通过退出 Gate 并授权本地 checkpoint commit。本报告随该 commit 成为 `ui/cp3-v07-paper` 的 HEAD。

## 基线与边界

- 日期：2026-08-21
- CP2 checkpoint：`55d45fc`
- 分支：`ui/cp3-v07-paper`
- 进入时工作树：clean
- production：只重排 Paper 信息层级并补保存期间的输入安全；Library、Vault 与阻塞文案属于 CP4
- 数据：浏览器 QA 使用内存 synthetic Paper 与 IPC；未选择或修改真实 Vault、持久配置或作者内容

## 实现结果

- 移除 PaperView 重复 hero、页面级新建/Library/Vault 导航，以及常驻 core version、绝对路径状态行；App Shell 成为唯一全局导航。
- Paper context 常驻 Paper 名、Tags、页数与必要 dirty/saving 状态；code、path、created、updated 和整份删除进入默认关闭的原生 `details`。
- 单页不渲染页码导航；多页保留真实页码按钮与 `aria-current="page"`。进一步模式位于正文之后、三个底部动作之前；类型隐藏时仍不清空。
- 删除常驻 clean 文案和卡页大阴影；长路径可换行；输入、页码、详情与底部动作保留明确 44px target/focus。
- 保存 Promise 未决时，作者字段保持当前 focus 但进入 `readonly`，页码、类型、分页、删除、整份删除与 Shell intent 均禁用；重复点击或 `Cmd+S` 不会发出第二次保存，避免保存返回后静默覆盖新输入。
- 保存成功 notice 在下一次真实编辑后清除；stale、repair、commit unknown、validation 与 Index degraded 仍靠近受影响对象。
- 未改变 Paper v4 schema、whole-Paper Save DTO、bridge、Python、Rust、Router、store、依赖或文件行为。

## 自动检查

| Command | Result |
| --- | --- |
| `npm --prefix frontend run test -- PaperV4Workbench.test.js PaperView.test.js App.test.js` | pass：`35 passed` in 3 files |
| `npm --prefix frontend run test` | pass：`72 passed` in 8 files |
| `npm --prefix frontend run build` | pass：32 modules transformed |
| production bundle scan for CP1 prototype-only text and selectors | pass：no match |
| `.venv/bin/python scripts/check_docs.py` | pass：active/required files and local links valid |
| `git diff --check` | pass |

## 浏览器 QA

使用隔离本地 Chromium 打开 production `/` 路由并注入内存 synthetic Tauri IPC；检查完成后关闭 task space 与 Vite server。该检查是 Vue production 浏览器证据，不是 Tauri、原生 macOS IME 或文件系统 smoke。

| 尺寸 | 结果 |
| --- | --- |
| `1220×780` | 无重复 hero/nav/status；Paper context 先于卡页；3 个页码中只有当前页有 `aria-current`；详情默认关闭，长路径展开后不溢出；三个动作均为 44px。 |
| `920×680` | 单页不渲染页码导航，context 显示 `1 页`；长路径展开后换行且无横向溢出；三个动作可通过明确纵向滚动完整到达。 |

- 实际 Tab 顺序覆盖 Paper 名、Tags、详情 summary、多页按钮、页标题、正文、进一步与三个动作；键盘聚焦 summary 时 outline 为 `3px solid`。
- 在正文选区位置 2 加页，原页从 `甲乙丙丁` 保留为 `甲乙`，新页为 `丙丁`；新页标题获得 focus。确认删除后页数复原，标题再次获得 focus；对话框打开时 focus 在“取消”。
- 慢保存期间只发生一次 `paper.save`；正文保持 focus 和原值，输入为只读，分页/删除/整份删除/Shell 均锁定；第二次 `Cmd+S` 与键盘输入没有改变值。保存返回后锁解除、focus 和中文正文保持。
- Chromium composition 事件序列完成后正文恰为“灵感”，没有重复或截断；随后 `Cmd+S` 仍只增加一次 whole-Paper save，并保留该文本。此项不冒充 macOS 原生 IME 证据。
- 空白页与 201 个 Unicode 字符均阻止 `paper.save`；字段旁显示错误，原始空白输入没有被静默规范化。
- synthetic Index degraded 保存后显示“Library 列表可能过期”和显式重建说明，草稿转 clean，保存仍可用，未自动触发 rebuild 或 replay。
- dirty Paper 离开：取消后 destination、中文草稿与发起按钮 focus 不变且未查询 Library；确认后只查询一次并把 focus 放入 Library 工作面。
- 两尺寸与全部交互的浏览器 warning、error、unhandled rejection 均为零；fresh Vite server 无警告输出。

## 未运行与风险

- 未运行 Tauri smoke：CP3 不改 bridge、Rust host、Python sidecar 或 lifecycle；当前源码平台路径属于 CP5。
- 未重跑 Python/Rust 基线：本 checkpoint 无 Python、Rust、schema、protocol 或文件服务变化；完整跨栈基线将在 CP5 对当前源码重跑。
- 未连接或修改真实 Vault、selected-Vault config、作者内容、provider folder 或外部编辑器。
- 浏览器 composition 不证明 macOS 原生输入法；平台级输入、原生确认和 close lifecycle 属于 CP5。
- CP3 不证明 CP4 Library/Vault、CP5 平台集成或 CP6 一号作者接受。
- 无发现的未解决 P0/P1；无 scope drift。

## Exit

创建、编辑、分页、删除、保存、保存竞态、离开保护、错误/退化状态、双尺寸、键盘与中文 composition 均有当前证据。开发者 advance YOLO 覆盖 CP3 退出判断与本地 checkpoint commit，因此 CP3 通过；CP4 可从该 checkpoint 线性开始。
