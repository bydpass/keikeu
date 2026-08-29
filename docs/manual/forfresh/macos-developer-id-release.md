# macOS Developer ID 人工发布手册

> **预启动状态（2026-08-26）：** Road v0.8 [计划草案](../../../PLAN_road_v0_8.md)已记录，
> 但 CP0 尚未获 seed 批准，打包、签名与受邀 Alpha 均未启动。
> app-specific password 已停用，现有 Keychain 公证 profile 必须视为不可用。
> 本文当前只用于教学，不授权创建凭据、构建发布候选或向 Apple 上传软件。

第一次接触 Apple 直接分发时，先读
[macOS 开发者入门手册](macos-developer-beginner-guide.html)。

本文不是产品或工程权威。当前边界回到 [SPEC](../../SPEC.md)、
[RULES](../../RULES.md)、[PROJECT](../../PROJECT.md) 与 Road v0.8 [计划草案](../../../PLAN_road_v0_8.md)；
草案中的建议值只有在 CP0 seed 获明确批准后才成为实施合同和 Gate。

## 1. 当前状态

已经知道：

- 开发者已加入 Apple Developer Program；
- 本机曾安装 Developer ID Application 证书及匹配私钥；
- 签名、公证、staple、Gatekeeper 和运行时 smoke 是不同结论；
- 私钥、凭据、原始日志、产物和本机身份信息不得进入 Git。

当前不能声称：

- 公证 profile 可用（app-specific password 已停用，残留 profile 必须视为不可用）；
- Road v0.8 的版本、bundle identifier、架构、最低 macOS 或候选名已锁定；
- 旧工具版本、beta 例外或旧命令可直接用于 v0.8；
- 任何 keikeu 产物已签名、公证、staple、通过 Gatekeeper 或安装验证。

本文不会删除 Keychain 中可能残留的 profile，也不会把残留项当作可用凭据。

## 2. 适用范围

本文只解释 Mac App Store 外的 Developer ID 直接分发。它不自动适用于：

- Mac App Store 或 TestFlight；
- PKG、自动更新、CI 签名或远端凭据；
- Intel Mac、universal binary 或 Rosetta；
- iOS、iPadOS、Android、HarmonyOS、Windows、Linux 或 watchOS；
- 尚未批准的 Road v0.8 平台和产品范围。

## 3. 四个信任动作

| 动作 | 做什么 | 不证明什么 |
| --- | --- | --- |
| Developer ID 签名 | 开发者用私钥声明签署来源，并让签名后的代码与资源改动可被检测 | 不证明 Apple 已检查，也不证明应用功能正确 |
| Apple 公证 | Apple 自动扫描提交软件中的已知恶意内容和代码签名问题；接受后生成票据 | 不是 App Review，不替代签名，也不保证没有未知漏洞 |
| Staple | 把既有公证票据附到对应应用、DMG 或安装包 | 不重新审批、不修复签名、不重新扫描 |
| Gatekeeper | 接收者 Mac 根据来源、签名、公证证据和本机策略决定是否放行 | 不执行前三步，也不证明产品质量 |

记忆方式：签名封住字节并声明签署者；公证让 Apple 自动检查并产生票据；
staple 让产物携带票据；Gatekeeper 在接收者 Mac 上消费这些证据。

## 4. 证书、私钥与公证凭据

### Developer ID 签名身份

Developer ID Application 证书与匹配私钥共同构成签名身份：

- 证书关联 Developer ID 身份与公钥；
- 私钥执行签名，必须留在 Keychain 或另行批准的私密存储；
- 本项目不导出任何私钥或 `.p12`；
- v0.8 开始时必须重新确认会员、证书有效性和匹配私钥。

### Notary 认证凭据

Notary 认证只用于向 Apple 公证服务提交，与签名身份不同：

- app-specific password 已停用；
- 任何残留 Keychain profile 当前都视为不可用；
- 现在不要查询、测试、创建或替换 profile；
- v0.8 只有在开发者明确批准持久 Keychain 修改后，才能生成新认证；
- 新密码必须由工具安全提示读取，不进入参数、环境变量、文件或聊天。

停用 app-specific password 不等于 Developer ID 证书或私钥已被撤销。

## 5. 立即停止条件

出现任一情况就停止：

- 发布契约或 Road Gate 尚未批准；
- app-specific password 或公证 profile 不可用；
- 会员、Developer ID 证书或匹配私钥不可用；
- 工具链、版本、bundle ID、架构、最低系统或容器未锁定；
- 工作树存在无法解释的改动；
- 签名、公证、staple、Gatekeeper、安装或 smoke 任一步失败；
- 候选在签名、提交或绑定哈希后发生无法解释的变化；
- 怀疑私钥、凭据、作者内容或本机身份信息泄漏。

不要通过右键打开、删除 quarantine、关闭安全策略、ad-hoc 签名或
`--deep --force` 绕过失败。

## 6. Road v0.8 必须重新锁定的契约

v0.8 开始打包前，开发者必须明确批准：

