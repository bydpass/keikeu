# ADR-0006：Road v0.6 beta 工程例外

**日期**：2026-08-02

**状态**：accepted
**决策者**：developer

## 背景

Road v0.6 的唯一工程工作站是 Apple Silicon Mac，当前运行 macOS 27.0 beta 与 Xcode 27.0 beta。没有稳定版 27 工具链可用于同一工作站，而 Road v0.6 只要求本地工程证据，不执行发布。

## 决策

开发者批准 macOS 27 与 Xcode 27 beta 用于 Road v0.6 CP0–CP7 的工程、测试、合成/复制 Vault smoke 和本地临时构建，直到对应稳定版发布。Node/npm 固定为 `22.23.2`/`10.9.8`，Rust/Cargo 固定为 `1.88.0`，Python 保持 `>=3.11,<3.14`。

本例外不授权 Developer ID 签名、公证、staple、DMG、公开分发、App Sandbox、push 或兼容性声称。它不支持 Intel Mac，也不自动延续给 macOS/Xcode 28 或之后的 beta。

## 后果

- beta-only 故障只能记录为当前工程观察，不能成为发布结论。
- Road v0.6 的 macOS 工程证据只适用于 Apple Silicon。
- 对应稳定版 27 可用时，本例外立即到期，后续证据应使用稳定工具链。
- 如在稳定版前更换到后续大版本 beta，Road 必须停止并另作显式决策。
- 发布工程继续延后到 Road v0.8；旧的 Developer ID 教学材料不构成本 Road 授权。

## 复核条件

稳定版 macOS 27 或 Xcode 27 发布、工作站发生大版本变化，或 Road 开始任何发布/兼容性工作时复核。
