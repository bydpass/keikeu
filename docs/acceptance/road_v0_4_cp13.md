# Road v0.4 CP13 — macOS 15.7+ compatibility

> 状态：**GitHub arm64 macOS 15.7 runner 已批准；等待远程运行**
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

## 待填证据

| 项目 | 结果 |
| --- | --- |
| GitHub macOS 15.7 / arm64 环境 | Pending |
| 锁定工具链 | Pending |
| 无 override production build | Pending |
| bundle metadata / minos | Pending |
| macOS 15 launch smoke | Pending |
| 同一产物哈希 | Pending |
| 当前工作站复验 | Pending |
| 未解决 P0/P1 | Pending |

## 出错怎么查与撤销

构建失败先查工具链与 deployment target；启动失败先查 Tauri host，再查
sidecar 握手，最后查 copied Vault。任何 mutation 结果不明时停止重试并检查
磁盘。CP13 回滚点是 `6efd039`；失败时继续保留 Flet 回退，不开始 CP14。

## 下一步依赖什么

需要 GitHub runner 成功产出候选，再下载该 artifact 到当前工作站复验。CP13
两端均通过并获开发者验收后，CP14 才能删除 Flet。
