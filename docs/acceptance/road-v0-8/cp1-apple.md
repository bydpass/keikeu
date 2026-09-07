# Road v0.8 CP1：Apple 平台可行性

日期：2026-09-07。源码父提交：CP0 `e84d0c5`；本记录随 CP1 最终源码提交。
开发者提前 YOLO 覆盖工程退出；以下只证明平台可行性，不证明 Paper 产品、输入体验或完整同步验收。

## 实现与环境

- `frontend/src-tauri/apple/AppleFiles.swift` 提供原生协调读、排他创建、下载状态及版本原字节保全。
  当前仅探针使用；正式 Paper 的路径固定、CAS 与恢复规则仍需 CP2／CP4 实现和验证。
- `tests/apple-probe/` 是一次性平台探针：Swift 调用 Rust，再回调原生文件操作。
  Tauri 添加 iOS 编译入口；手机不启动 Python，也不启用未完成的 Paper 写入。
- 本轮实际工具链：Apple Silicon macOS `27.0 (26A5425a)`、Xcode `27.0 (27A5194q)`、
  Rust `1.88.0`、Node `22.23.2`、npm `10.9.8`；Python `3.13.15` 使用原工作区既有受支持 `.venv`。
  开发者批准的本轮工程使用现有 beta 工作站；不扩展为稳定平台兼容性或分发结论。
- 复用现有开发证书、当前有效 profiles 和共享测试容器；未登录门户、创建账号或更改系统默认工具链。
  签名资料与设备标识仅在忽略的本机生成物中，不进入本记录或 Git。

## 实际执行

| 检查 | 实际结果 | 边界 |
| --- | --- | --- |
| Mac／iPhone 探针编译与严格签名核验 | 两端通过 | 开发包，不是最终分发 |
| 实体 iPhone 安装与启动 | devicectl 安装、启动成功，并取回实际运行 receipt | 非模拟器、非 XCTest 启动替代 |
| Rust → 原生本机协调读写 | 两端运行通过；已有不同字节时拒绝写入，原字节仍相同 | 专用随机合成测试目录 |
| NSFileVersion 原字节保全 | 两端 current version 读取到新副本，回读逐字节相同 | 不代表已覆盖真实 losing version／多冲突 |
| Mac → iPhone | Mac 原生协调创建；iPhone 原生 metadata 发现、下载、逐字节核对并回复 | 非普通目录扫描替代 provider |
| iPhone → Mac | Mac 终止并重新运行 verify，原生发现和回读回复通过 | `mac_roundtrip_verified` 原生窗口可见 |
| 终止／重开本机持久化 | iPhone 同一 run 重启，原测试文件回读及保全再次通过；Mac verify 同时重开原本机文件 | 不承诺任意未持久化输入零损失 |
| Tauri iOS 工程生成及 debug archive | `ios init`、`ios build --debug --no-sign --archive-only --ci` 通过；随后复用候选 profile 签名核验、实体安装和 launch 响应成功 | 尚未验证创作界面；不把 launch 响应当作产品 smoke |
| 桌面回归 | Python `299 passed`、Vitest `128 passed`、Rust `12 passed` | 本轮实际运行，不继承旧次数 |
| 工程检查 | Vite build、sidecar build、compileall、cargo fmt、文档与 diff 检查通过 | 原桌面运行链仍保留 |

最终探针运行使用一组新的随机测试身份；iPhone receipt 为 `iphone_read_reply_verified`，
同 run 重开为 `rust_native_local_passed`，均 `passed=true` 且 `native_rust_boundary=true`。
Mac 通过原生窗口读取 seed 和最终 verify 结果。命令进程无法直接读取其沙盒 Documents，
因此不宣称取回 Mac receipt 文件，也未修改沙盒权限；原生窗口结果与 iPhone 回读互相印证。

## 本轮发现与修复

1. Foundation 不允许组合 `.atomic` 与 `.withoutOverwriting`，首次探针因此断言退出。
   改为同目录临时文件、fsync 与 `RENAME_EXCL`，双端重新执行拒绝覆盖及原字节检查通过。
2. provisioning profile 的 iCloud services 通配值不能直接作为签名请求。改为明确的
   `CloudDocuments` 数组和容器 Info.plist 声明后，两端容器及往返通过。
3. Xcode 27 SwiftPM 默认 `swiftbuild` 与当前 `swift-rs 1.0.7` 跨编译参数不兼容，
   首次 Tauri 编译混用 Mac 框架并失败。局部 PATH 包装只为 `swift build` 加 `--build-system native`，
   随后 archive 成功；不修改 SDK、依赖缓存、系统设置或依赖版本。

复现入口（使用支持的 Python／Node 工具链）：

```bash
python scripts/build_apple_probe.py macos
python scripts/build_apple_probe.py ios
PATH="$PWD/scripts/apple-toolchain:$PATH" npm --prefix frontend run tauri -- ios build --debug --no-sign --archive-only --ci
```

探针参数为 `--run <新 UUID> --role seed/reply/verify`：Mac seed → iPhone reply → Mac verify；
同一 UUID 的 `local` 可重开检查。只使用这次创建的合成目录，不删除旧 provider 内容。
所有生成包、profiles、原始日志、receipt、构建目录留在忽略路径；已安装开发探针及合成数据保留可复查。

## 下一 Gate

CP1 平台路线成立，允许进入 CP2。CP2 冻结并实现 Paper v4 golden 对等与本地安全读写；
CP3 做实际手机创作和恢复；CP4／CP5 必须另验并发、离线、系统 losing versions、provider 改名副本、
多冲突、中断保全、输入体验和完整候选。任何一项不能用本探针往返替代。

API 参照本机 SDK 声明及 [NSFileCoordinator](https://developer.apple.com/documentation/foundation/nsfilecoordinator)、
[NSFileVersion](https://developer.apple.com/documentation/foundation/nsfileversion)；
Tauri 入口参照[官方开发指南](https://v2.tauri.app/develop/)。
