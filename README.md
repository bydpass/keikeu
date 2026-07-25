# keikeu

> 本地优先的同人写作辅助工具：把已有灵感整理成耐久的 Markdown Paper，再用 Flashcard 帮作者聚焦扩写。

简体中文 | [English](README_EN.md)

## 当前状态

当前代码已经实现 `Paper Markdown → Flashcard → 外部正文编辑器` 核心。Road v0.2 Phase 0–7 工程、macOS 文件服务 smoke，以及 Phase 8 真实 one-shot 与短/中篇跨会话作者验收均已完成，并已以 local annotated tag `v0.2.0` 标记。

Phase 7.5 是独立的轻量 iOS 快速测试版，已在独立分支完成响应式界面、本机沙盒 Vault 与真机修复验证；它不是 macOS Road 的合入闸门。Road v0.3 的工程、macOS candidate smoke 与 CP6 真实作者验收均已完成；检索更快且清楚、外部编辑器 handoff 清楚，未报告未解决 P0/P1。其设计与验收文档已[只读归档](docs/archive/road-v0-3/README.md)，未创建 v0.3 tag。Road v0.4 已进入 CP0 文档权威启用；当前 Python/Flet 运行时仍是可运行基线，尚未引入 Vue/Tauri 依赖。实时坐标见 [PROJECT](docs/PROJECT.md)。

## 当前运行时核心流程

```text
已有灵感 → Paper Markdown → Flashcard → 外部正文编辑器
```

- **Paper**：必填当前 Summary、冻结的首次保存副本、有序可选 Highlights、平面可选 Tags。
- **Flashcard**：Summary-first 的只读投影；每次打开或切换 Paper 都从第 1 页开始，不保存阅读位置。
- **Library**：按全部/未归类/一层文件夹检索和排序 Paper，并提供拖放、菜单、批量移动、分支、Trash 与恢复。
- **Vault**：只选择当前用户 Home 内路径；切换前验证，unsafe 旧 Vault 先复制并核对；尚未启用 Apple App Sandbox。
- **外部编辑器**：正式正文始终在 keikeu 之外完成。

## Road v0.3 归档

[最终 CP6 记录](docs/archive/road-v0-3/acceptance/road_v0_3.md)与产品、视觉、交互、架构、ADR、Planbook 一并保存在[版本归档](docs/archive/road-v0-3/README.md)。归档不改变 Vault、运行时或 Git 历史。

## 产品原则

- 本地优先；Markdown 是作者资产，JSON 索引可重建。
- 不静默改写、覆盖、上传或评价作者文字。
- 不做 keikeu 账号、云后端、遥测或后台同步。
- 用户可选择 iCloud Drive 等操作系统暴露的普通文件目录。
- 不接入 fandom 数据库，不做 AI 代写、社区或内置正文编辑器。

稳定产品边界见 [SPEC](docs/SPEC.md)，可判定纪律见 [RULES](docs/RULES.md)。

## 开发

要求 Python `>=3.11,<3.14`。

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
python -m pytest
flet run src/keikeu_app/main.py
```

## 仓库地图

```text
README.md                 外部入口与运行命令
AGENTS.md                 Agent 操作纪律与读图顺序
PLAN_revised.md           Road v0.4 执行计划
RULE_FOR_UNDERSTANDING.md Road v0.4 理解与审批闸门
docs/PROJECT.md           当前坐标、模块入口、下一闸门
docs/SPEC.md              Road v0.4 产品与作者控制边界
docs/RULES.md             工程、交互、数据与证据规则
docs/design/              Road v0.4 活跃视觉与交互 map
docs/architecture/        Road v0.4 活跃架构 map 与 ADR
docs/acceptance/          支持性验收记录；不独立定义状态
docs/manual/              面向人的补充说明；不定义规范
docs/generated/           可重建、可删除的观察输出
docs/archive/             只读历史；不参与冷启动
src/keikeu_core/          纯 Python 领域与文件逻辑
src/keikeu_app/           Flet 壳层、页面与设备本地状态
tests/                    可验证的实现事实
```

硬约束：`keikeu_core` 不得 import Flet。Markdown 读写只由 core 层负责。

## 文档入口

| 想知道什么 | 唯一入口 |
| --- | --- |
| 稳定产品目的与作者控制边界 | [SPEC](docs/SPEC.md) |
| 当前做到哪、下一步是什么 | [PROJECT](docs/PROJECT.md) |
| 修改时不可违反什么 | [RULES](docs/RULES.md) |
| Road v0.4 架构目标与当前实现 | [Architecture map](docs/architecture/architecture.html) |
| Road v0.4 视觉方向 | [Design map](docs/design/design.html) |
| Road v0.4 交互与迁移顺序 | [Interaction map](docs/design/interaction.html) |
| Agent 如何工作 | [AGENTS](AGENTS.md) |
| 人工阅读的设计、Git 与伦理说明 | [Human manuals](docs/manual/README.md) |
| 历史为何这样演变 | [Archive](docs/archive/README.md) |

## 路线

```text
v0.1        已归档的 macOS Cache / Outline pre-alpha
v0.2        macOS Paper / Flashcard Core；产品验收完成，等待 Road 收口决定
Phase 7.5   独立轻量 iOS 快速测试版
Phase 8.5   Road v0.3 准备；下一版 Mac 端前体
Road v0.3   macOS Paper Library；CP6 product accepted，设计与验收文档已归档
Road v0.4   Vue/Tauri 前端替换；CP0 文档权威启用中，Flet 仍是运行基线
Pre-Advance 可选 Markdown Outline；不阻塞核心流程
之后        iPhone/iPad 文件服务能力、Android、Windows
```

## 许可

代码与随附文档采用 [GPL-3.0-or-later](LICENSE)。用户创建的 Paper、Vault 与导出内容不属于 keikeu，其权利归作者。
