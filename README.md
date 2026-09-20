# keikeu

> 本地优先的同人写作辅助工具：把已有灵感整理成耐久、可继续编辑的 Markdown 卡页 Paper。

简体中文 | [English](README_EN.md)

## 当前状态

Road v0.6 已完成并归档：production 使用 Paper v4、Index v4 与 protocol v2，Paper 本身就是可编辑的有序卡页；旧正常运行链已删除，未知结果与人工修复 Gate、一号真实作者 Gate 均已通过，且无未解决 P0/P1。

Road v0.7 已通过 CP0–CP8，最终 checkpoint `2f03aee`，见[施工快照](docs/archive/snapshots/road-v0-7.html)。v08 已完成 CP0–CP4 工程及 CP5 的 15/16 组历史检查，B14 未验；该 Road 已中断转交，未获最终接受。[旧计划](PLAN_road_v0_8.md)与[双端改动图](docs/architecture/road-v0-8-changes.html)仅用于追溯。[Road v09](docs/road-v09.md) CP0–CP4 已完成：目录、纯 Rust 核心与工具重整通过工程和 Mac 合成冒烟，最终检查点 `c615ce5`，见[施工快照](docs/archive/snapshots/road-v09.html)。后续 v09.01 再替换原生 iOS。

产品文档与源码于 2026-08-26 按 Road v0.7 完成态复核。当时发现 App-root pending intent 的关闭保护只挂在 `PaperView`；2026-09-05 的[独立修复报告与教学](docs/acceptance/close-guard-2026-09-04.md)分别记录代理检查、开发者人工验收，以及测试工具自动重启导致正式每日启动状态更新的事件。当前批准边界见 [PROJECT](docs/PROJECT.md)。2026-08-29 又加入独立的开发者 TUI 与四份技术手册；本地交接路由于 2026-08-30 迁至根目录 `CONTEXT.md`。这些开发工具不改变产品界面、运行链或验收状态。

Phase 7.5 是独立的轻量 iOS 快速测试版，已在独立分支完成响应式界面、本机沙盒 Vault 与真机修复验证；它不是 macOS Road 的合入闸门。Road v0.3 的工程、macOS candidate smoke 与 CP6 真实作者验收均已完成；检索更快且清楚、外部编辑器 handoff 清楚，未报告未解决 P0/P1。其设计与验收文档已只读归档（Git 历史：`78eb755:docs/archive/road-v0-3/README.md`），未创建 v0.3 tag。**Road v0.4 已彻底完成**：Gate A、Gate B、产品验收与 macOS 15.7+ 兼容性均已通过；该桌面基线使用 Vue/Tauri 与本地 Python sidecar，Flet 已在 CP14 退役。**Road v0.5 也已完成并归档**：Paper Desk、保存基线、离开保护、Flashcard/Library 连贯性、全应用 Quiet Desk 视觉与固定滚动语义均已验收。实时坐标见 [PROJECT](docs/PROJECT.md)。

## 当前运行时核心流程

```text
已有灵感 → 编辑并保存卡页 Paper → 外部正文编辑器
```

- **Paper**：至少一张有序卡页；页标题始终可编辑，正文为作者 Markdown，类型可为总结/高光/碎碎念或空；保存一次提交整份 Paper。
- **Library**：搜索整份 Paper，按全部/未归类/一层文件夹检索和排序，并提供单份移动、分支、Trash 与恢复；当前没有拖放、多选或批量移动。
- **Vault**：普通本地路径限当前用户 Home 内，切换前验证；Apple 沙盒／iCloud 使用原生受控根目录，当前路由见 PROJECT。
- **外部编辑器**：正式正文始终在 keikeu 之外完成。

当前已接受的 CP8 composition、证据层级与 Road 收口边界见 [PROJECT](docs/PROJECT.md)。

## Road v0.3 归档

最终 CP6 记录（Git 历史：`78eb755:docs/archive/road-v0-3/acceptance/road_v0_3.md`）与产品、视觉、交互、架构、ADR、Planbook 一并保存在版本归档（Git 历史：`78eb755:docs/archive/road-v0-3/README.md`）。2026-09-18 已删除 snapshots 之外的归档文件；可用 `git show <提交>:<路径>` 查阅上述原文。Vault、运行时与 Git 历史不变。

## Road v0.4 完成记录

[CP14 验收记录](docs/acceptance/road_v0_4_cp14.md)、计划文档归档（Git 历史：`78eb755:docs/archive/road-v0-4/README.md`）与[完整施工 snapshot](docs/archive/snapshots/refactor-retire-flet-after-road-v0-4-acceptance.html)共同记录 CP0–CP14、架构迁移、验收闸门、问题修复、测试演进与兼容性证据。Road v0.4 至此彻底完成；tag、push、签名与分发仍是独立决定。

## Road v0.5 完成记录

[Road v0.5 施工 snapshot](docs/archive/snapshots/road-v0-5.html) 绑定最终 checkpoint `d900953`，记录 CP0–CP7 的 branch、commit、范围、改动、检查、QA、遗漏与风险。Road v0.5 已完成并归档；未创建 tag 或 push，签名、公证、DMG 与公开分发仍属于后续独立决定。

## Road v0.6 完成记录

