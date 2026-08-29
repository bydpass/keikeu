# Road v0.8 实施计划（设计草案；Road 尚未启动）

> 状态：开发者于 2026-08-26 授权把本草案与既有 `keikeu-routine` skill 改动一并落盘并提交。
> 本次只建立可评审的发布计划，不是 CP0 checkpoint，也不授权构建、Keychain 修改、Apple
> 上传、外部分发、tag、push 或 release。Road v0.8 仍不得早于 2026-08-28 启动。
>
> 继承基线：Road v0.7 最终产品 checkpoint `2f03aee`，以及其后独立 closeout
> `a7726ae`。Paper v4、Index v4、protocol v2、完整文件夹生命周期与已接受 App Shell 不变。
>
> 发布工程权威：本计划在 CP0 获开发者批准后定义 Road v0.8 的范围、顺序和 Gate；
> [`docs/SPEC.md`](docs/SPEC.md) 继续定义产品边界，
> [`docs/RULES.md`](docs/RULES.md) 继续定义数据、Git、证据与安全纪律。

## 0. Road 目标

Road v0.8 把已接受的 Apple Silicon 桌面应用交付为一个可验证、可撤回的受邀 Alpha：

```text
已接受源码 → 可重复构建演练 → Developer ID 候选
           → 公证与 staple → 保留 quarantine 的接收机安装 Gate
```

本 Road 是打包与交付 Road，不是产品功能、数据、UI、平台扩张或自动更新 Road。

## 1. 权威与执行纪律

- 本草案提交只供批准；CP0 开始后才成为实施计划。
- CP0 最早于 2026-08-28 创建，并从开发者明确接受的本计划提交开始。
- 2026-08-26 文档/源码复核发现 App-root pending durable intent 的窗口关闭保护仍由
  `PaperView` 注册；runtime blocked 卸载该组件后，以及 Library/Vault durable intent
  存在时，没有等价的 App-root guard。该实现偏差不改写已接受合同；开发者必须先决定
  由独立 Road 前修复还是修改本计划纳入窄修复，并以聚焦测试重证，之后才能批准 CP0 seed。
- 每个 CP 只从前一个已通过 checkpoint commit 建立一条 focused branch。
- 本 Road 不使用 advance YOLO。每个 checkpoint、Keychain 修改、Apple 上传、外部传输、
  tag、push 与 release 都保留独立授权。
- `docs/manual/forfresh/macos-developer-id-release.md` 只作教学参考；旧 profile、旧命令、
  beta 例外与历史 pass count 均不能成为本 Road 证据。
- 应用 bundle、DMG、source archive、哈希文件、原始签名/公证日志与凭据不进入 Git；
  所有本地 rehearsal/候选产物只进入忽略的 `build/release/road-v0-8/` 或另行批准的外部目录。
- 验收记录只写去标识结论；不写 Apple ID、邮箱、Team ID、证书 CN、profile 名、token、
  私钥、本机绝对路径、Vault 路径、作者内容或测试者身份。

## 2. 建议发布合同（CP0 待批准）

| 项目 | 建议值 | 边界 |
| --- | --- | --- |
| Road 名称 | 打包与受邀 Alpha 发布 | 不含新产品能力 |
| 应用版本 | `0.8.0` | 与 Road 对齐；不把候选号塞入产品版本 |
| 首个候选 | `C01` / `alpha.1` | 后续任何重建使用新候选号 |
| bundle identifier | `app.keikeu.desktop` | 保持既有身份；CP0 复核唯一性后冻结 |
| 架构 | `arm64` | 不支持 Intel、universal 或 Rosetta |
| 最低系统 | macOS `15.7` | 必须由同一最终候选在稳定目标系统重证 |
| 容器 | Tauri 默认 DMG | 不做 PKG、自制背景或新打包依赖 |
| Runtime | hardened runtime 开启 | 不启用 App Sandbox；不预加 entitlement |
| 分发 | 一次受邀、人工传输 | 无公开下载、自动更新或 CI 发布 |
| 许可 | GPLv3 + 对应 source archive | 不附加 NDA 或禁止再分发条款 |
| 数据 | synthetic Vault | 真实 Vault 需独立窄授权，不是发布 Gate 前提 |

建议产物名：

```text
keikeu-0.8.0-alpha.1-aarch64.dmg
keikeu-0.8.0-alpha.1-source.tar.gz
SHA256SUMS.txt
```

Tauri `version` 建议为 `0.8.0`，macOS `bundleVersion` 建议从 `80001` 开始；`C02` 对应
`80002`。Python、npm、Cargo、Tauri 与 sidecar hello 中的产品版本必须一致。

