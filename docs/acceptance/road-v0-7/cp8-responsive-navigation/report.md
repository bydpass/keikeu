# Road v0.7 CP8 响应式导航、Anchor 与原生 IME 验收记录

**日期：** 2026-08-26

**分支：** `ui/cp8-v07-responsive-navigation`

**进入基线：** CP7 checkpoint `1e17cea`

**Gate：** Gate A–D 已通过；开发者于 2026-08-26 明确接受 CP8

**Road 结论：** CP8 完成后，开发者明确判定 Road v0.7 正式完工

## Checkpoint 时点结论

CP7 已由开发者接受并在 `1e17cea` 建立本地 checkpoint。CP8 Gate A–C 已完成：未提交的
工作树重排单行 Shell，增加 all-page 横向页签滚轮、竖版 Paper 底部 Anchor，以及竖版
Library 顶部双 Anchor 与 native Popover；聚焦/完整自动检查、五档真实浏览器布局、debug
`.app` bundle 与 Figma Page `71:2` 原位覆写均有本轮证据。CP8 不改变 Paper v4、Index v4、
protocol v2、Core、bridge、DTO、Rust、Tauri 几何、依赖或作者资产合同。

开发者随后在 fake Home 与 synthetic Vault 中，以实体键盘和 macOS 简体拼音完成原生
候选窗复核，并明确反馈“全部通过，没有异常”。Gate D 的四类 P1 阻断均未出现，因此
CP8 现为已接受的 presentation override。该产品判断与自动化工程证据、Figma 对齐及 Git
checkpoint 彼此独立；在本报告随 checkpoint 提交前，CP8 工作树仍未提交。

基于 CP8 通过，开发者进一步明确判定 Road v0.7 的产品与实施工作正式完工。在该判断与
本报告进入 checkpoint 的时点，Road snapshot、tag、push、签名、打包与发布仍须分别处理。

## 实现边界

- 顶栏保持单行 `56px`，顺序为“编辑 Paper → 新 Paper → Library … Vault”；唯一
  dirty-departure guard 不变。
- `1/3/4/6/7/12` 页都使用同一单行局部滚轮；全部页按钮留在 DOM，约三槽、细滚动条、
  scroll-snap，无循环、箭头或换行。载入、直接点选、加页与删页后活动页自动居中。
- `@media (orientation: portrait)` 下，Markdown textarea 使用
  `clamp(220px, 34dvh, 300px)` 并在框内滚动；三项 Paper 动作使用不透明、safe-area-aware
  底部 sticky Anchor。横版 textarea 继续允许纵向 resize。
- 竖版 Library 在 Shell 下方显示等高的“范围 / 排序”与“新文件夹”sticky Anchor，分别
  打开 native Popover；失败保留输入与打开状态，成功后关闭，Escape/light-dismiss 后焦点
  返回。横版 sidebar、排序与内联创建保持不变。

## Gate A–C 工程证据

以下项目均在最终整合工作树实际运行；数字不复制自 CP7：

| 检查 | 本轮结果 |
| --- | --- |
| 聚焦 Vitest | `5` 个文件 / `86 passed` |
| 完整 Vitest | `9` 个文件 / `118 passed` |
| Vite production build | 通过 |
| pytest | `284 passed` |
| Python compileall / sidecar build | 均通过 |
| Cargo fmt / Rust test | format 通过；`12 passed` |
| debug `.app` bundle | `frontend/src-tauri/target/debug/bundle/macos/keikeu.app` 构建通过 |
| production bundle marker scan | clean；无 prototype marker |
| 文档检查 / `git diff --check` | 最终同步后通过；详见本报告末尾 |

五档 QA 使用 synthetic data，结果为 `PASS`；证据保存在忽略目录
`build/cp8-gate-c-browser/`，其中 `results.json` / `results.txt` 是结构化结果，截图按视口与
Paper/Library 状态分开保存。该检查明确记录 `synthetic_only: true`、
`real_vault_touched: false`。

| 视口 | 本轮结果 |
| --- | --- |
| `375×812` | PASS：单行 Shell、竖版双 Anchor、页签局部横滚，document `375 / 375` |
| `720×900` | PASS：默认竖版、80 行正文内滚、Paper Anchor 不遮内容，document `720 / 720` |
| `720×680` | PASS：横版 sidebar/内联创建与 textarea resize 可用，document `720 / 720` |
| `920×680` | PASS：横版内容不下沉，页签轨道恒高，document `920 / 920` |
| `1220×780` | PASS：宽版 Library 与全部操作无回归，document `1220 / 1220` |

