# keikeu

> keikeu 是一个本地优先的同人写作辅助工具：把已有灵感整理成 Markdown 纸片，再用 Flashcard 帮作者聚焦扩写。

简体中文 | [English](README_EN.md)

## 当前状态

keikeu Road v0.1 已完成并归档；当前代码仍是旧 `Cache → Outline`
macOS pre-alpha。新的产品契约已经定案，项目正准备进入
**Road v0.2：macOS Paper–Flashcard Core**，尚未作为生产版本发布。

当前实现以 [`appdesign.md`](appdesign.md) 与 [`techpolicy.md`](techpolicy.md)
为目标；Road v0.2 的行为与执行顺序见
[`spec_road_v0_2.md`](memory/specs/spec_road_v0_2.md) 和
[`planbook_road_v0_2.md`](memory/specs/planbook_road_v0_2.md)。

## 核心流程

```text
已有灵感 → Paper Markdown → Flashcard → 外部正文编辑器
```

- **纸片（Paper）** —— 一次准备写成正文的作品单元；包含必填 Summary、推荐 Highlights、推荐 Tags 和首次保存的初稿副本。
- **Flashcard** —— Summary-first 的有限上下文只读视图；一条 Highlight 对应一张卡，并记住每台设备的上次位置。
- **本地文件库（Library）** —— 按代号、Summary 和 Tags 检索 Paper，在 keikeu、默认编辑器或 Finder 中打开资产。
- **外部正文编辑器** —— 正式正文始终在 keikeu 之外完成。

## Road v0.1 历史基线

- 稳定的 Outline Markdown schema：内容要素、结局正文和三行关系块均可往返读取。
- Markdown 导出：系统保存对话框确认后，从 vault 字节一致复制到目标位置；取消无副作用。
- 软删除：cache 与 outline 移入 `.trash/`，重名自动避让，索引自动排除回收站内容。
- 动作驱动的 cache 状态：保存、炼成大纲和封存负责推进状态，用户不能手动制造冲突状态。
- 本地关系 picker：从索引选择前作、续作、IF、外传或同系列；不需要手输路径。
- Library 系统操作：默认程序打开、Finder 定位、vault 路径入口，并为非 macOS 提供安全降级。
- 暖纸色视觉 tokens、中文主界面和轻量侧栏，保持本地灵感小册子的气质。
- 归档时测试基线：`112 passed`。

这些能力记录旧产品线；Road v0.2 将迁移 Cache、退休活动 Outline，并把核心界面换成 Paper 与 Flashcard。

## 产品原则

- 本地优先。
- Markdown 文件是用户资产本体。
- `keikeu_index.json` 是可重建的软件索引。
- 不做 keikeu 账号、云后端或后台同步。
- 用户可以把 vault 放在 iCloud Drive 等系统文件服务目录中。
- 不接入外部 fandom / 角色 / CP 数据库。
- 不使用 AI 代写或自动改写作者文字。

## keikeu 是什么

- Markdown 纸片工具
- Flashcard 写作聚焦界面
- 本地 Markdown vault 工具
- 面向即兴型和混合型同人作者的写前辅助工具

## keikeu 不是什么

- AI 代写工具
- 社交平台
- 约稿交易平台
- fandom 数据库
- Obsidian / Notion 替代品
- 云端写作套件
- 完整正文编辑器

## 伦理基线

keikeu 以创作者优先的伦理底线为基础。完整论证见 [`ethics.md`](ethics.md)。

- 个人创作工具，不是同人内容平台。
- 只处理用户自己的输入 —— 不抓取、不搬运。
- 不做公开评分、排行或聚合。
- 不建作者库或作品库。
- 不做未经授权的 AI 训练、总结、仿写或嵌入。
- 默认本地优先；任何远程模型调用必须手动开启（opt-in）。
- 所有生成输出可编辑；用户永远是最终作者。
- 当便利与创作者边界冲突时，边界优先。

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
| [`ethics.md`](ethics.md) | 技术伦理指南 |
| [`readmedesign.md`](readmedesign.md) | readme手册设计的唯一事实来源 |
| [`gitspec.md`](gitspec.md) | 面向人类的 Git 工作流手册 |
| [`gitagent.md`](gitagent.md) | 面向 agent 的 Git 工作流规则 |
| [`memory/specs/README.md`](memory/specs/README.md) | 当前需求与历史规格归档索引 |
| [`memory/specs/spec_road_v0_2.md`](memory/specs/spec_road_v0_2.md) | Road v0.2 行为规范与迁移契约 |
| [`memory/specs/planbook_road_v0_2.md`](memory/specs/planbook_road_v0_2.md) | macOS-first 执行手册 |
| [`memory/specs/audit_v01_to_v02_2026-07-13.md`](memory/specs/audit_v01_to_v02_2026-07-13.md) | Road v0.2 开工前代码对照与测试基线 |
| [`memory/specs/road_pre_advance.md`](memory/specs/road_pre_advance.md) | 可选 Outline 的后置候选池 |
| [`memory/specs/9d033db326295874d1f32f23325e430e0461396d/planbook_road_v0_1.md`](memory/specs/9d033db326295874d1f32f23325e430e0461396d/planbook_road_v0_1.md) | Road v0.1 执行手册与阶段定义 |
| [`memory/specs/9d033db326295874d1f32f23325e430e0461396d/spec_road_v0_1.md`](memory/specs/9d033db326295874d1f32f23325e430e0461396d/spec_road_v0_1.md) | Road v0.1 功能规范与验收标准 |

## 路线图

```text
v0.1 — 已归档的 macOS Cache / Outline pre-alpha
v0.2 — macOS Paper / Flashcard Core
后续 — iPhone / iPad 文件服务对齐
Pre-Advance — 可选 Markdown Outline
更后 — Android / Windows
```

## 许可证

Copyright © 2026 BeyondPassenger.

keikeu 的源代码和随附文档采用
[GNU General Public License v3.0 或更高版本](LICENSE)（`GPL-3.0-or-later`）许可。
用户创建的 Paper、vault 与导出内容不属于 keikeu，不受此许可证约束；其权利归各自作者。

### 使用与分发注意事项

- 可以使用、复制、修改和分发 keikeu，也可以为副本或支持服务收费。
- 私下修改不需要公开；但向他人分发原版或改版（包括打包后的 macOS App）时，必须保留版权和许可证声明，并让接收者获得对应源码。
- 分发改版时，整个基于 keikeu 的作品须继续以 GPL-3.0-or-later 授权，并显著说明改动。
- keikeu 按“现状”提供，不提供明示或默示担保，也不承担法律允许范围外的责任。
- 本许可证不授予 `keikeu` 名称、标志或其他商标权；第三方依赖仍分别适用其自身许可证。
