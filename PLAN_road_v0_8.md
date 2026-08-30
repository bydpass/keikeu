# Road v0.8 实施计划（跨端基础设计草案；Road 尚未启动）

> 状态：开发者于 2026-08-30 批准重写本草案并同步活动文档。本次文档提交不是 CP0
> checkpoint，不授权修改产品代码、生成移动工程、配置 Apple 能力、签名、上传、招募、分发、
> tag、push 或 release。Road v0.8 仍须通过 §14 的新计划/seed Gate 才能启动。
>
> 继承基线：Road v0.7 最终产品 checkpoint `2f03aee` 及其独立 closeout `a7726ae`。
> 当前 production 仍是 macOS Apple Silicon 上的 Vue/Tauri/JSONL/Python runtime；Paper v4、
> Index v4、protocol v2、完整文件夹生命周期与已接受 App Shell 均未因本草案发生变化。
>
> 前置阻塞：App-root pending durable intent 的正常关闭保护仍错误地由 `PaperView` 注册。
> 该偏差必须先作为独立窄修复完成并聚焦重证；不得混入本 Road 的跨端实现。
>
> 权威：[`docs/SPEC.md`](docs/SPEC.md) 定义产品边界，
> [`docs/RULES.md`](docs/RULES.md) 定义数据、Git、证据与安全纪律，
> [`docs/PROJECT.md`](docs/PROJECT.md) 区分当前运行事实与本计划目标。

## 0. Road 目标与后续生态位

Road v0.8 建立同一 Vue 产品界面的跨端工程基础，并交付一个可在实体 iPhone 上完成核心循环的
开发候选；它不承担外部 Alpha、正式宣发或 Android 发布。

```text
Road v0.8  跨端工程基础 + iPhone 可测试候选
Road v0.9  iOS/macOS 首轮 Alpha + 正式宣发 Gate
Road v0.10 Android 开发 + 二轮 Alpha
之后       根据两轮实测决定 Windows Road
```

移动端采用 Tauri + 进程内 Rust Paper Core，不恢复已退役的 Flet runtime。Tauri mobile
不能启动当前 Python sidecar，因此移动端和 Apple 云端 Vault 不能伪装成现有桌面 transport
的直接复用。

## 1. 执行纪律

- 本草案提交只供新计划评审；开发者明确批准 CP0 seed 后才成为可执行 Road。
- close-guard 修复从当前已接受 checkpoint 单独建立 focused branch，修复和聚焦测试通过后才可
  作为 CP0 seed 的前置事实。
- 每个 CP 从前一个已通过 checkpoint commit 建立一条 focused branch；未通过的 CP 不得给下一个
  CP 当 seed。
- checkpoint、真实 iPhone、真实 Apple Account、Apple Developer Portal 持久修改、签名、上传、
  TestFlight、外部分发、tag、push 与 release 分别授权。
- 所有文件与生命周期实验先用 synthetic Vault、fixtures 或完整副本；未经窄授权不读写真实 Vault。
- 生成的 Xcode/Tauri 工程、构建包、签名产物、原始设备日志和凭据不得进入 Git，除非 CP 明确证明
  某个生成文件是可审查且必须跟踪的源码输入。
- 证据只记录去标识结果，不记录 Apple ID、邮箱、Team ID、证书 CN、profile 名、设备名称、
  本机路径、Vault 路径、作者内容或测试者身份。

## 2. Current 与 target runtime

### 2.1 当前已接受 runtime

```text
Vue → Tauri/Rust → JSONL protocol v2 → Python service/core
    → local Paper v4 Markdown / Index v4 / Vault
```

Road v0.8 不重写 macOS 本地 Vault 路径；它继续拥有完整的现有 Library、Index、Trash、迁移、
文件夹与外部编辑器能力。

### 2.2 Road v0.8 target

