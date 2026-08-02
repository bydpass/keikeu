# Road v0.6 实施计划（已批准；CP0–CP7 advance YOLO）

> 状态：依据已批准的 [Paper v4 产品与架构设计](docs/design/road-v0-6-paper-v4-design.md)
> 于 2026-08-02 重写；开发者于同日授权开始执行 Road v0.6，并以 advance YOLO
> 预先覆盖 CP0–CP7 的开发者退出判断，随后以“全部 YOLO”预先授权 CP0–CP6 的分支、
> 精确暂存、DeepSeek `aic`、checkpoint commit 与连续执行。YOLO 不替代实际证据，也
> 不授权真实 Vault、push、tag、发布、closeout 或 CP7 commit。

## 0. Road 目标

Road v0.6 把产品从“编辑 Paper，再打开独立 Flashcard”重构为：

```text
灵感 → 直接编辑由有序卡页组成的 Paper → 整体保存 → 带着 Paper 离开
```

Road 完成时，正常 runtime 使用 Paper v4、Markdown schema v4 与 JSONL protocol v2；
独立 Flashcard 活动链退役。Vue 3 → Tauri/Rust → JSONL → Python Service/Core →
Markdown/Index/Vault 的进程架构不重写。

当前事实仍是 Road v0.5、Paper v3、protocol v1 与独立 Flashcard。CP0–CP3 只能建立
target 契约、additive Core 和 development-only UI；production 必须继续完整启动 v0.5。
CP4 才允许一次性完成 v2 垂直切换。

## 1. 权威、批准与执行纪律

- 产品与架构 target 以
  [`docs/design/road-v0-6-paper-v4-design.md`](docs/design/road-v0-6-paper-v4-design.md)
  为准；本计划只安排顺序、证据和 Gate，不另造第二份 schema 或 protocol 权威。
- 在 CP0 校准前，[`docs/SPEC.md`](docs/SPEC.md)、[`docs/RULES.md`](docs/RULES.md)、
  `src/` 与 `tests/` 继续描述或证明 v0.5 current；target/current 不得混写。
- 开发者已审阅实际计划并授权开始执行。批准状态必须写回本文件与 `docs/PROJECT.md`
  并形成干净基线提交，之后才能创建 CP0 分支。
- CP0–CP7 的开发者退出判断由 2026-08-02 的 advance YOLO 预先覆盖。每个 CP 仍须完成
  声明的实际证据且无未解决 P0/P1，并从前一 CP 已通过且已提交的 commit 建立
  `<content-type>/cp<N>-<slug>` 分支；证据未完成的 CP 不得播种下一分支。
- “全部 YOLO”预先授权 CP0–CP6 的 checkpoint commit 与后续分支；每次仍须精确暂存、
  审阅 staged diff、确认无秘密/作者内容，并使用已批准的 DeepSeek `aic`。真实 Vault、
  push、tag、发布、closeout 与 CP7 commit 仍分别授权；提交不自动授权 push。
- 每次编辑前执行 Git Gate，点名 dirty 路径与混合风险；提交前精确暂存、审阅 staged
  diff、确认没有秘密或作者内容，并按 `docs/RULES.md` §7 使用 `aic`。
- 每个 CP 只修当前范围的 P0/P1。P2/P3 进入候选池，不扩张本 Road。

## 2. 全局工程与数据边界

### 2.1 架构与范围

- Vue 只拥有可见交互、draft、baseline、活动页与 App 根 pending intent。
- Tauri/Rust 只拥有 sidecar 生命周期、单队列、JSONL 请求匹配和原生 picker/open/reveal。
- Python Application Service 是唯一编排与 mutation 入口；Core 拥有领域校验和纯转换。
- `markdown_io.py` 独占 Paper Markdown；`indexer.py` 只生成可重建投影；`vault.py`
  独占路径校验和 destructive filesystem 规则。
- 不新增依赖、Router、Pinia、TypeScript、UI kit、数据库、文件 watcher、网络、账号、
  遥测、AI、远端 Agent、逐页协议、自动保存、页面重排或单页 deep-link。
- 不顺手重写 `vault.py`、`migration_v01.py`、sidecar worker 或大型 Vue 文件；先复用
  现有 helper 和现有 `?prototype=1` development-only 入口。

### 2.2 作者资产与迁移

- Markdown 是作者权威；Index 和设备状态可删除重建。不得静默删改、修复、规范化、
  上传或在日志/证据中回显作者正文。
- v2/v3 → v4 唯一获准丢弃的作者字段是 `initial_summary`。备份保留它；报告只记录
  每文件存在该处置，不记录内容或长度。
- legacy Tag 若含多行、控制字符、空项、外围空白，或 trim 后发生重复，迁移预检必须
  阻塞并要求用户按旧格式人工修复。迁移不得借 v4 的正常 trim/丢空/去重语义静默改变
  旧字段。
- raw loss-audit 必须让每个 legacy source byte 恰好属于已知结构、明确映射字段或
  `initial_summary`；任何歧义或未归属字节使整次预检 `ready=false`、零写入。
- v0.1 → 冻结 v3 与 v3 → v4 是两个独立 Gate，各有 token、确认、备份、报告和失败
  语义；中间 v3 不进入编辑、每日卡 claim 或 v4 Index rebuild。