## 3. 全局范围

### 3.1 包含

- 冻结版本、bundle ID、架构、最低系统、容器、候选命名与回撤合同。
- 校准 Node、npm、Python、PyInstaller、Rust、Cargo、Tauri、macOS 与 Xcode 工具锁。
- 复用现有 PyInstaller sidecar 与 Tauri bundler，生成 release `.app` 和默认 DMG。
- Developer ID Application 签名、hardened runtime、可信时间戳、嵌套 sidecar 验证。
- 通过 `notarytool` 公证、审查同次提交日志、staple 与 Gatekeeper 验证。
- 从候选源码 commit 生成对应 source archive，并交付 GPL、第三方许可说明和最终 SHA-256。
- 在稳定 macOS 15.7+ Apple Silicon 接收机上保留 quarantine 完成安装与 synthetic smoke。
- 失败时撤回候选；卸载应用不删除 Vault、配置或作者资产。

### 3.2 不包含

- Paper v4、Index v4、protocol v2、DTO、Core、bridge、保存、恢复或迁移合同变更。
- UI 重构、Figma、DMG 皮肤、品牌精修或新产品功能。
- AI、同步、账号、遥测、崩溃上报、后台服务、updater、自动下载或网络 runtime。
- CI 持有签名/公证凭据、GitHub Release、公开下载站或远端自动发布。
- App Sandbox、额外 entitlement、PKG、Mac App Store、TestFlight 或 App Store Connect 发布。
- Intel Mac、universal binary、iOS/iPadOS、Android/HarmonyOS、Windows、Linux 或 watchOS。
- 真实 Vault、第二产品用户、tag、push 或公开 release；这些不能由“Alpha”自动推出。

## 4. 候选与凭据安全合同

### 4.1 候选生命周期

```text
rehearsal          可丢弃；不得分发；不获得候选编号
C01 pre-staple     已签名 DMG；只允许提交公证并记录 SHA-256
C01 final          对同一 DMG staple 后重新计算 SHA-256
retired            任一失败或额外字节变化；不得修补后继续冒充 C01
```

- 公证提交后，只有计划内的 staple 可以改变同一候选。
- 签名、公证、staple、Gatekeeper、安装或 smoke 任一步失败，都撤回当前候选并从 clean
  source commit 生成 `C02`；不得原地覆盖、ad-hoc 补签或移除 quarantine 绕过。
- 最终候选身份由 source commit、版本、候选号、工具链摘要和完整交付集共同确定。
  `SHA256SUMS.txt` 至少覆盖 final DMG 与对应 source archive；安装说明、GPL 与第三方 notice
  必须包含在已哈希的交付文件内。任一交付文件变化都提升候选号并重新生成全部哈希。
- “可重复”表示锁定输入和命令可再次构建，不声称签名/时间戳产物逐字节复现。

### 4.2 凭据边界

- CP2 前不查询、创建、替换或删除 Keychain 公证认证。
- Developer ID 证书必须有匹配私钥；证据只记录可用/不可用，不复制原始输出。
- CP0 必须在 `notarytool` Keychain profile 与 App Store Connect API key 中明确选择一种
  本地认证方式。API key 如被选择，CP0 还须批准仓库外本机私密文件的位置类别、最小权限、
  保留期限与撤销/删除边界；实际路径和内容不进入证据。任何 secret 都不进入参数、环境文件、
  聊天、shell transcript、Git 或未经批准的明文文件。
- Tauri 负责现有应用与嵌套二进制的构建/签名；Apple 原生工具负责公证、staple 和验证。
- 不使用 `altool`、ad-hoc 发布签名、`codesign --deep --force`、右键打开、关闭 Gatekeeper
  或删除 quarantine。
- 原始公证日志仅在本机审查；tracked report 只记录状态、warning 数量、去标识根因和决定。
- 一旦怀疑凭据进入参数、未经批准的明文文件、Git/history、聊天或日志，立即停止发布并撤销相关凭据；
  完成本地暴露面清查后，只有经新授权才能建立新认证，受影响候选一律 retire。

### 4.3 工具链边界

- 当前 macOS/Xcode 27 beta 只提供规划盘点，不自动获得发布资格。
- CP0 必须为 CP3 冻结稳定 macOS 构建主机与稳定 Xcode。beta 例外如确有需要，只能通过单独 ADR
  覆盖 CP1 rehearsal，并逐项写明动作、不可推导的兼容性结论和到期条件；不得授权 CP3
  的 Developer ID 签名、公证或分发。没有稳定发布工具链就阻断 CP3。