[Road v0.6 施工 snapshot](docs/archive/snapshots/road-v0-6.html) 绑定最终 checkpoint `18a1024`，记录 Paper v4 从契约基线、Core、迁移、UI、全栈切换、安全 Gate 到真实作者验收的完整证据。Road 已收尾；未创建 tag、push 或发布声称。

## Road v0.7 完成记录

[Road v0.7 施工 snapshot](docs/archive/snapshots/road-v0-7.html) 绑定最终 checkpoint `2f03aee`，记录 CP0–CP8、连续编辑流、响应式 Anchor、Figma 与实体键盘原生 IME 证据。Road 已完成并归档；未创建 tag，亦未 push、签名、打包或发布。

## 产品原则

- 本地优先；Markdown 是作者资产，JSON 索引可重建。
- 不静默改写、覆盖、上传或评价作者文字。
- 不做 keikeu 账号、云后端、遥测或 keikeu 管理的后台同步。
- v08 已实现原生 iCloud Documents 候选；历史同步证据与未验 B14 分开保留，不能据此声称新版本已验收。
- 不接入 fandom 数据库，不做 AI 代写、社区或内置正文编辑器。

稳定产品边界见 [SPEC](docs/SPEC.md)，可判定纪律见 [RULES](docs/RULES.md)。

## 开发

要求 Python `>=3.11,<3.14`、Node/npm `22.23.2`/`10.9.8` 和
Rust/Cargo `1.88.0`。

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
python -m pip install -r requirements-build.lock
npm --prefix apps/desktop ci
./dev
.venv/bin/python scripts/build_sidecar.py
npm --prefix apps/desktop run tauri:dev
```

日常开发首选 `./dev`：按 `a` 使用现有 sidecar，按 `b` 重建后启动；它也显示所管理
进程的日志并浏览本地文档。后两条底层命令保留用于直接排障。

## 仓库地图

```text
README.md                 外部入口与运行命令
dev                       开发者 TUI：启动、进程日志与本地文档
AGENTS.md                 Agent 操作纪律与读图顺序
docs/PROJECT.md           当前坐标、模块入口、下一闸门
docs/SPEC.md              已接受桌面边界与 v08 存储契约
docs/RULES.md             工程、交互、数据与证据规则
docs/design/              CP8 accepted 视觉、交互 map 与详细设计
docs/architecture/        current/target 架构 map 与 ADR
docs/acceptance/          支持性验收记录；不独立定义状态
docs/manual/              面向人的补充说明；不定义规范
docs/archive/snapshots/   保留的只读施工快照；其余旧归档从 Git 历史查阅
CONTEXT.md                ignored 本地 Agent 路由；不定义权威
apps/desktop/python/keikeu_core/          纯 Python 领域与文件逻辑
apps/desktop/python/keikeu_bridge/        Application Service、JSONL 协议与 sidecar
apps/desktop/                 Vue/Vite 界面与 Tauri/Rust 宿主
crates/keikeu-core/        不含文件访问的 Rust Paper 规则
platforms/apple/          Apple 原生宿主与文件协调
tests/                    可验证的实现事实
```

硬约束：`keikeu_core` 不得依赖任何 GUI 或 transport。Markdown 读写只由
后端负责；纯 Rust 规则 crate 不访问文件。

## 文档入口

| 想知道什么 | 唯一入口 |
| --- | --- |
| 稳定产品目的与作者控制边界 | [SPEC](docs/SPEC.md) |
| 当前做到哪、下一步是什么 | [PROJECT](docs/PROJECT.md) |
| 修改时不可违反什么 | [RULES](docs/RULES.md) |
| 当前架构实现 | [Architecture map](docs/architecture/architecture.html) |
| 当前 Road v0.7 界面视觉规范 | [Design map](docs/design/design.html) |
| 当前 Road v0.7 界面交互规范 | [Interaction map](docs/design/interaction.html) |
| Agent 如何工作 | [AGENTS](AGENTS.md) |
| 人工阅读的开发技术、设计、Git 与伦理说明 | [Human manuals](docs/manual/README.md) |
| 历史为何这样演变 | [Archive](docs/archive/snapshots/) |

## 路线

```text
v0.1        已归档的 macOS Cache / Outline pre-alpha
v0.2        macOS Paper / Flashcard Core；产品验收完成，本地 annotated tag v0.2.0，归档另行决定
Road v0.3   macOS Paper Library；CP6 product accepted，设计与验收文档已归档
Road v0.4   Vue/Tauri 前端替换完成；CP14 已验收
Road v0.5   Quiet Desk UI 与交互收口完成；CP7 已验收并归档
Road v0.6   Paper v4 卡页重构；CP7 已验收并归档
Road v0.7   CP8 已验收并归档；最终 checkpoint 2f03aee
Road v0.8   中断／转交；CP5 未获最终接受，B14 未验
Road v09    CP0–CP4 完成并保存快照；最终检查点 c615ce5
Road v09.01 原生 SwiftUI iOS 替换；另行实施与设备验收
后续        桌面对等、Python 退役、Alpha、Android 原生实施各自排期
Mac         保留当前实现，日后重构
Windows     保留 Vue/Tauri/Python 路线，适配另排；v09 不要求可运行包
Pre-Advance 可选 Markdown Outline；未排期，不阻塞核心流程
```

## 许可

代码与随附文档采用 [GPL-3.0-or-later](LICENSE)。用户创建的 Paper、Vault 与导出内容不属于 keikeu，其权利归作者。