- CP1–CP6 只使用 tests、fixtures、合成 Vault 或完整副本。任何真实 Vault、selected
  Vault 配置、持久应用状态或真实迁移都需事前披露准确影响并取得单独授权。
- 真实迁移的完整备份必须位于 Home 下但 active Vault 之外；在替换任何源文件前，
  必须完成 regular-file manifest 与逐字节验证。备份不由本 Road 自动删除。
- mixed schema 时禁止编辑和 Index rebuild；启动只读扫描 active、一级 folder 与 Trash，
  重新确认后才续迁。未知 schema、symlink、特殊文件或损坏旧 Paper 阻塞整次迁移。

### 2.3 保存、Index 与未知结果

- Save 是一份 Paper 的整体 CAS；不增加 `page.add/delete/split` 或逐页 mutation。
- Markdown 已安全替换但 Index 失败仍返回保存成功与 `index_degraded`；Vue 建立新
  baseline，禁止重发保存，只能显式 rebuild 并由 Python 完整校验 Index。
- durable mutation 只发送一次。越过主 commit boundary 后无法证明结果时必须提升为
  `commit_unknown`，不得伪装成普通可重试错误。
- `paper.save` 的 App 根 intent 保存完整 submitted/baseline；其他 intent 不复制作者
  正文。组件卸载、runtime Gate 或 sidecar 重启不得清空 intent。
- `vault_locator` 由 Python 签发并绑定配置路径与 pinned root identity；Vue/Rust 不解析、
  不记录、不猜 `cache/<code>.md`。locator 不匹配时零目标读取、零 token，进入 stale。
- pending intent 只驻当前 App 内存。强退或断电仍可能丢未提交 draft，是 v0.6 已接受
  上限；本 Road 不增加 operation journal 或持久恢复胶囊。

### 2.4 平台、工具链与明确排除

- 唯一工程与一号作者 Gate 平台是 macOS Apple Silicon；Intel Mac 明确不支持。
- iOS/iPadOS、Android/HarmonyOS、Windows、Linux、watchOS 与二号用户不进入本 Road。
- Developer ID、签名、公证、staple、DMG 与人工分发延至 Road v0.8。
- Node 锁定 `22.23.2`，npm 锁定 `10.9.8`；Python 遵守 `>=3.11,<3.14`，
  Rust/Cargo 继续锁定 `1.88.0`。
- macOS 27 / Xcode 27 beta 只可用于已批准的 Road v0.6 工程工作站，直到对应稳定版；
  不产生发布或兼容性声称，之后的大版本 beta 不自动获准。
- 不自动 push，不改 remote，不 tag，不发布，不恢复或使用已停用的公证凭据。

## 3. 证据分层与通用检查

以下结论必须分开：

| 结论 | 最低证据 |
| --- | --- |
| 代码已实现 | source inspection + focused tests |
| CP 工程完成 | 该 CP 全部检查、风险、下一 Gate 和开发者判断 |
| 合成/复制 Vault smoke | 实际 Tauri 平台流程记录 |
| 产品接受 | CP7 一号真实作者全部场景，无未解决 P0/P1 |
| Road closeout | CP7 通过并提交后，开发者另行授权 snapshot |

完整自动检查集合：

```bash
.venv/bin/python -m pytest
.venv/bin/python -m compileall -q src
.venv/bin/python scripts/build_sidecar.py
npm --prefix frontend run test
npm --prefix frontend run build
cargo test --manifest-path frontend/src-tauri/Cargo.toml
.venv/bin/python scripts/check_docs.py
git diff --check
```

每个 CP 只运行与风险相称的 focused subset，并在 Gate 前运行该 CP 规定的完整集合。
不得复制旧 pass 数；没有运行的测试、smoke、设备检查、备份或接受必须明确写“未运行”。

证据文件沿用现有结构：

```text
docs/acceptance/road-v0-6/
  README.md
  cp0-contract/report.md
  cp1-core/report.md
  cp2-migration-index/report.md
  cp3-ui/report.md
  cp4-runtime/report.md
  cp5-cleanup/report.md
  cp6-safety/report.md
  cp7-author/report.md
```

只在对应 Gate 产生真实证据时创建目录和报告，不创建空文件夹。报告不包含作者正文、
真实路径、凭据、稳定设备标识、原始日志或完整 diff。

## 4. Checkpoint 总览

| CP | 分支 | 目标 | production 边界 |
| --- | --- | --- | --- |
| CP0 | `docs/cp0-v06-contract-baseline` | target 契约、HTML 图、工具链与 current/target 基线 | 仍为 v0.5 / v1 |
| CP1 | `core/cp1-paper-v4-core` | additive Paper v4 model 与严格 Markdown codec | 仍为 v0.5 / v1 |
| CP2 | `core/cp2-paper-v4-migration-index` | additive 迁移、loss-audit 与 Index v4 | 仍为 v0.5 / v1 |
| CP3 | `ui/cp3-paper-v4-development` | 合成 DTO 的 development-only 卡页与 Library Gate | 仍为 v0.5 / v1 |
| CP4 | `feat/cp4-runtime-v2-cutover` | 全栈 protocol v2 垂直切换 | 首次 production v4 / v2 |
| CP5 | `refactor/cp5-retire-flashcard-v3` | 删除不可达 Flashcard 与 v3 正常链 | 仅 v4 runtime |
| CP6 | `test/cp6-recovery-repair-gate` | 故障矩阵、人工修复手册与安全整合 | v4 候选 |
| CP7 | `test/cp7-real-author-gate` | 一号真实作者接受 | 可申请 Road closeout |

