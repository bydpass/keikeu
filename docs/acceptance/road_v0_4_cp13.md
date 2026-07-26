# Road v0.4 CP13 — macOS 15.7+ compatibility

> 状态：**通过；开发者已于 2026-07-26 验收**
> 日期：2026-07-26
> 基线：CP12 `6efd0394361579e3b4d6bdd627422df4ea6c8c2e`

## 现在要证明什么

CP12 证明当前 macOS 27 beta 工作站上的 production bundle 和产品流程可用，
但不能证明最低系统兼容。开发者把可证明的发布最低版本上调为 macOS 15.7，
并批准 GitHub `macos-15` arm64 runner、workflow 与分支 push。CP13 必须在
runner 的实际 15.7.x 环境构建并启动 `.app`，记录产物哈希，再把原产物搬到
当前工作站复验。任一端缺失时，不得宣称支持 macOS 15.7+。

当前工作站是 arm64 macOS 27.0，没有 macOS 15 VM。Docker 不能替代 macOS
内核，所以只把当前工作站用于第二端复验。

成功候选来自 GitHub Actions run
[`30212594969`](https://github.com/bydpass/keikeu/actions/runs/30212594969)，
commit 为 `a6db6d26cfafdd8634f8a345dca6a07fd2fd0639`。

## 边界

- 不修改 Markdown、索引、Vault、协议、权限、依赖或业务规则。
- 只使用 copied/synthetic Vault，不读取或修改真实作者 Vault。
- workflow 只做 CP13 构建、启动 smoke 与 artifact upload；不发布或部署。
- 不加入虚拟化依赖、签名、公证、DMG 或 App Sandbox。
- beta 工作站只负责复验，不负责生成 macOS 15 兼容候选。

## GitHub runner 构建清单

workflow 必须在 `macos-15` 上断言 arm64 与实际 `15.7.x`，再记录：

- workflow commit SHA 与 runner image version
- Node/npm、Rust/Cargo、Python/PyInstaller 实际版本
- frontend tests、Rust tests、Python compileall
- 无 config override 的 sidecar 与 Tauri production build
- frozen sidecar `system.hello`
- `.app` 启动、host/sidecar 存活与干净退出
- metadata、Mach-O、哈希和 artifact upload

锁定期望为 Node/npm `22.23.1`/`10.9.8`、Rust/Cargo
`1.88.0`/`1.88.0`、Python/PyInstaller `3.13.14`/`6.21.0` 和
`aarch64-apple-darwin`。workflow 只安装 lockfile 已固定的依赖。

## 产物身份

候选路径：

```text
frontend/src-tauri/target/release/bundle/macos/keikeu.app
```

必须记录：

- `CFBundleIdentifier=app.keikeu.desktop`
- `LSMinimumSystemVersion=15.7`
- 主程序与 sidecar 均为 arm64
- 主程序 Mach-O `minos 15.7`
- 主程序、sidecar 和传输压缩包的 SHA-256
- 未签名/未公证边界

压缩包只用于把同一产物移到当前工作站；当前工作站不得重新构建后冒充复验。

## 两端 smoke

GitHub macOS 15.7 runner：

1. frozen sidecar 完成 `system.hello`。
2. production `.app` 启动并保持运行。
3. 确认 host 与 sidecar 均出现并干净退出。
4. 使用 `ditto` 打包唯一候选并上传哈希证据。

当前工作站端：

1. 校验传输压缩包以及解包后主程序、sidecar 哈希不变。
2. 用新的临时 Home 重跑同一最小流程。
3. 确认没有依赖本机重建产物。

## 实际证据

| 项目 | 结果 |
| --- | --- |
| GitHub macOS 15.7 / arm64 环境 | Pass — `macos-15-arm64` image `20260715.0234.1`，macOS `15.7.7 (24G720)` |
| 锁定工具链 | Pass — Node/npm `22.23.1`/`10.9.8`，Rust/Cargo `1.88.0`/`1.88.0`，Python/PyInstaller `3.13.14`/`6.21.0` |
| Xcode / target | Pass — image 默认 Xcode `16.4`，产物 SDK `15.5`；`aarch64-apple-darwin` |
| 自动检查 | Pass — Python compileall、Vitest `48`、Cargo `10` |
| 无 override production build | Pass — frozen sidecar 与标准 `tauri:build` |
| bundle metadata / minos | Pass — `app.keikeu.desktop`，minimum/minos `15.7`，主程序与 sidecar 均为 arm64 |
| macOS 15 launch smoke | Pass — sidecar hello、host/sidecar 存活与干净退出 |
| 同一产物哈希 | Pass — 下载压缩包及解包后二进制与 runner 记录一致 |
| 当前工作站复验 | Pass — fresh fake Home、copied v3 Vault、Paper、Flashcard page 1、Library、退出与重启 |
| 未解决 P0/P1 | 无 |

实际 SHA-256：

```text
keikeu-desktop  b154fc2db565af13bf4fa093d75972e55c19c6cee082a64bb5df0f36a48fc875
keikeu-sidecar  2adccd679f0c417ad279077e26547a407a42f811077038d58c4773f9ef87e5ad
transfer zip    b8afdfb82de7f759a48791d55627c3d8bffa17e7083a62096a2a89ba144f018d
```

runner image 的不可变
[软件清单](https://github.com/actions/runner-images/blob/macos-15-arm64/20260715.0234/images/macos/macos-15-arm64-Readme.md)
记录默认 Xcode `16.4`；run 的 Rustup 输出记录
`1.88.0-aarch64-apple-darwin`，主程序 `vtool` 同时记录 SDK `15.5`。

当前工作站只写入精确临时根目录中的 copied Vault、临时配置和设备状态。
启动时把 fixture 的故意过期 v2 索引重建为 v3；Markdown 没有变化。退出后
host/sidecar 无残留，二进制哈希未变化，临时根目录随后删除。

## CI 收口

- run `30212236885` 暴露 Cargo test 早于 frozen sidecar 的顺序问题；
  `1de6d32` 改为先构建 sidecar。
- run `30212408271` 暴露 Tauri 打包后 sidecar basename 为
  `keikeu-sidecar`；`a6db6d2` 让验证和进程检查复用 bundle 内精确路径。
- run `30212594969` 全绿并上传唯一候选与证据。

GitHub 对固定 action 的 Node 20 runtime 发出弃用提示，但 runner 当前强制用
Node 24 后 workflow 仍通过；这不是项目锁定的 Node `22.23.1`。`npm audit`
报告的 6 个 high advisory 均在 `@vue/test-utils` 测试工具链；
`npm audit --omit=dev` 为 0。两项均不改变本次 production bundle 结论，也
不在未授权情况下改动已批准依赖。

## 出错怎么查与撤销

构建失败先查工具链与 deployment target；启动失败先查 Tauri host，再查
sidecar 握手，最后查 copied Vault。任何 mutation 结果不明时停止重试并检查
磁盘。CP13 回滚点是 `6efd039`；失败时继续保留 Flet 回退，不开始 CP14。

## 下一步依赖什么

CP13 两端工程证据已通过并获开发者验收。下一步在独立 CP14 分支删除 Flet
并完成最终审计；签名、公证、DMG、tag、archive 与发布仍不在本 gate。
