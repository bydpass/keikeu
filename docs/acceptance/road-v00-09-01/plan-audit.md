# Road v00.09.01 正式计划审计

审计对象：[正式计划书](../../road-v00-09-01.md)（版本 1.0，2026-09-30，工作树未提交版本）。审计者：Claude（Opus 5.5／High effort），2026-09-30。
状态：审计时只读；2026-09-30 用户决定后已并入[正式计划](../../road-v00-09-01.md) 1.1 并接入索引，处置见文末。本报告不代表任何步骤已通过。

## 结论

计划的方向与用户决定一致，证据分级和停止条件写得严谨，可以作为本 Road 的执行基线。**但步骤1开工前，需要先在计划中补上 5 项契约决定（下文 P1-1 至 P1-5）。**这些都不是计划写错了，而是源码里已经存在的约束，计划还没有点名。如果不先定下来，步骤1的退出条件可能以“链接了 keikeu-core”这种弱证明通过，到步骤2或步骤5才返工。

未发现 P0 问题。计划本身没有引入数据丢失或隐私泄露。

## 本轮实际读取与检查

| 类别 | 内容 |
| --- | --- |
| 现场 | `git rev-parse HEAD` = `1d8ed39`；分支 `codex/road-v00-09-01-reference-demos`；`git status --short`：计划、PROJECT、RULES、AGENTS、handoff 已修改；另有他人任务的 `.gitignore`、`.node-version`、三个 `Cargo.toml`、`architecture.html`、两个 dependency-map 文件，均未触碰 |
| 文档 | 计划全文（188 行）；PROJECT 1–60；RULES §6–§8 的 diff；AGENTS diff；handoff 第 106–126 行及“2026-09-30 审计与职责转交”一节；研究记录第 83、89、117 行 |
| 源码 | `platforms/apple/Host.swift`、`AppleFiles.swift`、`Cloud.swift`（第 1–40、110–210 行）；`src-tauri/build.rs`、`Cargo.toml`、`src/lib.rs`、`host/apple.rs`、`host/mod.rs` 第 1–140 行、`host/router.rs` 第 345–380 行、`host/private.rs` 第 1–60 行；`crates/keikeu-core/src/lib.rs`；`tauri.ios.conf.json`；`island-pager` Demo 源码 |
| SDK | iPhoneOS SDK 27.0 的 AppIntents：`IntentAuthenticationPolicy` 标注 iOS 16.0+（swiftinterface 第 3166–3167 行）；`SnippetIntent` 标注 26.0+ |
| 运行检查 | `cargo test -p keikeu-core --locked --offline`：2 个测试套件通过。`pytest -p no:cacheprovider tests/test_shared_paper_golden.py`：**失败**（见 P1-5） |
| 未执行 | 未构建桌面 crate，未运行完整 Python／前端／Rust 回归，未安装，未操作设备，未读取真实 Vault |

## 与用户决定的一致性

全部一致：最低 iOS 18、目标 18–27（计划第 26 行）；保留 Rust 与 Paper v4（第 17、27 行）；灵动岛速览＋iOS 26+ 系统卡片、共用位置（第 29 行）；目标为快速调出查看，允许收起（第 28 行）；操作按钮只能主动 opt-in（第 32 行）；“步骤N”命名（第 7 行）；B14 不重挂（第 33 行）；自动切点和手动切点规则（第 31 行）。

手动切点在用户规则“打回并提醒”之外，计划还加了“保留待修正切点”（第 31 行）。这是附加行为，不违背用户规则，实施时按计划做即可。

## 发现（按严重性）