| 环境 | 存储 | 执行后端 | Road v0.8 能力 |
| --- | --- | --- | --- |
| macOS 本地 Vault | 当前本地 Markdown | 现有 Python sidecar | 保持完整现有能力 |
| macOS iCloud Vault | App 的共享 iCloud Documents Vault | Rust Paper Core + Apple 文件协调 | 与 iPhone 相同的窄核心循环 |
| iPhone 本地 Vault | App 沙盒 | Rust Paper Core | 窄核心循环 |
| iPhone iCloud Vault | 同一共享 iCloud Documents Vault | Rust Paper Core + Apple 文件协调 | 窄核心循环与冲突恢复 |

Vue 继续只持有可见状态与草稿，不直接写文件。Rust Paper Core 是非 GUI 的产品层，只在 mobile
或 `icloud_documents` 存储模式处理 Paper v4；macOS 本地模式仍走 Python sidecar。两套实现都
服从同一 Paper v4 书面 grammar 与共享 golden fixtures，不允许各自扩展 schema。

前端继续调用现有 `bridgeRequest(method, params)` envelope：

- `paper.create_draft`、`paper.open`、`paper.save` 与 `library.query` 保持现有语义和 DTO 形状；
- macOS 本地请求继续进入 JSONL protocol v2；mobile/iCloud 请求由 Tauri host 在进程内分发；
- `system.hello` / `startup.load` 返回明确的 platform、storage mode 与 capability，不让 UI 猜平台；
- 新增的 storage、单篇导出与 conflict-recovery 方法只属于 host contract，不自动扩大 Python
  sidecar 的 protocol v2；CP0 必须冻结方法表与错误码后才能实施。

## 3. 全局范围

### 3.1 包含

- 中文/英文 UI：系统语言默认、设置内手动切换、本机持久选择。
- 复用现有 Vue 页面与 `bridgeRequest` 边界；为 iPhone 调整 safe area、软键盘、IME 与 lifecycle。
- 进程内 Rust Paper v4 窄 Core：创建、打开、整体 CAS 保存、列表/线性搜索和单篇 Markdown 导出。
- Python 生成、Rust/Python 双边消费的 golden fixtures；覆盖未知 frontmatter、marker 转义、页面
  规则、stale、首次/再次保存和失败前不写盘。
- App 私有、仅本机的未保存恢复稿。
- 本地沙盒 Vault；用户明确选择后才创建一个 iCloud Documents Vault。
- Apple 原生 metadata discovery、按需下载、file coordination、current/conflict version 处理。
- “冲突与恢复”列表：打开、导出、明确提升为当前版本；所有被替换版本先保留。
- iOS simulator、实体 iPhone 与 macOS 开发候选的跨端工程 Gate。

### 3.2 不包含

- 外部 TestFlight、Developer ID 最终候选、公证 DMG、招募、公开宣发或真实 Alpha；归入 Road v0.9。
- Android 实现或二轮 Alpha；归入 Road v0.10。
- iPad 正式验收、Windows、Intel Mac、HarmonyOS、Linux 或 watchOS。
- 移动端 Trash、永久删除、迁移、Vault relocation、文件夹管理、Branch、外部编辑器、批量导出或
  整库 ZIP。
- Rust Index v4、数据库、账号、CloudKit 数据库、自建同步服务、遥测、analytics、crash upload、
  updater、后台 agent 或 localhost。
- 自动把本地 Vault 搬到 iCloud、自动合并冲突、静默降级、自动重试未知 mutation。
- Flet 恢复、通用 plugin architecture、通用存储抽象或为未来平台提前搭架子。

## 4. 产品与数据合同

### 4.1 双语

- 支持 `zh-CN` 与 `en` 两种界面语言；首次启动按系统 locale 选择，无法匹配时默认 English。
- 设置页可随时切换，选择只写 App 的本机 device state；不进入 Vault、Paper 或 iCloud。
- 使用一个项目内字符串表和现有 Vue state，不引入通用 i18n 依赖。
- UI、错误、恢复、导出和 iCloud 状态均翻译；Paper、Tags、路径与作者内容绝不翻译或规范化。
- Python/Rust/Apple adapter 返回稳定错误 code 和安全参数；Vue 决定最终文案。诊断不得携带正文。

