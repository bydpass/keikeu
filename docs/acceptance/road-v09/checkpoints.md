# Road v09 执行记录

## CP0：基线集成

日期：2026-09-20。分支：`codex/road-v09-cp0-baseline`。开发者已批准 CP0–CP4 YOLO 与本地提交，不含推送、发布或 v09.01 实施。

输入：候选 `deaece8`；原工作区 `78eb755` 手册；`0447e16` 清理；`670142d` 批准计划。归档清理提交同时包含此前 PROJECT 顶部的转交提示，其余规划在后一提交中保存。两份原工作区保留，四份权威冲突按新候选事实与批准方向逐项解决。

工程接续例外见 [ADR-0010](../../architecture/decisions/0010-v09-engineering-continuation.md)。不把中断的 v08 或 B14 记为通过；现有安装 `83c4f60` 不代表后续主题 HEAD。

规划阶段原工作区工具测试 18 通过、1 失败：已删除归档引用，按计划留待 CP3。整合后全量 Python 300 通过、1 已知失败；首次缺少临时目录产生环境错误，创建隔离目录后复跑所得此结果。文档检查 86 active / 14 required 通过，差异空白检查通过。产品源码未修改，CP0 按批准的已知失败转交 CP3 边界完成。历史包、私有运行数据、签名和设备均未移动或操作。

## CP1：目录与构建入口

从 CP0 `e2c36d4` 建立 `codex/road-v09-cp1-layout`。仅搬 tracked 源码：`frontend/` → `apps/desktop/`，`src/` → `apps/desktop/python/`，三个 Swift 文件 → `platforms/apple/`。Python 导入名不变，业务代码不变；更新脚本、构建、测试与活动文档路径，历史验收只修源码链接。修复新工作区 pytest 缺少隔离临时目录父级的问题，Rust 测试路径统一回根目录 `tests/test-vault/`。

CP1 检查：前端 Vitest 142/10 通过、Vite 生产构建通过、Cargo 21 项通过、Python wheel 构建通过。独立 `.venv` 重建 sidecar，并检查 PyInstaller TOC：15 个项目模块全部来自 v09 新目录。共享旧 venv 的首轮包不作为交付证据；新环境安装项目后复验 Python。目录页 288 路径、链接、搜索及切换检查通过，文档 86/14 通过。npm/Cargo 离线缓存不足后按原锁定版本补齐；首次 npm 解析到错误引擎，改用项目固定 Node 22.23.2/npm 10.9.8 后通过。未做设备操作。

独立环境最终 Python 全量：300 通过、1 已知归档引用失败；compileall 通过。CP1 按已批准转交 CP3 的边界完成。

首次 CP1 提交被本机凭据钩子误报旧测试占位值阻止；将该占位值改为 `test-fresh`，保留迁移重启不重放场景，定向复验后重试 aic；未禁用钩子。

## CP2：独立纯规则核心

从 CP1 `32001ef` 建立 `codex/road-v09-cp2-core`。独立 Paper codec、Unicode 比较及错误类型，宿主薄重新导出保持调用链。根 Cargo workspace 统一锁文件，保存／恢复／云端运行代码未改。仅将宿主需要的 `code_sequence` 和错误构造器公开；JSON 字段及错误语义不变。黄金样本及 Unicode 表按原字节搬迁，不重生成。

独立核心测试 2 项通过、Python 黄金样本测试通过；依赖树不含 Tauri/Apple。逐项核对 Cargo 注册表依赖版本与校验和完全未变；黄金样本和 Unicode 表与 `deaece8` 字节一致。

完整 Cargo workspace 22 项通过（独立核心 2、宿主 20）；格式检查在新路径换行调整后通过，文档 86/14 和目录树 291 路径检查通过。CP2 工程完成，不证明新原生客户端或新 provider 验收。

## CP3：文档与开发工具

分支 `codex/road-v09-cp3-harness`，从 `2c7dbe6` 开始。三项工具问题均按原定范围修复：历史引用改用保留快照；缺失根文档汇总报告后继续检查其他链接；TUI 排除生成的根 `CONTEXT.md`。README、SPEC、RULES、PROJECT 与手册入口统一 v08 中断、v09 工程重整及 v09.01 原生 iOS 的顺序；旧手册保留历史说明。

CLI 试点使用 `dsh headless`，独立工作区 `keikeu-v09-cli`，会话 `session-7a656ed7-dba6-4ca0-bac9-5b218607d22f`。输入仅限测试修复说明及指定仓库文件，禁止提交、安装依赖、私有数据与进一步委派。返回只改 `tests/test_build_context_pack.py` 两个路径字符串；主代理核对完整差异和工作区状态后集成。CLI 报告 6 项通过，主代理实际复测三组工具测试 20 项通过、全 Python 302 项通过。回执未提供可核实的具体模型版本，不能声称验证了 DeepSeek v4.1 Flash。

文档检查 86 active／14 required 通过；目录树 292 个路径、搜索／展开／切换校验通过；`git diff --check` 通过。未改产品行为；原生 Mac 冒烟留给 CP4，旧 iCloud／设备记录未重跑。

