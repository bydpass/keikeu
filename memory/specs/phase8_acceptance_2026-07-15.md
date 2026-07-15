# keikeu Road v0.2 — Phase 8 产品验收记录

> 状态：进行中（尚未获得真实创作工作流结果）
> 分支：`feature/road-v02-acceptance`
> 关联：[`planbook_road_v0_2.md`](planbook_road_v0_2.md) § Phase 8、[`spec_road_v0_2.md`](spec_road_v0_2.md) §11

## 边界

这份记录只收集使用体验与可复现问题，不要求、也不应包含正文、灵感、角色名、关系或任何作者私密内容。验证在作者自己的 Vault 内完成；合成 Vault 的 Phase 7 smoke 不能代替本 Phase。

## 场景 A：真实 one-shot

1. 用一个准备写成正文的真实 Paper，完成 Library → Paper → Flashcard → 返回 Paper 的路径。
2. 从 Summary 开始浏览，前进到至少一张 Highlight（如该 Paper 有 Highlight），关闭并重新打开 Flashcard。
3. 需要时返回 Paper，再使用系统默认外部编辑器继续正文；keikeu 不承载正文输入。
4. 记录以下结果：

| 观察项 | 结果（待作者填写） |
|---|---|
| Summary-first 是否自然 | 未验证 |
| 是否需要频繁跳出 Flashcard | 未验证 |
| 是否能自然返回 Paper | 未验证 |
| 外部正文编辑器的衔接是否清晰 | 未验证 |
| P0/P1 阻塞问题 | 未验证 |

## 场景 B：短/中篇重复工作流

1. 在至少两个不同会话中处理一个短篇或中篇准备流程；可包含多个 Paper，但不记录其内容。
2. 检查跨会话 Flashcard 位置是否合乎预期，并注意是否因 Summary、Highlight 或标签而频繁回到 Paper。
3. 记录耗时感受、打断点和任何会导致无法继续的路径；非阻塞想法进入下一 Road 候选池，而不是扩大本 Road。

| 观察项 | 结果（待作者填写） |
|---|---|
| 跨会话位置是否符合预期 | 未验证 |
| Paper/Flashcard 往返是否自然 | 未验证 |
| 是否出现 P0 数据风险或无法继续 | 未验证 |
| 是否出现 P1 高频阻塞 | 未验证 |
| 其他候选改进（非阻塞） | 未验证 |

## 回传格式

作者只需回传类似下列的脱敏结果，不必粘贴写作内容：

```text
场景 A：通过 / 有问题
场景 B：通过 / 有问题
Summary-first：自然 / 不自然（原因）
频繁返回 Paper：是 / 否（原因）
P0/P1：无 / [级别] [可复现步骤]
候选改进：可选，简述即可
```

## 归档门槛

收到场景 A 与 B 的真实结果后，才可以：

1. 修复确认的 P0/P1，或明确记录没有此类问题；
2. 重新运行完整测试、编译、文档链接检查、`git diff --check` 和 macOS 手工验收；
3. 在审计记录中写入证据与剩余风险；
4. 由开发者决定是否创建 Road tag。

在此之前，Road v0.2 只能称为“功能实现与文件服务 smoke 已完成”，不能称为“macOS MVP 已验收”或“Road 已归档”。
