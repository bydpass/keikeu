# Road v0.4 CP10 — Gate A 功能等价证据

> 状态：**Complete — developer accepted Gate A**
> 日期：2026-07-26
> 基线：CP9 `2c2df7c`

## 现在发生了什么

当前 Vue/Tauri `.app` 已在隔离 Home、synthetic Vault 和 copied Vault 上复跑
Road v0.3 的主要作者流程。结果继续由同一 Python application service 写入
Paper v3 Markdown 和可重建索引；未发现 P0/P1，也没有为 CP10 修改产品代码。

Flet 对照来自已接受的 Road v0.3 场景、仍在运行的 Flet builder tests，以及
共享 service/Core 的全量测试。Gate A 只判断行为、安全和键盘路径；视觉重建
仍属于 CP11。

## 等价矩阵

| 行为 | Flet 基线 | Vue/Tauri 证据 | 结论 |
| --- | --- | --- | --- |
| Vault 预览、初始化、切换 | v0.3 CP5/CP6；Flet adapter tests | 当前 `.app` 目录选择、CREATE 初始化、Paper Vault 切换 | 等价 |
| daily card → 空白 Paper | v0.3 accepted；builder tests | 当前 `.app` 首次显示并由 Enter 进入 | 等价 |
| 新建、命名、保存、初稿冻结 | v0.3 accepted；service/builder tests | 当前 `.app` 保存后检查 Markdown v3 | 等价 |
| Highlights、Tags、`⌘S` | v0.3 accepted；builder tests | 当前 `.app` 保存并重新打开 | 等价 |
| Flashcard Summary-first、方向键、重开归第一页 | v0.3 accepted；builder tests | 当前 `.app` 页 1 → 页 2 → 重开页 1 | 等价 |
| 文件夹移动、文件夹 scope、分支 | v0.3 accepted；builder tests | 当前 `.app` 移入一层文件夹并创建同目录分支 | 等价 |
| Trash 隔离、软删除、恢复 | v0.3 accepted；builder tests | 当前 `.app` 删除、Trash 只读、恢复 | 等价 |
| v2 lazy upgrade 与未知 frontmatter | v0.3 copied-Vault smoke；Core tests | copied Vault 保存为 v3，`fixture` 字段保留 | 等价 |
| Finder 外移后的保存保护与刷新 | v0.3 copied-Vault smoke；builder tests | 旧快照保存返回 `application_service · not_found`；Library 找到新路径 | 等价 |
| 搜索与键盘聚焦 | v0.3 accepted；builder tests | 当前 `.app` `⌘F` 按代号筛成 1 项 | 等价 |
| 损坏资产隔离 | v0.3/Core tests | copied Vault 报告一条深层非法 Paper，合法三项仍可用 | 等价 |
| 系统 Finder handoff | v0.3 accepted；Rust validation tests | 当前 `.app` 在 Finder 定位 copied Vault | 等价 |
| relocation、v0.1 migration、永久删除门槛 | v0.3 accepted；service/protocol/builder tests | Vue 交互与一次 mutation contract tests；未重复做破坏性平台动作 | 等价（自动证据） |

## 数据怎么走

```text
用户动作
→ Vue 可见状态
→ 窄 Tauri command / 串行 Rust 队列
→ JSONL sidecar
→ Python application service
→ Python Core
→ synthetic/copied Vault 的 Markdown 与索引
→ DTO 返回 Vue
```

Vue 没有直接文件能力；Rust 没有 Paper、迁移、搜索或 Trash 规则。

## 实际检查

- `.venv/bin/python -m pytest -q` → **321 passed**
- `npm --prefix frontend run test` → **48 passed**
- `cargo test --manifest-path frontend/src-tauri/Cargo.toml` → **10 passed**
- `.venv/bin/python -m compileall -q src` → passed
- `npm --prefix frontend run build` → passed
- 当前源码 `.app` 由已记录的单次 `minimumSystemVersion=11.0` 工程 override 构建；
  这不是 CP12 production bundle 或兼容证据；CP12 后续把最低系统提高到 15.0。
- 两组有效平台 smoke 的临时 Home/Vault 已删除；真实 Vault、真实配置和真实
  device state 未修改。

第二次补充平台尝试被 macOS 自动化解析到一个已注册的非隔离实例。发现后未
执行任何用户动作并立即退出；该次不计入证据，也未改变所选 Vault 或磁盘。

## 出错怎么查

1. 先看 Vue 错误中的层级和错误码。
2. host/sidecar 生命周期查 Rust stderr；协议形状查 `docs/protocol.md`。
3. durable result 查 synthetic/copied Vault 的 Markdown 和 `keikeu_index.json`。
4. `not_found`、`stale_snapshot`、`commit_unknown` 不自动重试 mutation。

## 怎么撤销

CP10 仅新增/更新验收文档。丢弃本分支文档 diff 即回到 CP9 `2c2df7c`；
Flet、Vue/Tauri CP9、Paper schema 和 Vault 内容均保持可用。

## 下一步依赖什么

开发者于 2026-07-26 确认 Gate A 通过。CP11 只依赖已经稳定的 Vue 行为和
设计 tokens 做视觉重建，不改变 application service 或数据语义。
