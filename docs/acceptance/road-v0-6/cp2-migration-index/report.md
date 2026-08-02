# Road v0.6 CP2 迁移与 Index v4 证据

**日期：** 2026-08-02

**分支：** `core/cp2-paper-v4-migration-index`

**Gate：** advance YOLO 通过；本报告随 checkpoint commit 提交

## 结论

CP2 以独立 API 加入 v2/v3→v4 schema scan、raw loss-audit、显式迁移、Index v4、
Trash 临时投影与 v4 Branch。`migration_v01.py` 改接冻结的 v3 数据类/纯 codec；旧迁移
fixture 与输出测试保持通过。production Service、startup、v3 Index 和 protocol v1
没有接入或替换。

未发现未解决 P0/P1。CP3 可以只在既有 development-only 原型入口接入合成 v4 DTO。

## 数据与失败边界

- preflight 通过固定 Vault fd 扫描 active、一级 folder 与 Trash，并绑定整个 regular-file
  manifest；v0.1 与 Paper schema 共存、未知 schema、symlink、特殊路径、重复 code 或
  损坏 Paper 均进入 repair，零迁移写入。
- legacy raw loss-audit 检查重复/无效 frontmatter、重复/错序 section、游离文本、v2/v3
  Highlight 结构与编号。空、外围空白、trim 后重复、多行或控制字符 Tag 全部阻塞；含
  逗号单行 Tag 原样映射。
- current Summary 成为唯一 Summary 页，Highlight 依序成为 Snapshot；未知 frontmatter、
  路径、folder、Trash 位置和字段值保留。唯一不进入 v4 active schema 的字段是
  `initial_summary`，且只在去内容报告中计数。
- 迁移在替换任何源文件前建立 active Vault 外的完整备份并逐字节核对 manifest；每个
  Paper 使用 source bytes CAS 安全替换。中断后保留完整 v3/v4 文件，新的只读 preflight
  只列剩余项并要求再次确认。
- Index v4 只持久 active Paper，保存第一页原文 preview、页数、页名与 NUL 分隔的全页
  本地 search projection；查询按 NFC/casefold 比较且不向 Library 结果返回 `search_text`。
  Trash 使用 O(n) 临时投影，不写 Trash Index；坏 Paper 只返回路径 fallback 与原因。
- v4 Branch 只接受 active 已保存快照，在同一 folder 创建新 code/time 的完整 pages、Tags
  与 frontmatter 副本；源变化、重复 code 或目标冲突时零创建。

## 实际检查

| 检查 | 结果 |
| --- | --- |
| CP2 规定聚焦 pytest | `66 passed` |
| 新 migration/Index v4 focused pytest | `24 passed` |
| 全量 Python pytest | `316 passed` |
| Python compileall | 通过 |
| arm64 sidecar build | 通过 |
| 文档检查 | `49 active files`，通过 |
| `git diff --check` | 通过 |

规定聚焦测试覆盖 preflight 零写、v2/v3 确定映射、legacy Tag 阻塞、unknown frontmatter、
备份核验、stale、逐文件中断续迁、`index_degraded`、两段 v0.1 Gate、active/folder/Trash、
坏 Paper 隔离、全页搜索、只读 Index verify 与 v4 Branch。冻结旧迁移的 42 项在接线前后
均通过。

当前源码 Tauri dev host 通过 development-only 原型入口启动并干净退出；该入口不调用
`startup.load`，没有打开 Vault 或 claim 设备状态。Rust 启动路径仍强制完成 v1 hello，
且 production import 审计确认 Service/startup/rebuild 只调用 v3 API。

Vitest、Vite production build 与 Cargo tests 未运行：CP2 未改 Vue/Rust。未使用真实或
真实副本 Vault；所有 mutation 测试只使用 ignored `tests/test-vault/` 合成目录。未运行
真实迁移、作者接受、设备兼容、签名、公证、发布、push 或 tag。

## 剩余风险

- v4 migration/Index API 仍是 additive test-only 能力；CP4 前不得由 production startup
  或 Service 调用。
- CP4 仍需实现 locator、DTO、protocol v2、Service 编排、degraded warning、repair tagged
  state 与保存/对账的完整 runtime 边界。
- 合成 Vault 证明安全机制与确定映射，不证明真实作者迁移或产品接受。