严重性沿用 [RULES §6](../../RULES.md#6-scope-and-classification)。这里的 P1 指：计划就这样执行，会让常见主流程受阻或返工。

### P1-1 共享保存要抽到哪个 crate、Swift 宿主代码由谁编译，计划没有定

- **事实：**
  - 保存、恢复和路由代码都在 `keikeu-desktop` crate 里，这个 crate 直接依赖 Tauri（`apps/desktop/src-tauri/Cargo.toml:24`）。
  - `build.rs:32-52,73` 会把 `Host.swift`、`Cloud.swift`、`AppleFiles.swift` 编译成 `libKeikeuNative.a`，链接进 Rust。
  - Rust 通过 `keikeu_host_native` 和 `keikeu_coordinate` 反向调用 Swift（`host/apple.rs:4-6,19-25`；`Cloud.swift:192`）。
  - 现在只有 Rust→Swift 一个方向。**不存在 Swift→Rust 的导出接口。**
- **风险：**
  - 原生 App 以 Swift 为宿主。如果照现有方式链接一个自带 Swift 宿主副本的 Rust 静态库，会出现重复符号或两份 Swift 模块。
  - 步骤1的退出条件“最小 iOS 产品壳可构建并链接 Rust”（第 116 行）只链接 `keikeu-core` 也能满足，证明不了保存链路可用。
- **最小修改：**在步骤1契约里写明以下几点：
  1. 新建一个不依赖 Tauri 的宿主 crate（名称在步骤1定），`keikeu-desktop` 改为依赖它；
  2. iOS 上 Swift 宿主源码只由 App target 编译一次，Rust 侧只保留 `extern` 声明；Mac 的 `build.rs` 编译方式不变；
  3. 步骤1的桥接证明至少跑通一个宿主方法的往返，例如 `paper.create_draft` → `host.draft.put` → 重启后读回，而不只是调用 `keikeu-core`。

### P1-2 全局锁持有期间会同步等待主线程，草稿写入可能被阻塞 15 秒；从主线程调用会死锁

- **事实：**
  - `host::dispatch` 在整个 `request()` 期间都持有 Router 的 Mutex（`host/mod.rs:53-66`）。
  - `host.cloud.status` 在这把锁里调用 `Cloud.discover`（`router.rs:351-353`）；`discover` 把 `NSMetadataQuery` 投递到主队列，然后用信号量等待，最长 15 秒（`Cloud.swift:126-149`）。
  - `export` 同样是“投递到主队列＋信号量等待”（`Host.swift:34-66`）。不过 Rust 已经把系统分享面板放到锁外执行（`host/mod.rs:69-79`）。计划第 72 行只提到了分享面板。
- **风险：**
  - Swift 如果在主 actor 上调用 Rust，一遇到 `discover` 或 `export` 就会死锁。
  - 即使在后台线程调用，`host.draft.put` 也会排在最长 15 秒的 `discover` 后面，与第 41 行“进入后台时保全当前可持久化修订”冲突：iOS 给后台的时间很有限。
- **最小修改：**
  1. 步骤1契约写明：所有 Rust 调用都在同一个非主线程的串行执行器上进行；
  2. 步骤2把 `discover` 移到锁外，沿用 export 已有的“锁内取请求、锁外执行”做法，或者让草稿写入走独立路径；
  3. 步骤2增加一条退出检查：`discover` 挂起时，草稿写入仍能在限定时间内落盘并读回。

### P1-3 iCloud 容器 ID 和产品 bundle ID 没有决定，而步骤5和旧数据接续都取决于它们

- **事实：**
  - 容器 ID 写死为 `iCloud.app.keikeu.v08probe`（`Cloud.swift:6`），Mac 的 iCloud 路径也用它（PROJECT 第 40 行）。
  - 旧 iOS 候选包的 bundle ID 是 `app.keikeu.v08candidate`（`tauri.ios.conf.json:2`）。
  - 融合 Demo 用的是 wildcard 开发 profile（`island-pager/README.md:47`）。
- **推断（待核实）：**iCloud 能力要求使用显式 App ID 的 profile，wildcard profile 无法携带 iCloud 权限。
- **风险：**
  - 计划第 156 行“新测试包使用独立身份”适用于测试。但如果产品包的 bundle ID 和容器 ID 不定，步骤5无法和 Mac 互通；如果改名，现有的 Mac iCloud 库需要迁移。
  - 旧 iOS 沙盒里的私有草稿，只有沿用同一个 bundle ID 升级安装，新包才读得到。
- **最小修改：**在步骤1的“决定清单”里单列三项，由用户拍板：
  1. 产品 bundle ID（沿用 `v08candidate` 还是新建）；
  2. iCloud 容器 ID（建议保留 `v08probe`，避免 Mac 库迁移）；
  3. 这两项所需的显式 App ID 与 profile 由谁准备。

### P1-4 锁屏隐私只写了“实机核对”，没有给出安全的默认设计

- **事实：**
  - Live Activity 必定有一个锁屏呈现。Demo 在锁屏视图里直接显示了正文（`IslandWidget.swift:36-46`）。
  - 通过操作按钮或快捷指令调出的系统卡片，可以在锁屏状态下执行。
  - SDK 提供 `IntentAuthenticationPolicy`（iOS 16+），可以要求先解锁。
- **风险：**计划第 81 行“若系统无法可靠隔离，则保留应用内参考”是事后补救。到步骤4才核对，前面实现的锁屏视图可能已经默认显示正文。
- **最小修改：**在计划第 4 节写明三条默认：
  1. 锁屏呈现不显示正文，只显示“参考进行中”和页段号；
  2. 调出卡片的意图设为 `authenticationPolicy = .requiresAuthentication`；
  3. 灵动岛在锁屏时是否显示正文，作为步骤1的必核对项。

  默认先收紧；要放宽，需要实机证据加用户决定。

### P1-5 Python 与 Rust 的 Paper 规则已经不一致，共享回归目前是失败状态

- **事实：**
  - `tests/test_shared_paper_golden.py:18` 在用例 `datetime_2026-09-07T01:02:03+00:00:00.5` 上失败：Python 渲染成 `+00:00:00.500000`（`markdown_io.py:226-227` 直接使用 `.isoformat()`）。
  - Rust 的 `keikeu-core` 用同一份语料测试是通过的（`codec.rs:515`）。
  - Mac 本地库走 Python（PROJECT 第 39 行）。
- **风险：**
  - 步骤2的退出条件要求“原有共享安全回归……通过”（第 122 行），在修复之前无法达成。
  - 参考会话用“源内容摘要”判断修订（第 76 行），两种实现渲染出的字节不同，会让摘要发生误变。
- **最小修改：**
  1. 把修复 Python/Rust 的一致性列为步骤2的前置项，或者作为步骤1内的独立小修复（运行代码修改，交代码执行者）；
  2. 在计划第 8 节的风险表里记一行“共享语料当前失败”。

### P2-6 FFI 的 panic、内存释放和取消需要具体条款

- **事实：**
  - `host/apple.rs:7-17` 的 `call` 没有 `catch_unwind`，只有 `coordinate` 的回调捕获了 panic（第 32-41 行）。
  - 目前内存所有权是：Swift 用 `strdup` 分配，Rust 用 `libc::free` 释放（`Host.swift:72`，`apple.rs:15`）。
- **推断：**Rust 1.81 起，panic 穿过 `extern "C"` 边界会直接终止进程。本仓库的 rust-version 是 1.88。
- **最小修改：**在计划第 68 行的桥接约束里补四条：
  1. 每个导出给 Swift 的函数都用 `catch_unwind` 包住，把 panic 映射成 `commit_unknown` 或 `operation_failed`；
  2. Rust 返回的缓冲区只能由 Rust 导出的释放函数释放；
  3. 取消只影响界面等待，已经开始的写入以只读核对作结，计划第 72 行已有此意；
  4. 步骤1的检查里包含“注入 panic 后进程不崩溃、结果标为未知”。

### P2-7 分段测量拿不到岛的实际可用宽度，需要约定可验证的替代做法

- **事实：**
  - App 无法通过 API 取得灵动岛展开区的宽度。
  - iOS 27 SDK 新增了 `isDynamicIslandLimitedInWidth`，横屏时宽度会变窄（研究记录第 117 行）。
  - 小组件文字受动态字号影响。
  - Build 8 用“渲染 3 行、显示区预留 4 行”的余量方案，在一台设备上得到了用户接受。
- **风险：**计划第 29、132 行要求“实际排版测量”，但没有说明如何测量，步骤4可能反复试错。
- **最小修改：**
  - **写明测量办法：**在 App 内用同一字体和一个保守宽度做测量；岛内视图用 `dynamicTypeSize` 限定字号上限；保留渲染行数小于显示行数的余量；按“设备类别×横竖屏×字号”矩阵取证。
  - **写明数据流：**分段在 App 进程内完成。当前段文字通过活动的 ContentState 传给小组件扩展，只有一段、体积很小，因此不需要 App Group。

### P2-8 双向同步的写入方与存储位置可以更简单地定下来

- **事实：**
  - 设备日志显示，岛上的翻段意图 `island_step` 写进了 App 自己的容器（Build 9/10 日志），说明 LiveActivityIntent 在 App 进程里执行。
  - 卡片意图也在 App 进程里执行。
  - Demo 在没有活动时，用进程内变量记位置（`Fusion.swift:10`）。
- **建议：**阅读位置写在 App 容器内的一个小文件里，原子替换，带会话 ID 和修订号。两个入口的意图都只经 App 进程写入，旧修订的请求直接拒绝。这样计划第 80 行“确需跨进程访问时才增加共享容器”在首版可以不触发。步骤1要验证的是“活动结束或进程被杀后，位置能恢复”。

### P2-9 最有风险、最有特色的融合参考排在第 4 步，验证偏晚

- **现状：**步骤1只做“最小验证”，真实内容要到步骤3完整编辑器完成之后才接入。
- **建议：**依赖顺序不变。只是在步骤1的隐私和持久化验证中，改用“经 Rust 读出的合成 Paper”，而不是 Demo 的静态文本。如果条件允许，还可以明确授权：步骤2完成后，步骤4的只读会话部分与步骤3并行。并行与否由用户决定。

### P2-10 步骤1的退出条件范围很广，应该列出产物清单

- **现状：**步骤1同时覆盖原型、契约、桥接、持久化、隐私、测试隔离和旧数据（第 114–116 行）。
- **建议：**不拆步骤，但在计划里列出可勾选的产物清单：
  1. 可点击原型；
  2. 契约文档（含 P1-1 至 P1-4 的决定）；
  3. 桥接往返与 panic 检查；
  4. 位置持久化恢复检查；
  5. 锁屏实机核对记录；
  6. 旧数据访问边界清单；
  7. 设备矩阵。

  每项都要写明证据形式，才能判定是否通过。

### P2-11 收口时合回哪个分支没写清，主工作树现在也不干净

- **事实：**
  - 主工作树 `/Users/chenxi/kits/keikeu` 当前在 `codex/road-v00-09-01-plan` 分支上。
  - 它有两处暂存改动：`A .claude/skills/keikeu-routine/SKILL.md` 和 ` D PLAN_road_v0_8.md`；还有未跟踪的 `.build/`、`uv.lock`。
  - `git worktree list` 显示，没有任何工作树检出 `main`。
- **风险：**计划第 152 行只写了“合入主工作树”。实际执行时需要切换分支，并处理这些归属不明的改动。
- **最小修改：**写明合回目标是 `main`；收口前先由用户认领主工作树里的这些改动；同时写明 `codex/road-v00-09-01-plan` 分支的去留。

### P2-12 “Mac 与新 iOS 调用同一实现”需要限定到 Rust 宿主路径

- **事实：**
  - Mac 本地库走 Python，Mac iCloud 和旧 iOS Tauri 候选走 Rust 宿主（PROJECT 第 39–42 行）。
  - `lib.rs:106-182` 仍保留着 iOS 的 Tauri 入口。
- **最小修改：**
  1. 计划第 66、122 行写明：抽离只影响 Mac iCloud 路径和旧 iOS Tauri 目标，Mac 本地库的 Python 路径不在本次范围；
  2. 步骤2写明旧 iOS Tauri 目标是继续保持可编译，还是随原生 App 退役（由用户决定）。

### P3-13 其他

- **旧 iOS 数据：**2026-09-29 查询 iPhone 17 Pro 的已安装 App 时，没有 `app.keikeu.v08candidate`，这台设备上没有旧 iOS 沙盒数据。其他设备未知。旧数据主要在 Mac 和 iCloud 容器里，可以补进计划第 7 节。
- **Demo 分段不能直接照搬：**Demo 在段落边界会去掉换行（`Segments.swift:114`，`check.swift:14-16` 比较时过滤了换行），并且用正文里的 `｜` 作为手动标记。计划第 77 行已禁止这两种做法，这里只作提醒。
- **分支前缀：**分支仍以 `codex/` 开头，但执行者已换成 Claude。可以沿用以保持连续，由用户决定是否改名。

## 事实、推断与必须补验

| 类别 | 内容 |
| --- | --- |
| 已证实（源码或本轮检查） | 只有 Rust→Swift 桥接；Router 全局锁内会同步等待 `discover`；`export` 已移到锁外；容器 ID 写死为 `v08probe`；保存代码在依赖 Tauri 的 crate 里；golden 共享语料 Python 失败、Rust 通过；`IntentAuthenticationPolicy` 为 iOS 16+；`SnippetIntent` 为 26+；LiveActivityIntent 在 App 进程执行（Build 9/10 设备日志） |
| 合理推断（需要核实） | wildcard profile 无法携带 iCloud 权限；panic 穿过 `extern "C"` 会终止进程；ContentState 只放一段文字就足以避免 App Group；Live Activity 最长活动 8 小时（研究记录第 83 行引用的 Apple 文档，本轮未复查） |
| 必须补验（设备） | 锁屏时灵动岛和锁屏视图是否显示正文；卡片在锁屏时的认证行为；冷启动下的调出与翻段；岛→卡片方向的位置同步；动态字号与横屏窄岛；iOS 18 真机；无岛机型 |
| 不作为验收 | Demo 的 65 ms、2–4 ms 耗时；Build 8 的布局只针对合成正文和单台设备；Spotlight 可以调出卡片，不等于编辑器内的入口已经解决 |

## 建议修改顺序

1. **补齐步骤1的契约决定：**把 P1-1、P1-2、P1-3、P1-4 写入计划第 4 节和步骤1的通过条件。只改计划文本，由规划者（Claude）执行。其中 P1-3 的三项需要用户拍板。
2. **修复共享语料失败（P1-5）：**运行代码修改，按接力协议交代码执行者。修完重跑 `tests/test_shared_paper_golden.py` 和 `cargo test -p keikeu-core --locked`。
3. **补充桥接条款并列出步骤1产物清单：**P2-6、P2-10。
4. **写清分段测量办法、位置存储和锁屏默认：**P2-7、P2-8，与第 1 项的 P1-4 一起写。
5. **执行顺序与收口前提：**P2-9 的并行授权、P2-11 的合回目标、P2-12 的范围限定，由用户决定后写入计划。
6. 完成以上各项后，才开始步骤1的产品工程。

## 下一动作

- **需要用户决定：**
  1. P1-3 的产品 bundle ID、iCloud 容器 ID，以及显式 profile 由谁准备；
  2. P2-9 是否允许步骤3与步骤4的只读部分并行；
  3. P2-11 主工作树里的暂存改动归谁、`codex/road-v00-09-01-plan` 分支去留；
  4. P2-12 旧 iOS Tauri 目标是否退役。
- **用户授权后由 Claude 执行：**把上述决定和 P1-1、P1-2、P1-4 的契约写进计划，同步更新 PROJECT、handoff 和 CONTEXT，并把本报告接入文档索引。
- **交代码执行者：**P1-5 golden 一致性修复。

## 处置（2026-09-30）

用户决定：沿用旧身份 `app.keikeu.v08candidate`；iCloud 容器保留 `iCloud.app.keikeu.v08probe`；融合参考可与编辑器并行；旧 Tauri iPhone 版退役，新版为 Swift 原生；主工作树未署名改动打包移出，旧计划分支归档。

| 项 | 处置 |
| --- | --- |
| P1-1、P2-6 | 计划第 4 节“保存与恢复”“Swift–Rust 桥接”行及步骤1产物清单 |
| P1-2 | 计划第 4 节新增“调用线程”行；步骤2通过条件加文件发现挂起时的草稿写入检查 |
| P1-3 | 计划第 2 节身份与容器决定；步骤1产物⑥；第 8 节“签名与身份”风险 |
| P1-4 | 计划第 4 节参考状态第 6 条改为收紧的默认 |
| P1-5 | 未修复（运行代码），列为步骤2前置与第 8 节风险 |
| P2-7、P2-8 | 计划第 4 节“参考呈现”行及参考状态第 5 条 |
| P2-9 | 第 6 节依赖改为步骤2后步骤3与步骤4并行 |
| P2-10 | 步骤1产物清单 |
| P2-11 | 已执行：主工作树改动打包至其忽略目录 `tests/test-vault/history/main-worktree-unsigned-2026-09-30/`（含补丁、副本、压缩包与 SHA256SUMS，已校验），工作树恢复干净并切回 `main`；本地分支 `codex/road-v00-09-01-plan` 已删除，归档标签 `archive/road-v00-09-01-plan` → `20277c4`。远端同名分支未删（需推送授权）；本地 `main` 落后 `origin/main` 2 个提交，未拉取 |
| P2-12 | 计划第 4 节写明 Mac 本地仍走 Python；旧 Tauri iOS 入口随步骤2移除 |
