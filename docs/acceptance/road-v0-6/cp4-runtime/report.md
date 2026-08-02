# Road v0.6 CP4 protocol v2 全栈切换证据

**日期：** 2026-08-02

**分支：** `feat/cp4-runtime-v2-cutover`

**Gate：** advance YOLO 通过；本报告随 checkpoint commit 提交

## 结论

Production 已从 Paper v3 / protocol v1 垂直切换到 Paper v4 / Index v4 /
protocol v2。Vue、Rust、JSONL、Python Service 与 Core 使用同一套 `pages[]`、locator、
tagged repair、Index warning 与一次性 durable mutation 合同。`App.vue` 在发送前持有唯一
pending intent；未知 Paper 保存只经 `paper.reconcile_save` 只读对账，其他未知 mutation
在 sidecar 重启后重新读取磁盘状态，不自动重放。

App 导航、Python protocol 与 Rust public policy 已无 `flashcard.open` caller。不可达的
Flashcard/v3 正常链实现仍按计划留到 CP5 物理删除。本 checkpoint 未发现未解决 P0/P1。

## 实现证据

- startup 在每日卡 claim、Index 使用与编辑前完成 v0.1、v2/v3、v4、mixed 与 repair
  分类；v0.1→v3→v4 是两个显式阶段。
- Paper 新建、打开、整体保存、CAS、软删除、未知保存对账与普通损坏均使用固定 v2 DTO；
  `repair_required` 是不含作者正文的 tagged success。
- active/folder/Trash、全页搜索、Branch、folder 生命周期、per-item reports 与显式
  Index v4 rebuild 已接入 production Library。
- active locator 由 startup、Paper、Library 与 mutation 回显/核对；Vault preview 使用
  candidate locator，首次初始化目标不存在时才允许空 locator。
- CP3 的 `PaperV4Workbench` 与 `LibraryV4Projection` 已直接接入 production；没有复制
  第二套卡页编辑器或 Library 投影。
- protocol v2 方法表有 27 个方法，每个恰好一个分类；v1 hello fail-closed；Rust policy
  不再把 `startup.load` 当 mutation，且不暴露 Flashcard。

## 实际自动检查

| 检查 | 结果 |
| --- | --- |
| 全量 Python | `321 passed` |
| Python compileall | 通过 |
| arm64 sidecar build | 通过；最终 PyInstaller 输出 SHA-256 为 `305f11bcff9c91bc81db1e72e856fb0744b0bae45d9f1afc09d9096db7497dff` |
| 全量 Vitest | `58 passed` |
| Vite production build | 通过；`31 modules` |
| Rust host | `11 passed` |
| v2 protocol 聚焦 | `36 passed` |
| migration/service 聚焦 | `66 passed` |
| Core path/service 聚焦 | `121 passed` |

## 可视与 Tauri smoke

合成 development-only UI 在 `1220×780`、`920×680` 与 200% 文本等效视口检查：

- 920×680 的 Paper 与 Library 均无水平溢出；Paper 卡页宽 760px；
- 卡页底端仍精确为保存、删除本页、加一页；
- 200% 等效视口无页面或卡页水平溢出，三个底部按钮纵向重排且各高 44px；
- 页标题、正文、类型标签与 Library 全页元数据保持可达；可访问树中无 Flashcard；
- `ego-browser` 截图调用本次超时，因此本报告只采用实际可访问树与几何读数，不声称
  保存了截图。

隔离 Tauri smoke 使用临时 sidecar 和仓库忽略目录中的完整合成 v3 Vault。实际请求序列
跨过 Vue → Rust → JSONL v2 → Python：

```text
hello → startup → v3→v4 migration → startup
→ create → two-page save → reopen → all-page search
→ create folders → move → branch → Trash → restore → Trash → permanent delete
→ rename folder → merge folders → folder Trash → folder restore → Index rebuild
→ sidecar restart/hello → startup → final verified query
```

结束标记到达后，磁盘只剩两份有效 Paper v4、Index version 4、零 Index error；迁移报告
存在，活动 Paper 包含两个页面和两个页标题。临时 App 自动化入口、临时 sidecar、审计
记录与合成 Vault 已删除；临时 sidecar 恢复后又由最终完整检查重新构建 arm64 sidecar。
未改 `HOME`，未读取或修改真实 selected Vault、用户配置、作者内容或远端状态。

## 未执行与剩余风险

- 未执行真实 Vault 迁移、真实 provider/file-service smoke 或一号作者场景；CP7 仍是独立
  产品接受 Gate。
- `index_degraded`、各类 I/O fault、unknown-result 完整矩阵与中文修复手册演练属于 CP6；
  CP4 只覆盖主纵链和聚焦回归。
- 不可达 Flashcard/v3 实现和测试仍在仓库，CP5 必须先做零 caller 审计再删除。
- 未执行签名、公证、DMG、发布、tag、push、移动端、Intel Mac 或兼容性结论。