### 4.2 Rust Paper Core

- 支持当前 Paper v4 严格 parse/render，不产生另一个 schema 或移动专用 Markdown。
- 保留 intentionally blank optional fields 与可行的未知 frontmatter；损坏输入进入
  `repair_required`，不部分打开成可编辑对象。
- 整体保存使用打开时快照做 CAS；外部变化进入 `stale`，未知结果不自动重发。
- 同目录临时文件与安全替换保证失败前不暴露部分 Paper；平台不能证明安全原子行为就阻断写入。
- 移动 Library 只扫描受支持的 root/one-folder Paper 并在内存中线性搜索；不复制 Index v4。
- 单篇导出只通过系统 Share Sheet 或 Files 明确交付一份 Markdown，不改变 canonical Paper。

### 4.3 本机恢复稿

- 未保存草稿在输入静止后的短 debounce 与 App background/resign-active 时写入 App 私有恢复区。
- 恢复稿按本机 draft/Paper identity 区分，不进入活动 Vault、Index 或 iCloud，也不冒充正式保存。
- 成功正式保存或用户明确丢弃后清除；失败、`stale`、`repair_required` 或 `commit_unknown` 时保留。
- 重启后只提供“恢复、导出、丢弃”；不自动覆盖正式 Paper。

### 4.4 iCloud Documents

- 默认 `local`；`icloud_documents` 只能由作者明确启用。Alpha 每个 Apple Account 只支持一个
  App-owned 云端 Vault。
- 只允许创建或重新连接该云端 Vault；本 Road 不自动迁移已有本地 Vault，本地原件原样保留。
- 容器不可用、iCloud Drive 关闭、账号不匹配、文件未下载或协调失败时显示明确状态并阻断相应
  操作；不静默回到另一 Vault，也不搬动文件。
- Apple adapter 使用 `NSMetadataQuery`/等价原生 discovery、按需下载、`NSFileCoordinator` 与
  `NSFileVersion`/等价 conflict API；普通目录扫描不能冒充云端已同步。
- Apple current version 作为活动版本；keikeu 不比较客户端时钟自行选赢家。
- 每个 losing conflict version 先按原始字节保存到 Vault 的专用 recovery area，再向系统声明
  已处理。恢复项 ID 使用时间与随机值，不含设备名称或账号标识。
- “提升为当前版本”先把当时活动版本再保存成 recovery entry，然后执行安全 CAS；不自动 merge、
  overwrite 或 delete 任一版本。
- 同一 code 的离线并发新建也按 conflict 处理，不重写历史 Paper code；作者可导出后明确另建 Paper。

### 4.5 平台与分发边界

- Road v0.8 的正式 mobile Gate 是 iPhone；iPad 只记录观察结果，不据此声称适配或验收。
- iCloud Documents 可用于 Developer ID macOS App，但 debug 成功不能证明最终分发 entitlement。
- Road v0.9 必须用最终 TestFlight iOS build 与最终 Developer ID、公证、stapled macOS build 重证
  shared container、embedded provisioning profile 和完整跨端往返。
- 若最终 Developer ID DMG 的 shared-container Gate 无法通过，Road v0.9 将 macOS Alpha 分发
  改为 TestFlight；不得带着失效 entitlement 发布 DMG。

## 5. 通用证据

### 5.1 文档 checkpoint

```bash
.venv/bin/python scripts/check_docs.py
git diff --check
```

### 5.2 每个工程 checkpoint 的最低基线

```bash
.venv/bin/python -m pytest
.venv/bin/python -m compileall -q src
npm --prefix frontend run test
npm --prefix frontend run build
cargo test --manifest-path frontend/src-tauri/Cargo.toml
cargo fmt --manifest-path frontend/src-tauri/Cargo.toml --check
.venv/bin/python scripts/check_docs.py
git diff --check
```

