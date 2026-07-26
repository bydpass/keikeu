# Road v0.4：Vue 3 + Tauri 前端替换

> 状态：**ACTIVE · CP9 implementation complete / awaiting developer review**
> 基线：`84efc7e9b718bf06a4e7a09bcd1443ae81a6f80e`（Road v0.3 已验收并归档）
> 日期：2026-07-25

## Summary

- Road v0.3 已完成 CP6 验收并归档；当前基线没有 v0.3 tag，也未 push。
- 新架构为 `Vue 3 + Vite + JavaScript → Tauri/Rust → JSONL sidecar → Python application service → 现有 Python Core → Markdown/Index/Vault`。
- 保持 v0.3 全部产品行为；Markdown、Home 路径保护、外部修改拒绝和迁移事务不变。
- 先从 Flet 层提炼与传输无关的 Python application service，并让现有 Flet UI 全部改走该边界；边界稳定后，Tauri/JSONL 再复用同一 service。
- Flet 在纵向迁移期间保留为已验收回退基线。Tauri 完成功能等价与真实作者验收后才删除 Flet UI、测试和依赖。
- Road 交付 arm64、macOS 13.3+、未签名 `.app`；工程迁移可先在当前稳定构建环境推进，只有在最老承诺系统完成构建与验证后，才宣称 13.3+。签名、公证、DMG、App Sandbox 和移动端另立 Road。

## Architecture and Interfaces

### 目录与依赖

