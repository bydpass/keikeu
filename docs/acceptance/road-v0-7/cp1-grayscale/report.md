# Road v0.7 CP1：灰阶结构原型证据

> 状态：CP1 development-only 原型、自动检查与两尺寸浏览器证据已完成；开发者于 2026-08-20 以 advance YOLO 通过退出 Gate 并授权本地 checkpoint commit。本报告随该 commit 成为 `ui/cp1-v07-grayscale` 的 HEAD。

## 基线与边界

- 日期：2026-08-20
- CP0 checkpoint：`fb52b55`
- 分支：`ui/cp1-v07-grayscale`
- 进入时工作树：clean
- production：仍是已接受的 Road v0.6 页面结构；CP1 不切换 production route
- 数据：三份 synthetic Paper 与一个内存新 Paper；无 bridge、真实文件、Vault 选择或持久配置

## 实现结果

- 复用既有 development-only `?prototype=1` 动态入口、`PaperV4Workbench` 与 `LibraryV4Projection`，没有修改 `App.vue` production 路由。
- 将旧永久 rail 与大 hero 替换为 56px 紧凑顶栏；Paper 与 Library 是唯一同级日常位置，当前位置同时用文字、`aria-current` 与底边表达。
- 新 Paper 只新建合成内存草稿；保存只更新内存数组。正常 Vault 是单独环境入口，不与日常导航混排。
- 阻塞恢复样张接管工作面，说明发生了什么、未自动重发或修改什么、保留了什么与允许的安全动作。
- `920×680` 只通过 `PrototypeView.vue` 的 scoped CSS 将 Library 详情排到列表之后；production Library 留给 CP4。

## 自动检查

| Command | Result |
| --- | --- |
| `npm --prefix frontend run test -- PrototypeView.test.js` | pass：`4 passed` |
| `npm --prefix frontend run test` | pass：`64 passed` in 8 files |
| `npm --prefix frontend run build` | pass：31 modules transformed |
| production bundle `rg` scan for `ROAD V0.7 · CP1 · DEVELOPMENT ONLY` and `prototype-v07-` | pass：no match |
| `.venv/bin/python scripts/check_docs.py` | pass：active/required files and local links valid |
| `git diff --check` | pass |

## 浏览器 QA

使用隔离本地 Chromium 打开 `http://127.0.0.1:1420/?prototype=1`；检查完成后关闭 task space 与 Vite server。

| 尺寸 | 结果 |
| --- | --- |
| `1220×780` | Paper 内容在紧凑 Shell 后立即出现；Library 为列表/详情双列；正常 Vault 与 blocker 可点击往返；`scrollWidth === clientWidth === 1220`。 |
| `920×680` | 顶栏四个入口均在 viewport 内；Library 为单列，详情 top 在列表 bottom 之后，纵向滚动可达；Vault/blocker 完整；`scrollWidth === clientWidth === 920`。 |

- Tab 首个 focus 为 Paper，第二个为 Library；focus outline 为 `3px solid`。
- Paper、Library、Vault、blocked 与返回路径均由真实点击完成；阻塞时 Paper workbench 不存在于 DOM。
- 浏览器事件只含 Vite 连接 debug；未出现 console warning/error。
- 截图仅用于当次目视核对，未复制作者内容，也未纳入仓库。

## 未运行与风险

- 未运行 Tauri smoke：CP1 不改 production route、bridge、desktop API 或 lifecycle；平台 smoke 属于 CP5。
- 未连接或修改真实 Vault、selected-Vault config、作者内容、provider folder 或外部编辑器。
- CP1 证明信息架构方向与 prototype 隔离，不证明 CP2–CP4 production 实现、CP5 平台集成或 CP6 一号作者接受。
- 无发现的 P0/P1；无 schema、DTO、依赖、Python、Rust、Router、store 或新产品能力变化；未发现 scope drift。

## Exit

声明范围、点击路径、两尺寸、可访问性基础与 bundle 隔离均有当前证据。开发者 advance YOLO 覆盖 CP1 退出判断与本地 checkpoint commit，因此 CP1 通过；CP2 可从该 checkpoint 线性开始。
