# Road v0.8 CP3：iPhone 本机创作工程证据

日期：2026-09-07。基线：CP2 `50707f5`；分支 `feat/cp3-v08-local-creation`。
本轮使用专用候选与随机命名的合成数据区，没有选择或迁移真实作者 Vault。

## 实现与检查边界

- iPhone 的 `bridge_request` 进入串行 Rust 宿主；身份与 generation 不匹配时拒绝请求。
  桌面本地仍走原 Python sidecar，新增 `host.*` 不进入 JSONL protocol v2。
- 复用 `PaperV4Workbench.vue`，新增窄范围 `CoreWorkspace.vue`：创建、多页编辑、保存重开、
  全页搜索、恢复列表、明确恢复／导出／丢弃、系统默认及本机持久化中英文。
  不提供移动 Index、Trash、迁移或完整文件夹管理。
- 私有恢复区位于应用 Application Support，与本地 Vault 分开，设置并核验排除云备份。
  记录保留输入原文，包括未闭合 Tags 和未通过正式校验的页面；静止 500ms 与页面隐藏时尝试写入。
  使用固定目录身份、无符号链接访问、同目录替换、fsync 与字节回读；写入失败后冻结后续恢复写入，
  要求重启检查，防止用旧内存覆盖未知磁盘结果。
- 正式保存前先持久化完整 submitted；失败禁止正式写入。保存成功只清理对应修订，
  新输入保留并按新基线保护。未知结果只读核对；核对不会重发正式保存。
  外部变化时仍可保留、导出草稿，不能覆盖活动稿。
- 保存的 Paper 经系统面板交付 Markdown 副本；恢复稿可导出 JSON 原文，损坏 Paper 可原字节导出。
  恢复写失败时允许直接将当前内存原文交给系统导出。导出面板不持有存储锁，
  不阻挡后台草稿写入；取消／失败不清稿。导出临时副本保留在本机私有或系统临时区。
- 分配 Code 同时检查已保存稿、会话草稿、恢复稿、损坏文件名及可读取的改名 sibling，
  沿用 Unicode 十进制序号语义；单个坏稿不会阻止其他稿的创建。

## 实际自动证据

- Python：`300 passed`；`compileall -q src` 通过。
- Vitest：`134 passed`，含原桌面回归及移动保护、未完成输入恢复、保存失败阻断、
  保存期间新输入、导出取消／恢复失败原文导出、后台刷新、英文校验。
- Rust：`15 passed`，含 CP2 corpus／文件安全，以及本机创建、重开、Unicode 搜索、
  私有记录重启、修订拒绝回退、旧修订不能删除新稿、未知结果只读核对、恢复区替换拒绝、
  损坏原字节保留及 Unicode 序号分配。
- `cargo fmt --check`、文档检查、`git diff --check` 通过。
- 当前源码 Tauri iOS debug archive 编译、现有本机 profile 签名及签名校验、实体设备安装通过。
  使用 `scripts/apple-toolchain/swift` 的局部构建兼容入口；没有更改 SDK、依赖缓存或全局工具配置。
- 五个尺寸 `375×812`、`720×900`、`720×680`、`920×680`、`1220×780`：
  使用已安装 ego lite 的独立无头进程、合成宿主响应检查，均无横向溢出或页面异常；五张截图已检视。
  初次截图存在工具合成分块，关闭该无头进程的 GPU 并等候布局后重新截图；不改用户浏览器设置。
  修复了窄屏英文按钮宽度及中文页码辅助名称回归。此项是浏览器布局证据。

## 实体 iPhone 本机证据

- 首次候选的启动命令返回成功，随后进程退出；读取该次候选崩溃报告，栈顶为
  `___UIApplicationEvaluateRuntimeIssueForNoSceneLifecycleAdoption_block_invoke`。
  检视已锁定 Tao `0.35.3` 的 Scene 实现，补上 `Info.ios.plist` 声明后重新构建／签名／安装；
  候选能启动，原生私有 journal 成功建立，首次语言为英文。
- debug 构建仅在显式 `--keikeu-native-smoke <UUID> seed/recover` 参数下执行合成宿主检查，
  使用独立 `CP3-<UUID>` 目录。release 不编译该入口；它不读取或改写普通候选稿件。
- `seed` 在实体设备调用同一 Rust 宿主创建两页 Paper、保护修订、保存并重开，
  再留下包含未闭合 Tags 的新修订；原生回执为 `native_host_passed: true`。
- 终止该候选进程后以同一个 UUID 的 `recover` 启动，读回未完成 Tags 与第二页原文，
  执行 Unicode 搜索，并确认旧修订删除被拒绝；原生回执为 `native_host_passed: true`。
- 回执通过设备应用文件服务取回，仅记录运行身份、阶段与结果；原始日志、签名资料、
  合成稿件和截图留在忽略的 `tests/test-vault/cp3/`，不进入 Git。
  普通候选本地存储与上述 smoke 存储分开；旧候选的未知本机状态未删除或迁移。

## 尚未完成的批次 B 检查

本机宿主 smoke 不经过 UIKit 输入或 Vue 点击，不替代完整原生创作循环。
Mac 已锁定，界面工具报告无法自动解锁；已请求开发者解锁，未猜测密码或更改系统安全设置。
设备截图服务不可用；未把失败的截图或启动命令当作可见界面证据。

尚需实体 iPhone 检查：可见启动与错误页、多页点击／编辑、系统导出完成及取消、
中文／英文 IME、软键盘、safe area、光标／选区分页、前后台切换，以及真实使用手感。
Mac 原生 UI 回归、双端云端 provider 矩阵及全套候选验收仍属于后续 CP4／CP5。

提前 YOLO 覆盖本阶段工程退出；自动与可执行本机宿主检查成立后可进入 CP4 工程。
本记录不宣称 iPhone 产品人工验收、iCloud 同步、CP5、Road 归档或发布完成。

本阶段最后一次设备 seed／recover 使用同一当前源码候选；可执行文件 SHA-256：
`2b1e28d214638fc00c0b16b18c25e486fda1d4dad59ca28e929e951dfc53b4e3`。两份回执均为 `native_host_passed: true`。
