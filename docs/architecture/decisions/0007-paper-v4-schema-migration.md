# ADR-0007：Paper v4 schema 与迁移

**日期**：2026-08-02

**状态**：accepted
**决策者**：developer

## 背景

Paper v3 把必填 Summary、冻结的 `initial_summary` 与有序 Highlights 分开保存，再生成独立 Flashcard。Road v0.6 的产品决定是直接编辑由有序卡页组成的 Paper，并以 Paper 本身作为离开 keikeu 时的成果。

## 决策

Paper v4 以一份 Paper 和至少一张有序 `CardPage` 为唯一 active 模型。每页持久保存可空 `name`、原样 `content` 与可空 `type`；类型只允许 `summary`、`snapshot`、`whisper`。一份 Paper 最多一个 Summary，Snapshot 与 Whisper 不限量。Paper display name 与 page name 是两个独立字段。

Markdown v4、marker escape、Tags grammar、DTO、unknown-result 和修复契约只由已批准的 [Paper v4 设计](../../design/road-v0-6-paper-v4-design.md)定义；本 ADR 不复制第二套 grammar。

v2/v3 → v4 迁移中，`initial_summary` 是唯一获准不进入 active v4 schema 的作者字段。完整备份必须保留其原始字节。该决定只适用于显式迁移，不是普通保存、解析错误或修复时删除作者文字的例外。

Legacy Tag 只要含多行、控制字符、空项、外围空白或 trim 后重复，整个预检就阻塞。迁移不得借 v4 的正常编辑语义静默 trim、丢空或去重旧字段。Raw loss-audit 必须让每个 legacy source byte 唯一归属；任何歧义均零写入。

## 后果

- CP1/CP2 以 additive v4 符号实现模型、codec、迁移与 Index；CP4 前 production 继续使用 v3/v1。
- 真实迁移前必须创建 active Vault 外但 Home 内的完整备份，并先完成 regular-file manifest 与逐字节验证。
- Mixed schema 在完成续迁前禁止编辑、每日 claim 与 Index rebuild。
- 迁移报告只记录字段处置和状态，不记录作者内容、长度、名称或私密路径。
- App 不自动修复损坏 Paper；人工修复契约在 CP6 交付并只对合成数据或完整副本演练。

## 复核条件

只有当实际迁移 fixture、复制 Vault 或真实作者证据表明该模型会造成 P0/P1，或需要丢弃 `initial_summary` 之外的作者字段时，才复核本决策。后一情况必须停止迁移并取得新的明确批准。