- `.node-version`、`.python-version`、`rust-toolchain.toml`、`requirements-build.lock`、npm/Cargo
  lockfile 与实际工具必须一致；旧 CP13 workflow 不直接复用。

## 5. 通用证据

### 5.1 文档 Checkpoint

```bash
.venv/bin/python scripts/check_docs.py
git diff --check
```

### 5.2 工程基线

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

### 5.3 构建演练

```bash
.venv/bin/python scripts/build_sidecar.py
npm --prefix frontend run tauri:build -- --bundles app,dmg
```

- 每次记录实际命令、日期、工具版本、结果和未执行项；不复制旧 pass count。
- `file`、`lipo`、`vtool` 与 `PlistBuddy` 检查主程序/sidecar 架构、最低系统、版本和 bundle ID。
- sidecar 必须实际完成 protocol v2 `system.hello`；旧 protocol v1 workflow 证据无效。
- build 不证明签名、公证、安装、启动、重启、文件 handoff 或产品接受。

### 5.4 信任与安装证据

CP2 冻结实际工具链后再在本地 runbook 中写入带占位符的精确命令。至少验证：

- `.app`、所有嵌套 Mach-O 与外层 DMG 的 Developer ID 签名；同时验证代码的 hardened runtime、
  可信时间戳和 entitlement；
- 不存在 `com.apple.security.get-task-allow=true`；
- DMG 公证状态、同次 submission log、staple validation 与 Gatekeeper assessment；
- staple 前后 DMG SHA-256、完整交付集 hash list，以及接收机逐项核对结果；
- 普通安装、首次启动、退出、重启和 sidecar 无残留。

## 6. Checkpoint 总览

| CP | 建议分支 | 结果 | 主要 Gate |
| --- | --- | --- | --- |
| CP0 | `docs/cp0-v08-release-contract` | 发布合同、稳定工具链、许可与证据边界 | 开发者批准计划；无双重权威 |
| CP1 | `build/cp1-v08-release-rehearsal` | 同步版本/工具锁并完成不可分发构建演练 | `.app`/DMG/sidecar/合成 smoke 通过 |
| CP2 | `chore/cp2-v08-credential-readiness` | Developer ID 与公证认证就绪 | 独立授权的 Keychain Gate 通过 |
| CP3 | `release/cp3-v08-trust-candidate` | 签名、公证、staple 的最终 `C01` | 同一候选信任链与哈希通过 |
| CP4 | `test/cp4-v08-alpha-install` | 受邀接收机安装与 synthetic Alpha Gate | 开发者明确接受；撤回则终止 |

## 7. CP0 — 发布合同与稳定基线

**进入条件：** 日期不早于 2026-08-28；工作树 clean；开发者明确接受本计划提交作为 seed，
并批准创建 `docs/cp0-v08-release-contract`。本次草案落地授权不替代该判断。

**范围：**

- 将进入前已批准的 §2 版本、bundle ID、架构、最低系统、DMG 与候选命名校准到活动权威；
  如需修改，先更新本计划并重新取得 §14 批准，不在 CP0 内静默改合同。
- 冻结受邀 Alpha 接收范围、人工传输渠道和无 NDA 的 GPL/source 交付方式。
- 盘点稳定构建环境和全部工具锁；决定 beta 环境是排除、替换还是另立 ADR。
- 审计 GPL、第三方 license notice 与对应 source archive：证明其覆盖最终二进制所需的构建/
  安装脚本、捆绑 Rust/Python/JavaScript 模块的对应源码和第三方许可。`git archive` 只是一种
  起点；如不足，必须扩展 source bundle，不能把仓库快照自动视为完整对应源码。
- 校准 SPEC、PROJECT、README 与本计划的 current/target；不改 production code。
- 运行 §5.2 完整基线。

**明确不做：** 构建 release artifact、查询/修改 Keychain、调用 Apple 服务、选择真实 Vault、
tag、push 或外部分发。

**退出 Gate：** §14 进入批准已被准确记录；权威无冲突；CP3 稳定工具链可用；对应源码边界
已经证明；§5.2 基线真实通过；没有未解释失败。

## 8. CP1 — 可重复构建演练

**范围：**

- 将 Python、npm、Cargo、Tauri 与 sidecar hello 的应用版本同步为 CP0 批准值。
- 校准 `.node-version`、`.python-version`、build lock 注释与实际稳定工具链。
- 显式配置 DMG target、hardened runtime、最低系统和 `bundleVersion`；不增加依赖。
- 从 clean CP0 checkpoint 重建 sidecar、release `.app` 与默认 DMG。
- 构建前确认没有签名/公证环境变量或 tracked signing identity；使用明确的临时 ad-hoc/unsigned
  rehearsal 配置，并验证产物不是 Developer ID 签名。意外调用私钥立即阻断 CP1。
