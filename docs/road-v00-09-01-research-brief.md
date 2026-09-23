# Road v00.09.01：手机编辑器调研委托

状态：2026-09-21 用户已交回 WorkBuddy 报告，完成首轮有限复核；报告可作为讨论输入，尚未作为选型依据接受。

## 产品背景

keikeu 面向创作者的突发、即兴输入：有灵感就写下来；写完放下，得到稳定私密的 Paper 文件；再次拿起时辅助创作。是否整理由创作者主动选择：可以直接阅读 flash 样式的只读 Paper，也可以整理成更精密的 flashcard 后使用。flashcard 是创作参考卡片，不默认指背诵题库或间隔重复学习。

目标是在主流手机写作软件中快速查阅、调用这些内容，系统备忘录也在范围内。理想形态是小窗与编辑器同屏，但尚未确认 iPhone 平台可行性。研究应帮助选择交互方式，不预先承诺任意应用悬浮。

## 给 WorkBuddy 专家团的任务

请开展当前中文与国际手机写作编辑器市场及平台可行性研究，并使用实际可用的专家分工交叉核对结论。

1. 先宽查，再选择约 10–15 个代表软件，覆盖系统备忘录、专注写作、Markdown／知识笔记、通用文档、中文长篇／网文创作。Apple 备忘录必含；其他按当前可用性选择。解释样本和“主流”依据，不能将候选名单冒充市场排名。
2. 软件矩阵列出：iPhone 可用性、写作场景、文件格式与导入导出、离线／账号要求、分享扩展、URL scheme／深链、快捷指令或公开集成能力，以及与独立参考卡片协作的具体操作成本。无法核实写未知；价格仅在影响可行性时查证地区与日期。
3. 以 Apple 官方文档和审核规则优先核实 iPhone 上“任意第三方编辑器＋文本参考小窗”的边界。比较跨应用悬浮、画中画、系统多任务、自定义键盘、分享扩展、快捷指令、复制／深链往返。区分正式支持、特定设备／应用限定、技术可尝试但用途或审核受限、不可行、未证实。不能将视频画中画直接推定为通用可交互文本窗，也不能把 iPad 分屏当作 iPhone 能力。Android／iPad 仅作独立对照，不扩展本 Road。
4. 提出 2–3 条有证据的产品方案，比较编辑器覆盖、操作步数、输入法兼容、阅读空间、隐私／剪贴板／网络暴露、维护成本、分发限制及降级路径。保留直接使用原 Paper 与整理后使用两条路径，不替用户批准方案。

## 权限与交付

仅开展公开资料调研和建议，不实施代码、不修改项目或设备、不安装或购买软件，不读取私人笔记、本地账号凭据及其他无关文件。无须读取仓库源码。

交付中文报告，包含：关键结论与不能承诺的体验、软件矩阵、平台能力矩阵、方案比较、需实机验证清单、来源。重要判断附直接来源链接、查证日期及适用系统／应用版本；事实、推断、建议、未验分开标注。官方资料优先，社区内容补充真实痛点；不得编造实测。

保留实际检索与查阅轨迹、受阻项，供委托方复核。若不能联网或缺工具，明确报告阻点。提交任务、研究完成、来源复核和用户选择方案分别记录，不以已发送代替已完成。


## 报告接收与首轮复核

用户交回 `keikeu-road-v00.09.01-手机写作编辑器调研报告.md`，原件位于 Downloads，保持未修改。SHA-256：`cc6f7decd2739c14ee603bf1475f20c8775fab9ab8699149227ea0eb97e32efc`。报告提供 14 款样本及三种方案，未做实机验证；所列检索轨迹为报告自述，本轮未核对 WorkBuddy 原始执行日志。

2026-09-21 主代理复核范围：键盘能力／审核要求、Notion 离线及证据质量。不是全软件矩阵验收。