---

## 5. CP0 — 契约与基线

**分支：** `docs/cp0-v06-contract-baseline`

**进入条件：** 本计划已由开发者明确批准、批准状态已提交、工作树干净；从该规划
基线 commit 建分支。CP0 的开发者退出判断由本 Road 的 advance YOLO 覆盖。

**范围：** 把已批准设计落为 active target 契约，同时让 `PROJECT/src/tests` 明示
current v0.5；锁定 Markdown grammar、protocol v2 方法表、工具链、平台例外和排除项。

**主要文件：**

- `docs/SPEC.md`
- `docs/RULES.md`
- `docs/PROJECT.md`
- `docs/architecture/architecture.html`
- `docs/design/design.html`
- `docs/design/interaction.html`
- `README.md`、`README_EN.md`
- `frontend/package.json`、`frontend/package-lock.json`
- 新增 `docs/architecture/decisions/0006-road-v0-6-beta-engineering-exception.md`
- 新增 `docs/architecture/decisions/0007-paper-v4-schema-migration.md`
- `docs/acceptance/README.md` 与有证据后创建的 CP0 报告
- `scripts/check_docs.py` 仅在新 required file 或预算确实需要时修改

**顺序步骤：**

- [x] 运行 Git Gate，记录规划基线 HEAD、分支、dirty 与实际工具版本。
- [x] 列出 `SPEC/RULES` 中 frozen initial Summary、必填 Summary、Highlight、Flashcard、
      v3 schema 和 protocol v1 的冲突条款；逐项改为已批准 target，并保留 current 标签。
- [x] 在 `PROJECT` 保持 runtime v0.5 事实、下一 Gate 和 CP0 实施期间尚未完成的边界。
- [x] 以已批准设计 §4、§8、§11、§13 为唯一细节来源，核对 Paper v4 不变量、Markdown
      grammar、DTO、method classification、repair 与 unknown-result 所有权；不复制新规格。
- [x] 更新 architecture/design/interaction HTML，使 current v0.5 与 target v0.6 可视化并列；
      不伪造代码、测试或 smoke 证据。
- [x] 将 Node 锁定从 `22.23.1` 校准为 `22.23.2`，同步 package manifest、lockfile、
      README 与 PROJECT；不升级任何依赖。
- [x] 新建 ADR-0006，记录 macOS/Xcode 27 beta 仅限本 Road 工程、稳定版到来即结束、
      后续大版本 beta 不获继承，且不产生发布/兼容性声称。
- [x] 新建 ADR-0007，记录 Paper v4 权威页模型、`initial_summary` 唯一丢弃决定、
      legacy Tag 阻塞、备份后果与复核条件；不得把它扩张成普通保存时的删文例外。
- [x] 创建 CP0 evidence index/report，记录检查与未运行项，不记录本地敏感信息。
- [x] 审阅所有链接、术语、平台矩阵、排除项和最终 diff。

**自动检查：**

```bash
.venv/bin/python scripts/check_docs.py
git diff --check
npm --prefix frontend run test
npm --prefix frontend run build
```

另以只读命令记录 `node/npm/rustc/cargo/python` 版本。应用源码未改时不把旧 Python/Rust
pass 数复制为 CP0 证据；若 package metadata 变更影响构建，则补跑完整自动检查集合。

**退出 Gate（advance YOLO）：** 逐节确认 target/current、schema、protocol、HTML 图、
工具链、ADR、平台与排除项一致；确认 protocol v2 尚未激活。声明证据完成且无 P0/P1
时，CP0 由 advance YOLO 通过；其 checkpoint commit 已由“全部 YOLO”预先授权。

**明确排除：** 不改 Core、Service、Vue 业务调用方或 Rust policy；不启用 v2、不写 v4、
不迁移 Vault、不删除 Flashcard、不发布、不 push。

---

## 6. CP1 — Paper v4 Core（additive）

**分支：** `core/cp1-paper-v4-core`

**进入条件：** CP0 已由 advance YOLO 通过并提交；从 CP0 commit 建立干净分支。

**范围：** 以独立 target 符号加入 `CardPageV4`、`PaperV4`、
`parse_paper_v4_bytes` 与 `render_paper_v4_bytes`；实现领域不变量、严格 parser、canonical
renderer 和 golden fixtures。production 的 `Paper/Highlight`、v3 codec 与 import 不变。

**主要文件：**

- `src/keikeu_core/models.py`
- `src/keikeu_core/markdown_io.py`
- 新增 `tests/test_models_v4.py`
- 新增 `tests/test_markdown_v4.py`
- 仅在 golden bytes 确有价值时新增 `tests/fixtures/paper-v4/`
- CP1 报告与 `docs/PROJECT.md`

**顺序步骤：**

