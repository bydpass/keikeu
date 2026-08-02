# Road v0.6 CP6 未知提交、人工修复与安全整合证据

**日期：** 2026-08-02

**分支：** `test/cp6-recovery-repair-gate`

**Gate：** advance YOLO 通过；本报告随 checkpoint commit 提交

## 结论

CP6 已把 Paper v4 候选的未知提交、只读恢复、损坏隔离和人工修复边界补齐。durable
mutation 越过可证明的提交边界后只会返回 `commit_unknown`，App 不会自动重放；Paper
Save 通过 baseline、submitted 与磁盘三方只读对账，其他 mutation 在重启后先恢复 Vault，
再读取相应状态。普通损坏和未知保存损坏均不由 App 自动改写。

本 checkpoint 使用 fixture、合成 Vault 与临时 fault sidecar；没有读取或修改真实 Vault、
真实 selected-Vault 配置或作者内容。安全 smoke 暴露的 Library 重启后 `no active Vault`
P1 已在同一 checkpoint 修复并复验。最终没有未解决 P0/P1。

## 实现与故障矩阵

- `RepairDto`、Paper open 与 reconcile result 现在校验 strict tagged shape；page number 只在
  parser 能确定时返回。protocol 结果拒绝非有限数；durable response serialization 失败
  提升为 `commit_unknown`，只读方法仍是普通失败。
- Service 在 Paper 创建/替换、Library 路径、Vault/config、迁移与 Index rebuild 的实际
  durable boundary 前后区分已证明的输入冲突和未知结果。首次保存目标已存在仍是确定的
  `conflict`，不会误报未知提交。
- Save 对账覆盖 committed、not committed、第三内容、损坏、首次目标缺失/已提交、同 code
  异路径、duplicate code、existing 目标消失、`code/created` 身份变化、invalid submitted、
  locator/config/root identity 变化，以及 Index stale/extra/degraded。
- fault injection 覆盖 Paper 替换、Library path mutation、Vault config、Index 替换、迁移
  第 N 文件和 response serialization 后失败。已越过 durable boundary 的结果均未降级为
  普通可重试错误。
- Rust public method policy 逐项枚举；mutation timeout、EOF、错误 response ID 与无效响应
  均只写一次并返回 `commit_unknown`。只读 `paper.reconcile_save` 响应丢失保持
  `sidecar_unavailable`，不会伪造未知提交。
- App 根 pending intent 跨组件卸载、runtime blocked 与 sidecar restart 存活。Paper
  unknown-save repair 保留 submitted 草稿、禁用保存并维持离开/关闭保护；只有只读对账
  得到 committed/not committed，或用户明确放弃，才清除 intent。
- migration、Vault/config、Library path mutation 与 Index rebuild 的恢复入口只读磁盘且
  不重放 mutation。Library 在新 sidecar 上先执行 `startup.load`，确认 active Vault 后才
  `library.query(verify_index=true)`；这修复了 smoke 发现的 P1。

## 中文人工修复手册与演练

新增 [Paper v4 人工修复手册](../../../manual/paper-v4-repair.html)。它离线可读且不加载外部
资源，包含完整可复制 Paper v4、frontmatter、page marker、`name/content/Tags`、三个英文
类型值及中文显示名、null/空值、两类 escape、UTF-8/换行、错误字典、Finder、重新检查与
显式 Index rebuild，并明确 App 不会自动改写损坏文件。

演练只使用 `tests/test-vault/` 下随后销毁的合成 Vault：

1. 故意把第 1 页 type 写成旧值 `highlight`，startup 仍保持正常 runtime，直接打开返回
   `repair_required` 与 `page_number=1`。
2. 先复制一份逐字节一致的备份，只把旧 type 改为 `snapshot`，不改正文、标题、Tags 或
   其他 frontmatter。
