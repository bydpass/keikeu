# Road v0.6 CP5 Flashcard 与 v3 正常链清理证据

**日期：** 2026-08-02

**分支：** `refactor/cp5-retire-flashcard-v3`

**Gate：** advance YOLO 通过；本报告随 checkpoint commit 提交

## 结论

Production runtime 现在只剩 Paper v4 / Index v4 / protocol v2。不可达的独立
Flashcard 页面、DTO、Service endpoint、Rust 残余测试分支，以及 v3 正常读写、Index
和旧 UI 专用测试已经删除；v0.1→v3→v4 迁移仍直接使用冻结的 `legacy_v3.py`。

本 checkpoint 没有增加产品行为或依赖。最终 diff 以删除为主：删除旧页面和三个只覆盖
旧正常链的 Python 测试文件，保留 v4 runtime、两段迁移与手工可读 Markdown 边界。
未发现未解决 P0/P1。

## 删除与保留边界

- 删除 `FlashcardView.vue` 及其测试、Flashcard DTO/deck/option、`flashcard.open` Service
  实现和已失去 caller 的兼容辅助函数。
- 删除正常 runtime 的 v3 `Paper`/`Highlight` model、Markdown codec、Index rebuild/load/list
  与对应旧测试；新 Vault 初始 Index 直接为 version 4。
- v4 Vault 测试改为使用 `PaperV4`、`CardPageV4` 与 v4 codec，不再借旧正常链造数据。
- v0.1 和 v2/v3→v4 测试直接引用冻结 `legacy_v3.py`，继续证明迁移 reader/model/renderer
  可用；legacy fixture、archive 与历史说明没有删除。
- runtime source、活动 tests、当前 protocol 与权威 docs 对 `flashcard.open`、
  `FlashcardView`、Flashcard DTO、`open-flashcard` 和 production
  `destination="flashcard"` 的精确零引用检查通过。

## 实际自动检查

| 检查 | 结果 |
| --- | --- |
| 全量 Python | `256 passed` |
| Python compileall | 通过 |
| arm64 sidecar build | 通过；最终 PyInstaller 输出 SHA-256 为 `e8c5aceea97d6811ab219583951502483b61493a59deb2f942dc86fc996a1ba8` |
| 全量 Vitest | `52 passed` |
| Vite production build | 通过；`31 modules` |
| Rust host | `11 passed` |
| Rust format | `cargo fmt --check` 通过 |
| v4 runtime / legacy migration 聚焦 | `241 passed` |
| 零引用 Gate | runtime、tests、当前 protocol 与权威 docs 均为零 |

## Tauri 导航 smoke

使用仓库忽略目录中的合成 Paper v4 Vault 和仅供本次 smoke 的临时 sidecar，实际启动
当前 Vue、Rust、JSONL v2 与 Python runtime，并完成：

```text
Paper → Library → 打开合成 Paper → Paper → Vault
```

Library 实际显示一份含一页、标题、预览与 tag 的合成 Paper；返回 Paper 后标题、页名、
正文和 tag 均可见；Vault 选择界面可达。坐标探查曾在合成 Vault 内创建一份未保存的新
draft，但没有写入磁盘。随后改用可访问性树完成导航。

临时 sidecar、测试 Vault、截图和构建目录均已删除；仓库 sidecar 先按原 SHA-256 恢复，
再由最终完整检查重新构建。未改 `HOME`，未读取或修改真实 selected Vault、用户配置、
作者内容或远端状态。

## 未执行与剩余风险

- 未执行 CP6 的 response-loss、timeout、EOF、错误 response ID、locator、Index audit 与
  durable mutation 完整故障矩阵。
- 两类 repair UI 的安全组合、中文 HTML 人工修复手册和开发者修复演练仍属于 CP6。
- 未执行真实 Vault、真实作者、provider/file-service、签名、公证、DMG、发布、tag、
  push、移动端或 Intel Mac 检查。