- [x] 先枚举 v3 export 与所有 production caller，记录当前 focused tests。
- [x] 添加独立 v4 model；实现至少一页、精确空白谓词、200 code point、非法字符、
      类型集合、最多一个 Summary、null/空名称与 Tags 规则。
- [x] 实现无 BOM UTF-8、统一 LF/CRLF、frontmatter scalar、精确外层结构与 strict failure。
- [x] 实现 page marker JSON、名称连字符 `\u002d`、正文保留 marker 前置反斜线的可逆
      round-trip；拒绝重复/未知 JSON key，不损失正文首尾空行。
- [x] 实现 Tags 最后一节、逗号普通字符、trim/丢空/首次去重和 canonical 输出。
- [x] 补齐正向 golden、损坏输入、任意合法模型的 render→parse 字段等价、
      parse→render→parse canonical 等价和 content 保真测试。
- [x] 检查 production import graph，确认 Service/Index/startup 仍只引用 v3 API。
- [x] 用隔离合成环境启动现有 v0.5 App，确认 protocol 仍为 v1。

**自动检查：**

```bash
.venv/bin/python -m pytest tests/test_models_v4.py tests/test_markdown_v4.py
.venv/bin/python -m pytest
.venv/bin/python -m compileall -q src
.venv/bin/python scripts/build_sidecar.py
.venv/bin/python scripts/check_docs.py
git diff --check
```

**退出 Gate（advance YOLO）：** 核对 v4 model、canonical Markdown 与错误边界；确认作者 content
保真、失败零写、所有 v4 符号 additive、production import 未变，v0.5 实际仍启动。

**明确排除：** 不实现迁移或 Index v4；不改 Service/DTO/protocol/Rust/Vue；不替换 v3
export；不触碰真实或复制 Vault；不新增依赖或顺手重构 v3 codec。

---

## 7. CP2 — 迁移与 Index v4（additive）

**分支：** `core/cp2-paper-v4-migration-index`

**进入条件：** CP1 已由 advance YOLO 通过并提交；production 仍完整使用 v3/v1。

**范围：** 新增独立 v2/v3→v4 迁移模块、raw loss-audit、schema scan、Index v4、全页
搜索、Trash 临时投影和 v4 Branch。所有 v4 mutation 只从 tests、fixtures 或副本调用。

**主要文件：**

- 新增 `src/keikeu_core/migration_v4.py`
- `src/keikeu_core/indexer.py`
- `src/keikeu_core/models.py`、`src/keikeu_core/markdown_io.py`
- `src/keikeu_core/vault.py` 仅复用或补齐必要的既有安全 primitive
- `src/keikeu_core/migration_v01.py` 仅做 frozen-v3 import 接线
- 新增 `tests/test_migration_v4.py`、`tests/test_indexer_v4.py`
- 既有 migration/vault/index fixture tests
- 仅按测试需要新增 v2/v3/v4/mixed fixtures
- CP2 报告与 `docs/PROJECT.md`

**顺序步骤：**

- [x] 为 v0.1 migrator 建立最小 frozen-v3 接线，先证明现有 fixture manifest 与输出不变。
- [x] 实现 active、一级 folder、Trash 的 no-follow schema scan 和 pure-v4/mixed/unsupported
      分类；不信任旧 Index version。
- [x] 实现独立 raw loss-audit：重复/无效 frontmatter、重复 section、游离文本、malformed
      Highlight、未归属 bytes 全部阻塞。
- [x] 实现 Summary/Highlight 映射、未知 frontmatter 保留、`initial_summary` 明确处置；
      多行/control/空/有外围空白/trim 后重复 legacy Tag 全部阻塞。
- [x] 实现全量 preflight、外置完整备份、隔离 staging、render→parse→字段等价、逐文件
      安全替换、去内容报告和中断续迁；备份必须位于 Home 下但 active Vault 之外，
      并在任何源替换前完成 regular-file manifest 与逐字节验证。测试只使用临时复制 Vault。
- [x] 实现 v0.1→冻结 v3→v4 的两段 Gate；不得在中间 claim、编辑或建 v4 Index。
- [x] 实现 Index v4 entry、全页本地 `search_text`、NUL 字段分隔、NFC/casefold 内存比较、
      类型值/中文标签搜索、第一页原文 preview、全 Index verify、坏 Paper 隔离和
      active-only 持久化；不可逆截行只由 Vue CSS 完成。
- [x] 实现 Trash 查询时 O(n) 临时投影；`search_text` 不落 Trash Index、不进 DTO。
- [x] 实现 v4 Branch 的 source snapshot、pages/Tags/frontmatter 保留、新 code/time/path，
      源变化或冲突时零创建。
- [x] 检查 production Service/startup/rebuild 仍调用 v3 API，并启动现有 v0.5 App。

**自动检查：**

```bash
.venv/bin/python -m pytest \
  tests/test_migration_v4.py \
  tests/test_indexer_v4.py \
  tests/test_migration_v01.py \
  tests/test_v01_fixture.py \
  tests/test_road_v03_fixture.py
.venv/bin/python -m pytest
.venv/bin/python -m compileall -q src
.venv/bin/python scripts/build_sidecar.py
.venv/bin/python scripts/check_docs.py
git diff --check
```

