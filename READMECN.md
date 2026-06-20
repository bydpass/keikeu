# keikeu

> keikeu 是一个本地优先的写作辅助工具，用来帮助同人创作者把零碎灵感整理成可继续写作的 Markdown 大纲。

简体中文 | [English](README.md)

## 当前状态

keikeu 当前处于重启后的早期开发阶段。

旧代码库已经清空。当前实现以 [`appdesign.md`](appdesign.md) 与
[`techpolicy.md`](techpolicy.md) 为准。

这是开发预览版，尚未达到生产可用状态。

## 核心流程

```text
原始灵感 → 灵感 cache Markdown → 大纲 Markdown
```

- **cache（灵感缓存）** —— 低摩擦记录一个原始念头。你的原话会被原样保留，不做总结、不做改写。
- **大纲（outline）** —— 从某条 cache 衍生出的结构化 Markdown 文件：标题、原始灵感、fandom、人物 / CP、观前提醒、流水账、Ending Type、与其他灵感的关联。

## 产品原则

- 本地优先。
- Markdown 文件是用户资产本体。
- `keikeu_index.json` 是可重建的软件索引。
- MVP 前不做账号系统。
- MVP 前不做云同步。
- 不接入外部 fandom / 角色 / CP 数据库。
- 不把 AI 作为必要工作流。

## keikeu 是什么

- 灵感缓存工具
- 大纲编辑器
- 本地 Markdown vault 工具
- 面向同人创作者的写作准备工具

## keikeu 不是什么

- AI 代写工具
- 社交平台
- 约稿交易平台
- fandom 数据库
- Obsidian / Notion 替代品
- 云端写作套件

## 开发环境配置

需要 Python ≥3.11，<3.14。

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
```

### 运行测试

```bash
python -m pytest
```

### 启动应用

```bash
flet run src/keikeu_app/main.py
```

## 仓库结构

```text
appdesign.md      产品设计的唯一事实来源
techpolicy.md     技术政策
gitspec.md        面向人类的 Git 工作流
gitagent.md       面向 agent 的 Git 工作流

src/
  keikeu_core/    核心逻辑；不得 import Flet
  keikeu_app/     Flet 界面层

tests/            核心与界面层测试
```

硬性规则：

```text
keikeu_core 不得 import Flet。
```

核心层必须能在不启动界面的情况下测试。

## 文档地图

| 文件 | 作用 |
|---|---|
| [`appdesign.md`](appdesign.md) | 产品设计的唯一事实来源 |
| [`techpolicy.md`](techpolicy.md) | 技术栈与实现政策 |
| [`gitspec.md`](gitspec.md) | 面向人类的 Git 工作流手册 |
| [`gitagent.md`](gitagent.md) | 面向 agent 的 Git 工作流规则 |

## 路线图

```text
v0.1 — macOS 开发预览版
v0.2 — iOS 内测版
v0.3 — Android APK
v0.4 — Windows 预览版
```

## 许可证

License: TBD.
