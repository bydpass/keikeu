# 人工文档地图

> 这里解释“为什么”和“如何理解”，不回答“现在必须怎么做”。当前答案回到 [PROJECT](../PROJECT.md)、[SPEC](../SPEC.md)、[RULES](../RULES.md) 与 [AGENTS](../../AGENTS.md)。

> 2026-08-30：保留前日新增的开发者 TUI 与四份速查手册，并把本地交接路由校准为仓库根目录 `CONTEXT.md`。

```text
manual/
├─ keikeu-current-logic.html  系统理解
├─ paper-v4-repair.html       Paper v4 离线人工修复
├─ forfresh/                  项目开发技术手册
└─ prospect/                  产品、用户研究与价值
```

## 开发者 TUI

完成依赖安装后，在仓库根目录运行 `./dev`。默认文档分组是 `Manual`，也可查看
`Active docs`；预览为纯文本，`/` 搜索标题、路径与可见正文，`Enter` / `o` 用系统应用
打开，`p` 打开同名 PDF。

进程键位：`a` 使用已有 sidecar 启动；`b` 重建成功后启动，失败则停留在日志页；
`s` 确认后停止；`K` 确认后强制终止。`q` 在进程运行时会先确认并等待进程组退出。
TUI 只管理自己启动的任务，日志仅驻留内存。

这里“默认展示 Manual”只定义人类界面：`docs/manual/` 仍是非权威、按需读取的说明，
不进入 Agent 冷启动。TUI 状态与日志也不是产品验收证据。

## Agent context route

仓库改动完成、检查结束且任何获准的 Git 动作收口后，用现有 builder 刷新 ignored 的
仓库根目录 `CONTEXT.md`。只重复传入下一任务确实需要的 tracked 文件；四份权威
文件会自动加入：

```bash
.venv/bin/python scripts/build_context_pack.py \
  --path docs/manual/README.md \
  --path docs/manual/forfresh/developer-tui-quickstart.html
```

生成后检查 branch、HEAD、selected-file status、selected/skipped 数量、current-local-tree
来源与每个文件边界。它只是可丢弃的本地交接物，不是权威、测试或验收证据，也不会由
builder 上传。未跟踪文件不能选入；不得只为刷新而擅自暂存。

## 第一次接手

1. 先读 [TUI 极简使用手册](forfresh/developer-tui-quickstart.html)，用 `./dev` 启动应用或检视手册。
2. 再读 [技术栈与组件图鉴](forfresh/stack-component-atlas.html)，确认 Vue、Tauri、JSONL 与 Python 的职责边界。
3. 准备改代码前读 [测试与证据手册](forfresh/testing-and-evidence-guide.html)；需要产出 sidecar 或安装包时再读 [构建与打包手册](forfresh/build-and-packaging-guide.html)。
4. 最后按任务回到 [PROJECT](../PROJECT.md)、[SPEC](../SPEC.md)、[RULES](../RULES.md) 与实际源码；手册不能替代权威或运行事实。

## 我要改……

| 任务 | 先读 | 再核对 |
| --- | --- | --- |
| 开发入口、进程或文档 TUI | [TUI 极简使用手册](forfresh/developer-tui-quickstart.html) | [`dev`](../../dev) 与 [`tests/test_dev_tui.py`](../../tests/test_dev_tui.py) |
| Agent 上下文路由与交接 | [技术栈与组件图鉴](forfresh/stack-component-atlas.html) | [`build_context_pack.py`](../../scripts/build_context_pack.py)、[`test_build_context_pack.py`](../../tests/test_build_context_pack.py)、[AGENTS](../../AGENTS.md) 与 `keikeu-routine` |
| UI 状态和交互 | [Tauri + Vue 入门](forfresh/tauri-vue-beginner-guide.html) | `frontend/src/`、[交互设计](../design/interaction.html) 与 [RULES](../RULES.md) |
| 原生能力或 Sidecar 生命周期 | [技术栈与组件图鉴](forfresh/stack-component-atlas.html) → [Rust 简易入门](forfresh/rust-beginner-guide.html) | `frontend/src-tauri/` 与 [architecture](../architecture/architecture.html) |
| JSONL protocol、Python core 或文件规则 | [技术栈与组件图鉴](forfresh/stack-component-atlas.html) → [Python Caveman](forfresh/python-caveman-guide.html) | [SPEC](../SPEC.md)、[RULES](../RULES.md)、`src/` 与直接测试 |
| 测试、fixture 或验收证据 | [测试与证据手册](forfresh/testing-and-evidence-guide.html) | `tests/`、`frontend/src/**/*.test.js` 与 [RULES](../RULES.md) |
| Sidecar、前端或桌面安装包 | [构建与打包手册](forfresh/build-and-packaging-guide.html) | 构建脚本、当前配置与 [PROJECT](../PROJECT.md) |

## 系统理解

