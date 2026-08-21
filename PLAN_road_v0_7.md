# Road v0.7 实施计划（已批准；CP2 已通过）

> 状态：开发者于 2026-08-20 批准本计划与目标设计，并对 CP0–CP6 的开发者退出判断与本地 checkpoint commit 给出 advance YOLO。CP0 `fb52b55`、CP1 `8019969` 与 CP2 production Shell 已通过并形成线性 checkpoint；CP3 是下一 Gate。Road v0.7 产品接受尚未发生；真实 Vault、push、tag、closeout 与发布未获授权。
>
> 目标设计：[`docs/design/road-v0-7-app-shell-design.md`](docs/design/road-v0-7-app-shell-design.md)
>
> 伴随评审物：[`docs/design/road-v0-7-planbook.html`](docs/design/road-v0-7-planbook.html)（非规范权威，不构成实现或 Gate 证据）
>
> 当前接受基线：Road v0.6 Paper v4 / Index v4 / protocol v2。

## 0. Road 目标

Road v0.7 将已接受的 Paper、Library 与 Vault 收口为一个稳定桌面工作台：

```text
紧凑 App Shell → Paper / Library 日常工作面 → Vault 环境与阻塞恢复
```

本 Road 是 Vue 结构、交互层级与视觉收口，不是数据、Core、transport、平台或发布 Road。

## 1. 权威与执行纪律

- 当前已接受产品由 [`docs/SPEC.md`](docs/SPEC.md) 定义。
- Road v0.7 目标由已批准的[设计](docs/design/road-v0-7-app-shell-design.md)定义；CP0 已把 target 摘要写入 SPEC，同时不得把 target 冒充 current。
- [`docs/RULES.md`](docs/RULES.md) 继续约束作者资产、Git、证据与安全边界。
- [`docs/PROJECT.md`](docs/PROJECT.md)、源码和测试标明每个 Checkpoint 的当前事实。
- 不得把未完成 target 写成已实现；每个 CP 只从前一已通过 checkpoint commit 建分支。
- 每个 CP 单独 commit；CP0–CP6 的本地 checkpoint commit 已获 advance YOLO，真实 Vault、push、tag、closeout 与发布始终另行授权。

## 2. 全局范围

### 2.1 包含

- `App.vue` 的紧凑 Shell 与现有页面切换整合。
- Paper、Library、Vault 的信息层级与响应式布局。
- 现有状态、确认、focus 与错误反馈的位置校准。
- development-only 灰阶 prototype。
- Vitest、Vite build、两种窗口尺寸检查和最终 Tauri smoke。
- 一号作者对同一核心任务的结构接受。

### 2.2 不包含

- Paper / Index / Vault schema 或文件迁移。
- Python、Rust、JSONL protocol、sidecar 或 Tauri capability 变更。
- 新 endpoint、依赖、Router、store、TypeScript 或 UI kit。
- AI、同步、账号、数据库、自动保存、页重排、deep-link 或内置正文编辑器。
- 移动端、Intel Mac、Windows、签名、公证、DMG、tag、push 或公开发布。

## 3. 通用证据

### 3.1 每个 UI Checkpoint

```bash
npm --prefix frontend run test
npm --prefix frontend run build
.venv/bin/python scripts/check_docs.py
git diff --check
```

- 运行相关的聚焦 Vitest 后再运行完整 Vitest。
- 同时检查 `1220×780` 与 `920×680`。
- 检查可见 focus、语义名称、键盘路径、滚动和控制台错误。
- 不复制旧 pass count；记录本次命令、状态和日期。

### 3.2 Road 基线与最终集成

```bash
.venv/bin/python -m pytest
.venv/bin/python -m compileall -q src
.venv/bin/python scripts/build_sidecar.py
npm --prefix frontend run test
npm --prefix frontend run build
cargo test --manifest-path frontend/src-tauri/Cargo.toml
cargo fmt --manifest-path frontend/src-tauri/Cargo.toml --check
.venv/bin/python scripts/check_docs.py
git diff --check
```

Python/Rust 无改动不代表可以复制历史结果；CP0 与 CP5 各运行一次完整基线。

## 4. Checkpoint 总览