- 记录实际命令、实际 pass/fail 与日期；不得复制旧 pass count。
- iOS build 只证明 build；不证明安装、启动、恢复、文件访问、iCloud 或产品接受。
- simulator 不替代实体 iPhone；debug provisioning 不替代 TestFlight/Developer ID 最终候选。
- real-provider smoke 与 synthetic/local smoke 分开记录；不拿真实作者 Vault 做故障实验。

## 6. Checkpoint 总览

| CP | 建议分支 | 结果 | 主要 Gate |
| --- | --- | --- | --- |
| CP0 | `docs/cp0-v08-cross-platform-contract` | 冻结 method、DTO、语言、storage、recovery 与 Apple 边界 | 开发者批准；current/target 无冲突 |
| CP1 | `feat/cp1-v08-bilingual-shell` | 中英字符串表、locale 选择与双语错误/恢复 UI | macOS 回归与中英 IME/UI Gate |
| CP2 | `feat/cp2-v08-rust-paper-core` | Rust 窄 Core 与共享 golden fixtures | Python/Rust byte 与错误语义一致 |
| CP3 | `feat/cp3-v08-iphone-local-loop` | Tauri iOS、本地 Vault、恢复稿、单篇导出 | simulator + 实体 iPhone 核心循环 |
| CP4 | `feat/cp4-v08-icloud-documents` | Apple coordination、云端 Vault、冲突恢复 | 本地/离线/冲突/不可用状态安全 |
| CP5 | `test/cp5-v08-cross-platform-candidate` | macOS+iPhone 开发候选与 Road v0.9 handoff | 双语、跨端与回归 Gate；开发者接受 |

## 7. CP0 — 合同与可行性

**进入条件：** close-guard 独立修复及 focused tests 已通过；工作树 clean；开发者明确批准本计划
提交作为 seed，并批准创建 CP0 branch。

**范围：**

- 冻结 mobile/iCloud method table、DTO、mutation 分类、稳定 error code、capability matrix 和
  `local` / `icloud_documents` 状态机。
- 冻结双语字符串 inventory、locale fallback、恢复稿与 conflict entry 生命周期。
- 用最小 Tauri iOS probe 证明 WebView、Rust command、App sandbox path、safe-area 和 lifecycle
  回调可达；probe 只用 synthetic data，不形成 product implementation。
- 设计同一 Rust Core 在 iPhone 与 macOS iCloud mode 的调用边界；macOS local mode 不变。
- 盘点 Apple Developer Program、explicit App IDs、shared iCloud container、开发/Developer ID
  provisioning 与所需 entitlement，但不在没有独立授权时创建或修改它们。
- 记录 Road v0.9 分发 Gate 与 Android handoff，不创建 v0.9/v0.10 空脚手架。

**退出 Gate：** 方法和数据合同完整；probe 没有发现必须改 runtime 方向的 blocker；Apple 配置需求
可审计；基线与 docs checks 通过；开发者接受 CP0。

## 8. CP1 — 双语 App Shell

**范围：**

- 把全部用户可见字符串、错误与恢复状态迁入一个中文/英文字符串表；保持作者文本原样。
- 按系统 locale 初始化并提供设置内切换；只复用现有 Vue/App state 与本机 device state。
- 将现有 Python/Rust structured errors 映射到语言中立 code；未知错误使用安全通用文案，不显示正文、
  绝对路径或 transport 细节。
- 覆盖 Paper、Library、Vault、blocked/recovery、确认框、空态与辅助功能名称。
- 在现有五个 viewport 复跑布局；实体 macOS 键盘验证中文、英文与切换后输入法不重复提交。

**明确不做：** iOS 工程、Rust Paper Core、品牌重写、第三种语言或翻译平台。

**退出 Gate：** 字符串 inventory 无硬编码漏项；两种 locale 的核心流和错误流可达；macOS 现有行为、
IME、可访问名称与布局无回归。

## 9. CP2 — Rust Paper Core

**范围：**