- 应用版本；
- bundle identifier；
- 支持架构和明确不支持的架构；
- 最低 macOS；
- hardened runtime 和 entitlement 边界；
- 分发容器及不可变候选命名；
- 稳定工具链及任何窄范围例外；
- 签名、公证、staple、Gatekeeper、安装与产品 Gate；
- 证据、凭据、产物和测试者隐私边界。

旧 Road 的数值、候选名、beta 例外和命令不得自动沿用。

## 7. v0.8 启动前检查

重新开始时按顺序确认：

1. 当前 source commit 与工作树状态明确；
2. 版本、bundle ID、架构、最低系统和容器已获批准；
3. macOS、Xcode、Rust、Node、Python、Tauri 与打包工具重新盘点；
4. Developer ID Application 身份与匹配私钥重新验证；
5. 经明确批准建立新的公证认证并直接保存到 Keychain；
6. 构建输出目录、DMG 和原始日志不会进入 Git；
7. 测试只使用合成 Vault 或副本，不触碰唯一真实 Vault。

任何一项不满足都不进入打包。

## 8. 未来候选的验证顺序

精确命令必须在 Road v0.8 的实际工具链上逐条演练后补入。当前不提供旧命令。

未来至少要按以下顺序证明：

1. 从明确 commit 构建应用和所有嵌套代码；
2. 验证版本、bundle ID、架构、最低系统和 hardened runtime；
3. 使用合成 Vault 完成启动、退出、重启和内容找回 smoke；
4. 从同一源代码生成新的 Developer ID 签名候选；
5. 验证嵌套签名与可信时间戳；
6. 生成不可变分发容器并记录 staple 前 SHA-256；
7. 只提交该候选公证，审查同一次提交的状态与日志；
8. 对同一候选 staple 并验证票据；
9. 重新计算最终 SHA-256；
10. 保留 quarantine 通过普通 Gatekeeper、安装、启动和重启路径。

公证提交后，只有被计划明确允许的 staple 可以改变同一候选。其他变化必须
废弃该候选并使用新编号。

## 9. 隐私与证据最小化

可以记录：

- keikeu 版本与 source commit；
- 工具版本；
- 证书、私钥匹配和 profile 的可用/不可用布尔结果；
- 候选编号与 staple 前后 SHA-256；
- 每个 Gate 的成功、失败、遗漏和风险。

不得记录：

- Apple ID、邮箱、Team ID、密码、token、API key 或 profile 名；
- 完整签名身份、证书 CN、私钥、`.p12` 或 CSR；
- 原始 `security` 输出、公证历史、提交日志或本机绝对路径；
- DMG、应用 bundle、构建输出、Vault 路径、作者内容或测试者身份。

若需要排障，先在本机查看原始输出，只把最小脱敏结论写入证据。

## 10. 接收者安装与 smoke

未来有效的接收者验证必须：

1. 传输精确最终哈希，并保留 quarantine；
2. 按普通方式打开分发容器并安装；
3. 不右键绕过、不降低安全设置、不删除 quarantine；
4. 正常启动、退出并重启应用；
5. 使用合成内容完成 Road v0.8 批准的核心流程；
6. 记录完成情况和介入次数，不记录作品或真实路径。

Gatekeeper 通过不能替代运行时 smoke；运行时通过也不能替代产品价值判断。

## 11. 排障与凭据事故

- 证书没有匹配私钥：停止签名，核对 CSR、证书和 Keychain 归属；
- 公证认证失败：停止提交，确认凭据状态，不在聊天或脚本中暴露密码；
- 签名或公证失败：审查本机最小诊断，修复根因后生成新候选；
- staple 失败：确认公证接受状态与操作对象是同一候选；
- Gatekeeper 阻止：核对最终哈希、签名、公证、quarantine 与当前策略。

若密码曾进入明文文件：

1. 停止发布并撤销该密码；
2. 销毁明文副本，不要只移动文件；
3. 检查仓库、shell history、证据和聊天暴露面；
4. 只有在发布重新启动且经明确批准后，才生成新密码并重建 profile；
5. 证据只记录动作的布尔结果。

## 12. 官方参考

- [Preparing your app for distribution](https://developer.apple.com/documentation/xcode/preparing-your-app-for-distribution)
- [Developer ID certificates](https://developer.apple.com/help/account/certificates/create-developer-id-certificates/)
- [Packaging Mac software for distribution](https://developer.apple.com/documentation/xcode/packaging-mac-software-for-distribution)
- [Notarizing macOS software before distribution](https://developer.apple.com/documentation/security/notarizing-macos-software-before-distribution)
- [Resolving common notarization issues](https://developer.apple.com/documentation/security/resolving-common-notarization-issues)
- [App code signing process in macOS](https://support.apple.com/guide/security/app-code-signing-process-sec3ad8e6e53/web)
- [Gatekeeper and runtime protection](https://support.apple.com/guide/security/gatekeeper-and-runtime-protection-sec5599b66df/web)