**退出 Gate（advance YOLO）：** 核对合成 preflight、阻塞报告、mixed 续迁、两段 v0.1 和 Index/Trash/
Branch 证据；确认失败时源 bytes 不变，唯一丢弃字段只有 `initial_summary`，production
仍为 v3/v1。

**明确排除：** 不接 startup/Service/DTO/protocol/Rust/Vue；不替换 active v3 Index；
不迁移真实 Vault、不删备份、不自动修复、不重写旧算法、不新增依赖。

---

## 8. CP3 — Vue v4 预备层（development-only）

**分支：** `ui/cp3-paper-v4-development`

**进入条件：** CP2 已由 advance YOLO 通过并提交；production 默认导航和 bridge 仍为 v0.5/v1。

**范围：** 复用现有 `?prototype=1` 与 `PrototypeView.vue`，以合成 DTO 驱动两块可由
CP4 直接接入的 Paper/Library 生产候选组件；完成交互和视觉 Gate，不创建 Router、
第二个 dev 入口或 Vault 写入链。

**主要文件：**

- `frontend/src/PrototypeView.vue`
- 新增 `frontend/src/PaperV4Workbench.vue`、`frontend/src/LibraryV4Projection.vue`
- 新增对应 focused `*.test.js`
- 新增 `frontend/src/PrototypeView.test.js`
- `frontend/src/App.vue` 仅在现有 dev-only 动态入口确需校准时修改
- `frontend/src/style.css` 仅在共享 token 确有复用时最小修改
- `frontend/src/App.test.js` 用于证明 production 默认路径不变
- CP3 报告、设计截图或去内容 visual evidence、`docs/PROJECT.md`

**顺序步骤：**

- [ ] 建立只通过 props/emits 接收数据与意图的 `PaperV4Workbench`、
      `LibraryV4Projection`；组件不 import bridge、不写文件，CP4 不得复制第二套 UI 逻辑。
- [ ] 由现有 `PrototypeView` 用无作者内容、无真实路径的合成 Paper v4/Library DTO 驱动
      两个候选组件，并醒目标注“不连接 Vault”。
- [ ] 实现外层只读代号、始终可编辑 Paper 名称、每行一 Tag 与中央大卡页。
- [ ] 逗号在 Tags 中只作普通字符；切换基础/进一步模式不清除隐藏类型，`null` 不显示标签。
- [ ] 实现始终可编辑页标题、正文、基础/进一步模式、类型标签与 Summary 唯一禁用说明。
- [ ] 实现页码真实按钮、光标首/中/尾、从未聚焦时正文末尾和选区截断；新页 null
      name/type，焦点进入标题。
- [ ] 实现删普通页、唯一页替换、确认与焦点；底部主操作严格只有保存/删除/加页。
- [ ] 实现内存 draft/baseline、整体 dirty、合成 Save、离开保护；`ui_key` 不进 DTO。
- [ ] 实现 Library 行、第一页预览、页数、页标题、Tags 与合成搜索；结果打开整份 Paper
      第一页，不做 deep-link。
- [ ] 合成显示 stale、两种 repair、index degraded 与 commit_unknown；不伪造 transport 恢复。
- [ ] 完成 `1220×780`、`920×680`、文本缩放、对比、Tab、Enter/Space、`Cmd+S`、
      类型原生方向键、加删页焦点和确认框 `Escape` QA。
- [ ] 用 200/201 个 astral emoji 验证名称按 Unicode code point 计数；不得用原生
      `maxlength` 或 JavaScript `.length` 提前拒绝 Core 允许的输入。
- [ ] 以默认 URL 启动 Tauri，确认仍进入 v0.5 production workflow、protocol v1 和 Flashcard。

**自动检查：**

```bash
npm --prefix frontend run test -- \
  PaperV4Workbench.test.js \
  LibraryV4Projection.test.js \
  PrototypeView.test.js \
  App.test.js
npm --prefix frontend run test
npm --prefix frontend run build
cargo test --manifest-path frontend/src-tauri/Cargo.toml
.venv/bin/python scripts/check_docs.py
git diff --check
```

**退出 Gate（advance YOLO）：** 实际核对两个窗口尺寸、键盘路径、分页/删页/标记/dirty；确认原型
零 bridge/Vault 调用，两个候选组件可由 CP4 接入而无需复制交互逻辑，production bundle
与默认导航仍是 v0.5。声明证据完成且无 P0/P1 时由 advance YOLO 通过，提交后才进入 CP4。

**明确排除：** 不改 Python、Rust policy、bridge contract 或 protocol；不接默认导航；
不删活动 Flashcard；不真实保存/迁移/写 Index；不新增依赖、自动保存、重排或 deep-link。

---

## 9. CP4 — protocol v2 全栈垂直切换

**分支：** `feat/cp4-runtime-v2-cutover`

**进入条件：** CP3 已由 advance YOLO 通过并提交；CP1–CP3 target tests 均通过；Node 实际为
`22.23.2`。CP4 的 breaking change 必须在一个 Checkpoint 内形成可启动完整状态。