- 校验主程序和 sidecar 均为 `arm64`，protocol v2 hello、Info.plist 与锁定合同一致。
- 使用隔离 Home 与 synthetic Vault 完成启动、退出、重启、创建、保存和 Library 找回 smoke。
- 按 CP0 已批准的对应源码打包方式生成 source rehearsal，并审查无 secret/author content；
  只有 CP0 已证明充分时才可直接使用 `git archive`。

**候选边界：** 本 CP 产物是 disposable rehearsal，不编号、不上传、不分发，也不能晋升为 C01。

**退出 Gate：** §5.2、§5.3、artifact inspection 与 synthetic smoke 通过；无未解决 P0/P1；
release recipe 不依赖 beta-only 或未锁定输入。

## 9. CP2 — Developer ID 与公证认证就绪

**进入条件：** CP1 checkpoint 已通过；开发者另行批准只读身份盘点，并在需要时批准精确的
Keychain 持久修改。

**范围：**

- 本机确认 Apple Developer Program 状态、Developer ID Application 证书有效性和匹配私钥。
- 选择 CP0 已批准的公证认证方式；停用的 app-specific password 与残留 profile 一律不复用。
- 如需新认证，以安全提示读取 secret 并保存到 Keychain 或批准的本机私密存储。
- 本机验证认证可用；tracked report 只记录布尔结果、工具版本、遗漏和风险。

**明确不做：** 构建 C01、上传软件、导出 `.p12`、创建 CI secret、打印身份/历史、修改源码、
tag、push 或分发。

**退出 Gate：** 签名身份与认证均可用；没有敏感输出进入 Git、聊天或证据；开发者确认
CP2 Gate。任一项不满足就停止，不进入 CP3。

## 10. CP3 — Developer ID、公证与最终候选

**进入条件：** CP2 checkpoint 已通过；工作树 clean；使用 CP0 冻结的稳定 macOS 构建主机
与稳定 Xcode 工具链；开发者另行批准使用签名私钥和向 Apple 上传本候选。候选 source commit
在构建前固定，macOS 或 Xcode 任一 beta 都不得进入 CP3。

**范围：**

1. 从固定 source commit 全新生成 sidecar、frontend 与 Rust release binary，不复用 CP1 rehearsal。
2. 运行已审查的 Tauri bundle/signing 流程；它必须在 DMG 组装前签名并验证所有嵌套 Mach-O
   和 `.app` 的 Developer ID、hardened runtime、时间戳与 entitlement。
3. 校验签名后 `.app` 的版本、`bundleVersion`、bundle ID、`arm64`、最低系统和 protocol v2 hello。
4. 从该精确签名 `.app` 组装 DMG，使用 Developer ID Application 签名并验证外层 DMG；
   挂载后再次验证其中 `.app` 和 sidecar 的签名与身份一致，然后生成 `C01 pre-staple` SHA-256。
5. 仅提交该 DMG 公证，等待结果并审查同次完整日志；warning 也必须判断。
6. 接受后对同一 DMG staple 并 validate；生成 `C01 final` SHA-256。
7. 对 final DMG 运行 Gatekeeper assessment；生成已证明完整的对应 source archive，把 GPL、
   第三方 notice 与安装说明纳入已哈希交付文件，并以 `SHA256SUMS.txt` 覆盖完整交付集。
8. 用隔离 Home 复跑启动、退出、重启与 synthetic 核心 smoke。

**失败合同：** 任一步失败即 retire C01；修复从新 source commit 和新候选号开始。不得原地覆盖、
跳过日志、移除 quarantine、降低安全策略或把一次成功推断到另一产物。

**退出 Gate：** 信任链、哈希、source/许可包与本机 synthetic smoke 全部通过；无未解决 P0/P1；
tracked report 不含 secret 或身份信息。CP3 不授权外部传输。

## 11. CP4 — 受邀 Alpha 安装 Gate

**进入条件：** CP3 checkpoint 已通过；开发者批准完整交付集 hash list、接收环境、传输渠道和
外部写入。接收机是稳定 macOS 15.7+ Apple Silicon，且没有既有 keikeu 配置或真实 Vault。

**范围：**

- 同时交付 final DMG、对应 source archive、GPL/notice、安装说明与 `SHA256SUMS.txt`；接收机
  逐项核对所有交付文件的 hash。