- 在现有 Tauri Rust crate 内建立最小非 GUI Paper module，不拆新服务或进程。
- 从当前 Python Paper v4 fixtures 生成版本化 golden corpus；双方测试同一合法/非法/边界样本。
- 实现 strict parse/render、create、open、CAS save、root/one-folder list 与线性 query。
- 保留未知 frontmatter 和作者字节语义；覆盖 marker、Unicode、blank optional fields、重复 summary、
  无效页面、stale、code collision、首次/再次保存与故障前不写盘。
- 保持 UI envelope 与现有 DTO；mobile 不实现 Index v4、Trash、迁移或 folder mutation。

**退出 Gate：** Python/Rust golden tests 对有效 render bytes、结构 DTO、拒绝类和错误 code 一致；
安全替换在目标 Darwin 环境可证明；无法证明时阻断，不以普通 overwrite 代替。

## 10. CP3 — iPhone 本地核心循环

**范围：**

- 生成并审查 Tauri iOS 项目；`#[cfg(mobile)]` 路径不得启动 sidecar 或调用 desktop-only opener。
- 接入 Rust Paper Core、本地单 Vault、线性 Library、单篇系统导出和 App 私有恢复稿。
- 调整 iPhone safe area、软键盘、portrait 编辑、selection/caret split、background/foreground、
  memory pressure 后的明确恢复。
- simulator 先覆盖自动化和生命周期；实体 iPhone 使用 synthetic Vault 完成创建、编辑、保存、
  重启找回、搜索、导出、未保存恢复、stale 与失败保稿。

**明确不做：** iCloud、iPad Gate、外部 TestFlight、真实作者内容或公开包。

**退出 Gate：** 核心循环与双语输入在实体 iPhone 通过；没有 sidecar/localhost/隐藏上传；App 被系统
终止后恢复稿可见且从不覆盖正式 Paper；无未解决 P0/P1。

## 11. CP4–CP5 — iCloud 与跨端候选

### CP4：iCloud Documents

- 经独立授权后创建/关联 explicit iOS/macOS App IDs 与同一 iCloud container；只记录脱敏状态。
- 实现 Apple native adapter、状态机、新云端 Vault 和 recovery area。
- 在 synthetic Papers 上覆盖：容器不可用、iCloud Drive 关闭、metadata-only、按需下载、离线创建/
  编辑、恢复在线、并发保存、同 code 新建、多个 conflict versions 与 promote 回滚保护。
- 验证 macOS 本地 Vault 从未被自动移动、选择或改写；云端 mode 只暴露窄核心循环。

**CP4 退出 Gate：** 每个失败状态可解释、可恢复且无静默丢稿；所有 conflict bytes 可从 recovery
列表打开或导出；两端 debug build 的单向与往返同步通过。该结论不替代最终分发 Gate。

### CP5：跨端开发候选

- 在同一 reviewed source checkpoint 构建 macOS 与实体 iPhone 开发候选。
- 复跑 macOS local 完整回归、macOS iCloud 窄循环、iPhone local/iCloud 窄循环、中文/英文、
  background/restart、offline/reconnect、conflict promote 与单篇导出。
- 形成 Road v0.9 handoff：实际 Apple capability 状态、未解决 P2/P3、工具链、设备范围、最终分发
  尚未证明项、测试招募统计合同和明确下一命令。

**CP5 退出 Gate：** 无未解决 P0/P1；macOS local 行为未退化；实体 iPhone 核心循环与 debug
iCloud 往返通过；开发者明确接受 Road v0.8。随后另作 snapshot/closeout，不自动启动 v0.9。

## 12. Road v0.9 / v0.10 handoff 合同

Road v0.9 才负责：

- iOS external TestFlight 与 macOS Developer ID、公证、stapled DMG；DMG shared-container Gate
  失败时改用 macOS TestFlight。
- 手机候选完成后，只在小红书与 X 进行小范围 Alpha 招募；这不是正式发布宣传。
- 14 天报名、目标 60 份合格样本（中文/英文各 30）；不足 40 时延长一次 7 天，仍不足只报告
  探索性结果。
