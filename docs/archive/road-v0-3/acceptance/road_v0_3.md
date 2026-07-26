> **ARCHIVE — READ ONLY.** Final Road v0.3 acceptance record; archived on 2026-07-25.

# keikeu Road v0.3 — CP5 证据与 CP6 产品验收

> 状态：**CP5 macOS candidate smoke complete / CP6 complete / product accepted**
> 日期：2026-07-25
> 权限：支持性证据；验收契约以 [`../SPEC.md`](../SPEC.md) §12 为准，当前结论以 [`../PROJECT.md`](../PROJECT.md) 为准

## 证据边界

- CP5 证明当前分支的工程实现和 macOS candidate workflow；CP6 结论来自开发者确认的去标识化真实作者场景。
- 所有破坏性动作先在 synthetic 或 copied Vault 执行；唯一真实 Vault、真实 config 和真实 device state 未修改。
- 记录不包含正文、灵感、名称、关系、Vault 路径、设备标识或 provider 私密信息。
- Product acceptance、tag、archive 和 push 是四个独立决定；本记录不授权后三项。

## CP5 candidate smoke

可见 Flet synthetic flow 实际完成：

1. 通过 Vault picker 初始化隔离 Vault，显示一次 daily start card 后进入空白 Paper；
2. 新建并命名 Paper，保存合成 Summary；
3. 新建一层文件夹，把 Paper 移入文件夹并建立同目录分支副本；
4. 从 Library 打开指定 Paper 的 Flashcard；
5. 将分支移至 Trash、展开 Trash 并恢复；
6. 通过 macOS 系统目录选择器预览并切换第二个 Vault；以及
7. 同一本地日期 relaunch，确认 daily start card 不重复出现。

Copied-Vault flow 实际完成：

1. 在副本中保存一个 v2 Paper，确认 lazy upgrade 到 v3，未知 frontmatter 保留；
2. 用 Finder 把副本中的 Paper 移到一层文件夹，显式 Refresh 后仍显示 1 个 Paper、目标文件夹与 0 个资产错误；
3. copied-Vault relocation 的 copy/verify/switch 结果保留原副本且使用独立 config；以及
4. smoke 结束后删除全部 synthetic/copied Vault 与临时 config，源 Vault 未修改。

真实 outside-Home/external-volume 来源没有被拿来做交互首测；路径拒绝、copy-before-switch、source unchanged 和 failure-before-config-change 继续由直接自动化测试覆盖。本记录不宣称真实 provider、跨设备同步、外部卷或 Apple App Sandbox 已验证。

## Smoke 中发现并修复的问题

| 问题 | 分级 | 修复与复验 |
| --- | --- | --- |
| 合法 Paper Vault 缺少尚未使用的 `.trash/` 时，Vault switch 成功但 Library 打不开 | P1 | 空 Trash 枚举改为 0；第一次 soft-delete 安全创建缺失布局。聚焦测试和可见 Flet 复验通过。 |
| Vault preview 只统计 `cache/` 根层，漏掉一层文件夹 Paper | P2 | 改用统一的安全 active-Paper 枚举。文件夹 Paper preview 与 Finder Refresh 可见复验均为 1。 |

修复后 candidate 未再发现 P0/P1。CP5 关闭；CP6 仍不可由 synthetic/copy 证据代替。

## 自动检查

Phase 7 最终检查：

- `.venv/bin/python -m pytest -q --basetemp=tests/test-vault/pytest-final-rerun` → **276 passed in 47.37s**
- `.venv/bin/python -m compileall -q src` → passed
- `.venv/bin/python scripts/check_docs.py` → **27 active files、16 required files，预算和本地链接通过**
- `git diff --check` → passed

本地 HTML browser QA 实际检查 architecture/design/interaction：nav、theme、search、architecture layer filter、design device tabs 与 interaction stepper/Flashcard prototype 均可用；375/768/1440 三档没有水平溢出，控件没有空的 button/input 名称。仓库没有视觉 baseline，且运行环境没有 axe-core，因此视觉回归与完整 WCAG 审计为 **inconclusive / not run**，不能据此宣称无障碍已完整通过。

## CP6 去标识化产品验收 SOP

开始前：使用已经备份且可恢复的真实作者 Vault；不要把任何内容或路径复制到本记录。若出现 P0/P1，停止场景，记录最短去标识化复现并修复后重跑。

### 启动与记录

本轮人工测试会写入真实 Vault：保存既有 v2 Paper 会写成 v3，移动、Trash 与恢复会改变文件位置。先制作可恢复备份，再在应用内确认目标 Vault。

从仓库根目录启动：

```bash
.venv/bin/flet run src/keikeu_app/main.py
```

完成场景 A 后执行场景 B 的 Session 1。完全退出应用，再执行 Session 2。只在下方结果表记录完成状态、检索体验、handoff 清晰度和 P0/P1；不要写正文、名称、关系或路径。

### 场景 A — 新 Paper

1. 新建并命名一个真实 Paper。
2. 保存后把它移动到一层文件夹，再从该文件夹 scope 找回。
3. 在 Flashcard selector 中选择它，验证第 1 页、列表与合法跳页。
4. 使用外部编辑器 handoff；确认“keikeu 管 Paper / 外部编辑器管正文”的边界仍清楚。

只记录：检索是否更快且清楚、handoff 是否清楚、是否发生 P0/P1。

### 场景 B — 既有 v2 Paper / 两个 session

Session 1：

1. 打开一个既有 v2 Paper，保存一次并确认可继续读取。
2. 在 Finder 将它移动到一层文件夹，返回 keikeu 显式 Refresh 后找回。
3. 创建分支副本，将副本移至 Trash，再恢复。

Session 2：

1. 完全退出并重新打开 keikeu。
2. 从文件夹 scope 与 Flashcard selector 再次找回原 Paper 和恢复后的分支。
3. 再次确认外部编辑器 handoff 边界清楚，没有丢失、重复或静默覆盖。

只记录：跨 session 检索是否更快且清楚、handoff 是否清楚、是否发生 P0/P1。

## CP6 结果

| 项目 | 结果 |
| --- | --- |
| 人工测试状态 | **Complete** |
| 场景 A 完成 | Complete |
| 场景 B Session 1 完成 | Complete |
| 场景 B Session 2 完成 | Complete |
| 检索更快且清楚 | Yes |
| 外部编辑器 handoff 清楚 | Yes |
| P0/P1 | None reported |
| CP6 结论 | **Complete — Road v0.3 product accepted** |

开发者于 2026-07-25 确认上述去标识化结论，并明确决定归档 Road v0.3 设计文档。未创建 tag、commit 或 push。
