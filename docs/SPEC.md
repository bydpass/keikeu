# keikeu Product Boundary

> 产品契约：Road v0.7 是已接受的桌面基线；§13 保留已实施至 CP5 的 v08 存储契约。v08 已中断转交；当前 [v09](road-v09.md) 只重整工程与纯规则核心，v09.01 再替换原生 iOS。当前进度与待验项见 [PROJECT](PROJECT.md) 及 [CP5 验收单](acceptance/road-v0-8/cp5-candidate.md)。本文以行为和验收条件描述产品，工作权限见 [RULES](RULES.md)。

Paper v4 语法、DTO、迁移及协议以 [Paper v4 设计](design/road-v0-6-paper-v4-design.md) 为准；桌面界面以 [App Shell 设计](design/road-v0-7-app-shell-design.md) 和下述 CP7／CP8 契约为准。2026-09-16 仅重写表达及校正当前／历史标签，既有产品判据保持。

## 1. Definition

keikeu 为单个同人作者提供私密、本地优先的写作前整理与专注工具。核心流程是：已有灵感 → 可编辑卡页组成的 Paper → 保存 Paper → 交给外部正文编辑器。作者带走的产物就是可读、可修复的 Paper Markdown。

## 2. Author control

- 作者选择 Vault、编辑内容和外部编辑器；应用按明确操作及保存契约处理文字。显示名、页面、Tags 和可保留的未知字段维持作者意图。
- Markdown 是权威资产，Index 为可重建索引，普通设备状态为辅助数据；本机恢复草稿按 §13 的持久保护契约处理。
- 完整文件夹回收先明确显示“全部内容”并取得确认；在 Trash 永久销毁需要第二次不可撤销确认。
- 已接受桌面基线在本地运行；候选的 iCloud Documents 由用户主动启用，范围见 §13。应用自建云服务、账号、遥测及作者内容的评分／训练需另行明确的产品决定。
- 损坏 Paper 保留原字节、说明错误并提供导出；可编辑打开以完整合法解析为前提。

## 3. Current runtime and accepted composition

已接受的 Mac 本地流程为 `Vue → Tauri/Rust → JSONL v2 → Python service/core → Paper v4 / Index v4 / Vault`。当前工程继承的 v0.8 候选在此基础上按存储选择路由：Mac iCloud 和 iPhone 本地／iCloud 使用 Rust Paper Core，云端增加 Apple 原生协调；Mac 本地全功能继续由 Python 承担。

桌面界面继承 Road v0.7 CP8：紧凑 App Shell → Paper／Library 日常位置 → Vault 环境或阻塞恢复入口。CP7 的整树生命周期见 §10，CP8 的响应式和原生输入要求见 §11。候选实现与产品接受分别由当前验收记录判定。

## 4. Current Paper v4 behavior (unchanged by Road v0.7)