[keikeu-current-logic.html](keikeu-current-logic.html) 与两个分类文件夹并列，简明说明已完成并归档的 Road v0.7、已接受的 CP8 响应式导航/Anchor composition、Road v0.6 延续的 Paper v4 业务链路、数据权威、保存防护与 Vue/Tauri/JSONL v2/Python 分层；最终 checkpoint 为 `2f03aee`。2026-08-30 状态复核继续记录 App-root pending intent 与 PaperView-scoped close guard 的实现偏差，并明确开发者工具不进入产品运行链。最终核对 [PROJECT](../PROJECT.md)、[SPEC](../SPEC.md)、[RULES](../RULES.md) 与 [architecture](../architecture/architecture.html)。

[paper-v4-repair.html](paper-v4-repair.html) 是面向普通纯文本编辑器用户的离线修复手册，包含完整 schema v4 示例、类型/空值、可逆转义、错误含义、Finder、未知保存、重新检查和 Index 重建；app 不会自动改写损坏文件。

## `forfresh/`：项目开发技术手册

定位为“原始人也能看懂”的技术手册：用直白语言解释项目如何开发、协作与发布；它帮助理解，不授予 Git 或发布权限。

| 阅读路径 | 读到什么 | 最终核对 |
| --- | --- | --- |
| [TUI 极简使用手册](forfresh/developer-tui-quickstart.html) | 五分钟学会启动、重建、检视手册、搜索与安全退出 | [`dev`](../../dev)、[`tests/test_dev_tui.py`](../../tests/test_dev_tui.py) 与 [PROJECT](../PROJECT.md) |
| [技术栈与组件图鉴](forfresh/stack-component-atlas.html) | Vue → Tauri/Rust → JSONL v2 → Python → Markdown/Index 的组件职责与任务路由 | 当前依赖 metadata、[architecture](../architecture/architecture.html) 与源码入口 |
| [测试与证据手册](forfresh/testing-and-evidence-guide.html) | 改动类型、最小命令、fixture/mock，以及每项检查能证明和不能证明什么 | 当前测试、[RULES](../RULES.md) 与 [SPEC](../SPEC.md) |
| [构建与打包手册](forfresh/build-and-packaging-guide.html) | editable install、Hatchling、PyInstaller、Vite、Cargo 与 Tauri bundle 的边界 | 当前构建脚本、配置与 [PROJECT](../PROJECT.md) |
| [npm 新人手册](forfresh/npm-beginner-guide.html) | Node/npm 边界、锁文件、当前脚本、依赖纪律与故障速查 | [frontend/package.json](../../frontend/package.json)、[PROJECT](../PROJECT.md) 与 [RULES](../RULES.md) |
| [Tauri + Vue 入门](forfresh/tauri-vue-beginner-guide.html) | Vue 状态流、Tauri command、Sidecar、一次保存与恢复语义 | [architecture](../architecture/architecture.html)、[SPEC](../SPEC.md) 与 [RULES](../RULES.md) |
| [Python Caveman 诠释](forfresh/python-caveman-guide.html) | Python 对象、core/bridge 分层、Markdown 权威与安全追代码 | [SPEC](../SPEC.md)、[RULES](../RULES.md) 与当前 `src/` / `tests/` |
| [Rust 简易入门](forfresh/rust-beginner-guide.html) | Tauri 宿主、Option/Result、所有权、单 worker 与 Sidecar 生命周期 | [architecture](../architecture/architecture.html)、[RULES](../RULES.md) 与当前 `frontend/src-tauri/` |
| [Git 状态地图](forfresh/git-interactive.html) → [Git 手册](forfresh/gitspec.md) | 工作区、暂存区、本地历史、远端与最短安全路径 | [RULES §7](../RULES.md#7-git) |
| [macOS 开发者入门](forfresh/macos-developer-beginner-guide.html) → [Developer ID 发布手册](forfresh/macos-developer-id-release.md) | 签名、公证、staple、Gatekeeper 与尚未批准的 Road v0.9 发布骨架 | [Road v0.8 跨端基础计划](../../PLAN_road_v0_8.md)、[PROJECT](../PROJECT.md) 与 [RULES](../RULES.md) |

## `prospect/`：产品与价值

| 阅读路径 | 读到什么 | 最终核对 |
| --- | --- | --- |
| [产品设计](prospect/appdesign.md) | 已接受的 Paper v4 产品模型，以及明确标作“未实现”的 Road v0.8+ 用户与平台方向 | [Road v0.6 Paper v4 设计](../design/road-v0-6-paper-v4-design.md)、[Road v0.7 App Shell / CP8 accepted override](../design/road-v0-7-app-shell-design.md)、[活动 Road v0.8](../../PLAN_road_v0_8.md) |
| [Alpha 用户画像与宣发渠道研究](prospect/alpha-audience-research.md) | 2026-08-30 六平台新证据、四端待实测口径、18+ 准入、样本与正式宣发 Gate | [活动 Road v0.8](../../PLAN_road_v0_8.md)、[PROJECT](../PROJECT.md) 与 [SPEC](../SPEC.md) |
| [技术伦理](prospect/ethics.md) | 作者控制、数据边界与功能评审方法 | [SPEC](../SPEC.md) 与 [RULES](../RULES.md) |

若 manual 与 truth 冲突，manual 错；修 manual，不复制一份新规则。
