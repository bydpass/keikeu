# Road v0.4 CP12 — Production bundle 与产品验收

> 状态：**通过；开发者于 2026-07-26 确认产品验收**
> 日期：2026-07-26
> 基线：CP11 `908fd85`

## 现在发生了什么

开发者把 Road v0.4 的发布最低系统提高到 **macOS 15.0**。追踪的 Tauri
配置、active SPEC、Planbook、理解规约与兼容 gate 已同步；历史归档不改。

锁定工具链从当前源码重建 PyInstaller sidecar，并用无 override 的标准
`tauri build` 生成 production identity `app.keikeu.desktop` 的
`keikeu.app`。隔离 copied Vault smoke 与去标识化真实作者场景 A/B 均已
完成；开发者确认没有未解决 P0/P1，CP12 Product acceptance 通过。

## 新增概念

- **发布最低系统：**`tauri.conf.json` 的 `minimumSystemVersion=15.0` 同时进入
  `Info.plist` 与主程序 Mach-O deployment target；它是构建约束，不是兼容证据。
- **Production bundle smoke：**使用生产名称、标识、内嵌冻结 sidecar 和追踪
  配置验证组合产物；未签名、未公证仍是明确的 Road 边界。
- **真实作者验收：**作者在有恢复备份的真实 Vault 中完成 A/B，只记录结论和
  问题等级，不记录文字、名称、关系、路径或设备标识。

## 数据怎么走

```text
作者动作
→ Vue
→ Tauri/Rust + JSONL sidecar
→ Python application service / Core
→ Markdown 与可重建索引
→ Library / Flashcard / 外部编辑器反馈
```

## Production bundle 工程证据

- Node/npm `22.23.1`/`10.9.8`，Rust/Cargo `1.88.0`/`1.88.0`，
  Python/PyInstaller `3.13.14`/`6.21.0`，arm64。
- `.venv/bin/python scripts/build_sidecar.py` → passed；冻结 sidecar 的
  protocol-v1 `system.hello` → passed。
- `npm --prefix frontend run tauri:build` → passed，无 CLI config override。
- `.venv/bin/python -m pytest -q` → **321 passed**；
  `npm --prefix frontend run test` → **48 passed**；
  `cargo test --manifest-path frontend/src-tauri/Cargo.toml` → **10 passed**。
- Python compileall、文档检查（28 active / 16 required）与
  `git diff --check` → passed。
- `CFBundleIdentifier=app.keikeu.desktop`，版本 `0.1.0`，
  `LSMinimumSystemVersion=15.0`；主程序 Mach-O `minos 15.0`。
- 主程序 SHA-256：
  `7d75998e78520ba03567a4a6f2b0781bdd1db03eb731553abac8effaf0e60264`。
- sidecar SHA-256：
  `0b73c9e14a2028088deaa2f85494c5595baed6ed00e96523895da488dd00acda`。
- fresh fake Home + copied v3 fixture 实际完成启动、合成 Paper 保存、初稿副本、
  Tags、Flashcard page 1、Library 找回、移入一层文件夹、完全退出与重启。
- 外部程序 handoff 返回成功；外部文件移动后显式 Refresh 找到新路径并清除旧
  路径。默认编辑器的目标标签在辅助功能树中不可确认，所以不扩大结论。
- 终止隔离 sidecar 后，下一请求显示
  `tauri_host · sidecar_unavailable · restart_sidecar`；手动重启恢复 Paper。
- 合成 Markdown 与索引路径一致。测试应用、sidecar 与假 Home 全部退出/删除；
  production `.app` 保留在忽略的 Tauri build 目录供作者验收。

以上只证明当前 macOS 27 beta 工作站上的 production bundle 工程行为。没有
macOS 15.0 机器的构建/启动证据，不得提前宣称 15.0+ 兼容。

## 作者报告的系统诊断

真实作者验收期间，终端输出：

```text
error messaging the mach port for IMKCFRunLoopWakeUpReliable
```

仓库源码不包含该字符串；本机 unified log 把它归于 HIToolbox，并显示同一进程
此后继续处理 WebKit 与输入法事件。12:21 验收时段没有对应崩溃报告，作者也未
观察到输入失效或数据异常。因此按非阻塞平台观察记录，不归为 P0/P1，也不修改
产品代码。若以后出现输入卡死、文本丢失或进程退出，必须按可见症状重新分级。

## 去标识化真实作者 SOP

开始前必须确认真实 Vault 有可恢复备份。以下步骤会保存、移动、建立分支、
Trash/恢复真实 Paper，并更新真实 config/device state；若出现 P0/P1，立即停止。

从仓库根目录人工启动当前候选：

```bash
open frontend/src-tauri/target/release/bundle/macos/keikeu.app
```

### 场景 A — 新 Paper

1. 新建、命名并保存一张真实 Paper。
2. 移入一层文件夹，从该 scope 找回。
3. 打开 Flashcard，确认 page 1、列表和合法跳页。
4. 使用外部编辑器 handoff。
5. 记录三栏定位、视觉层级、固定功能栏、键盘路径与 handoff 是否清楚。

### 场景 B — 既有 Paper / 两个 session

Session 1：打开并保存既有 Paper；在 Finder 外移后 Refresh 找回；创建分支，
将分支移至 Trash 后恢复。

Session 2：完全退出并重开；从文件夹 scope 与 Flashcard selector 找回原
Paper 和恢复后的分支；确认没有丢失、重复、静默覆盖或主流程阻塞。

只记录以下去标识化结果：

| 项目 | 结果 |
| --- | --- |
| 场景 A | Pass |
| 场景 B Session 1 | Pass |
| 场景 B Session 2 | Pass |
| 三栏定位与视觉层级 | Pass |
| 键盘路径 | Pass |
| 外部编辑器边界 | Pass |
| P0/P1 | 无未解决项 |

## 出错怎么查与撤销

1. UI 状态查 Vue；host/sidecar 查结构化层级与错误码；磁盘结果查已备份 Vault。
2. mutation 返回不明时不重试，先重新加载磁盘状态。
3. 立即退出候选可退回 Flet：`.venv/bin/flet run src/keikeu_app/main.py`。
4. CP12 diff 的回滚点是 `908fd85`；数据异常先停止并从确认过的备份恢复。

## 下一步依赖什么

CP12 已获准提交。开发者随后把 CP13 可证明的发布最低版本上调为 macOS 15.7；
CP13 使用同一接口构建候选，再于当前工作站复验原产物。