## CP4：整体验证与转交

分支 `codex/road-v09-cp4-handoff`，从 CP3 `a637e15` 开始。2026-09-20 完成。补充一处隔离修复：仅 `app.keikeu.desktop` 可沿用正式桌面的旧状态；其他 bundle identifier 均将 `--state-directory` 指向自己的应用数据目录。旧 v08 候选路径行为保持，v09 调试包不再意外继承日常 Vault。未改正式配置、依赖或业务文件格式。

### 实际工程检查

- Python 全量 302 项通过（CP3 最终 Python 状态，此后未改 Python）；独立状态与 Home 边界定向回归 1 项再次通过。
- Rust workspace 22 项通过；`cargo fmt --all -- --check` 通过。
- Vitest 142 项／10 文件通过；Vite 生产构建与最终 Tauri debug app 构建通过；compileall 通过。
- sidecar 使用 CP1 的独立环境与新路径产物；模块来源已核对。最终包实际启动并完成往返，旧工作区产物不作证据。
- 构建保留 3 个既有 debug smoke 未使用函数警告；未新增警告修复范围。Windows、新原生 iOS、iCloud provider 和外部编辑器集成未在本轮实测。

### Mac 原生合成数据冒烟

平台为 Apple Silicon Mac／macOS 27；Node 22.23.2、npm 10.9.8、Rust 1.88.0、Python 3.13.15。以绝对路径启动本工作区 `target/debug/bundle/macos/keikeu v09 Smoke.app`，标识 `app.keikeu.v09smoke`。合成 Vault 位于忽略的 `tests/test-vault/v09/native-vault`；独立状态位于该标识的 Application Support 目录，未改变正式选中 Vault。

| 操作 | 实际结果 |
| --- | --- |
| 启动与隔离 | Core 就绪，进程实参确认为独立 `--state-directory`，未读取正式选中 Vault |
| 创建、保存 | 在原生窗口创建 `K-20260920-001`，保存标题、页标题、Tags 和多语言正文，界面与磁盘对应 |
| 检索与重开 | Library 搜索 `STRASSE` 找回合成稿；重开原文完整；此输入同时含 STRASSE，不单独证明 ß 折叠，折叠由核心测试证明 |
| 未保存离开 | 修改名称后点击 Library，出现保护确认；选继续编辑后名称仍在 |
| 普通退出保护 | 同一未保存修改下 Cmd+Q 出现确认；取消后仍在，保存后 Cmd+Q 正常退出 |
| 重启持久性 | 重新启动同一包，Library 找到相同编号；韩文搜索命中，重开标题／页标题／Tags／正文完整 |
| 收尾 | 正常退出后确认 app 和 sidecar 均不存活；日常配置与状态摘要与启动前一致 |

首轮临时调试签名配置开启 Hardened Runtime，PyInstaller 内部 Python 库签名不匹配导致启动阻塞；只将忽略的 smoke overlay 设为 ad-hoc 签名、`hardenedRuntime: false` 后重新构建，最终包通过。没有改生产签名设置，也不据此声明可分发、公证或 Hardened Runtime 兼容。界面工具首轮锁屏由用户手动解锁；批量输入曾出现键入／剪贴板竞态，逐字段重新核对后才保存，磁盘断言确认无无关剪贴板文本。该冒烟不替代物理键盘 IME 验收。

### 源码与包绑定

最终包源码是 `a637e15` 加本 CP 的 `bridge.rs` 两行隔离差异；其余 CP4 变更为交接与证据文档。忽略目录保留源码逐文件摘要、包逐文件摘要及去标识回执。下面的 manifest SHA-256 对应按路径排序后的 JSON 字节。

- 源码清单：`808e4f87afbb24a764b9417c81be219b6e2738dbeb0bc0ab20b652c59322344e`。
- 包清单：`29b02d053ae8aa00cc519440d60d85ed7bba00ac0c7637dd56980b3523bae3a5`。
- 宿主可执行文件：`57b332935ea86fdea40cce592ad401ba90f5e00d8215d962ed99f3529a87f0cb`。
- sidecar：`e0e1f938aea6f1bc188495054d04514dce6651aa5421503ba7cd725f1be1ac6f`。

### 接受与转交

CP4 的工程检查及原生合成场景均完成，按事先批准的全计划 YOLO 接受 v09 工程范围；独立收口快照在 CP4 提交之后保存。文档检查 87 active／14 required、目录树 293 路径及搜索／切换、差异检查均通过；最终 CONTEXT 路由在收口提交后刷新。

[v09.01 清单](../../road-v09-01-handoff.md) 已列出接口冻结、运行核心与 Apple 适配拆分、本地 SwiftUI、双端失败恢复及验收顺序。v08 仍为中断／转交，B14 未验；没有推送、发布、外部 Alpha 或 v09.01 实施。合成 Vault、测试包、独立状态及 CLI 隔离补丁留在本机，未删除原工作区。