| CP | 分支 | 结果 | 主要 Gate |
| --- | --- | --- | --- |
| CP0 | `docs/cp0-v07-contract` | 批准合同、基线证据、current/target 校准 | 目标与排除明确 |
| CP1 | `ui/cp1-v07-grayscale` | development-only 灰阶结构 | 开发者批准信息架构 |
| CP2 | `ui/cp2-v07-shell` | production Shell 与统一导航 | dirty guard 无回归 |
| CP3 | `ui/cp3-v07-paper` | Paper 内容优先工作面 | 编辑/分页/保存无回归 |
| CP4 | `ui/cp4-v07-library-vault` | Library、Vault 与恢复层级 | 两尺寸路径完整 |
| CP5 | `test/cp5-v07-integration` | 全量检查与 Tauri 合成 smoke | 无未解决 P0/P1 |
| CP6 | `test/cp6-v07-author-gate` | 一号作者真实日常接受 | 产品 Gate 通过 |

## 5. CP0 — 合同与基线

**进入条件（已满足）：** 开发者于 2026-08-20 书面批准 Road v0.7 设计与本计划，并以 advance YOLO 通过 CP0 开发者退出 Gate。

**范围：**

- 将批准的 v0.7 target 写入 SPEC，并在 PROJECT 标明 current/target 与下一 Gate。
- 校准 `design.html`、`interaction.html` 与 architecture map 的 current/target 标签。
- 冻结 Shell、Paper、Library、Vault、窗口与可访问性验收矩阵。
- 运行 §3.2 完整基线，不改 production code。

**退出 Gate：** 文档无双重权威；基线检查真实运行；无未解释失败。

## 6. CP1 — 灰阶结构原型

**范围：**

- 复用现有 development-only `PrototypeView.vue` 与 `?prototype=1`。
- 只用合成内存数据画 Shell、Paper、Library、正常 Vault context 与阻塞恢复。
- 同时渲染 `1220×780` 与 `920×680`。
- 验证 Paper/Library 切换、新 Paper、Vault 入口和阻塞页的点击路径。
- 证明 production bundle 不包含 prototype 文本或样式。

**明确不做：** bridge 调用、真实文件、产品 DTO、视觉精修或 production route 切换。

**退出 Gate：** 开发者明确批准导航层级、两种尺寸与 Paper 内容优先方向。

**结果（已通过）：** 合成 Shell、Paper、Library、新 Paper、正常 Vault context 与阻塞恢复点击路径均已实现；两种目标尺寸、键盘 focus、完整 Vitest、fresh production build 与 prototype bundle 隔离通过。开发者 advance YOLO 覆盖退出判断；证据见 [`CP1 report`](docs/acceptance/road-v0-7/cp1-grayscale/report.md)。

## 7. CP2 — Production App Shell

**范围：**

- 在 `App.vue` 内加入紧凑顶栏，不先抽新组件。
- Paper / Library / 新 Paper / Vault 入口复用现有 destination 与事件。
- PaperView 暴露一个复用现有逻辑的 `confirmDeparture()`；App Shell 不重写确认规则。
- PaperView 在打开或保存后回报已保存 path，保证 Vault 往返仍回到同一 Paper。
- 新 Paper 只在 guard 通过后清空 path 并替换 PaperView 实例。
- 当前位置使用语义与文字表达，不只靠颜色。
- 更新 `App.test.js` 与直接 PaperView 测试，覆盖取消、确认、当前 path、新 Paper、
  当前位置和 runtime blocked。

**明确不做：** Router、store、新 bridge 方法、持久 last-location 或侧 rail。

**退出 Gate：** 导航稳定；取消不改变 destination；确认只执行一次原有 intent。

**结果（已通过）：** production 紧凑 Shell、语义当前位置、单一 dirty guard、已保存 path 的 Vault 往返、新 Paper 实例替换、durable pending-intent 锁与 runtime blocker 接管均有直接测试和合成浏览器证据；两种目标尺寸无横向溢出，完整 Vitest、fresh build 与 prototype bundle 隔离通过。开发者 advance YOLO 覆盖退出判断；证据见 [`CP2 report`](docs/acceptance/road-v0-7/cp2-shell/report.md)。

## 8. CP3 — Paper 工作面

**范围：**

- 移除重复 hero 与页面级导航，保留 Paper context 和卡页中心。
- Paper 名、Tags、页码、页标题、类型、正文与三个底部动作保持原语义。
- code/path/time 使用原生详情披露。
- clean、dirty、saving、validation 与 degraded 状态靠近影响对象。
- 更新 Paper 聚焦测试与两尺寸视觉证据。