**范围：** production 从 Paper v3/protocol v1 一次切换为 Paper v4/protocol v2；
同一 CP 激活 startup Gate、Service/DTO/protocol、Rust policy、Vue Paper/Library/Vault、
locator、pending intent、tagged repair、Index warning 与 `paper.reconcile_save`。活动
Flashcard 调用同时退役，实现文件留到 CP5 删除。

**主要文件：**

- CP1/CP2 的 v4 model、codec、migration、index 文件
- `src/keikeu_bridge/dto.py`、`service.py`、`protocol.py`
- `frontend/src-tauri/src/bridge.rs`
- `frontend/src/App.vue`、`PaperView.vue`、`LibraryView.vue`、`VaultView.vue`、`bridge.js`
- 对应 Python、Rust、Vitest
- CP4 报告与 `docs/PROJECT.md`

**顺序步骤：**

- [ ] 先按设计 §13.1 逐方法写 strict DTO、method classification parity 与 v1/v2
      mismatch failing tests；每个方法恰好属于一类，不能按前缀猜测。
- [ ] 接通 startup 全量 schema Gate，确保 scan 发生在每日卡 claim、Index load 和编辑前。
- [ ] 接通 v0.1→冻结 v3→v4 两段迁移；mixed 只进入续迁 Gate。
- [ ] Service 切换 `paper.create_draft/open/save/reconcile_save`、locator、target path、source
      digest、CAS、tagged repair、fixed save result 与 degraded warning。
- [ ] 接通 Library v4、active/folder/Trash、全页搜索、Branch 与完整 Index verify。
- [ ] Python protocol 与 Rust host 同时升 v2；方法恰好归入已批准分类，v1/v2 hello 错配阻塞。
- [ ] App 根在发送前保存所有 durable pending intent；Save 另存 baseline 与 submitted。
- [ ] 由 Startup/Migration/Library/Paper DTO 回显并核对同一 active locator；Vault preview
      使用 candidate locator，只有首次 initialize 尚不存在目标时允许 null。
- [ ] 把 CP3 已接受的候选组件接入 production Paper/Library，完成 dirty、离开、repair、
      degraded、commit_unknown 与关闭保护；不得另写第二套卡页或 Library 投影。
- [ ] 从 App/Library/Python protocol/Rust allowlist 删除活动 `flashcard.open`、导航和动作；
      暂不删除不可达实现文件。
- [ ] 运行 focused/full checks、构建 sidecar，再执行合成/复制 Vault Tauri smoke。
- [ ] 更新 PROJECT，明确 CP4 是首次 production v4，CP5 只做死代码清理。

**自动检查：** 运行 §3 的完整自动检查集合。focused tests 至少覆盖 protocol v2 hello、
strict DTO、method parity、v1/v2 mismatch、startup pure/mixed/repair、Paper save/CAS、两类
repair、Index degraded、locator、一份 App 根 pending intent、Library 全生命周期与活动
Flashcard caller 为零。

**Tauri smoke：** 只使用 fake Home/config 和合成或完整复制 Vault，完成启动、复制 v3
迁移、创建、分页、保存、重开、搜索、folder、Branch、Trash、restore、degraded rebuild、
sidecar restart、退出；检查 `1220×780`、`920×680` 和键盘核心路径。结束后清理临时
host/sidecar，不保留 production debug 入口。

**退出 Gate（advance YOLO）：** 核对最终 diff、方法表、DTO 与实际窗口；确认 production 启动、
迁移、保存、Library、Vault 与恢复可用，活动 Flashcard route/protocol 已退役，无 P0/P1。

**明确排除：** 不执行真实迁移；不删除不可达 Flashcard/v3 文件；不完成 CP6 全故障
矩阵；不加依赖/架构；不发布、移动端或 Intel Mac。

---

## 10. CP5 — Flashcard 与 v3 正常链清理

**分支：** `refactor/cp5-retire-flashcard-v3`

**进入条件：** CP4 已由 advance YOLO 通过并提交，production v4 已独立完成主流程；任何行为缺口
都退回 CP4，不偷渡到清理 CP。

**范围：** 删除不可达 Flashcard 页面/DTO/endpoint/Rust 分支与旧测试，删除 v3 正常
runtime import/export；保留 v2/v3→v4 migration 所需冻结 parser/model/fixtures 和历史说明。

**主要文件：**

- 删除 `frontend/src/FlashcardView.vue`、`frontend/src/FlashcardView.test.js`
- `frontend/src/App.vue`、`LibraryView.vue` 与相关 tests
- `src/keikeu_bridge/dto.py`、`service.py`、`protocol.py`
- `frontend/src-tauri/src/bridge.rs`
- v3 runtime exports/tests 与当前 docs
- CP5 报告与 `docs/PROJECT.md`

**顺序步骤：**

- [ ] 全仓列出 Flashcard/v3 活动定义与 caller，区分 runtime、legacy migration、manual 与 archive。
- [ ] 删除不可达 Vue 文件、import、destination、emit、按钮和旧测试。
- [ ] 删除 Flashcard DTO/deck/option、Service 方法、protocol endpoint 与 Rust 残余分支。
- [ ] 删除 v3 正常 runtime export/import 和只为旧 UI 存在的 compatibility；保留迁移 reader。
- [ ] 收紧 tests，证明 v4 runtime 与 legacy migration 各自仍有直接覆盖。
- [ ] 运行零引用 Gate、完整自动检查和最小 Tauri 导航 smoke。

