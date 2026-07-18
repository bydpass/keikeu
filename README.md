# keikeu

> 本地优先的同人写作辅助工具：把已有灵感整理成耐久的 Markdown Paper，再用 Flashcard 帮作者聚焦扩写。

简体中文 | [English](README_EN.md)

## 当前状态

当前代码已经实现 `Paper Markdown → Flashcard → 外部正文编辑器` 核心，Road v0.2 Phase 0–7 工程与 macOS 文件服务 smoke 有记录。Phase 8 仍缺完整的真实 one-shot 与短/中篇跨会话作者证据，因此不能称为“macOS MVP 已验收”或“Road 已归档”。

iOS 7.5 已完成响应式界面、本机沙盒 Vault 与真机修复验证；它是独立的平台工程轨道，不替代 macOS 产品验收。实时坐标见 [PROJECT](docs/PROJECT.md)。

## 核心流程

```text
已有灵感 → Paper Markdown → Flashcard → 外部正文编辑器
```

- **Paper**：必填当前 Summary、冻结的首次保存副本、有序可选 Highlights、平面可选 Tags。
- **Flashcard**：Summary-first 的只读投影；位置是每台设备可丢弃的本地状态。
- **Library**：从本地索引检索、打开、软删除和恢复 Paper。
- **外部编辑器**：正式正文始终在 keikeu 之外完成。

## 产品原则

- 本地优先；Markdown 是作者资产，JSON 索引可重建。
- 不静默改写、覆盖、上传或评价作者文字。
- 不做 keikeu 账号、云后端、遥测或后台同步。
- 用户可选择 iCloud Drive 等操作系统暴露的普通文件目录。
- 不接入 fandom 数据库，不做 AI 代写、社区或内置正文编辑器。

完整产品契约见 [SPEC](docs/SPEC.md)，可判定纪律见 [RULES](docs/RULES.md)。

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
docs/PROJECT.md           当前坐标、模块入口、下一闸门
docs/SPEC.md              产品唯一真相源
docs/RULES.md             工程、交互、数据与证据规则
docs/design/              可执行视觉系统与交互样张
docs/architecture/        模块、数据流、生命周期与 ADR
docs/acceptance/          支持性验收记录；不独立定义状态
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
| 项目为何存在、做什么、不做什么 | [SPEC](docs/SPEC.md) |
| 当前做到哪、下一步是什么 | [PROJECT](docs/PROJECT.md) |
| 修改时不可违反什么 | [RULES](docs/RULES.md) |
| 模块与数据如何流动 | [Architecture map](docs/architecture/architecture.html) |
| 视觉 token 与组件状态 | [Design system](docs/design/design.html) |
| 用户操作及成功/错误路径 | [Interaction map](docs/design/interaction.html) |
| Agent 如何工作 | [AGENTS](AGENTS.md) |
| 历史为何这样演变 | [Archive](docs/archive/README.md) |

## 路线

```text
v0.1        已归档的 macOS Cache / Outline pre-alpha
v0.2        macOS Paper / Flashcard Core；产品验收进行中
iOS 7.5     设备壳层与本机 Vault 工程验证
Pre-Advance 可选 Markdown Outline；不阻塞核心流程
之后        iPhone/iPad 文件服务能力、Android、Windows
```

## 许可

代码与随附文档采用 [GPL-3.0-or-later](LICENSE)。用户创建的 Paper、Vault 与导出内容不属于 keikeu，其权利归作者。
