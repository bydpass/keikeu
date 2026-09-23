# keikeu

> 本地优先的同人写作前整理工具：把已有灵感整理成可编辑、可修复的 Markdown 卡页 Paper，再交给你惯用的正文编辑器。

简体中文 | [English](README_EN.md)

![License](https://img.shields.io/badge/license-GPL--3.0--or--later-blue)
![Platform](https://img.shields.io/badge/platform-macOS%20(Apple%20Silicon)-lightgrey)
![Status](https://img.shields.io/badge/status-personal%20dev%20build-orange)

## keikeu 是什么

keikeu 服务于单个同人作者，只管写正文之前的阶段：

```text
已有灵感 → 编辑并保存卡页 Paper → 外部正文编辑器
```

你带走的产物就是普通 Markdown 文件，任何文本编辑器都能打开、阅读和修复。keikeu 不做账号、云后端、遥测、AI 代写、fandom 数据库、社区，也不内置正文编辑器。

## 目前能做什么

- **Paper 卡页**：一份 Paper 由至少一张有序卡页组成，可设显示名和 Tags。每页有可选标题、Markdown 正文，类型为总结、高光、碎碎念或不设；每份最多一张总结。
- **按光标拆页**：“加一页”从光标处拆开当前页，后半段移入新页。
- **整份保存**：一次保存提交整份 Paper，并检查文件在编辑期间是否被改动。切换 Paper／Vault、导航或关闭窗口前会提示未保存内容。
- **Library**：搜索所有页面，按全部／未归类／单层文件夹筛选和排序；支持移动、分支、Trash 与恢复。
- **Vault**：Vault 是你选定的本地文件夹，限当前用户 Home 目录内。iCloud Documents 路线已有候选实现，需要你主动启用，尚未正式验收。
- **恢复**：遇到损坏的 Paper 会保留原字节、说明错误并允许导出。写入结果不确定时，先只读核对再决定下一步。旧格式可迁移，迁移前会先做完整备份。

## 当前状态

| 项目 | 状态 |
| --- | --- |
| 已接受的产品基线 | Road v0.7 CP8（`2f03aee`）：Paper v4、Index v4、JSONL 协议 v2 |
| 最近完成的工程整顿 | Road v09 CP0–CP4（`c615ce5`）：目录重排、纯 Rust 规则 crate、开发工具与文档 |
| 下一步 | 用原生 SwiftUI 替换 iOS 界面，尽可能复用 Rust 内核；见[转交清单](docs/road-v09-01-handoff.md) |
| 发行 | 个人开发构建；没有签名、公证或公开安装包 |

实时进度与证据边界以 [PROJECT](docs/PROJECT.md) 为准。

## 平台

| 平台 | 实现 | 状态 |
| --- | --- | --- |
| macOS，本地 Vault | Vue/Vite → Tauri/Rust 宿主 → Python sidecar | 已接受的桌面基线 |
| macOS，iCloud Vault | 进程内 Rust Paper Core＋Apple 原生文件协调 | 候选实现，未正式验收 |
| iPhone | 旧 Vue/Tauri 候选，将由原生 SwiftUI 替换 | 规划中 |
| Windows／Android | 分别保留 Vue/Tauri/Python 路线、另排原生实施 | 未排期，无可运行包 |

## 从源码运行（macOS）

需要 Apple Silicon Mac、Python `>=3.11,<3.14`、Node `22.23.2`／npm `10.9.8`，以及 Rust `1.88.0`（由 `rust-toolchain.toml` 固定）。

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
python -m pip install -r requirements-build.lock
npm --prefix apps/desktop ci
./dev
```

`./dev` 是开发者终端面板：按 `a` 用现有 sidecar 启动，按 `b` 先重建 sidecar 再启动；它还会显示所管理进程的日志，并可浏览本地文档。直接排障时可用底层命令：

```bash
.venv/bin/python scripts/build_sidecar.py
npm --prefix apps/desktop run tauri:dev
```

## 测试

```bash
.venv/bin/python -m pytest
npm --prefix apps/desktop run test
cargo test --workspace --locked
.venv/bin/python scripts/check_docs.py
```

自动测试生成的合成 Vault 和临时产物写入被忽略的 `tests/test-vault/`，不会碰你的真实 Vault。

## 仓库结构

```text
apps/desktop/src/                  Vue 界面
apps/desktop/src-tauri/            Tauri/Rust 宿主、存储路由与恢复
apps/desktop/python/keikeu_core/   纯 Python 领域与文件逻辑
apps/desktop/python/keikeu_bridge/ Application Service、JSONL 协议与 sidecar
crates/keikeu-core/                不访问文件的 Rust Paper 规则
platforms/apple/                   Apple 原生宿主与文件协调
scripts/                           构建、上下文打包与文档检查
tests/                             Python 测试与受版本控制的 fixtures
docs/                              产品、规则、设计、架构、验收与手册
dev                                开发者终端面板
```

硬约束：`keikeu_core` 不依赖任何 GUI 或 transport；Markdown 读写只由后端负责；纯 Rust 规则 crate 不访问文件。

## 文档

| 想知道什么 | 入口 |
| --- | --- |
| 产品目的与作者控制边界 | [SPEC](docs/SPEC.md) |
| 当前进度与下一步 | [PROJECT](docs/PROJECT.md) |
| 修改时必须遵守的规则 | [RULES](docs/RULES.md) |
| 架构 | [Architecture map](docs/architecture/architecture.html) |
| 桌面视觉与交互规范 | [Design map](docs/design/design.html)、[Interaction map](docs/design/interaction.html) |
| Agent 工作方式 | [AGENTS](AGENTS.md) |
| 面向人的技术、设计、Git 与伦理手册 | [Manuals](docs/manual/README.md) |
| 历次 Road 的施工快照 | [Archive](docs/archive/snapshots/) |

## 路线

| 阶段 | 内容 | 结果 |
| --- | --- | --- |
| v0.1–v0.2 | macOS 原型、Paper／Flashcard Core | v0.1 已归档，v0.2 已验收 |
| Road v0.3 | Paper Library | 已验收并归档 |
| Road v0.4 | 前端替换为 Vue/Tauri，退役 Flet | [已验收](docs/acceptance/road_v0_4_cp14.md) |
| Road v0.5 | Quiet Desk 界面与交互收口 | [已验收](docs/archive/snapshots/road-v0-5.html) |
| Road v0.6 | Paper v4 卡页重构 | [已验收](docs/archive/snapshots/road-v0-6.html) |
| Road v0.7 | 连续编辑流、响应式布局、原生输入法 | [已验收](docs/archive/snapshots/road-v0-7.html) |
| Road v0.8 | 统一 Rust 核心与 iCloud 候选 | 中断并转交，未最终验收 |
| Road v09 | 工程目录与执行体系整顿 | [已完成](docs/archive/snapshots/road-v09.html) |
| 下一步 | 原生 SwiftUI iOS | 规划中 |
| 后续 | 桌面功能对等、Python 退役、外部 Alpha、Android | 各自另排 |

## 许可

代码与随附文档采用 [GPL-3.0-or-later](LICENSE)。你创建的 Paper、Vault 和导出内容不属于 keikeu，权利归作者本人。
