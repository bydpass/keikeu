# keikeu Road v0.2 — Phase 8 产品验收记录

> 状态：完成
> 作者确认日期：2026-07-21
> 权限：支持性证据；当前状态以 [`../PROJECT.md`](../PROJECT.md) 为准，验收契约以 [`../SPEC.md`](../SPEC.md) §12 为准
> 更新前记录与 SOP：[`../archive/9114d63153711a7fa55e55bd663b27bfc11828b1/`](../archive/9114d63153711a7fa55e55bd663b27bfc11828b1/)

## 结论

唯一作者确认已完成：

1. 一次真实 one-shot 的 Paper → Flashcard → Paper → 外部编辑器流程；以及
2. 一个短/中篇准备流程的两次会话，包括 Flashcard 位置与 Paper/Flashcard 导航。

作者在完成两个场景后提交了脱敏 issue list，并明确断言 Phase 8 完成。记录中没有作者文字、灵感、名称、关系、Vault 路径或设备标识。

未观察到 P0 数据风险或 P1 主流程阻塞。发现的问题均为 P2/P3 候选、既定产品约束或已退役 v0.1 范围，因此不阻断 Phase 8。

## 场景 A：真实 one-shot

| 观察项 | 结果 |
| --- | --- |
| 场景状态 | 完成 |
| Summary-first 是否可接受 | 可接受；作者完成流程后未报告 Summary-first 异常或阻塞 |
| 是否需要返回 Paper | 有往返需求；返回可完成，但跨 Paper/Flashcard 切换不够便捷，列为 P2 |
| Flashcard → Paper | 通过 |
| 外部 Markdown 编辑器衔接 | 清楚；可使用系统默认程序打开 Markdown |
| 重新打开 Flashcard 的位置 | 符合完成场景的预期；未报告位置丢失 |
| P0/P1 | 无 |

## 场景 B：短/中篇跨会话流程

| 观察项 | 结果 |
| --- | --- |
| 场景状态 | 两次会话完成 |
| 跨会话位置 | 未报告位置丢失或无法继续 |
| Paper ↔ Flashcard | 可完成；直接切换和选择另一 Paper 不够便捷，列为 P2 |
| 高频阻塞 | 无 P1；存在导航效率问题 |
| P0/P1 | 无 |

## Issue 分级

| 观察 | 判定 | Phase 8 处理 |
| --- | --- | --- |
| 新 Paper 代号格式固定，不能任意自定义 | 既定约束 | SPEC 要求 `K-YYYYMMDD-NNN`；若要放开，进入下一 Road 产品决策 |
| Flashcard 间切换与直接选择不便 | P2 | 下一 Road 候选；当前可从 Paper 或 Library 打开 |
| 回收站访问不便，且没有永久清除 | P2 / 范围外 | v0.2 只承诺软删除与恢复；永久删除需另行设计数据安全规则 |
| Highlight 调整顺序生硬 | P2 | 下一 Road 交互候选 |
| iOS Flashcard 字体过大 | P2/P3，Phase 7.5 独立轻量测试轨道 | 不阻断 macOS Phase 8，也不是 Phase 8.5 的合入闸门 |
| macOS 缺少主动更换 Vault 的入口 | P2 | 当前流程可完成；不得以删除原 Vault 作为切换方式 |
| macOS 键盘操作不足 | P2；潜在无障碍风险 | 下一 Road 候选；若实际令必要操作无法完成则重新分级为 P1 |
| Cache、Outline、Custom Ending、CE、PA 等旧流程问题 | v0.1 历史范围 | Outline 已退出 Road v0.2，不进入当前修复范围 |

## 证据边界与剩余风险

- 这是唯一真实作者的产品证据，不是外部用户研究。
- 作者确认覆盖场景 A 与 B；原始应用 build/commit 没有单独记录。
- 未验证 iOS 文件服务、跨设备同步、provider 冲突合并或长篇工作流；这些不属于 macOS Phase 8 验收。
- P2/P3 候选不应被偷偷并入 Road v0.2；需要下一 Road 单独排序和验收。
- Phase 8 完成不自动创建 tag，也不自动宣告 Road 已归档。

## Road 收口门槛

在开发者决定归档或标记 Road v0.2 前，仍需：

1. 对当前候选提交运行完整测试、编译、文档检查和 `git diff --check`；
2. 复核 macOS 当前 build 与本记录的核心流程一致；
3. 保持 Phase 7.5 独立轻量 iOS 测试版与 Phase 8.5 Mac 前体的范围分离；以及
4. 由开发者明确决定是否创建 Road tag。
