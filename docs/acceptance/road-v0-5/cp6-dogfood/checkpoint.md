# CP6 dogfood 暂停断点（已恢复）

- 分支：`qa/cp6-dogfood-acceptance`
- 基线 HEAD：`1e87ad44875fe1eb62b1b6f506d975344ae2e9dc`
- 第二轮开始：`2026-07-30T01:10:45-0400`
- 用户要求暂停：`2026-07-30T01:40:19-0400`
- 暂停时状态：第二轮尚未宣告完成；距完整 30 分钟还差 26 秒，且最后一条 Trash 恢复路径尚未收尾。
- 隔离目录：`tests/test-vault/cp6-dogfood-round2-20260730-1e87ad4`
- 当前 Vault：隔离复制 `home/Vault-B`
- 精确断点：搜索“车票”后，将“月光车票 🌙”移入复制 Vault 的 Trash；确认操作已完成，尚未进入 Trash 恢复。
- 恢复结果：2026-07-30 使用同一 candidate 与隔离数据恢复“月光车票 🌙”，完成 Core 阻塞/恢复、迁移 blocked/ready、两种窗口尺寸与 Library 上下文复验；另跑 10:45:13–11:15:13 EDT 的连续 30 分钟。
- 当前状态：Agent dogfood 已完成；详细结果见 [`report.md`](report.md)。开发者于 2026-07-30 明确通过 CP6。
- CP6 证据已精简并获 commit 授权；真实 Home、真实 Vault 与真实配置未触碰。
