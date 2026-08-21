# Road v0.7 CP4：Library、Vault 与阻塞恢复证据

> 状态：CP4 production Library、正常 Vault context、阻塞恢复层级、自动检查与两尺寸浏览器证据已完成；开发者于 2026-08-20 以 advance YOLO 通过退出 Gate 并授权本地 checkpoint commit。本报告将随该 commit 成为 `ui/cp4-v07-library-vault` 的 HEAD。

## 基线与边界

- 日期：2026-08-21
- CP3 checkpoint：`55b5313`
- 分支：`ui/cp4-v07-library-vault`
- 进入时工作树：clean
- production：只收口 Library、Vault 与阻塞恢复的信息层级；Paper、Index、Vault、protocol 与 sidecar 合同不变
- 数据：浏览器 QA 使用内存 synthetic Paper、Library、Vault startup 与 IPC；未选择或修改真实 Vault、持久配置或作者内容

## 实现结果

- LibraryView 的重复 hero 与页面级“新 Paper / Vault”导航退出；App Shell 保持唯一全局导航。搜索、范围、排序、详情与已有操作仍由原组件承担。
- `1220×780` 保留“范围—列表—详情/操作”三段；投影详情在 `1000px` 以下进入列表之后，因而 `920×680` 保留左侧范围与列表，同时让详情和操作按文档顺序纵向到达。
- 正常 ready 且可返回的 Vault 入口先显示安静的“本地环境 / 当前 Vault”context，不读取完整路径、不调用 bridge、不自动检查或切换 Vault。“选择或维护 Vault”才进入已有 picker，并把 focus 放到路径输入。
- startup picker、migration 与 pending-intent 对账仍进入完整 VaultView；正常 context 没有绕过 migration 或 unknown-result Gate。
- runtime blocker 按 `commit_unknown`、`protocol_mismatch`、`sidecar_unavailable` 与 fallback 说明“发生了什么、保持原样、安全下一步”，保留 code/layer/recovery 与重启动作；不展示待处理内容，也不自动重放持久 mutation。
- `commit_unknown` 文案明确磁盘可能已提交或未提交；阻塞页只承诺不继续写入，并要求重启后回到对应工作面从磁盘核对，不虚构提交结论。
- 独立预提交审阅发现 Library durable mutation 未决时，两条 Paper 打开路径可绕过 Shell 锁。根因在 App-root `openPaper()` 未检查 pending 状态；修复后 App 拒绝 blocked child intent，Library 整体使用原生 `inert` 暂停交互，外部打开/reveal 也拒绝并发 handoff。
- 未增加 drawer、Router、store、endpoint、依赖、自动修复、mutation replay 或 Library 正文编辑；未修改 Python、Rust、bridge DTO 或文件行为。

## 自动检查

| Command | Result |
| --- | --- |
| `npm --prefix frontend run test -- LibraryView.test.js LibraryV4Projection.test.js VaultView.test.js App.test.js PaperView.test.js` | pass：`51 passed` in 5 files |
| `npm --prefix frontend run test` | pass：`77 passed` in 8 files |
| `npm --prefix frontend run build` | pass：32 modules transformed |
| production bundle scan for CP1 prototype-only text and selectors | pass：no match |
| `.venv/bin/python scripts/check_docs.py` | pass：active/required files and local links valid |
| `git diff --check` | pass |

## 浏览器 QA

使用隔离本地 Chromium 打开 production `/` 路由，并注入内存 synthetic Tauri IPC；检查完成后三个 task space 与各次 Vite server 均已关闭。该检查是 Vue production 浏览器证据，不是 Tauri、文件系统或真实 Vault smoke。

| 尺寸 | 结果 |
| --- | --- |
| `1220×780` | Library scope、Paper 列表与详情的实际边界按三段从左到右排列；不存在重复 Library 页头；打开、系统 handoff、Branch、移动和 Trash 动作可见；无横向溢出。 |
| `920×680` | scope 仍位于列表左侧；详情实际位于列表之后，所选 Paper 操作位于详情之后；页面高度可纵向滚动到全部操作；正常 Vault、migration 与阻塞恢复无横向溢出。 |

- 正常 Vault context 首屏没有路径输入；从 Library 打开 Vault 前后 IPC 调用数不变。显式进入维护后才出现路径输入并获得 focus，仍没有自动 bridge 调用；“取消并返回”恢复 Library 工作面与 work-surface focus。
- migration startup 直接显示“迁移旧 Vault”与 migration summary，不渲染正常 context，也不提供可取消的日常返回。
- `commit_unknown` 阻塞页显示三段安全说明、原技术字段和重启动作；没有 App Shell、作者内容或 pending mutation 摘要。协议不匹配使用不同标题，并指向同版本 app 的安全重启路径。
- Library 系统 handoff 只调用一次现有 `open_system_target`。Trash 显示“恢复 / 永久删除”；取消永久删除后没有 mutation 且 focus 留在发起按钮，恢复只调用一次 `library.restore` 并显示部分结果摘要。
- repair `details` 展开后，Finder 显示只调用一次现有 reveal handoff。真实 Tab 键进入“全部 Paper”，focus outline 为 3px；全部检查的 warning、error、unhandled rejection 为零。
- 延迟 `library.branch` 的竞态复测中，Library 标记 `inert` / `aria-busy=true`，Shell 全部 disabled；程序化触发两条 Paper 打开路径与默认编辑器 handoff 后仍停留在 Library，`paper.open` 和 `open_system_target` 均为零，Branch 仍只有一次。Promise 完成后锁解除并显示结果摘要。

## 未运行与风险

- 未运行当前源码 Tauri smoke：CP5 将重跑跨栈基线与 synthetic Vault 平台路径，覆盖 sidecar lifecycle、原生确认和残留进程。
- 未重跑 Python/Rust 基线：本 checkpoint 无 Python、Rust、schema、protocol 或文件服务变化；CP5 会在其自己的 commit 候选上重新运行，不能复制本报告结果。
- 未连接或修改真实 Vault、selected-Vault config、作者内容、provider folder 或外部编辑器；浏览器中的 Finder/default-editor 调用是 synthetic host handoff。
- 本 CP 不证明原生 Tauri crash/restart、文件服务、真实 provider、真实作者舒适度或 CP6 产品接受。
- 预提交审阅发现的 1 个 pending-lock P1 已在根因处修复，并由直接测试和 production-browser 延迟 Promise 复测通过；无未解决 P0/P1，无 scope drift。

## Exit

Library 日常路径、Trash/恢复/Finder、正常 Vault context、migration 与 runtime blocker 在两种目标尺寸下均有当前 production-browser 和直接测试证据。开发者 advance YOLO 覆盖 CP4 退出判断与本地 checkpoint commit，因此 CP4 通过；CP5 可从该 checkpoint 线性开始。