- 入选 24 人（中文 12、英文 12），至少 8 人覆盖 iPhone、8 人覆盖 macOS，可双端重叠。
- 正式宣发 Gate：无未解决 P0/P1、无静默丢稿；至少 18 人完成且中英各至少 8；创建、编辑、
  保存、重开、搜索、导出六项任务逐项成功率至少 90%，分母为所有完成测试且被要求执行该项
  任务的参与者，未完成该任务计失败；至少 6 人完成 iPhone↔macOS iCloud 往返。
- Gate 通过后，小红书 + X 为主宣发，Bilibili + YouTube 为副宣发；微博、Reddit 仅作研究与
  社区观察。

正式宣发启动后才进入 Road v0.10：Android 复用 Rust Paper Core，首版保持本地 Markdown 与
显式导入/导出，不新增跨平台云服务，并加入二轮 Alpha。Windows 只持续统计设备需求，待二轮证据
后再决定，不与 Android 并行承诺。

画像与招募完整统计合同见
[`docs/manual/prospect/alpha-audience-research.md`](docs/manual/prospect/alpha-audience-research.md)。

## 13. 已知风险

| 风险 | 控制 |
| --- | --- |
| Python/Rust 两套 Paper 实现漂移 | 同一书面 grammar、共享 golden corpus、byte/error 双边 Gate；不复制 Index/迁移/Trash |
| macOS cloud 路径绕过 Apple coordination | cloud mode 与 mobile 共用 Rust Core + native adapter；Python 只处理本地 Vault |
| iOS lifecycle 丢失未保存内容 | App 私有恢复稿、background flush、重启明确恢复；正式保存仍是唯一 canonical 边界 |
| iCloud 冲突静默吞稿 | current 只作活动版本；每个 losing/current replacement 先保存 recovery bytes，不自动 merge/delete |
| 离线并发创建同一 Paper code | 保留为 conflict，不重写历史 code；作者明确导出或另建 |
| debug 同步被误当发布证据 | Road v0.9 用最终 TestFlight 与 Developer ID/TestFlight macOS 候选重证 entitlement/profile |
| 双语扩张变成文案重写 | 只翻译现有产品和新状态，不改变 Paper、作者文本或产品边界 |
| 画像用平台注册量冒充目标用户 | OS 占比只来自合格报名者；平台数据只决定渠道，不做总体加权 |
| Road 被 Android/Windows 拖宽 | v0.8 只做 Apple 跨端基础；Android/Windows 保持后续 Gate |

## 14. 实施计划批准 Gate（尚未通过）

CP0 开始前，开发者须逐项确认；任一项改变时先更新本计划并重新批准：

- [ ] Road 名称与范围是“跨端工程基础 + iPhone 可测试候选”，不含外部 Alpha 或正式宣发。
- [ ] close-guard 独立修复和 focused re-verification 已完成。
- [ ] current macOS local runtime 保持 Python sidecar；mobile/macOS iCloud 使用窄 Rust Paper Core。
- [ ] `bridgeRequest` envelope、方法表、DTO、error code 与 mutation ownership 已冻结。
- [ ] 中英双语、恢复稿、local/iCloud storage、conflict recovery 合同已冻结。
- [ ] iPhone 是正式 mobile Gate；iPad、Android、Windows 与移动完整生命周期明确排除。
- [ ] Apple Account、App IDs、iCloud container、entitlement 与实体设备动作分别授权。
- [ ] CP0–CP5 顺序、分支、证据与退出 Gate 被接受；不使用旧 pass count 或 debug 冒充发布证据。
- [ ] synthetic data 是默认边界；真实 Vault、签名、上传、TestFlight、分发、tag、push 与 release
  不由本计划批准自动获得授权。

2026-08-30 的“实施本计划”只批准本草案和活动文档进入一个本地 documentation commit；以上
checkbox 仍全部未通过。
