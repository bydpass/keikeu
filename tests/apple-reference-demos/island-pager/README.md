# Ref Island Build 6–9：灵动岛自动分段与融合实验

Road v00.09.01 隔离实验，非产品实现。2026-09-29 用户把所有路线的目标从“持续显示参考”改为“**可以快速被调出＋查看**”；本版回答：长按灵动岛展开后，参考能否不溢出、按钮完整、逐段翻完一份长文。

## 边界

- 独立目录与 XcodeGen 规格；只读引用上级 `Sample.swift` 与 `Icons/Island.xcassets`，Build 5 的源码、工程与包不修改。bundle ID 沿用 `app.keikeu.refisland`，安装会替换设备上的 Build 2（其包留在忽略目录 `build-2/`）。
- 活动类型名 `ReferenceAttributes` 与 Build 2 相同，状态只保留 `page`（现为段序号），旧活动仍可解码。
- 只用合成文本：共享三页、一段合成长段落、一页合成手动切点。不读 Vault、不保存输入、不联网、无推送。

## 分段规则（用户 2026-09-29 定义）

岛内没有滚动容器，“组件内滚动”改为事先切段、按段翻。规则在 [`Segments.swift`](Segments.swift)：

| 切法 | 规则 |
| --- | --- |
| 手动切点 | 仅“进一步”模式（见 [SPEC](../../../docs/SPEC.md)）：用户在光标处打标记；相邻标记间文字不得超过展开岛的最大行数，否则整组打回并提示超出的段号与行数。实验中以文内 `｜` 代表已保存的光标标记 |
| 自动切点 | 要渲染的文字若溢出，在最近的未溢出标点后截断；换行本身是切点；可达范围内没有标点时在上限处硬切 |

手动标记被打回时退回自动切点。行数按字宽估算：每行 44 个半角单位（中文 2），每段最多渲染 3 行（`renderLines`），岛内显示区仍预留原先的 4 行（`displayLines`），多出的一行吸收估算误差；这是针对 iPhone 17 Pro footnote 字号的估计，未做真实排版测量。

## 布局

- 展开态：‹ › 翻段按钮放在摄像头两侧（leading／trailing），中间一行显示“参考 页 · 段”，下方整块只放正文，固定预留 4 行显示区，每段文字只占 3 行。
- 紧凑态：图标与“页·段”；最小态：页码。锁屏：按钮与标签一行，正文区同为 4 行。
- App 显示用法提示、手动切点接受／打回状态和全部分段预览。

## iOS 15–27

| 部分 | 最低版本 | 旧版表现 |
| --- | --- | --- |
| 宿主 App（提示与分段预览） | 15.0 | 可安装 |
| Live Activity 与岛内按钮 | 17.0（Widget 扩展部署版本） | iOS 15–16 只显示预览及原因 |
| 灵动岛 | 带岛机型 | 无岛机型只在锁屏显示 |

实测设备只有 iPhone 17 Pro／iOS 27.0；其他版本只证明编译。

## 构建、检查与签名

```sh
rtk proxy xcrun swiftc -swift-version 6 tests/apple-reference-demos/Sample.swift tests/apple-reference-demos/island-pager/Segments.swift tests/apple-reference-demos/island-pager/check.swift -o tests/test-vault/reference-demos/island-pager/segment-check
rtk proxy tests/test-vault/reference-demos/island-pager/segment-check
rtk proxy xcodegen generate --spec tests/apple-reference-demos/island-pager/project.yml --project-root tests/test-vault/reference-demos/island-pager --project tests/test-vault/reference-demos/island-pager
rtk proxy xcodebuild -project tests/test-vault/reference-demos/island-pager/ReferenceIslandPager.xcodeproj -scheme RefIsland -configuration Debug -sdk iphoneos -destination generic/platform=iOS -derivedDataPath tests/test-vault/reference-demos/island-device/build6 build
```

签名沿用 wildcard 开发 profile（路径记录在忽略目录 `island-device/profile-path.txt`，设备信息在 `island-device/device-details.json`）：先签扩展内 dylib 与扩展，再签宿主 dylib 与宿主，strict／deep 验证。签名包在忽略目录 `island-device/build-6/`–`build-10/`，摘要 `island-device/refisland-build{6…10}-packages.json`。

## 真机最短 SOP

前提：在旧 Ref Island 中先点“结束本 Demo 的参考”；不操作真实 Vault，不改操作按钮。

1. 打开 Ref Island → 开始参考 → 切到 Ref Editor，唤起惯用中文键盘。
2. 长按灵动岛：记录正文是否完整、有无溢出，‹ › 是否完整可点。
3. 连按 › 翻完 13 段（Build 8）：第 3、4 页应分段，第 4 页每段在逗号后结束，第 5 页按手动标记分 3 段。
4. 点输入区继续输入，再长按调出：记录“调出＋查看”是否顺手。

## 2026-09-29 真机结果（iPhone 17 Pro，iOS 27.0）

- Build 6（4 行）：用户实测评价“这个试验方案简直完美”；仍有一点溢出。
- Build 7 把分段与显示区一并砍到 3 行：**用户判定此改法不对，已回滚。**
- Build 8（用户指定改法）：渲染文字限 3 行，显示区上限仍为原先 4 行；13 段。已签名验证、替换安装并启动（设备显示版本 8）。**用户确认不再溢出，定为首选路线。**
- 一碰输入区或键盘岛即收起，属系统行为；按新目标“快速调出＋查看”，长按重新调出即可。