- `frontend/`：Vue/Vite JavaScript、npm lockfile、`src-tauri/` Rust 工程。
- `src/keikeu_bridge/`：无 GUI 的 Python application service、DTO 与进程内 opaque handles；CP3 再加入 JSONL dispatcher，并把现有 handles 绑定 protocol session。application service 与 JSONL transport adapter 必须分开，`keikeu_core` 继续不依赖 Vue、Tauri、Flet 或 stdout。
- 迁移前先让现有 `keikeu_app` 调用同一 application service；Flet 页面不得继续保有另一套 Vault、保存、迁移或系统动作编排。
- 前端运行依赖只含 Vue 与 Tauri API；构建依赖为 Vite、Vue plugin 与 Tauri CLI；测试依赖为 Vitest、Vue Test Utils 与 jsdom。不加 Vue Router、Pinia、UI kit、图标库或网络 client。
- Rust 只用 Tauri、`tauri-build`、`serde`、`serde_json` 及官方 shell/dialog/opener plugin crates；Rust 标准库没有 JSON parser，因此协议解析不能省略 `serde` / `serde_json`。shell 不直接暴露给 Vue，且不安装未被 Vue 直接调用的 plugin JavaScript bindings。Vue 只能调用窄的 Rust commands，例如 bridge request、目录选择、validated open/reveal、runtime status 与 sidecar restart。
- PyInstaller 6.x 仅作构建依赖，具体 patch 版本写入构建 lock；生成 `keikeu-sidecar-aarch64-apple-darwin`。二进制与 `.app`、`node_modules`、Vite `dist`、Cargo `target` 全部忽略。Tauri 要求 external binary 使用 target-triple 后缀。([Tauri sidecar](https://v2.tauri.app/develop/sidecar/))
- 提交并固定 `.node-version`、`package-lock.json`、`rust-toolchain.toml`、`Cargo.lock`、`.python-version` 与 Python build lock；候选记录必须包含 Node/npm、Rust/Cargo、Python/PyInstaller、macOS、Xcode 和 target triple 的实际版本。

### CP0 依赖批准候选

以下精确版本已由开发者于 2026-07-25 批准。当前 macOS 27 / Xcode 27
beta 仅获准用于 CP4–CP12 工程构建；CP13 兼容验证不受该例外替代。

| 包与精确候选 | 用途 / 类别 | 为什么需要；更轻替代 | 移除范围；进入 `.app` |
| --- | --- | --- | --- |
| `vue@3.5.40` | UI runtime | 目标 UI 框架；原生 DOM 会把状态与表单编排重新手写 | `package.json`、lock、Vue source；是 |
| `@tauri-apps/api@2.11.1` | UI runtime | Vue 调用窄 Rust commands；手写 WebView IPC 不受支持 | `package.json`、lock、bridge client；是 |
| `vite@8.1.5` | build | Vue 开发与生产 bundle；手写模块构建不更轻 | `package.json`、lock、Vite config/scripts；否 |
| `@vitejs/plugin-vue@6.0.8` | build | 编译 Vue SFC；不用它只能放弃 SFC | `package.json`、lock、Vite config；否 |
| `@tauri-apps/cli@2.11.4` | build | 开发、bundle 和 Tauri config 校验；没有等价 stdlib 路径 | `package.json`、lock、Tauri scripts；否 |
| `vitest@4.1.10` | test | 与 Vite 同配置的组件/状态测试；Node 内建 runner 不处理 Vue SFC | `package.json`、lock、Vue tests/config；否 |
| `@vue/test-utils@2.4.11` | test | mount Vue 组件并触发用户动作；手写 DOM harness 更重 | `package.json`、lock、component tests；否 |
| `jsdom@29.1.1` | test | 为 Vue Test Utils 提供 DOM；浏览器 E2E 更重 | `package.json`、lock、Vitest environment；否 |
| `tauri@2.11.5` | Rust runtime | 桌面窗口、commands 与应用生命周期；自写 WebView host 更重 | `Cargo.toml`、lock、Rust host；是 |
| `tauri-build@2.6.3` | Rust build | Tauri build-time codegen；无受支持的手写替代 | `Cargo.toml`、lock、`build.rs`；否 |
| `serde@1.0.229` | Rust runtime | 强类型协议结构；手写 JSON 字段解析更危险 | `Cargo.toml`、lock、protocol structs；是 |
| `serde_json@1.0.151` | Rust runtime | JSONL 解析与序列化；Rust stdlib不提供 JSON | `Cargo.toml`、lock、protocol parser；是 |
| `tauri-plugin-shell@2.3.5` | Rust runtime | 作为 Tauri sidecar 启停打包后的 Python；通用 shell 权限不授予 Vue | `Cargo.toml`、lock、sidecar host/capability；是 |
| `tauri-plugin-dialog@2.7.2` | Rust runtime | 原生目录 picker；HTML picker 不能提供所需桌面目录语义 | `Cargo.toml`、lock、picker command/capability；是 |
| `tauri-plugin-opener@2.5.4` | Rust runtime | 执行 Python 已验证目标的 open/reveal；手写平台命令更脆弱 | `Cargo.toml`、lock、open command/capability；是 |
| `PyInstaller==6.21.0` | Python build | 生成随 `.app` 分发的 sidecar；要求用户另装 Python 不符合交付目标 | Python build lock/script；工具否，生成的 sidecar 是 |

候选版本来源为各包的 npm、docs.rs 与 PyInstaller 稳定发布页。正式批准时仍需在稳定工具链上复查相互兼容性；模板额外生成的包一律删除或另行批准。

### JSONL 协议

每行一个 UTF-8 JSON 对象：

```json
{"v":1,"id":12,"method":"paper.save","params":{}}
{"v":1,"id":12,"ok":true,"result":{}}
{"v":1,"id":12,"ok":false,"error":{"code":"stale_snapshot","message":"…","recovery":"refresh"}}
```

- Rust 启动并拥有唯一 sidecar，使用串行请求队列；stdout 仅传协议，stderr 仅传不含作者内容的诊断。
- sidecar 启动后必须先完成 `system.hello` 握手，返回 `protocol_version`、`session_id`、`app_version` 与 `core_version`。版本不兼容或 stdout 被污染时，Tauri 显示阻塞错误页并禁止进入写入流程。
- Vault preview、Paper snapshot 和 migration preflight 等 opaque token 必须绑定当前 `session_id`；sidecar 重启后，旧 token 全部失效。
- 不启 localhost、HTTP、WebSocket 或后台服务。
- 不自动重试 mutation。若 mutation 已发出但 response 丢失，界面必须把结果标记为“提交状态未知”，要求重新加载磁盘状态确认；不得简单提示失败后鼓励用户再次执行。
- sidecar crash、EOF、超时和 response 丢失必须区分。读取请求可在明确安全时重新发起；mutation 不自动重试。
- v0.4 不实现未被当前界面消费的 server event；若后续真实流程需要进度事件，通过协议版本升级增加。
- 错误码固定为 `invalid_request`、`validation_failed`、`not_found`、`stale_snapshot`、`conflict`、`unsafe_path`、`preflight_blocked`、`operation_failed`、`sidecar_unavailable`、`protocol_mismatch`、`session_expired`、`commit_unknown`；Vue 不解析 Python 异常文本来决定流程。

### Python bridge API

- application service 必须与 JSONL 无关，可由 Flet adapter 与 JSONL dispatcher 共同调用；它不读取 stdin、不写 stdout，也不知道 Vue、Tauri 或 Flet。
- JSONL adapter 处理 `system.hello` 协议握手与 session 建立；application service 的启动入口只有 `startup.load`。
- Vault：`vault.inspect/open/initialize/relocate`。
- 迁移：`migration.preflight/run`。
- Paper：`paper.create_draft/open/save/soft_delete`。
- Flashcard：`flashcard.open`，由 Python 返回 Summary-first cards；卡片位置只留在 Vue 内存。
- Library：`library.query/rebuild` 及 folder、move、branch、Trash、restore、permanent-delete mutation。
- 系统动作：Vue 只提交 action 与 Vault-relative target；Rust 调用 `system.resolve_target`，在内部取得 Python 再次验证过的绝对路径并立即执行 open/reveal。绝对路径不返回 Vue，Rust 不提供任意 shell、任意路径 open 或通用文件读写命令。
- Vault preview、Paper snapshot、migration preflight 分别返回进程内且绑定 session 的 opaque token；Vue 永不持有 source bytes、root identity 或未知 frontmatter。
- `PaperDto` 包含相对 `path`、`edit_token`、code、display name、initial/current Summary、Highlights、Tags 和时间；未知 frontmatter 留在 Python snapshot 中保留。
- `LibraryView` 包含当前 scope、排序后的 entries、folders、Trash、index errors 和逐项 `OperationReport`。搜索、NFC+casefold 排序继续由 Python执行，避免 JavaScript Unicode 行为漂移。

## Implementation Changes

1. **v0.4 权威启用**
   - 以已验收并归档的 Road v0.3 为行为基线，不重开或改写历史验收。
   - 接入本 Planbook、理解优先规约和 Road v0.4 ADR，修改 RULES 的固定 Flet stack，明确 Tauri/sidecar、无网络和 Flet 退场条件。
   - HTML architecture/design/interaction 在并存期间明确标注 current Flet 与 target Tauri，切换后再校准为单一事实。

2. **Application boundary、Tauri 基础与视觉确认 gate**
   - 先从 Flet 页面提炼 transport-agnostic Python application service 与 DTO；让现有 Flet UI 全部改走该 service，并通过原有 smoke 与测试，随后才建立 JSONL dispatcher。
   - 用官方 Vue + JavaScript + npm 模板建立 `frontend/`；bundle identifier 为 `app.keikeu.desktop`，默认窗口 `1220×780`，最小 `920×680`，`minimumSystemVersion=13.3`。
   - 建立 Rust sidecar worker、协议握手、session 生命周期、请求队列、child cleanup 和阻塞错误页。
   - 先交付只使用合成数据的真实 Vue 组件样张；用户确认后冻结视觉方向、tokens 与布局规则，但完整视觉重建不得阻塞或掩盖功能等价迁移。
   - **Gate A · Platform parity：**先用稳定、朴素的工作台壳完成全部 v0.3 行为等价，不同时改变产品流程、字段结构或动作语义。
   - **Gate B · Visual reconstruction：**Gate A 通过后，再完整落地“编辑部工作台”、视觉层级、细节动效与组件修饰；用户反馈必须能区分行为问题和视觉问题。
   - 视觉采用“编辑部工作台”：72px 全局栏、260px 上下文栏、弹性主内容；启动/Vault/迁移 gate 使用全窗口布局。
   - Token：暖灰 canvas `#ECEAE4`、paper `#FFFEFA`、ink `#1E2523`、muted `#646B68`、deep-teal accent `#2E5D57`、oxblood signal `#9A4E3F`、rule `#C8C9C2`、danger `#A33E3E`、success `#2F6B50`。
   - 标题使用系统 serif，正文系统 sans，code/path 使用系统 monospace；无渐变、无卡片套卡、无外部字体或图片。记忆点为边注式 Paper code/path 与细窄校样线。
   - 仅亮色；支持 visible focus、`prefers-reduced-motion`、语义 HTML、文本换行和拖放菜单等价路径。

3. **纵向业务切片**
   - 切片开始前，Flet 必须已经通过新 application service 完成启动、Vault、Paper、Library、Flashcard、迁移和系统动作的现有行为；此 gate 用来单独验证新边界，不与 Vue/Tauri 同时调试。
   - 每个切片遵循 `application service command → JSONL contract → Rust request handling → Vue UI → Flet/Vue 对照验收`，不把多个页面一次性并行重写。
   - **Paper slice：**启动、每日卡、现有 Vault 打开、新建/编辑/保存、初稿副本、Highlight 排序、Cmd+S、软删除、外部移动/修改拒绝。
   - **Flashcard slice：**Paper selector、Summary-first、列表/左右键/跳页、Summary context、每次 page 1、返回 Paper。
   - **Library slice：**scope、搜索/排序、三栏上下文、损坏项、选择清空、文件夹与系统 open/reveal。
   - **Mutation slice：**move、branch、folder create/rename/merge、Trash/restore、逐项 partial result、永久删除门槛。
   - **Vault/migration slice：**原生目录选择、preview/init/switch、Home 外复制验证、v0.1 preflight/backup/staging/migration；所有危险动作保留明确确认和 busy 状态。

4. **候选、验收与退场**
   - 在 synthetic/copied Vault 上完成 Tauri 全流、Finder 外部移动、launch/relaunch、协议版本不匹配、sidecar crash/EOF、mutation response 丢失和生产 bundle smoke。
   - 工程迁移 gate 允许先在当前稳定 arm64 macOS 构建环境完成；macOS 13.3+ 是独立 release compatibility gate，不得反向阻塞 application service、JSONL、Tauri 或 Vue 的实现。
   - 用 arm64 macOS 13.3 环境构建并启动 `.app`，再在当前 arm64 macOS 27 复验同一产物；仅两端均通过才宣称 13.3+。PyInstaller 官方要求在最老支持系统构建以建立兼容性证据。([PyInstaller requirements](https://pyinstaller.org/en/stable/requirements.html))
   - 先完成 Gate A 的功能等价验收，再完成 Gate B 的视觉验收；两类结果分别记录，不能用“看起来更好”替代行为证据。
   - 用 Tauri `.app` 重跑去标识化真实作者场景 A/B，并新增三栏定位、视觉层级、键盘路径和外部编辑器边界是否清楚的记录。
   - 无未解决 P0/P1 且产品验收通过后，删除 `keikeu_app`、Flet builder tests、`flet` dependency 和旧 Python `keikeu` GUI entry；最终用户入口为 `.app`。
   - Flet 删除后重跑全量检查和一次 Tauri launch smoke；tag/archive/push 仍需单独授权。


### 执行 Checkpoints

- 每个 Checkpoint 使用独立分支 `codex/road-v04-cpN`；下一分支只从前一已验收并提交的 checkpoint HEAD 创建，不在一个分支混合两个 phase。
- **CP0（完成）：**启用 v0.4 权威文档与三张 map，记录当前工具链；依赖与 lockfile 获开发者批准后再冻结。
- **CP1（完成）：**提炼 transport-agnostic Python application service、DTO 与进程内 opaque handles。
- **CP2（完成）：**现有 Flet UI 全部改走 application service，并重跑 v0.3 测试与 smoke。
- **CP3（完成）：**完成 JSONL dispatcher、协议握手、opaque handle 的 session binding 与 contract tests。
- **CP4（完成）：**完成 Tauri sidecar 生命周期、串行队列、阻塞错误页和窄 Rust commands。
- **CP5（完成）：**Vue synthetic prototype 与自动检查已完成；开发者已确认并冻结视觉方向，进入 Gate A。
- **CP6（完成）：**Paper slice 实现、自动检查、隔离浏览器 QA 与复制 Vault `.app` smoke 已完成；开发者于 2026-07-25 确认验收。
- **CP7（完成）：**Flashcard slice、Vue 自动检查与隔离浏览器 QA 已完成；开发者于 2026-07-25 确认验收。
- **CP8（完成）：**Library read slice、自动检查与隔离浏览器 QA 已完成；开发者于 2026-07-25 确认验收并提交为 `f12374c`。
- **CP9（待确认）：**Library mutation、Vault 与 migration slice 已实现；自动检查与隔离浏览器 QA 已通过，等待开发者验收后提交。
- **CP10：**完成 Flet / Tauri 功能等价验收，通过 Gate A。
- **CP11：**完成完整视觉重建与独立视觉验收，通过 Gate B。
- **CP12：**完成真实作者场景 A/B 与生产 bundle smoke。
- **CP13：**完成 arm64 `.app` 和最老承诺系统兼容验证；通过后才宣称 macOS 13.3+。
- **CP14：**删除 Flet、校准文档并重跑全量检查；tag、archive、push 仍需单独授权。

## Test Plan

- Python：现有 Core 测试全部保留；CP1 覆盖 application service DTO、错误码、snapshot stale 与 Vault preview/confirm；CP2 覆盖 Flet adapter parity；CP3 覆盖 session-bound opaque token、协议畸形输入与 sidecar stdin/stdout。
- JSONL contract：覆盖 `system.hello` 握手、protocol mismatch、session 失效、ID 配对、stdout 污染、EOF/crash、read timeout、mutation response 丢失与 `commit_unknown`；测试必须证明 mutation 不会被自动重试。
- Vue：使用 Vitest + Vue Test Utils，覆盖 gate routing、表单错误保留、Flashcard reset/jump、Library scope/selection、永久删除门槛、键盘、bridge failure 和“提交状态未知”；不引入浏览器 E2E 框架。
- Rust：覆盖 request queue、握手、session 生命周期、非法 response、EOF/crash、退出时 child cleanup，以及 validated open/reveal；确认 Vue 无法调用任意 shell、任意路径 open 或通用文件读写。
- 手工 macOS smoke 覆盖 HTML drag、键盘菜单、目录 picker、Finder/open、默认与最小窗口，无横向溢出；不把 component test 当作平台证据。
- 固定检查命令：

```bash
node --version
npm --version
rustc --version
cargo --version
.venv/bin/python --version
.venv/bin/python -m PyInstaller --version
.venv/bin/python -m pytest
.venv/bin/python -m compileall -q src
npm --prefix frontend ci
npm --prefix frontend run test
npm --prefix frontend run build
cargo test --manifest-path frontend/src-tauri/Cargo.toml
npm --prefix frontend run tauri:build
.venv/bin/python scripts/check_docs.py
git diff --check
```

当前批准的 macOS 27 / Xcode 27 beta 工作站存在一个非候选构建限制：
Rust 1.88 在 Tauri 注入 `MACOSX_DEPLOYMENT_TARGET=13.3` 时无法加载 release
proc-macro。CP4 用一次性的 `minimumSystemVersion=11.0` CLI config override
验证了 arm64 bundle 与内嵌 sidecar；仓库正式配置仍为 `13.3`，标准
`tauri:build` 未通过，因此该临时 bundle 只算 CP4 工程 smoke，不算 CP12
production bundle 或 CP13 兼容性证据。

## Assumptions

- Road 名称为 v0.4；产品范围仍是 v0.3，不新增 AI、正文编辑、同步、账户、数据库或文件监听器。
- npm、JavaScript、单一 light theme、arm64 和 `app.keikeu.desktop` 已锁定；Node、Rust、Python 与构建依赖必须使用项目内版本文件和 lock 精确固定。CP4 的 Rust/Cargo 锁定版本为 `1.88.0`。
- `.app` 未签名、未公证、未启用 App Sandbox；Home containment 仍由 Python Core 强制执行。Tauri 可生成 macOS app bundle，但签名与 entitlement 是独立发行工作。([Tauri macOS bundle](https://v2.tauri.app/distribute/macos-application-bundle/))
- 用户会提供 arm64 macOS 13.3 构建/验证环境；缺少该环境时，架构与功能工程可以推进，但 13.3 兼容 gate 不得标为完成，也不得对外宣称支持 13.3+。
- Road v0.4 从干净的 Road v0.3 归档基线建立；后续 checkpoint 若出现既有 dirty 文件，仍按 `docs/RULES.md` Git gate 逐项确认。