**明确不做：** schema、保存 DTO、逐页 mutation、自动保存、页重排或 deep-link。

**退出 Gate：** 创建、编辑、分页、删除、保存、离开保护和错误恢复无行为回归。

## 9. CP4 — Library、Vault 与恢复

**范围：**

- Library 宽窗口保留三段结构；`920×680` 改为纵向详情。
- 保留搜索、打开、移动、分支、Trash、恢复与系统 handoff。
- 正常 Vault 降级为环境上下文，完整 VaultView 仍处理选择与维护。
- migration、repair、commit unknown 与 sidecar blocked 继续接管工作面。
- 危险操作继续复用原生确认边界。

**明确不做：** drawer 依赖、Library 正文编辑、同步状态、自动修复或 mutation replay。

**退出 Gate：** 两尺寸下日常与阻塞路径完整；Finder/Trash/恢复没有语义退化。

## 10. CP5 — 集成与安全 Gate

**范围：**

- 运行 §3.2 完整检查。
- 用 synthetic Vault 或完整副本运行当前源码 Tauri smoke。
- 覆盖启动、创建、分页、保存、Library 找回、Vault 进入/返回与正常退出。
- 覆盖 dirty departure、Index degraded、repair 与 commit unknown 的合成路径。
- 检查 production bundle、控制台、子进程退出与残留进程。

**真实数据边界：** 不选择、不迁移、不损坏唯一真实 Vault；不改持久配置。

**退出 Gate：** 无未解决 P0/P1；自动检查、平台 smoke 和未执行项分别记录。

## 11. CP6 — 一号作者 Gate

**进入条件：** CP5 checkpoint 已通过并提交；真实 Vault 使用另行明确授权。

**场景：**

1. 启动后判断当前工作位置并进入已有或新 Paper。
2. 创建、命名、分页、标记并保存一份真实 Paper。
3. 带未保存草稿分别测试一次取消离开与确认离开。
4. 在 Library 找回整份 Paper，完成一次整理或系统 handoff。
5. 查看当前 Vault 环境入口，但不进行非必要迁移或破坏实验。
6. 在 `1220×780` 与 `920×680` 判断舒适度、清楚度与操作直觉。

**记录：** 只记录完成情况、介入次数、P0–P3 与去标识化判断，不记录正文、名称、
Tags、路径或内容截图。

**退出 Gate：** 核心任务完成；作者能解释 Paper/Library/Vault 层级；无未解决 P0/P1。

## 12. Road 完成与 closeout

Road v0.7 只有在 CP0–CP6 都有实际证据、通过开发者 Gate、形成线性 checkpoint commit、
production runtime 不含 prototype、且一号作者接受无未解决 P0/P1 后，才可申请 closeout。

closeout、snapshot、tag、push、签名、打包与发布分别决定，不由 Road 完成自动授权。

## 13. 已知风险

| 风险 | 控制 |
| --- | --- |
| UI Road 变成新功能 Road | 每个 CP 重复明确不做清单 |
| App Shell 绕过离开保护 | CP2 统一 App-root intent，并直接测试取消/确认 |
| Paper 层级变化影响输入焦点 | CP3 覆盖焦点、快捷键与中文输入 smoke |
| Library 小窗口丢失危险动作 | CP4 `920×680` 逐路径检查，不依赖 hover |
| Vault 降级掩盖安全 Gate | 正常 context 与 blocking surface 明确分开 |
| 原型进入生产 bundle | CP1、CP5 两次 bundle 检查 |
| 并行文档产生双重权威 | CP0 在批准后一次校准 SPEC/PROJECT/maps |

## 14. 实施计划批准 Gate（已通过：2026-08-20）

开发者已确认：

- [x] Road 名称与范围为“App Shell 与信息层级收口”。
- [x] CP0–CP6 顺序和分支边界可执行。
- [x] CP1 灰阶 Gate 先于 production UI 修改。
- [x] 不新增依赖，不修改后端或持久数据合同。
- [x] CP5 使用 synthetic Vault / 完整副本，CP6 的真实 Vault 另行授权。
- [x] CP0–CP6 开发者退出判断与本地 checkpoint commit 采用 advance YOLO；证据仍须实际运行且不得复制或虚构。

本次批准与 advance YOLO 已用于通过 CP0–CP2；不表示 CP3–CP6 已完成、任何历史测试仍然有效，也不授权真实 Vault 或 Git 远端动作。
