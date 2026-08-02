# 人工文档地图

> 这里解释“为什么”和“如何理解”，不回答“现在必须怎么做”。当前答案回到 [PROJECT](../PROJECT.md)、[SPEC](../SPEC.md)、[RULES](../RULES.md) 与 [AGENTS](../../AGENTS.md)。

```text
manual/
├─ keikeu-current-logic.html  系统理解
├─ forfresh/                  项目开发技术手册
└─ prospect/                  产品与价值
```

## 系统理解

[keikeu-current-logic.html](keikeu-current-logic.html) 与两个分类文件夹并列，交互说明当前业务链路、数据权威、保存防护与 Vue/Tauri/JSONL/Python 分层。最终核对 [PROJECT](../PROJECT.md)、[SPEC](../SPEC.md)、[RULES](../RULES.md) 与 [architecture](../architecture/architecture.html)。

## `forfresh/`：项目开发技术手册

定位为“原始人也能看懂”的技术手册：用直白语言解释项目如何开发、协作与发布；它帮助理解，不授予 Git 或发布权限。

| 阅读路径 | 读到什么 | 最终核对 |
| --- | --- | --- |
| [Git 状态地图](forfresh/git-interactive.html) → [Git 手册](forfresh/gitspec.md) | 工作区、暂存区、本地历史、远端与最短安全路径 | [RULES §7](../RULES.md#7-git) |
| [macOS 开发者入门](forfresh/macos-developer-beginner-guide.html) → [Developer ID 发布手册](forfresh/macos-developer-id-release.md) | 签名、公证、staple、Gatekeeper 与延期至 Road v0.8 的发布骨架 | [PROJECT](../PROJECT.md)、[SPEC](../SPEC.md) 与 [RULES](../RULES.md) |

## `prospect/`：产品与价值

| 阅读路径 | 读到什么 | 最终核对 |
| --- | --- | --- |
| [产品设计](prospect/appdesign.md) | Road v0.2 的产品设计来路与长篇解释 | [SPEC](../SPEC.md) |
| [技术伦理](prospect/ethics.md) | 作者控制、数据边界与功能评审方法 | [SPEC](../SPEC.md) 与 [RULES](../RULES.md) |

若 manual 与 truth 冲突，manual 错；修 manual，不复制一份新规则。
