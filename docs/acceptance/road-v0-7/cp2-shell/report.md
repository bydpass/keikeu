# Road v0.7 CP2：Production App Shell 证据

> 状态：CP2 production Shell、自动检查与两尺寸浏览器证据已完成；开发者于 2026-08-20 以 advance YOLO 通过退出 Gate 并授权本地 checkpoint commit。本报告随该 commit 成为 `ui/cp2-v07-shell` 的 HEAD。

## 基线与边界

- 日期：2026-08-20
- CP1 checkpoint：`8019969`
- 分支：`ui/cp2-v07-shell`
- 进入时工作树：clean
- production：只收口 App Shell 与跨页面 intent；Paper、Library、Vault 内部层级仍分别属于 CP3、CP4
- 数据：浏览器 QA 使用内存 synthetic Paper/Library 与故障响应；未选择或修改真实 Vault、持久配置或作者内容

## 实现结果

- `App.vue` 直接加入 56px 紧凑顶栏；Paper 与 Library 是同级日常位置，新 Paper 是动作，Vault 是环境入口。当前位置同时用文字、`aria-current` 与底边表达。
- Shell 离开 Paper 时只调用 `PaperView.confirmDeparture()`；该窄接口复用原有 dirty/pending-save 确认规则，没有第二套 guard。
- Paper 打开或保存后向 App 回报当前 path；Vault 取消后返回原位置与同一份已保存 Paper。新 Paper 仅在 guard 通过后清空 path 并替换 PaperView 实例。
- App 根部使用既有 `pendingIntent` 锁住四个 Shell intent。Library/Vault durable mutation 未决时不会卸载发起组件；`commit_unknown` 仍能进入 runtime blocker，且不会重放 mutation。
- runtime blocked 继续在 ready Shell 之外接管整个工作面；未增加 Router、store、bridge endpoint、schema、DTO、依赖或持久 last-location。

## 自动检查

| Command | Result |
| --- | --- |
| `npm --prefix frontend run test -- App.test.js PaperView.test.js` | pass：`20 passed` in 2 files |
| `npm --prefix frontend run test` | pass：`69 passed` in 8 files |
| `npm --prefix frontend run build` | pass：32 modules transformed |
| production bundle scan for CP1 prototype-only text and selectors | pass：no match |
| `.venv/bin/python scripts/check_docs.py` | pass：active/required files and local links valid |
| `git diff --check` | pass |

## 浏览器 QA

使用隔离本地 Chromium 打开 production `/` 路由并注入内存 synthetic Tauri IPC；检查完成后关闭 task spaces 与 Vite server。该检查是浏览器交互证据，不是 Tauri 平台 smoke。

| 尺寸 | 结果 |
| --- | --- |
| `1220×780` | Shell 高度 56px；四个入口均在 viewport；Paper 当前语义正确；`scrollWidth === clientWidth === 1220`。 |
| `920×680` | 顶栏仍为 56px，四个入口均完整可达；Paper、Library、Vault 与 blocker 均无横向溢出；`scrollWidth === clientWidth === 920`。 |

- dirty Paper 点击 Library：原生 confirm 取消后仍在 Paper，草稿原文保留，focus 返回 Library 发起按钮；确认后只进入一次 Library，focus 进入 `Library 工作面`。
- Vault 可从 Shell 进入并取消返回 Library；工作面标签、当前位置和纵向可达路径正确。
- 延迟 `library.branch` 期间四个 Shell 控件均禁用；程序化切页尝试不改变 destination，Library 保持挂载；随后 synthetic `commit_unknown` 使 blocker 接管。
- synthetic sidecar failure 使 ready Shell 退出 DOM，显示错误码与安全重启入口；两种 blocker 均无横向溢出。
- 最终 fresh Vite 进程只有预期 HMR 行；浏览器捕获的 warning、error 与 unhandled rejection 均为零。

## 未运行与风险

- 未运行 Tauri smoke：CP2 没有改 bridge、Rust host、Python sidecar 或 lifecycle；当前源码平台路径属于 CP5。
- 未重跑 Python/Rust 基线：本 checkpoint 无 Python、Rust、schema、protocol 或文件服务变化；完整跨栈基线在 CP0 已运行，并将在 CP5 对当前源码重跑。
- 未连接或修改真实 Vault、selected-Vault config、作者内容、provider folder 或外部编辑器。
- CP2 不证明 CP3 Paper、CP4 Library/Vault、CP5 平台集成或 CP6 一号作者接受。
- 无发现的未解决 P0/P1；无 scope drift。

## Exit

导航、取消、确认、path 往返、并发点击、durable pending intent、runtime blocker、双尺寸与 bundle 隔离均有当前证据。开发者 advance YOLO 覆盖 CP2 退出判断与本地 checkpoint commit，因此 CP2 通过；CP3 可从该 checkpoint 线性开始。