## 融合评估（Build 9 起实施，见下节）

- 旧融合（灵动岛按钮唤起系统 Snippet）两种衔接均已真机失败，不再重试。
- 按新目标可行的组合：灵动岛作 3 行速览；用户主动绑定的操作按钮 → Snippet 作长段查看（最高 400pt）。Snippet 动作在主 App 进程运行，可读当前活动的段序号，两边共用同一套分段与阅读位置，无需 App Group 或推送；分段也替代了 Snippet Build 4 失败的卡内滚动。
- 代价：卡片遮挡编辑正文（Build 4 实测）；操作按钮只能用户主动 opt-in。用户随后要求实验，以确定可行性与性能。

## Build 9：融合实验（2026-09-29）

同一 App 内两个入口共用一个阅读位置（岛的段序号）：

| 入口 | 实现 | 系统门槛 |
| --- | --- | --- |
| 灵动岛速览 | Build 8 不变；‹ › 为 `IslandStep` | iOS 17+，带岛机型 |
| 系统卡片长看 | App Shortcut（Build 10 起标题“Island Reference Card”、短标题“Island Reference”）→ `ShowIslandReference` 返回 `IslandReferenceCard`（SnippetIntent）；从岛当前段起连显同页最多 3 段，首段主色，其余次色；卡内 ‹ › 为 `CardStep`，同步写回岛 | iOS 26+ |

入口可为 Spotlight、快捷指令，或用户自行在系统设置中选择的操作按钮；本实验不修改操作按钮绑定。无岛运行时卡片用进程内位置。

性能证据：[`FusionLog.swift`](FusionLog.swift) 写 `Documents/fusion-events.jsonl`，只记事件、段序号与耗时，不记正文：`card_requested`（`hasActivity`）、`card_rendered`（自请求或翻段起的毫秒数）、`card_step`／`island_step`（写回活动耗时）；每条带 `sinceLaunchMs`（距进程内核启动时间），用于区分冷／热启动。取回：`devicectl device copy from --domain-type appDataContainer --domain-identifier app.keikeu.refisland --source Documents/fusion-events.jsonl`。日志计时只到视图构建，屏幕实际出现另凭观察。

已构建（App Shortcut 元数据含 `ShowIslandReference`、`CardStep`、`IslandReferenceCard`）、签名验证、替换安装并启动（设备显示版本 9）；**真机可行性与性能待测**。

### 真机最短 SOP（融合）

1. Ref Island → 开始参考 → 在岛上翻到 3.2（第 3 页第 2 段）。
2. 切到 Ref Editor，唤起中文键盘；从 Spotlight 搜“Island Reference”（或你自选的操作按钮）调出卡片。记录：卡片是否出现、是否从 3.2 起、出现快慢、键盘与输入是否保留。
3. 卡内点 › 两次，关卡后长按岛：岛是否在 3.4。
4. 在岛上翻一段，再调出卡片：是否从岛的新位置起。
5. 冷启动对照：在 App 切换器上划掉 Ref Island（活动保留）后再调出卡片，比较快慢。

### Build 9 结果与 Build 10 修正

用户回报 Build 9 卡片调用失败：Spotlight 搜出的是旧的“Show Reference”（Ref Snippet／Fusion 同名），不是新 Ref Island。设备日志 `island-device/events/fusion-events-1.jsonl` 只有 6 条 `island_step`（写回活动 3–4 ms，运行于 App 进程），无 `card_requested`：新入口从未被调用。Build 10 将标题、短标题与说法改为唯一的 “Island Reference”，并在 App 启动时调用 `updateAppShortcutParameters()` 请求系统重新登记；已构建、签名验证、替换安装并启动（设备显示版本 10），待复测。

### Build 10 真机结果（融合版定为首选）

用户实测 Build 10：卡片能调出。设备日志 `island-device/events/fusion-events-2.jsonl`（忽略目录，只含事件、段序号与耗时）：

| 指标 | 结果 | 样本 |
| --- | --- | --- |
| 卡片请求 → 首次视图构建（热进程，已运行约 103 s） | 65 ms；系统在 96 ms 内构建 3 次 | 1 次请求 |
| 卡内翻段写回灵动岛 | 2–4 ms（中位 2.5） | 6 次，均 `hasActivity: 1` |
| 翻段后卡片重建 | 14–20 ms | 6 次 |
| 岛内翻段写回 | 3–4 ms | 6 次（Build 9 时段） |

卡片窗口按规则变化：同页剩余段数为 1–3（日志 `segments` 1／3／2 交替）。**未取得的证据：**冷启动（无低 `sinceLaunchMs` 的请求）、岛→卡片反向同步（卡片后无 `island_step`）、本轮卡片与软键盘共存细节；计时只到视图构建，屏幕出现快慢凭用户观察。

用户决定：**融合版（灵动岛速览＋系统卡片长看，共用阅读位置）是更好的方案，定为首选**；本 Road 参考小窗探索收尾，准备新开 Road。