**零引用 Gate：** 在 runtime source、活动 tests、当前 protocol 与权威 docs 中，
`flashcard.open`、`FlashcardView`、Flashcard DTO、`open-flashcard` 与 production
`destination="flashcard"` 必须为零。archive、迁移说明和手册中的历史对比不计失败。

**退出 Gate（advance YOLO）：** 确认 diff 以删除为主、没有新行为或顺手重写；确认 v4 runtime、
v0.1 两段迁移和 v2/v3→v4 tests 仍通过。运行 §3 完整检查与 Paper→Library→Paper→Vault
Tauri smoke。

**明确排除：** 不删 archive、legacy migration 或旧 fixtures；不重写 `vault.py`、旧
migrator 或大型 Vue；不做视觉润色、新功能、人工修复、真实作者或发布。

---

## 11. CP6 — 未知提交、人工修复与安全整合 Gate

**分支：** `test/cp6-recovery-repair-gate`

**进入条件：** CP5 已由 advance YOLO 通过并提交；正常 runtime 只剩 v4；全部故障实验只用 fixture、
合成 Vault 或完整副本。

**范围：** 完成 `commit_unknown`、locator、Index audit、其他 durable mutation 的故障
矩阵；完成两种 repair UI；交付并演练中文 HTML 人工修复手册；完成全套安全 smoke。

**主要文件：**

- App/Paper/Library/Vault/bridge 与 Rust bridge
- Python DTO/Service/protocol；Core/Index 只在暴露根因时最小修正
- 对应 Python/Rust/Vitest
- 新增 `docs/manual/paper-v4-repair.html`
- `docs/manual/README.md`
- CP6 报告与 `docs/PROJECT.md`

**顺序步骤：**

- [ ] 用现有 fake spawner、monkeypatch 与 fixture 建故障注入，不留下 production 开关。
- [ ] 覆盖 Save baseline/submitted/第三内容/损坏、首次目标、同 code 异路径、重复 code、
      已有目标消失 `missing_existing`、`code/created` 身份变化 `identity_changed`、
      invalid submitted、locator/config/root identity 变化、strict tagged DTO 与全 Index
      stale/extra。
- [ ] 证明 App 根快照跨 PaperView 卸载、runtime blocked、sidecar restart 和关闭请求存活；
      原 Save 只发送一次。
- [ ] 在 Paper 替换、Library/Vault 路径变化、迁移第 N 文件、Index 替换和 response
      serialization 后注入失败；结果不得降级为普通可重试错误。
- [ ] 覆盖 mutation timeout、EOF、错误 response ID 与无效响应：均须只发送一次并成为
      `commit_unknown`；只读恢复调用的响应丢失不得误报 `commit_unknown`。
- [ ] 验证 migration、Vault/config、Library path mutation、Index rebuild 各自的只读恢复
      入口和“绝不自动重放”。
- [ ] 验证普通 open repair 不建半成品；unknown-save repair 保留 submitted/关闭保护；
      Finder、复制草稿、重新检查和 Index rebuild 可达且不回显正文。
- [ ] 编写逐项满足设计 §12 的中文 HTML 手册：完整示例；frontmatter、page marker、
      `name/content/Tags`；三种类型值、中文显示名和 null/空值；两类 escape；UTF-8/换行；
      常见错误及错误信息含义；Finder、修复、重新检查和 rebuild；明确 App 不会自动
      改写损坏文件。
- [ ] 开发者仅对故意损坏的合成 Paper 或完整副本，完全按手册完成一次修复。
- [ ] 运行完整自动检查、sidecar build 与 Tauri 安全 smoke，删除临时故障入口。

**Tauri smoke：** fake Home/config 下至少完成一次 response-loss→restart→reconcile、四态
代表 UI、degraded→rebuild、非 Save unknown 不重发、Finder 修复复制 Paper、正常关闭
保护、两个窗口尺寸和键盘路径。自动化已覆盖的组合不强迫用 production debug 开关重复。

**退出 Gate（advance YOLO）：** 逐项核对故障矩阵、smoke 和手册；开发者能不依赖 agent 猜正文而
修复一份损坏副本；全部 P0/P1 已修复并复验。运行 §3 完整自动检查集合。

**明确排除：** 不损坏唯一真实 Vault、不开始真实作者 Gate、不加 journal/恢复胶囊、
自动修复或源码编辑器，不保留测试后门，不修 P2/P3，不发布。

---

## 12. CP7 — 一号真实作者 Gate

**分支：** `test/cp7-real-author-gate`

**进入条件：** CP6 已由 advance YOLO 通过并提交；候选 commit、完整自动检查、复制 Vault smoke 已
固定。任何真实 Vault 选择、备份、迁移或 config 变化先单独说明并取得授权。

**范围：** 一号作者用真实灵感完成创建、分页、删页、标记、保存、退出重启、Library
找回与继续编辑；记录去标识化结果、介入次数和 P0/P1。二号用户不参加。

**主要文件：**