五档的 Paper 与 Library 均满足
`document.scrollWidth <= document.documentElement.clientWidth`，没有 document 横向溢出。
`12` 页全部保持同一行，轨道高度恒为 `60px`，局部 `scrollWidth` 大于 `clientWidth`；
首、尾、加页后、删页后与中间活动页的居中误差均 `< 0.4px`。`80` 行正文的 textarea
在五档均可把 `scrollTop` 推到精确 `maxScroll`，竖版 `resize: none`，横版保持纵向 resize。
最大合法 `200` code point 名称没有撑宽容器。Paper sticky Anchor 与正文保持正间隙；Library
双 Anchor 等宽、位于 Shell 下方，范围/排序 Popover 含两个 select，Escape、light-dismiss、
成功关闭与焦点返回均通过。页面错误、console error 与 request failure 均为零；`375×812`
唯一 favicon `404` 被明确隔离为非产品错误。

## Figma Gate C 证据

- Figma file：`Eubz4vHZ0YaCk0Mki12ljS`。
- 桌面 version-history 保存流程已使用精确标题
  `CP7 Gate D accepted · before CP8 overwrite` 完成。当前 connector 不暴露 version ID，
  因此本报告不伪造 ID。
- Page `71:2` 已原位重命名为 `CP8 · 响应式锚点与横向滚轮` 并覆写；没有创建第二套活动
  母版。主要 Sections 为 `71:4` 与 `71:5`。
- 五档视口、`4/6/12` 页滚轮、长正文框内滚动、Paper 底部 Anchor、Library 顶部双
  Anchor、两个 Popover 与单层 Shell 已同步。
- 递归审计确认五档 viewport、bounds、字体角色与 CP7 residue 全部 clean；不存在越界节点、
  错误字体、旧双 Shell 或残留 CP7 活动母版。

Page/Section 名称与节点已逐段回读并截图检查。Figma 结果只完成 Gate C 设计对齐，不替代
浏览器、debug `.app` 或 Gate D。

## 原生 macOS 候选窗记录（Gate D 已通过）

| 记录 | 本轮结果 |
| --- | --- |
| 隔离启动 | 关闭同名旧应用后，从正式 CP8 debug bundle 直接启动；`HOME` / `TMPDIR` 指向忽略目录 `tests/test-vault/` 下的 synthetic 环境，未选择真实 Vault |
| 合成数据 | 两份 synthetic Paper；目标样张含 Tag“暴食”，对照样张不含该 Tag；启动前 `library_query("暴食")` 只命中目标样张 |
| 平台 | macOS `27.0`，build `26A5421a`；输入源 `com.apple.inputmethod.SCIM.ITABC` |
| Artifact | arm64 debug 可执行文件 SHA-256：`c31ed3f72d67da7ae7ee393e3e5d068cadc6e93982905ea4a2c2e9c1af08c750` |
| 实体键盘观察 | 输入 `baoshi` 时候选窗真实出现且保持稳定；选择“暴食”前没有中间拼音查询或结果重绘 |
| 提交结果 | 选择“暴食”后候选窗关闭，输入框只保留最终中文，结果只刷新一次且无残留 `ba` 或重复提交 |
| 开发者判断 | 2026-08-26：“全部通过，没有异常” |
| 生命周期 | App 正常退出，进程 exit code `0` 且无进程残留；退出时 macOS IMK 打印一次 mach-port diagnostic，未伴随开发者可见异常，也不属于四类 Gate D 阻断；未保留真实作者内容、真实 Vault 路径或设备标识 |

自动化输入会绕过候选器，本节只记录开发者的实体键盘观察，不把自动化 composition
冒充为原生候选窗证据。本轮未保存截图；保留的工程记录只含 synthetic 边界、
build/OS/input-source 与 artifact digest。

## 未执行与授权边界

- Gate D 四类 P1 阻断均未出现；本次人工复核不自动重判 Gate D 范围外的 P2/P3。
- 未操作真实 Vault、provider 同步、作者内容或持久工作站配置。
- 本报告进入 checkpoint 前，CP8 commit 尚未创建；该 checkpoint-time 边界不回写成提前完成。
- 未 push、tag、closeout、签名、公证、DMG、发布或扩大平台支持。

## 最终文档 Gate

- `.venv/bin/python scripts/check_docs.py`：通过，`72 active / 15 required`，budget 与本地链接
  全部有效。
- `git diff --check`：通过；新建的未跟踪报告另以行尾扫描确认无尾随空白。

## 后续 Git closeout（2026-08-26）

- 开发者随后明确授权“全部提交，并做 Road 快照”。
- CP8 checkpoint 已创建为 `2f03aeecc1f287e5cdb4f9ddab462ae169af68c4`。
- [Road v0.7 snapshot](../../../archive/snapshots/road-v0-7.html) 在该 checkpoint 后作为独立
  docs-only closeout 加入；它不改写本报告的 checkpoint-time 证据。
- Road v0.7 至此完成产品、实施、checkpoint 与文档归档。未创建 tag，亦未 push、签名、
  公证、DMG、打包或发布；未操作真实 Vault、provider 或作者内容。