- **需纠正：键盘无法读取任何宿主文本。** Apple 文档提供光标附近文本上下文接口；这不等于能访问整个文档或任意应用。隐私策略应明确不采集无关上下文，不能宣称系统完全隔离。来源：[Apple 自定义键盘文档](https://developer.apple.com/library/archive/documentation/General/Conceptual/ExtensibilityPG/CustomKeyboard.html)。
- **需纠正：审核必然要求自建中文输入法。** [审核指南 4.4.1](https://developer.apple.com/app-store/review/guidelines/#extensions)要求键盘输入功能、切换键盘及无完全访问仍可工作，没有要求自建拼音／九宫格。具体卡片键盘方案能否合规仍需按实现判断。
- **需纠正：Notion 协作必然需联网。** [官方离线说明](https://www.notion.com/help/use-pages-offline)支持移动端下载页面后离线阅读编辑及新建页面；部分内容仍受限制。报告的操作成本判断需要更新。
- **待核实：无完全访问的共享数据。** 当前 Apple 搜索摘录提到共享容器只读访问，历史指南则写无共享访问；本轮当前正文受 JavaScript／Markdown 抓取限制，不能以历史文字替代当前系统行为。按[当前官方入口](https://developer.apple.com/documentation/uikit/configuring-open-access-for-a-custom-keyboard)与目标设备明确只读、写入和系统版本差异后再判断。
- **待核实：粘贴必有确认、分享必定切前台、覆盖率 100%、固定操作步数、零暴露。** 这些绝对结论没有逐场景证据，不进入验收承诺。PiP、当前系统窗口能力与各编辑器兼容性仍需定向核实。
- **市场证据不足：** 多个软件的在架与接口判断仅引用第三方清单；没有逐项官方依据及版本，也没有市场占有率数据。可作为候选样本，不称为已验证的主流排名或兼容名单。

## 对产品讨论的影响

卡片键盘替换当前键盘位置，不等于在原中文输入法旁常驻参考窗。若切回惯用输入法，卡片能否持续可见不能由这个方案自动满足。单独 App 快速往返可作为候选基础体验，键盘或深链为候选增强；这只是建议，未获用户选型决定。

用户后续明确：理想形态是 cheatsheet 式持续可见；翻一下再返回属于 opt-out 基础功能。因此快速切换只能承担基础路径，不能认定持续参考目标已经达成。后续研究应优先验证实际打字时的持续可见性，并明确平台不支持的部分；技术方案仍未批准。


## 后续明确的小窗要求

用户决定：主应用选好一份内容后一直参考；更换整份内容回主应用完成。当前内容必须能在小窗内滚动、翻页，不能要求返回应用完成阅读操作。视频网站小窗仅作为操作习惯参照，不构成 PiP 选型授权。

后续可行性验证必须同时覆盖：外部编辑器输入、参考内容持续可见、小窗内滚动与翻页。只支持静态展示、切换键盘时查阅或跳回主应用的方案，应明确标注未满足核心目标；不得以额外操作悄然替换用户要求。


## 2026-09-21 连接后预检

- 实机连接已确认：iPhone 17 Pro，iOS 27.0（24A435），有线、已配对、开发者模式开启。未安装或启动新测试包，未操作作者内容。此项仅证明设备就绪，不是小窗验收。
- 仓库 `scripts/build_apple_probe.py` 是旧文件协调探针，并无当前交互小窗原型；不复用它冒充本轮测试。
- 已直接读取 [Apple 视频通话 PiP 当前正文](https://developer.apple.com/documentation/avkit/adopting-picture-in-picture-for-video-calls)：该窗口不接收触摸事件，不能添加可操作按钮。此路线不满足手动滚动／翻页要求，不必先安装一个静态展示包才能作出这个判断。
- 已读取 [PiP 内容源](https://developer.apple.com/documentation/avkit/avpictureinpicturecontroller/contentsource-swift.class)：公开入口为播放器层、样本缓冲显示层及视频通话。播放控制回调不等于通用滚动视图；本轮没有取得符合全部要求的公开实现路线。这是有限 API 复核，不是对所有未来系统能力的穷尽证明。
- 已读取 [键盘完全访问当前正文](https://developer.apple.com/documentation/uikit/configuring-open-access-for-a-custom-keyboard)：默认允许只读访问包含应用的共享容器，写入共享容器与网络访问需要扩大权限。此前新旧文档冲突已有当前正文依据；具体目标版本行为仍未实测。此能力不解决与惯用输入法同时持续显示的问题。
- 尝试在 WorkBuddy 原会话补查，但界面返回 `elementHasNoFrame`／`noWindowsAvailable`，未发送补查任务。不能将本轮标记为外包完成或实机交互通过。

### 待发送的定向补查

沿用原专家团，只查公开资料，不读本地文件或设备、不安装软件。围绕完整要求寻找可证实路线：iPhone 外部编辑器正在使用惯用输入法时，预选的一份 Paper／flashcard 持续可见，用户可以在小窗内手动滚动和翻页，更换整份内容才回主应用。短暂往返只算 opt-out 基础能力。

请逐项说明公开 API、内容类型、触摸／手势接收、前后台生命周期、输入法共存及正式分发边界。重点验证是否有上述 PiP 与键盘之外的公开路线；没有证据则报告未找到，不以自动滚动、视频播放进度、键盘替换或频繁切换应用冒充满足。纠正原报告的绝对结论，引用当前 Apple 原文，给出最小可证伪实验；不要求开发不能回答关键问题的原型。


补查发送状态更新：2026-09-21 19:10（America/Toronto），用户重新打开 WorkBuddy 后，已在原“手机写作编辑器平台可行性调研”会话发送完整要求，界面确认深度研究专家开始处理。首次输入故障导致残缺消息已停止；随后完整消息在发送前后均经界面核对。当前仅确认补查启动，结果与执行轨迹尚待复核。


## 补充报告接收与有限复核

2026-09-21 用户交回 `keikeu-road-v00.09.01-补充报告-同屏小窗定向核查.md`，原件位于 `/Users/chenxi/WorkBuddy/2026-09-21-11-59-27/`，未修改。SHA-256：`b279194fde183d480f66d0b9e5a4052c810e2a6541bcf5e827511c12df133032`。报告已收到并读完；其检索轨迹仍是报告自述，本轮未取得 WorkBuddy 原始工具执行日志，不能标为完整外包审计通过。

结论采用“目前未找到满足全部要求的公开路线”。报告承认未逐项核查 iOS 27 API 变更，因此不采用“所有入口已排除／公开 API 不存在”的穷尽性断言，也不把新闻未提及某能力当作不存在的证明。小窗前置关口尚未通过，无实机交互结果。

本轮直接读取 Apple 当前 Markdown 正文，复核新增的 ActivityKit／WidgetKit 关键依据：

- [Live Activity 展示与生命周期](https://developer.apple.com/documentation/activitykit/displaying-live-data-with-live-activities.md)：系统选择紧凑／最小呈现，长按可展开；活动最长八小时不等于可展开阅读八小时。文档另列 transient 类型，点击岛外、锁屏或折叠会结束，不能据此认定它适合外部编辑器内持续输入。
- [交互按钮与 App Intents](https://developer.apple.com/documentation/widgetkit/adding-interactivity-to-widgets-and-live-activities.md)：展开与锁屏呈现支持按钮／开关，可以执行动作并更新内容。因此“没有专用翻页控件”不能推导出“无法用按钮换页”；按钮换页是可研究的实现推断，尚无本项目原型。文档没有证明任意滚动容器或边打字边保持展开，完整目标仍无证据。
- 不采纳补充报告沿用旧资料的 144–160pt 为 iPhone 17 Pro／iOS 27 的已核定尺寸。精确高度不是当前缺口的关键，不为测它单独开发探针。
- 键盘共享容器只读规则沿用上节主代理已直接读取的现行官方正文；WorkBuddy 未独立复核，不撤销已有直接证据。键盘扩展也未被用户批准为 opt-out 产品功能；用户确认的是临时翻看再返回这条基础行为。
- PiP 不接收触摸的直接证据限视频通话入口，不扩大成所有 PiP 模式一概不接收任何控制事件。其他媒体控制同样未证明满足手动滚动要求。

本机已确认 Xcode 27.0（27A266a）及 iPhoneOS SDK 27.0，可做针对性声明核查；本轮未完成 SDK 差异审计。SDK 搜索同样只能支持具体入口的判断，不能单凭未命中关键词升级为穷尽证明。报告建议的 Live Activity／键盘实验属于建议，不是用户新授权或已完成工作；本轮未安装探针、未读取编辑器正文、未变更设备或作者数据。

下一步：如继续技术核查，只围绕“能否在外部输入时持续展开”和“是否有受支持的手动滚动入口”检查具体公开契约；出现可信候选后再做合成实机探针。当前不承诺交付跨应用小窗，也不把键盘替换或应用往返标成目标达成。若要先推进原生记录／Paper／只读查阅，把持续小窗延后或调整其使用场景，须由用户明确选择。


## 第二轮：公开接口与系统呈现复核

2026-09-21 用户要求继续细查。本轮以当前 Apple 文档、WWDC25／26 原始讲解及本机 Xcode 27.0（27A266a）的 iPhoneOS27.0.sdk 为依据，没有采用媒体报道作 API 结论，未构建或安装新应用。以下是有限接口审查，不是跨 SDK 版本的完整差异审计。

### 新发现：Snippet 不能按原报告直接排除

[交互式 Snippet 官方文档](https://developer.apple.com/documentation/appintents/displaying-static-and-interactive-snippets.md)说明，Snippet 会保留到用户关闭，支持通过 App Intent 按钮更新内容；可见期间，系统保持提供内容的应用在后台活动。这纠正了补充报告把它笼统归为“瞬态、不可驻留”的判断，但后台存活不等于外部编辑器仍能接收输入。

[WWDC25「Design interactive snippets」](https://developer.apple.com/videos/play/wwdc2025/281/) 1:30 的设计讲解明确谈到长内容需要滚动，并建议保持简短。因此“任何 Snippet 都不能滚动”缺乏依据。需要区分系统外层的溢出滚动与开发者自定义 ScrollView／拖动手势；前者存在的文字依据不能证明后者可用。

[当前 Snippets HIG](https://developer.apple.com/design/human-interface-guidelines/snippets)（变更记录 2026-06-08）要求自定义内容不超过 400pt，并建议更多细节通过链接打开应用。该页面通过 Apple 官方 DocC JSON 正文读取。旧视频的 340pt 建议不作为当前设备上限。系统外层能滚动也不等于长 Paper 阅读已成为受支持的设计用途。

当前开发文档还提示：Siri AI 调用 App Intent 时，系统可能不显示 IntentDialog 或 ShowsSnippetView。因此调用入口也是实验变量；不能用一次 Siri 未显示结果判定所有 Snippet 入口都失败，也不能承诺随时可靠唤起自定义卡片。

**准确定位：Snippet 是值得证伪的局部候选，尚不是满足产品要求的可信完整路线。** 本轮没有找到官方承诺其可让底层编辑器继续接收触摸与惯用软键盘输入；也没有取得相反的目标设备观察。不能把“无需打开提供内容的 App”推导为“无需中断正在进行的输入”。按钮换页可按状态更新研究，仍待实际验证。

### 本机 SDK 核查范围

SDK 根目录：`/Applications/Xcode.app/Contents/Developer/Platforms/iPhoneOS.platform/Developer/SDKs/iPhoneOS27.0.sdk/System/Library/Frameworks/`。读取／检索以下公开声明；未读取私有框架或应用数据。

| 入口与文件（相对 SDK 根目录） | 直接观察 | 对目标的影响 |
| --- | --- | --- |
| `ActivityKit.framework/Modules/ActivityKit.swiftmodule/arm64e-apple-ios.swiftinterface` | ActivityStyle 的 standard／transient、启动／更新／结束及状态观察入口 | 未找到固定展开呈现或转发滚动手势的公开成员；这不是整个系统不存在此能力的证明 |
| `WidgetKit.framework/Modules/WidgetKit.swiftmodule/arm64e-apple-ios.swiftinterface` | iOS 27 的 `isDynamicIslandLimitedInWidth`，以及小组件尺寸等新增声明 | [WWDC26 Live Activities essentials](https://developer.apple.com/videos/play/wwdc2026/223/) 9:51 之后讲解横屏的紧凑／最小呈现及宽度适配，不是新增可常驻展开的阅读窗 |
| `AppIntents.framework/Modules/AppIntents.swiftmodule/arm64e-apple-ios.swiftinterface` | SnippetIntent、reload 和返回 Snippet 的接口，SnippetIntent 从系统 26 起可用 | 支持继续做当前系统的 Snippet 小实验，未发现让底层应用继续接收输入的 Snippet 专用设置 |
| `UIKit.framework/Headers/UISceneAccessory.h`、`UISceneAccessoryRegistration.h` 及 Scene／WindowScene 相关头文件 | iOS 27 场景附件的构造入口为 externalNonInteractive，系统决定可用性及呈现位置 | 外接屏非交互内容，不是 iPhone 屏内跨应用小窗；不能把 API 标注 iOS 可用当成手机支持任意多窗口 |
| `AVKit.framework/Headers/AVPictureInPictureController*.h` | 视频通话内容明确不接收输入；样本缓冲代理有播放／暂停、跳转时间及尺寸变化等回调 | 媒体 PiP 不是完全没有按钮交互，但没有取得任意拖动滚动接口；把跳转时间映射成换页仍缺手动滚动，不能冒充达标 |

[ActivityKit 当前文档](https://developer.apple.com/documentation/activitykit/displaying-live-data-with-live-activities.md)对 transient 类型明确说明点击外部或折叠会结束；该事实不扩写为所有 standard 活动必有相同生命周期。持续发通知或反复弹出来维持展开，会额外干扰写作，不作为现有要求的实现。

### 收敛后的最小实验与停止条件

优先级从“再测所有入口”收敛到 Snippet 的一个关键问题：**显示自定义结果卡片后，外部编辑器能否继续使用原软键盘输入，且卡片仍完整可见？**

1. 使用独立合成测试包与固定示例内容，经系统真正承载的 result Snippet 展示；主应用内画一个相似浮层不能代替。先确认触发入口实际显示 Snippet，不改变用户日常快捷键或 Action button 配置。
2. 外部编辑器使用空白合成文稿，先唤起原软键盘，再触发 Snippet。分别记录键盘是否保留、首次点击键盘的结果，以及尝试连续输入时内容实际写入哪个界面。仅底层画面看得见或光标仍闪烁不算通过。
3. 如输入会关闭卡片、被阻止或进入系统输入框，该入口立即判定不满足，停止为它开发滚动／翻页。不能把反复唤起变成默认操作；也不能用物理键盘或镜像注入替代手机软键盘结论。
4. 仅输入共存通过后，再测长内容的实际可达范围、手动滚动、按钮换页、换页后的阅读位置，以及中英文组合输入／选区恢复。系统溢出滚动与自定义 ScrollView 分开记录；超过当前 HIG 内容范围的偶然表现不直接升级为稳定产品能力。
5. 每项绑定包、系统版本、调用入口和观察；模拟器只作先行筛查，最终仍需 iPhone 17 Pro／iOS 27 实机。本轮资料复核结束时五步均未执行；后续结果按下节日期单独记录。

产品判断保持不变：没有完整目标通过的证据。下一项有信息量的工作是上述输入共存实验，而不是继续凭搜索结果概括“绝对不可能”，也不是先完成完整的原生重构再发现系统呈现不合要求。

## 2026-09-22 隔离探针与实机记录

用户已授权制作入口视觉原型并进入下一步，暂停后于 2026-09-22 要求继续。视觉原型解释目标体验、视频通话 PiP、媒体 PiP、灵动岛、Snippet、自定义键盘、主屏小组件、分享扩展、外接屏和应用往返；其中假设交互明确标为模拟，不能作为平台通过证据。产物位于当前任务的本机可视化目录 `reference-entryways.html`，不含作者正文。

最小原生探针位于 [`tests/apple-reference-probe/`](../tests/apple-reference-probe/README.md)：Ref Probe 提供固定两页合成内容，Ref Editor 是另一进程中的原生 UITextView，仅保留内存输入并显示字符数。无网络代码、云权限或 Vault 访问；使用已有 XcodeGen、SDK 27.0 和本机有效开发 profile，未创建开发者门户资产、未覆盖旧 keikeu 安装。

| 项目 | 实际结果及边界 |
| --- | --- |
| 工程与签名 | 两个 iphoneos Debug 目标构建成功；App Intents 元数据生成成功。两个包通过 strict／deep 签名验证；9 月 22 日按逐文件摘要复核，产物未变 |
| 安装 | Ref Probe 在 9 月 21 日安装；Ref Editor 在 9 月 22 日安装成功。bundle ID 分别为 `app.keikeu.referenceprobe`、`app.keikeu.referenceeditor` |
| 设备 | iPhone 17 Pro，iOS 27.0（24A435）；真实设备，非模拟器 |
| 调用入口 | iPhone Mirroring 中使用 Spotlight 搜索 `Show Reference`，点击 Ref Probe 名下动作；系统实际展示含 Done 按钮的结果卡片，非 App 内仿制浮层 |
| 翻页 | 卡片初始显示 1/2 及第一段合成文本；点击“翻页”后，直接观察到 2/2 及第二段文本。证明当前包在此入口的按钮与状态更新 |
| 输入共存 | 待用户直接在手机上操作 Ref Editor 与 Siri 入口；没有用镜像或硬件键盘输入认定通过。Siri 入口若未显示卡片，只记为入口未成功，不推导为全部 Snippet 失败 |
| 未验 | 惯用软键盘持续输入、长文手动滚动、翻页后的输入状态、备忘录等真实编辑器、重启和其他系统版本。前置关口仍未通过 |

本次源码未提交，基础 HEAD 为 `d0a557a`。源码 SHA-256：`Probe.swift` 为 `bcc5e9bc2dd92a40cb8944042246bd3fb532930649958cbbcba4758b555343aa`，`Editor.swift` 为 `0f2c03a862477584168448b4d5ff87e25240e6083074f92d718f6872a885ba30`，`project.yml` 为 `3f610aa65d9d80c9510b039ef5d5f1006cd8c62b40a9b0689030643a2b222a53`。

签名后包的逐文件清单（含 Debug dylib）保留在忽略目录 `tests/test-vault/reference-probe/signed-packages.json`；同目录保留 `probe-build.log`、`editor-build.log`、`signing.log`、两份安装回执及 `probe-launch.log`。个人 profile、设备标识和安装清单只留本机，不纳入提交。系统显示与翻页结果来自本任务 CUA 直接截图观察；未把带无关 Spotlight 内容的全屏截图复制到版本库。

下一步只验证输入共存：用户在 Ref Editor 唤起手机软键盘，经 Siri 尝试 `Show reference in Ref Probe`，卡片出现后继续输入 `REF-001`；分别记录卡片是否保留、键盘是否可用和文字实际接收位置。未触发卡片时先解决入口，不判交互失败；成功触发但输入使卡片关闭或被截获时，停止该入口的长文滚动开发。