- 有真实证据后创建 CP7 报告
- `docs/acceptance/README.md`
- `docs/PROJECT.md`
- 仅在发现 P0/P1 时修改最小源码与直接测试

**顺序步骤：**

- [ ] 重跑 §3 完整自动检查与 sidecar build，记录候选 commit、Apple Silicon 环境和
      启动方式，不记录私密路径。
- [ ] 开发者选择已有真实 Vault 或新 v4 Vault；已有 v3 Vault 必须先只读 preflight、
      在 Home 下但 active Vault 外创建完整备份并完成 regular-file manifest/逐字节验证、
      staging 验证，再单独批准迁移。
- [ ] 测试前只说明隐私、停止条件和不记录作品内容，不先做功能教学。
- [ ] 一号作者创建 Paper，编辑 Paper 名称、页标题和正文，在真实光标处分割新页，
      设置需要的类型，删除一页并确认，然后整体保存。
- [ ] 正常退出并重启，从 Library 搜索或浏览找回整份 Paper，打开并继续编辑。
- [ ] 只记录完成/未完成、犹豫点、介入次数、错误等级和脱敏原话；不记录正文、名称、
      Tags、路径或含内容截图。
- [ ] 不在唯一真实 Vault 故意制造损坏；repair 只复用 CP6 合成/副本证据。
- [ ] P0 立即停止写入并保留原 Vault/备份；P1 停止接受，先在 fixture/副本修复并重跑
      CP6 相关 Gate，再申请重试。
- [ ] 无 P0/P1 后完成报告；实际场景证据满足时，CP7 由 advance YOLO 通过。

**退出 Gate（advance YOLO）：** 必须确认哪里可写、如何分页/删页/保存；退出重开和 Library 找回符合
预期；无内容丢失、静默改写或危险继续；没有未解决 P0/P1。CP7 只证明一号作者接受，
不证明第二用户、多用户 MVP、移动端或市场匹配。

**明确排除：** 二号用户与全部非 macOS ARM 平台；签名、公证、staple、DMG、发布；
故意损坏唯一真实作品；收集作者内容；P2/P3 扩展；AI、同步、账号、遥测；自动 closeout、
tag 或 push。

---

## 13. Road 完成与独立 closeout

Road v0.6 只有在 CP0–CP7 逐项完成声明证据、由 advance YOLO 通过并提交、normal runtime 只使用 v4、活动/Trash
没有未处理旧 schema、Flashcard 活动链清零、修复手册演练完成、一号作者 Gate 通过且
无未解决 P0/P1 后，才达到“可申请 closeout”。

随后仍需开发者另行决定：

1. 是否创建 `docs/archive/snapshots/road-v0-6.html` 的独立 closeout 变更；
2. 是否提交该 snapshot；
3. 是否 tag；
4. 是否 push。

这些决定不产生签名、公证、DMG、移动端、二号用户或多用户 MVP 声称。

## 14. 已知风险与控制

| 风险 | 控制 |
| --- | --- |
| CP4 变更面大 | breaking contract 只能垂直切换；内部按测试顺序推进，但不提交不可启动半态 |
| legacy Tag 被归一化 | 迁移对空项、外围空白、trim 后重复一律阻塞，人工修复后重试 |
| `initial_summary` 丢弃后后悔 | 设计明确披露，真实迁移前完整备份；不扩张为其他字段 |
| 宽松 parser 吞字节 | 独立 raw loss-audit + 全量预检 + 零写入失败 |
| mixed schema 被误当 ready | startup 全路径扫描；迁移完成前禁止编辑与 Index rebuild |
| Index 被当权威 | 打开始终读 Markdown；Index 可删重建并完整 verify |
| `commit_unknown` 自动重发 | App 根 intent、只读对账、method-specific recovery，绝不 replay |
| 错 Vault 对账 | Python locator + pinned root identity；不匹配零目标读取 |
| 内存草稿遭强退 | 明示 v0.6 上限，正常关闭保护；无证据不加持久 journal |
| Flashcard 死代码残留 | CP4 清 caller/contract，CP5 删除不可达实现并执行零引用 Gate |
| 移动/发布范围回流 | 平台矩阵和 v0.8 延期每 CP 复核 |

## 15. 实施计划批准 Gate（已通过）

开发者于 2026-08-02 授权开始执行 Road v0.6，并确认：

- CP0–CP3 不切 production，CP4 一次完成 protocol v2 垂直切换；
- legacy Tag 的保守迁移阻塞规则准确，唯一获准丢弃字段仍是 `initial_summary`；
- CP4/CP5 的 Flashcard 退役顺序准确；
- CP6 的 unknown-result、repair 和人工手册 Gate 准确；
- CP7 只是一号作者 Gate，不含二号用户、移动端或发布；
- CP0–CP7 的开发者退出判断采用 advance YOLO，但实际证据不得省略；CP0–CP6 的分支、
  精确暂存、DeepSeek `aic`、checkpoint commit 与连续执行由“全部 YOLO”预先授权；
  真实 Vault、push、tag、发布、closeout 与 CP7 commit 仍分别授权。

批准状态形成独立干净基线提交后，Road v0.6 才能从该提交创建 CP0 分支。批准与
advance YOLO 不表示任何 CP 已开始或已有未运行的证据。