3. 重新检查得到 `opened`；Library audit 先显示 `degraded`，显式 rebuild 后为 `current`。
4. 完整手册示例另经实际 parser 读取为 4 页，type 顺序为
   `summary/snapshot/whisper/null`，标题连字符和两个 Tags 均按文档保留。

原生 Tauri repair 实际调用了经过 Python 校验的 Finder reveal。macOS 27 beta 的
`System Events` 在本机返回 `-10827`，因此 GUI Duplicate 不作为已执行证据；逐字节复制、
修复和重新检查由上述隔离演练完成。

## Tauri 安全 smoke

实际启动当前 Vue、Rust、JSONL v2 与 Python runtime，临时 sidecar 固定指向合成配置；
production 没有环境开关或测试 endpoint。实际流程为：

```text
normal Paper → ⌘S 路径保存一次 → 错误 response ID → commit_unknown
→ restart → startup → readonly reconcile → unknown-save repair
→ 复制保留草稿 / Finder reveal → readonly reconcile committed
→ Library → Branch 一次 → 错误 response ID → commit_unknown
→ restart → startup → verified Library query → degraded
→ explicit Index rebuild → open intentionally broken Paper → ordinary repair page 1
```

清理前的 audit 断言为 `paper.save=1`、`paper.reconcile_save=2`、
`library.branch=1`、`library.rebuild=1`；原 mutation 没有重放。首次实际 smoke 发现非 Save
恢复直接进入 Library 时，新 Service 尚无 active Vault；修复为先 `startup.load` 后，同一
流程显示 3 份 Paper、重启读取提示与 degraded Index，再经一次显式 rebuild 恢复。

代表截图：

- [正常 Paper，1220×780](screenshots/tauri-start-1220x780.png)
- [非 Save commit_unknown，1220×780](screenshots/branch-commit-unknown-1220x780.png)
- [重启只读核对后的 degraded Library，1220×780](screenshots/library-degraded-1220x780.png)
- [普通 repair 第 1 页，1220×780](screenshots/ordinary-repair-1220x780.png)
- [正常 Paper，920×680](screenshots/paper-920x680.png)

运行时 `window.set_size` 未获 Tauri capability，因此最小窗口证据通过仅在 smoke 期间把
初始尺寸改为 `920×680`、实际启动并截图后恢复配置获得；production capability 未扩大。
原生关闭确认无法在 `System Events -10827` 下自动点击，故不声称真人点击；关闭保护、
pending Save 即使 draft 与 baseline 相同仍拦截、明确确认才 settle 的组合由聚焦 Vitest
覆盖。临时 App 自动化、fault source/binary、合成 Vault、配置、audit 和构建缓存均已删除。

## 最终自动检查

| 检查 | 结果 |
| --- | --- |
| 全量 Python | `265 passed` |
| Python compileall | 通过 |
| arm64 sidecar build | 通过；SHA-256 `b64536388613b0bbd7c6af2c2cfb1b853169e67c4c489b553b05bf4362e01baa` |
| 全量 Vitest | `61 passed`，8 个文件 |
| Vite production build | 通过；`31 modules` |
| Rust host | `12 passed` |
| Rust format | `cargo fmt --check` 通过 |
| 文档与 whitespace | 文档 `54 active / 15 required`；`git diff --check` 通过 |

## 未执行与剩余风险

- 未使用真实 Vault、真实作者内容、provider service、外部正文编辑器、真实迁移或 CP7
  场景；CP6 工程完成不等于产品接受。
- pending intent 仍只在当前 App 内存；强退或断电可丢未提交 draft，这是已批准的 v0.6
  上限，不在 CP6 增加 journal。
- 当前平台证据只来自获准的 arm64 macOS 27 / Xcode 27 beta 工程例外，不产生稳定版、
  macOS 15.7+、移动端、Intel Mac 或发布兼容性结论。
- 未签名、公证、staple、打包、tag、push 或发布。下一 Gate 是 CP7 一号真实作者；任何
  真实 Vault 选择、备份、迁移或持久配置变化仍需单独授权。
