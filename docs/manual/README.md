# 人工文档地图

> 这里解释“为什么”和“如何理解”，不回答“现在必须怎么做”。当前答案回到 [PROJECT](../PROJECT.md)、[SPEC](../SPEC.md)、[RULES](../RULES.md) 与 [AGENTS](../../AGENTS.md)。

```text
manual/
├─ keikeu-current-logic.html  系统理解
├─ paper-v4-repair.html       Paper v4 离线人工修复
├─ forfresh/                  项目开发技术手册
└─ prospect/                  产品与价值
```

## 开发者 TUI

完成依赖安装后，在仓库根目录运行 `./dev`。默认文档分组是 `Manual`，也可查看
`Active docs`；预览为纯文本，`/` 搜索标题、路径与可见正文，`Enter` / `o` 用系统应用
打开，`p` 打开同名 PDF。

进程键位：`a` 使用已有 sidecar 启动；`b` 重建成功后启动，失败则停留在日志页；
`s` 确认后停止；`K` 二次确认后强制终止。`q` 在进程运行时会先确认并等待进程组退出。
TUI 只管理自己启动的任务，日志仅驻留内存。

这里“默认展示 Manual”只定义人类界面：`docs/manual/` 仍是非权威、按需读取的说明，
不进入 Agent 冷启动。TUI 状态与日志也不是产品验收证据。

## 系统理解

[keikeu-current-logic.html](keikeu-current-logic.html) 与两个分类文件夹并列，简明说明已完成并归档的 Road v0.7、已接受的 CP8 响应式导航/Anchor composition、Road v0.6 延续的 Paper v4 业务链路、数据权威、保存防护与 Vue/Tauri/JSONL v2/Python 分层；最终 checkpoint 为 `2f03aee`。2026-08-26 同步还记录了 App-root pending intent 与 PaperView-scoped close guard 的实现偏差。最终核对 [PROJECT](../PROJECT.md)、[SPEC](../SPEC.md)、[RULES](../RULES.md) 与 [architecture](../architecture/architecture.html)。

[paper-v4-repair.html](paper-v4-repair.html) 是面向普通纯文本编辑器用户的离线修复手册，包含完整 schema v4 示例、类型/空值、可逆转义、错误含义、Finder、未知保存、重新检查和 Index 重建；app 不会自动改写损坏文件。

## `forfresh/`：项目开发技术手册

定位为“原始人也能看懂”的技术手册：用直白语言解释项目如何开发、协作与发布；它帮助理解，不授予 Git 或发布权限。

| 阅读路径 | 读到什么 | 最终核对 |
| --- | --- | --- |
| [npm 新人手册](forfresh/npm-beginner-guide.html)（[PDF](forfresh/npm-beginner-guide.pdf)） | Node/npm 边界、锁文件、当前脚本、依赖纪律与故障速查 | [frontend/package.json](../../frontend/package.json)、[PROJECT](../PROJECT.md) 与 [RULES](../RULES.md) |
| [Tauri + Vue 入门](forfresh/tauri-vue-beginner-guide.html)（[PDF](forfresh/tauri-vue-beginner-guide.pdf)） | Vue 状态流、Tauri command、Sidecar、一次保存与恢复语义 | [architecture](../architecture/architecture.html)、[SPEC](../SPEC.md) 与 [RULES](../RULES.md) |
| [Python Caveman 诠释](forfresh/python-caveman-guide.html)（[PDF](forfresh/python-caveman-guide.pdf)） | Python 对象、core/bridge 分层、Markdown 权威与安全追代码 | [SPEC](../SPEC.md)、[RULES](../RULES.md) 与当前 `src/` / `tests/` |
| [Rust 简易入门](forfresh/rust-beginner-guide.html)（[PDF](forfresh/rust-beginner-guide.pdf)） | Tauri 宿主、Option/Result、所有权、单 worker 与 Sidecar 生命周期 | [architecture](../architecture/architecture.html)、[RULES](../RULES.md) 与当前 `frontend/src-tauri/` |
| [Git 状态地图](forfresh/git-interactive.html) → [Git 手册](forfresh/gitspec.md) | 工作区、暂存区、本地历史、远端与最短安全路径 | [RULES §7](../RULES.md#7-git) |
| [macOS 开发者入门](forfresh/macos-developer-beginner-guide.html) → [Developer ID 发布手册](forfresh/macos-developer-id-release.md) | 签名、公证、staple、Gatekeeper 与 Road v0.8 预启动草案下仍受阻塞的发布骨架 | [Road v0.8 草案](../../PLAN_road_v0_8.md)、[PROJECT](../PROJECT.md) 与 [RULES](../RULES.md) |

## `prospect/`：产品与价值

| 阅读路径 | 读到什么 | 最终核对 |
| --- | --- | --- |
| [产品设计](prospect/appdesign.md) | Road v0.6 建立、已归档 Road v0.7 继续使用的 Paper v4 产品模型；不定义 Gate | [Road v0.6 Paper v4 设计](../design/road-v0-6-paper-v4-design.md)、[Road v0.7 App Shell / CP8 accepted override](../design/road-v0-7-app-shell-design.md) |
| [技术伦理](prospect/ethics.md) | 作者控制、数据边界与功能评审方法 | [SPEC](../SPEC.md) 与 [RULES](../RULES.md) |

若 manual 与 truth 冲突，manual 错；修 manual，不复制一份新规则。