- 使用普通下载/传输路径保留 quarantine；打开 DMG 前只读验证 `com.apple.quarantine`
  属性确实存在。属性缺失即停止，不能补写后冒充真实传输或计入 Gatekeeper 证据。
- quarantine 与 hash 通过后，按普通方式打开 DMG 并拖入 Applications。
- 不右键绕过、不删除 quarantine、不关闭 Gatekeeper、不从 build 目录直接启动。
- 使用 synthetic 内容完成首次启动、Vault 初始化、创建/保存/重开 Paper、Library 找回、dirty
  departure、Finder/default editor handoff、退出与重启；确认 host/sidecar 无残留。
- 记录人工介入次数、成功/失败、P0/P1 和未执行项；不记录测试者身份、内容或路径。
- 失败就停止继续分发并撤回候选；卸载只移除应用，不删除 Vault 或配置。

**退出 Gate：** 完整交付集 hash 与原始 quarantine 均通过，同一 final DMG 在目标系统普通安装
与核心 smoke 通过，无未解决 P0/P1，且开发者明确选择“接受 Alpha”。“撤回”是可记录的
终止状态，不算 CP4 通过，也不能进入成功 closeout。自动化、builder smoke 或 Gatekeeper
单项不能替代。

## 12. Road 完成与独立决定

CP4 通过只证明首个受邀 Alpha 候选完成。以下仍是独立决定：

- 使用真实 Vault；
- 扩大测试者范围或公开下载；
- tag、push、GitHub Release 或其他远端 release；
- 自动更新、崩溃上报、支持 SLA 或下一候选；
- Road snapshot 与 Road 完成判断。

最终 checkpoint 获开发者接受后，按 RULES 在单独 closeout change 创建
`docs/archive/snapshots/road-v0-8.html`；snapshot 不包含 DMG、源码包、原始日志、身份或 secret。

## 13. 已知风险

| 风险 | 控制 |
| --- | --- |
| beta 工作站冒充发布环境 | CP3 只用稳定 macOS 与稳定 Xcode；beta ADR 最多覆盖 CP1 rehearsal |
| Python sidecar 未被完整签名 | CP3 逐个验证嵌套 Mach-O、hardened runtime 与时间戳 |
| 公证后候选被悄悄改动 | 只允许 staple；其他变化 retire 并换候选号 |
| 凭据或身份泄漏 | secret 只留 Keychain/批准私密存储；证据只写布尔与脱敏结论 |
| 疑似凭据泄漏后仍继续候选 | 立即停止、撤销、清查暴露面；新授权后重建认证与候选 |
| 最低系统声称沿用旧证据 | CP4 用同一 final hash 在稳定 macOS 15.7+ 重证 |
| 传输绕过 quarantine | 从真实传输开始；禁止右键、`xattr` 删除和安全策略降级 |
| GPL Alpha 被错误加 NDA | 二进制、对应 source 与 GPL 同时交付；不附加限制性条款 |
| 发布测试读取真实作者配置 | 接收机无既有配置；只用 synthetic Vault |
| DMG 美化吞掉 Road | 使用 Tauri 默认 DMG；视觉偏好按 P3 记录 |
| Alpha 被误写成公开 release | CP4 只覆盖一个批准渠道和接收范围；扩大分发另行授权 |

## 14. 实施计划批准 Gate（尚未通过）

CP0 开始前，开发者须逐项确认；若修改任一项，先更新本计划并重新批准：

- [ ] Road 名称与范围为“打包与受邀 Alpha 发布”。
- [ ] 应用版本、候选号、bundle ID、`arm64`、最低 macOS 与 DMG 合同。
- [ ] CP3 稳定 macOS 构建主机、稳定 Xcode 与锁定工具链；beta ADR 如有，仅覆盖 CP1
  rehearsal 并有明确期限。
- [ ] hardened runtime、无 App Sandbox 与最小 entitlement 原则。
- [ ] GPL/source archive、第三方 notice 与无 NDA 的交付合同。
- [ ] CP0–CP4 顺序、分支、退出 Gate 与失败撤回语义。
- [ ] synthetic Vault 是默认数据边界；真实 Vault 不进入本 Road 默认授权。
- [ ] 不使用 advance YOLO；checkpoint、Keychain、Apple 上传、传输、tag、push、release 分别授权。
- [ ] 本计划提交可在 2026-08-28 或之后作为 CP0 seed。

2026-08-26 的“落地并提交”只批准本草案与既有 skill 改动进入一个本地 planning commit；
以上 checkbox 仍全部未通过。