- 一份 Paper 有稳定的可选显示名、有序 Tags 和至少一个有序卡页。
- 每页包含始终可编辑的可选标题、作者 Markdown 正文及类型 `summary`、`snapshot`、`whisper` 或 `null`。显示名分别为总结、高光、碎碎念；`null` 隐藏类型标签。
- 每份 Paper 最多一个 Summary，Snapshot／Whisper 页数不限。基本／进一步模式只改变呈现，标题、正文和隐藏类型保留。
- 每页保存时标题或正文至少一项含非空白字符；校验只判断合法性，正文按原文保存。
- Paper 名和页名仅裁去外侧空白，空值存为 `null`，最多 200 个 Unicode 码点，拒绝控制、代理及行分隔字符。
- Tags 为单行值，逗号可作为内容；正常 v4 编辑裁去外侧空白、去空项、按裁剪后值保留首个重复项，保留其余作者文字。
- 精确 frontmatter 标量编码、页面标记、可逆转义、Tags 语法与严格失败行为见 [设计 §8](design/road-v0-6-paper-v4-design.md#8-markdown-schema-v4)。

## 5. Accepted interaction baseline (unchanged by Road v0.7)

- 默认直接编辑一个大卡页，Paper 名和当前页标题在两种模式下都可修改。底部三个主动作是保存、删除、加一页。
- 加一页按真实光标／选区拆分：当前页保留前缀，后缀移入新建的无标题／无类型页，焦点转到新页标题。正文尚未取得焦点时在末尾拆分。
- 删除经确认后移除当前页；删除唯一页时替换成一张空白页。页码按钮按既定顺序切页。
- 保存是整个 Paper 的 compare-and-swap。Markdown 替换成功即推进基线，Index 更新失败按降级单独报告。
- 脏稿保护覆盖 Paper／Vault 切换、导航及正常关闭。已知失败保留输入；过期或结果未知的写入先只读核对。
- Library 表示整份 Paper，搜索全部页面，预览第一页，打开时定位第一页。搜索比较保持 NFC＋Unicode casefold 语义。

## 6. Recovery and migration

- `repair_required` 是带标签的成功领域结果；普通打开与未知保存分别拥有对应恢复状态，诊断只包含去标识错误。
- `commit_unknown` 冻结受影响的持久意图。`paper.save` 使用只读 `paper.reconcile_save`；其余变更使用各自定义的 refresh／inspect 核对。下一次写入由核对后的明确操作触发。
- `index_degraded` 表示作者文件变更已成功、Index 需要重建；保持已成功文件与新基线。
- v2/v3 → v4 迁移仅按已批准契约舍弃 `initial_summary`，其原件存在活动 Vault 外的完整备份中。
- 旧 Tags 出现多行／控制字符、空项、外侧空白或裁剪碰撞时，预检阻止迁移并报告原状。
- 迁移执行原始损失审计、完整预检、Home 内活动 Vault 外备份、常规文件清单及字节验证、隔离暂存、逐文件安全替换及混合格式恢复。
- 迁移、删除、恢复及故障验证先在 fixture、合成 Vault 或完整副本执行；真实 Vault 操作按单独授权范围实施。

## 7. Architecture boundaries

- Vue 管理可见状态、draft／baseline、当前页和 App-root pending intent；文件读写通过后端方法完成。
- Mac 本地的 Rust 宿主管生命周期、一个 Python sidecar、JSONL 队列、原生目录选择／确认和已验证系统动作。Python service 管编排和严格 DTO，`keikeu_core` 管纯领域与文件规则。
- Mac 本地 `markdown_io.py` 拥有编解码，`vault.py` 拥有 Home 包含关系、支持路径、活动／Trash 枚举、编号与生命周期。迁移模块管受 Gate 约束的备份、暂存和替换。
- iPhone／Mac 云端的 Rust Core 按 CP0 契约及 CP2 golden 结果拥有对应 Paper 能力；Apple 适配层管容器、身份及协调。桌面剩余能力移交以 §13 的独立对等和切换验证为前提。
- 产品通信范围为本机宿主／sidecar 及用户启用的系统 iCloud Documents。后端能力与协议显式声明，未知写入结果通过只读核对恢复。

## 8. Explicit exclusions and platforms

- Road v0.7 的验收平台为 Apple Silicon Mac，交付范围是既有桌面能力上的 App Shell 与响应式呈现。Flashcard 独立产出步骤及旧页面重排路径已随先前 Road 退役；当前页面操作以 §4–5 为准。
- v08 已中断转交。当前 v09 重整工程并独立纯 Rust 规则核心，v09.01 再实施原生 SwiftUI iOS。移动端采用原生语言与组件，尽可能复用 Rust；Mac 重构延后，Windows 保留 Vue/Tauri/Python 路线且适配另排。桌面对等、Python 退役、外部 Alpha 与 Android 原生实施独立排期，不占用旧草案编号。Intel Mac 不受支持；Linux、watchOS 未排期。
- 新增 AI 生成、正文编辑器、社区、数据库、应用自建服务、自动保存、页面重排或技术栈替换属于产品扩展，使用单独提案和明确批准。
- 2026-09-07 从 `3c387c5` 在独立 worktree 重新实施，用户授权 CP0–CP5 工程、提前 YOLO 和本地 checkpoint 提交；该 v08 历史证据以当次实施记录为准。
- [App-root 关闭保护](acceptance/close-guard-2026-09-04.md) 在 2026-09-05 独立获得开发者普通退出接受；强制退出按最后成功落盘修订恢复。
- Mac／iPhone 个人 debug 候选已经本地签名、打包和安装。对外 Developer ID、公证、staple、DMG、TestFlight、发布与推广使用独立 Gate。旧 Phase 7.5 iOS 分支保留为历史试验。
- `./dev`、人工手册和 `CONTEXT.md` 服务开发工作流，其结果按各自用途解释。

## 9. Accepted Road v0.7 App Shell baseline (CP6 passed; CP7 override in §10)

- Paper 和 Library 是同级日常位置；Vault 为环境入口，正常时安静呈现，选择、迁移、修复、未知提交和 sidecar 故障时提供完整处理面。
- 紧凑 Shell 显示产品、当前位置、新 Paper 和 Vault。CP7／CP8 的侧栏、主结果流和顶层 Popover 延续下面两节契约。
- PaperView 拥有既有 dirty-departure 判据，App 编排导航意图和普通关窗保护。保存、危险动作和恢复入口在目标尺寸可见或可通过明确竖向滚动到达。
- 导航和动作具有语义名称、可见焦点、键盘路径、颜色以外的状态标识及减少动画行为。
- [v0.7 验收矩阵](design/road-v0-7-app-shell-design.md#141-road-v07-验收矩阵) 与 [CP6 作者 Gate](acceptance/road-v0-7/cp6-author/report.md) 保存接受证据。该次真实 Vault 授权已执行完毕；后续真实资产操作按本次精确授权判断。

## 10. Accepted Road v0.7 CP7 continuous-flow override

CP7 保留 Paper v4、Index v4、JSONL v2、DTO 和作者数据契约，调整 Vue 呈现与 Tauri 窗口，并明确批准三个 Python 文件夹生命周期方法的例外。

- Paper 形成连续竖向流程：上下文 → 页导航 → 当前页 → 动作。
- 默认窗口 `720×900`，最小 `720×680`，支持调整到横屏；`375×812` 在此阶段属于浏览器响应式证据。
- Tags 使用单行逗号分隔输入，Vue 以可逆 CSV 式引号保留字面逗号／引号；DTO 和 Markdown 延续有序 Tags 数组与 v4 bullet 语法。Library 在 IME 组合期间等待，确认中文后提交一次查询。
- Paper 详情和 Library 预览放在文档流外的原生 Popover；列表选择保持行与操作位置稳定。脏稿通过既有离开／新建／选库／关窗保护处理。
- Paper 名、页名用 Opus 衬线角色，其余控件和正文用系统无衬线；文本焦点安静，按钮／导航的键盘焦点清楚。生产元信息色为满足对比度的 `#5c6a71`，Figma 旧值为 `#627078`。
- 经确认的文件夹回收／恢复原子搬移包含未知和嵌套条目的完整树，目标冲突时整体拒绝。永久删除固定身份并做 symlink-safe 递归，拒绝不安全平台和挂载子树；不可逆阶段后若失败，已删除条目保持实际结果，剩余树恢复可见 Trash 名并报告失败。单 Paper、文件夹合并／改名沿用严格校验，详见 [ADR-0008](architecture/decisions/0008-whole-folder-trash-lifecycle.md)。
- 工程、Figma、隔离 Tauri 及两轮整改记录见 [CP7 报告](acceptance/road-v0-7/cp7-continuous-flow/report.md)。开发者于 2026-08-25 通过 Gate D，本地提交 `1e17cea`；原生候选窗口检查由 CP8 完成。

## 11. Accepted Road v0.7 CP8 responsive-navigation override

CP8 保留产品能力及数据／后端契约，调整呈现和导航；工程／Figma、原生物理键盘及开发者 Gate D 于 2026-08-26 完成，见 [报告](acceptance/road-v0-7/cp8-responsive-navigation/report.md)。

- 单行 `56px` Shell 顺序为 `编辑 Paper → 新 Paper → Library … Vault`，复用既有脏稿离开判据。
- 全部页按钮保留在 DOM 中的单行局部滚动轨道，约三个可见槽，细横向滚动条与 scroll snap。加载、直接选择、增加和删除居中活动页，保留 `aria-current`、焦点及保存锁；滚动限轨道内部，整份文档宽度保持视口内。
- 竖屏以 `height >= width` 和原生 `@media (orientation: portrait)` 判断，Markdown 高度为 `clamp(220px, 34dvh, 300px)`，长文在内部滚动；竖屏高度由布局控制，横屏保留竖向 resize。
- 竖屏 Paper 动作使用不透明、考虑安全区的底部 sticky Anchor，末行、错误和焦点保持可达。竖屏 Library 的“范围／排序”“新文件夹”使用等高 sticky Anchor 和原生 Popover，支持键盘、Escape、轻触关闭、焦点返回、失败保留输入、成功关闭；横屏保留侧栏、排序行和行内新建。
- 布局验证覆盖 `375×812`、`720×900`、`720×680`、`920×680`、`1220×780`，含 `1/3/4/6/7/12` 页、80 行正文、最大合法名称、局部滚动、安全区和 `document.scrollWidth <= clientWidth`。
- Figma Page `71:2` 在覆盖前保存 `CP7 Gate D accepted · before CP8 overwrite`，同页更新为 `CP8 · 响应式锚点与横向滚轮`，维持单个当前主版。
- 原生 IME 使用绝对路径 debug 候选、fake Home、含 Tag“暴食”的合成数据、macOS 简体拼音和物理键盘。候选窗口中断、中间拼音查询或重复最终查询按 P1 处理。
- CP8 源码、工程检查、原生观察和开发者接受各有记录，最终 checkpoint `2f03aee` 及 [快照](archive/snapshots/road-v0-7.html) 完成 Road 收口；验证使用合成资产。

## 12. Road v0.6 completed acceptance record

历史记录按 [v0.6 快照](archive/snapshots/road-v0-6.html) 读取：CP0–CP3 保持旧运行契约，CP4 激活 v4／v2，CP5 清理已确认不可达代码，CP6 验证安全恢复集成，CP7 取得真实作者接受。工程 YOLO、真实作者授权、产品接受、快照、tag、push 与发布按各自记录判定。

## 13. Documented unified-core target

[ADR-0009](architecture/decisions/0009-unified-rust-core-transition.md) 定义逐步 Rust 收敛及 ADR-0004 的条件替代。[历史 v08 计划](../PLAN_road_v0_8.md#0-先看我们正在改什么) 将工程、真实设备和 provider 验收分开。

| 环境／阶段 | 后端与边界 |
| --- | --- |
| v0.8 Mac 本地 Vault | JSONL Python sidecar，保留完整桌面能力 |
| v0.8 Mac 共享 iCloud Vault | 进程内 Rust Paper Core＋Apple 原生协调 |
| v0.8 iPhone 本地／共享 iCloud | 同一 Rust Paper Core；云模式增加原生协调 |
| 候选后的独立收敛 | 桌面剩余能力对等及安全切换验证通过后移交 Rust，退役 Python 产品运行时 |
| 首轮外部 Alpha 及后续 Android | 统一 Rust 产品 Core；Python 可继续作为开发比较工具 |

- CP2 已实现共享 Rust Core，CP3 已接入 iPhone 本地创作，CP4 已实现云路由和保全，CP5 交付同源码双端候选。工程记录见 [CP2](acceptance/road-v0-8/cp2-core.md)、[CP3](acceptance/road-v0-8/cp3-local.md)、[CP4](acceptance/road-v0-8/cp4-cloud.md)；当前必需证据见 [CP5](acceptance/road-v0-8/cp5-candidate.md)。
- iPhone 候选包含多页创建／编辑、保存／重开、列表／搜索、单 Paper Markdown 导出、本机草稿恢复和 Mac iCloud 往返。移动／云端采用窄能力集和可无 Index 的线性搜索；完整移动管理、全 Vault 导出与正式 iPad 验收属于后续独立范围。
- 保留 `bridgeRequest` 和 Paper v4 文件契约。宿主 capabilities、共享业务 DTO 与 host-only 方法依 [CP0 宿主契约](design/road-v0-8-host-contract.md) 冻结，Python JSONL v2 按原协议执行。
- 每个客户端的选定 Vault 只交由一个受控后端写入，失败保留后端与草稿供处理；跨设备并发仍需原生协调。
- 中英文初始跟随系统，用户可切换并保存在本机；作者文字、名称和 Tags 按作者输入保存。
- 默认本地；用户明确启用 iCloud 后创建／重连共享云 Vault，原本地库保留。切换前处理脏稿和未决写入，完整验证目标后更改选择；失败保留旧选择，旧请求结果只作用于原身份与代次。
- 草稿为私有、非正式、不同步的本机记录，按存储、Paper／草稿身份和修订隔离。已知保存成功只清对应修订，或由用户明确丢弃；较新、失败和未知保存继续保留。恢复写入失败明确报告，重启提供恢复、导出、丢弃；保证范围是最后成功持久化的修订。
- 区分替换前失败、写成但响应丢失、外部变化。未知结果先只读核对并保留草稿；完整持久化和读回校验每个冲突原字节后，才标记已处理。恢复为活动稿前保全被替换版本，使用安全 CAS。恢复中断保留既有副本，内容取舍由用户明确选择。
- 原生版本冲突与 provider 改名 sibling 都须支持发现、显示、完整保全、导出与明确恢复；文件名／code 不一致按原状展示，变更需明确选择。损坏副本提供原字节导出。
- 2026-09-07 用户批准 B10 按同编号新建的实际 provider 结果验收；两轮实际均为 sibling。原生冲突保全由 B09／B11 的已有稿并发编辑独立证明；“同编号新建产生原生冲突”保留为未观察到的证据边界。
- v08 未最终接受并已中断。B14 账号／容器不可用及 Drive 关闭后的恢复和重连要求转交 v09.01，不能因替换界面删除或标为通过。
- 独立收敛在 fixture／副本上保持桌面 Index、文件夹、Trash、迁移、恢复、设备状态及系统动作。功能对等、安全切换和开发者接受共同构成移除 sidecar／产品 JSONL／Python 打包以及首轮外部 Alpha 的前提。
- 移动端采用原生语言与组件，尽可能复用 Rust；Mac 重构延后，Windows 沿用现有技术结构。v09 重排目录与纯规则核心，v09.01 实施 SwiftUI；窗口、保存和平台语义保持既有安全契约。
- 外部 Alpha 的签名、公证、TestFlight 与真实分发检查单独排期；Android 原生实施、Windows 适配及 Python 产品运行时退役不属于 v09，不重分配未来版本号。
