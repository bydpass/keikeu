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

## 2026-09-22 三条路线独立 Demo

用户新增授权：新开工作树，制作 Snippet only、灵动岛 only、融合方案三个极简 Demo。工作树 `/Users/chenxi/.codex/worktrees/keikeu-reference-demos/keikeu`，分支 `codex/road-v00-09-01-reference-demos`，基础 HEAD `d0a557a`；原主工作树未修改。规划文件与旧探针源码按当前版本复制接续，不丢弃原改动。产品 CP0 尚未启动，原生完整产品和滚动阅读不在本次 Demo 实现中。

实现与最短操作见[三路线 Demo](../tests/apple-reference-demos/README.md)。三份新包使用独立 bundle ID；Island／Fusion 各有独立 Widget 扩展，无 App Group、推送或网络代码。融合方案使用 Live Activity 页码作为共享状态，从活动按钮返回 `ShowsSnippetIntent`；该公开类型组合能构建，是否有系统呈现仍待设备观察，不视为已证实的承载路径。

| 检查 | 结果及证据边界 |
| --- | --- |
| 页码逻辑 | `Sample.swift`＋`check.swift` 编译并运行通过：循环、负数与整数边界 |
| 三包工程 | RefSnippet／RefIsland／RefFusion 的 iphoneos Debug 构建成功；两份扩展包含在宿主内。首次 Island 构建的 Swift 6 静态可变属性错误已修复后重建通过 |
| 签名与安装 | 三份宿主及扩展通过 strict／deep 签名检查；三次安装回执均 success，安装清单另行读回确认三个包存在 |
| Ref Snippet | 已成功启动并直接观察原生控制页；此新包的系统卡片和翻页尚未实测，不移用 Ref Probe 旧包结果 |
| Ref Island | 主动开始后切到 Ref Editor，直接观察顶部参考图标及 1/3；回 App 结束后状态变为已结束。展开、翻页及软键盘共存待测 |
| Ref Fusion | 主动开始后切到 Ref Editor，直接观察顶部参考图标及 1/3；已交用户在手机长按、点击“展开参考”并测试输入。Snippet 是否呈现、两处页码同步与软键盘共存待测 |
| 工具边界 | 首次 devicectl 启动等待未返回，终止该命令后有限超时重试成功；不计为应用通过或失败。镜像右键未能展开灵动岛，不将此工具局限判为 iPhone 不支持展开 |

Build 1 包与源码绑定：忽略目录 `tests/test-vault/reference-demos/build-1/signed-packages.json` 记录每份包（含扩展和 Debug dylib）的逐文件摘要以及全部 Swift／工程配置摘要；该清单 SHA-256 为 `ca66066120ea5c4adac43e066f39a10e056153aee7b678845cafc3e3160f4c4e`。该目录保存原包及构建、安装回执，启动回执在上一级。设备仍为 iPhone 17 Pro／iOS 27.0（24A435）；个人标识、profile 和安装清单不提交。

独立审查已纠正证据风险：Snippet 的 400pt 限高和裁切是 Demo 自身布局，第三页显示不全不能归因平台，也不能据此否定系统滚动。当前仅按顺序点击筛查入口，不承诺连点、重启恢复、常驻展开或长文阅读。若完整输入共存失败，保留可运行 Demo 和具体入口结果，再由用户决定路线，不以紧凑页码仍可见代替参考正文持续可见。

### Build 2：按钮裁切与无响应诊断

用户报告：融合版灵动岛“展开参考”按下无可见反应，按钮下沿被黑边吃掉。此次没有观察到系统 Snippet，不能记为融合入口通过；也尚未区分按钮动作未执行与系统未呈现结果。

代码检查发现，共享视图把标题、无限行正文和按钮全部放进展开岛的 bottom 区域。Build 2 将标题／页码放到 leading／trailing，岛内正文最多两行，按钮优先保留空间，并为圆角区域设置水平及底部边距。锁屏正文也限制为三行。摘要截断属于 Demo 布局决定，不是平台长文能力结论。

`OpenReferenceSnippet.perform()` 现在先递增 Activity 的可见“已执行请求”计数，再按原路径返回 `ReferenceSnippet`。字段为可选值以兼容旧活动状态；普通翻页保留该字段。计数增加只证明动作执行；卡片是否出现仍需独立观察。未加入后台保活、定时重弹或 `reload()`，避免混淆两条触发机制。

Apple 当前[活动交互文档](https://developer.apple.com/documentation/widgetkit/adding-interactivity-to-widgets-and-live-activities)说明按钮执行 App Intent，未找到其保证呈现返回 Snippet 的文字。[Snippet 文档](https://developer.apple.com/documentation/appintents/displaying-static-and-interactive-snippets)明确介绍其他系统入口，但不能因此作穷尽排除。`ReferenceSnippet.reload()` 的单次实验可留待诊断结果后判断；公开 SDK 与[符号页](https://developer.apple.com/documentation/appintents/snippetintent/reload())为静态同步方法，不能写成实例异步调用，也不保证从任意系统宿主创建呈现。

三个 Build 2 iphoneos 构建、宿主／扩展签名及更新安装通过。更新前通过 Demo 自身按钮结束旧 Fusion 活动；更新后重新开始，并返回 Ref Editor，直接观察原 14 字符合成输入仍保留。已请求用户手机复验：按钮下沿、请求计数、系统卡片三项；结果待回报，不认定裁切或无响应已通过实机修复。

当前包清单 `tests/test-vault/reference-demos/signed-packages.json` 的 SHA-256 为 `352f933ae9559328bd9ec6355e976a794f7cec85a9155b2f5fdb0b41ad2aa1e9`，包含当前 Swift／配置摘要。旧包和旧清单完整留在 `build-1/`；不用新源码解释旧安装行为。

### Build 2 复验与 Fusion Build 3

用户明确回报“展开参考依旧无效，但溢出问题已被解决”。随后主代理通过 CUA 直接观察到完整按钮和“已执行请求 3”，点击一次后计数变为 4，仍未出现系统卡片。裁切修复通过用户复验及直接观察；按钮动作已执行，“Live Activity 按钮返回 Snippet 结果”在此包／入口／设备上未显示卡片。不能再把无可见反应归为按钮没执行，也不推导为其他 Snippet 入口或整个系统都不支持。

Fusion Build 3 保持已通过的布局和计数，仅把按钮实现改为一次静态 `ReferenceSnippet.reload()`，随后返回普通 `.result()`；不与原返回 Snippet 路径同时调用。此实验依据当前官方文章的刷新说明，是否能从该宿主呈现仍是假设，不是已知修复。没有定时器、循环或后台保活。

仅重建并更新 Fusion（含 Widget）为 Build 3，构建、签名及安装通过；Snippet／Island 保持 Build 2。升级结束原活动后，已在新 App 开始活动并返回 Ref Editor，原 14 字符合成输入仍在。用户回报“依旧无效”；主代理随后通过 CUA 直接看到“已执行请求 3”和展开的灵动岛，未出现系统 Snippet。单次 reload 路径也未通过，停止重复尝试该触发方式，不以反复弹出替代持续参考。

Build 3 逐文件包／源码清单为 `tests/test-vault/reference-demos/fusion-build3-packages.json`，SHA-256 `7bd6f5ea04c17c3c88306d99fd2dbd8e1891a7cd3bac618a09315dd9ae235480`。Build 2 的三个包、源码和清单已保留在 `build-2/`；上节 Build 2 摘要继续对应其历史包。各次结果按版本及触发方式分开，不混为同一次试验。

最终处置：按钮下沿裁切已解决；当前设备上，Live Activity 按钮返回 Snippet 结果与点击触发单次 reload 两种衔接均未显示系统卡片。保留这两轮独立证据和可复现源码，不将融合入口标为可用。此结论不否定独立 Siri／Spotlight Snippet，也不证明灵动岛展开与手机软键盘输入共存；这两项仍按各自测试判断。未改成自动回主 App、键盘替换或自绘浮层来冒充成功。


### 操作按钮独立入口实验

2026-09-22 用户要求换思路，并指出 Spotlight 无法在编辑器中直观唤起。既有 Spotlight 证据仅证明系统卡片呈现与翻页，不证明写作中的便捷调用。用户随后授权继续试验 **Action button → App Shortcut → Snippet**；原灵动岛转调的两种失败结论保留，不重试原路径。

[Apple 的 Snippet 说明](https://developer.apple.com/documentation/appintents/displaying-static-and-interactive-snippets)明确以操作按钮触发 App Shortcut 后显示交互卡片为例；[操作按钮手册](https://support.apple.com/guide/shortcuts/run-shortcuts-with-the-action-button-apdfea15680b/ios)提供 Shortcut 绑定步骤。这支持入口试验，不保证卡片与底层手机输入共存。新的融合候选是两个入口共享同一参考状态，不再由灵动岛负责打开 Snippet；尚未据此接受产品范围或持续阅读能力。

本轮复用已安装 Ref Snippet Build 2，无源码修改、重建或重装。CUA 重连后直接看到 Ref Editor 原 14 字符合成输入。操作按钮原绑定为 **Shortcut → Show Code Scanner**；已在选择器中按 **Ref Snippet** 应用归属选中 **Show Reference**，随后设置页显示新绑定。Ref Fusion／Ref Probe 同名动作未选。

已返回 Ref Editor，原输入仍为 14 字符，当前交由用户操作手机：唤起惯用软键盘，长按实体操作按钮；卡片出现后不先关闭，追加 `AB-01`，预期计数 19。入口呈现、卡片在输入期间留存、文字实际进入编辑器三项分别记录。**当时结果待回报、扫码绑定待恢复；完成状态见下段**；不得将配置成功当作入口或输入共存通过。Mirroring 断开是实体手机接管，不据此判断功能失败。

本轮设备 CLI 启动尝试因 CoreDeviceService 初始化超时未成功；随后通过 UI 返回 Ref Editor。该工具失败不作为 Snippet 行为证据。

用户随后答复三项“都没有问题”：按其手机实测，操作按钮呈现卡片、点击手机软键盘后卡片留存、追加输入进入编辑器均通过。主代理重连直接看到 Ref Editor 计数由 14 增至 19，新增行可见 `ABBA`；不主张输入逐字等于指定的 `AB-01`，也不把重连后画面当作输入期间卡片留存的直接录像。此结论绑定 Ref Snippet Build 2 和本次手机操作，不扩展到长文滚动、其他编辑器或融合入口。随后通过 CUA 将操作按钮恢复为 **Shortcut → Show Code Scanner**，设置页已直接核实。

下一实验仅为 Ref Snippet Build 4 增加正文内层 ScrollView（180pt），复用既有第三页首尾文字；页码和下一页按钮固定在正文外，换页从页首开始。Fusion 路径保持既有行为，不重装其他包。Build 3 的 Fusion 包、构建源码和摘要保留在忽略的 `tests/test-vault/reference-demos/build-3/`。构建、安装、长页拖动与翻页后输入的结果待后续记录。

Ref Snippet Build 4 的 iphoneos Debug 构建通过；沿用本机已批准有效开发 profile 签名，strict/deep 验证通过，设备安装回执 `RefSnippet-install-build4.json` 为 success。包与源码逐文件摘要保存在 `tests/test-vault/reference-demos/snippet-build4-packages.json`，清单 SHA-256 为 `401595728b3b3708ea5d98dee74196685c6e56a0c155ec35ce8eefaa15d1d084`。只读代码复核确认新增 ScrollView、提示和版本仅影响独立 Ref Snippet，Fusion 既有路径保留；本轮未重建或更新 Fusion／Island。

第二轮已在操作按钮选择器按完整应用名 **Ref Snippet** 选中 Show Reference，随后通过设备 CLI 返回 Ref Editor，CUA 直接看到原 19 字符合成输入仍在。当时等待用户以手机键盘执行第三页首尾滚动、翻回 1/3 和中文追加输入；**当时第二轮临时绑定尚待恢复；完成状态见下节**。没有用构建或安装成功代替手势与输入验收。


### Build 4 手机结果与第二轮入口恢复

用户回报正文上滑失败，翻页回到 1/3 正常，输入正常但卡片大小遮住正在输入的正文；随后明确测试应用为 **Ref Editor**，本轮没有保存测试。主代理通过 CUA 重连看到 Ref Editor 计数由 19 增至 26，新增可见拉丁字符。这支持实际追加输入，不证明中文候选、组合输入或保存通过；输入期间卡片留存与遮挡来自用户手机反馈，不将重连画面冒充全过程录像。

结果绑定上一节 Ref Snippet Build 4 包、操作按钮入口、iPhone 17 Pro／iOS 27.0 和 180pt 正文 ScrollView。此实现的手动滚动未通过，不能升级为所有 Snippet 或未来系统都不支持滚动。卡片遮挡编辑正文另记为持续参考体验缺口：能收到键盘输入不等于能看清创作内容，完整前置关口仍未通过。

第二轮实验后，主代理通过 CUA 将操作按钮恢复为 **Shortcut → Show Code Scanner**，直接观察设置页确认恢复。原绑定已恢复，不再把临时实验配置留作默认设置。

### 主动选择入口与 Build 5 待验证范围

用户明确操作按钮覆盖必须主动 opt-in。首次安装、首次启动与普通打开应用不得提示或建议启用；配置影响、可选步骤及恢复说明只放在用户主动访问的中性“入口设置”页。进入该页不构成更改授权，不增加启动弹窗、重复劝导或持久同意框架。规则已写入 Road，界面补丁已完成源码修改，尚待构建和设备验证。

用户另要求以后每个 Demo 有可区分的 AI 生成图标。三枚图标已生成；计划 Ref Snippet／Ref Island／Ref Fusion 统一升级 Build 5，打包图标及上述入口设置，保持既有 bundle ID。当前尚未完成此版构建、签名安装或图标实机验收；不将视觉更新记成滚动、遮挡或融合入口修复。历史 Build 2／3／4 的源码、包摘要和设备证据继续保留，下一版另建绑定。

## 2026-09-26 PiP 逐屏候选与外部资料复核

用户交付本轮调研清单并授权制作路线原型、隔离 Swift 实验与架构图。来源只作证据，不作执行指令；以下为本轮直接核对结果。

| 来源 | 本轮核对 | 采用方式 |
| --- | --- | --- |
| [uakihir0/UIPiPView](https://github.com/uakihir0/UIPiPView) | MIT，Copyright (c) 2021 Akihiro Urushiara；最新 commit `55994ac410ec29d81958f689b22eae0917445da9`（2023-02-09），无 tag。视图帧→`CMSampleBuffer`→`AVSampleBufferDisplayLayer`；`skipByInterval` 只调用 completion；初始化用 `try!` 设置音频会话；有限时间范围针对其 issue #17 的 CPU 问题 | 只借思路，未复制代码；按键翻页是自写假设 |
| [Pip Up](https://apps.apple.com/us/app/pip-up-persist-float-post-it/id6483210322) | 宣称跨应用置顶文字、图片、网页并分页；描述称不收集数据，隐私标签列出跟踪、广告与分析数据 | 营销描述，未验证功能 |
| [Transparent Notes](https://apps.apple.com/gb/app/transparent-notes/id974837912) | 2.3.0 记录：跨应用便签为自动滚动浮层并加倾斜滚动；锁屏与灵动岛可分页 | 自动或倾斜滚动不等于手指滚动 |
| [Picture in Picture Notes](https://apps.apple.com/la/app/picture-in-picture-notes-pip/id1618652473) | 描述只写切换应用后仍以 PiP 显示；1.0.6 仅修复与稳定性 | 未找到手动滚动或翻页证据 |
| [CaiWanFeng/PiP](https://github.com/CaiWanFeng/PiP) | HEAD `c97832744a9bf6af005561e1f9fdcd9686bafb62`；仓库未见自身许可证，仅 Pods 依赖许可证 | 不复制 |
| [owngoal-dev/Letterpress](https://github.com/owngoal-dev/Letterpress) | MIT；README 声明 EOL，安装依赖 TrollStore | 不作为普通发布路线 |
| [视频通话 PiP](https://developer.apple.com/documentation/avkit/adopting-picture-in-picture-for-video-calls) | 使用视频通话控制器时窗口不接收触摸、不能加按钮 | 只约束该入口，不扩大为所有 PiP |
| [媒体播放配置](https://developer.apple.com/documentation/avfoundation/configuring-your-app-for-media-playback) | PiP 需要 Audio, AirPlay, and Picture in Picture 背景模式；建议延后激活音频会话以免打断其他音频 | 实验只在点“开始小窗”时激活 |
| [Claude 模拟器面板](https://code.claude.com/docs/en/desktop-ios-simulator) | 面板要求 Xcode 26.x，暂不支持 Xcode 27 | 未安装、降级或切换工具链 |

本机 iPhoneOS 27.0 SDK 头文件确认：`skipByInterval` 必须调用 completion；`requiresLinearPlayback` 控制跳转控件；层级 `enqueue` 自 iOS 18 弃用。

新实验 [Ref PiP](../tests/apple-reference-demos/pip-pager/README.md) 的结果：纯逻辑检查、iphoneos 与 iOS 26.5 模拟器构建通过；模拟器首帧经显示层渲染；该模拟器 `isPictureInPictureSupported()` 为 false，因此模拟器不能筛查 PiP。未签名、未安装，没有设备证据；临时 UI 测试已移除，日志留在忽略目录。路线结论与证据边界见[设计说明](design/road-v00-09-01-reference-window-design.md)。

状态更正：Build 5 三个 Demo 已构建并签名（`build5-packages.json`、`signing-build5.log`），截至本日尚未安装；本轮未改其源码与包，源码摘要仍与清单一致。

## 2026-09-29 Ref PiP 真机探索

用户通知真机已连接，并要求以真机结果为准，模拟器结果只作 legacy；兼容目标为 iOS 15–27。设备：iPhone 17 Pro，iOS 27.0（24A435），开发者模式开启。Ref PiP 部署版本改为 15.0，新系统 API 按版本隔离；Build 2–4 各自签名验证并安装，操作经 iPhone Mirroring，证据取自设备上的合成事件日志。详见 [Ref PiP README](../tests/apple-reference-demos/pip-pager/README.md)。

| 观察 | 结果 |
| --- | --- |
| 设备支持 | `isPictureInPictureSupported()` 为 true（iOS 26.5 模拟器为 false） |
| 启动条件 | `.playback` 音频会话激活前 `possible` 为 false，激活后约 1 秒转 true；`.mixWithOthers` 可启动 |
| 跨应用 | 切到 Ref Editor 后小窗保持在上方；前进／后退回调在 Ref PiP 处于后台时到达并换屏 |
| 设备缺陷与修复 | 首帧空白（加入窗口时重绘）；开始按钮在折叠线下（移到预览上方）；无控制时基时 ⏩ 置灰（暂停时基置于区间中点） |
| 退出 | 关闭小窗后 `pip_stopped` 与 `audio_released`，无错误 |
| 限制 | 1.5 秒内连按丢失跳转；手指滚动不满足 |
| 未验 | 手机软键盘共存、中文候选、输入可见性、独占音频、iOS 15–26 |

本轮开始前 Ref Editor 已不在运行，原 26 字符内存输入已丢失，非本轮操作所致；之后以新进程（0 字符）测试。Build 5 与其他 Demo 包未改动，操作按钮未改。

用户手机实测（同日）：Ref PiP 小窗在 Ref Editor 上方一直可见，中文候选正常。事件日志显示 19:06:22–39 共 35 次后台跳转全部到达，同一秒内多次也生效；此前 1.5 秒间隔丢失跳转来自镜像点按，不是系统限制。用户原话：“长文本滚动显示由播放‘快进/回退 10s’按钮实现”。据此 PiP 路线的长文阅读以 ±10 秒键逐屏推进；手指拖动滚动在 PiP 中不可实现的事实保留。正文遮挡、拖动缩放与翻页后焦点未单独回报。

用户补充（2026-09-29）：小窗能拖到角落，翻页后光标仍在。问题：1. PiP 小窗 UI 遮挡，尤其播放／暂停按钮；切页等操作会频繁激活系统控件，使其常态显示，观感差。2. 遮挡对潜在用户的影响不明；可把窗口拉到侧边收起，但收起后不能当小抄用，展开时又挡正文输入区。用户决定：PiP 路线暂停，下次试验换一条路线，逐步试水再决定。

## 2026-09-29 灵动岛展开态试水

按 Codex 交接的最小实验，复用手机上已安装的 Ref Island Build 2（未改代码、未安装 Build 5，结果不移给 Build 5）。设备 iPhone 17 Pro／iOS 27.0。用户在 Ref Editor 用惯用中文键盘实测，原话要点：

- “收起正常”：用户确认**一碰输入区或键盘，展开的灵动岛就收起**；打字期间不能保持展开。
- 展开正文连标题在按钮以上最多约三行，且有严重溢出；可考虑重构布局（需新 Build，不改 Build 5 历史源码）。
- 展开的灵动岛只占屏幕顶部约 1/5，对大多数编辑器几乎无遮挡。
- 输入、候选词、光标等与平常无异。

版本与硬件门槛：Live Activities 需 iOS 16.1+；灵动岛仅 iPhone 14 Pro 及之后带岛机型；无岛机型只在锁屏显示；iOS 15 无此能力，只能回退为应用内翻看。本路线不覆盖 iOS 15–27 全部范围。

2026-09-29 用户调整目标（适用于所有路线）：经短时探索，“打字时持续显示参考”不切实际，验收目标改为“**可以快速被调出＋查看**”——写作中能迅速唤出参考、看清内容、再回到输入。据此重评灵动岛：长按即可展开查看，满足“快速调出＋查看”的形态；紧凑态常驻顶部可作入口。短板是岛内只有约三行且溢出严重，需重构正文布局（新 Build，不改 Build 5）后再测。PiP 路线按新目标可重评，但系统控件遮挡的体验问题仍在，维持暂停。

### Ref Island Build 6（自动分段）

用户定义切段规则：手动切点仅限“进一步”模式，标记间文字超过展开岛最大行数即打回提醒；自动切点在溢出前最近的标点处截断。据此在 `tests/apple-reference-demos/island-pager/` 新建 Build 6（沿用 `app.keikeu.refisland`，Build 5 源码未改）：按钮移到摄像头两侧，正文独占下方 4 行；11 段合成内容的纯逻辑检查通过，iphoneos 构建与签名验证通过，2026-09-29 经用户同意替换 Build 2 安装并启动（设备显示版本 6）；**岛内外观与翻段尚未真机验证**。

### Ref Island Build 6／7 真机结果与融合评估

用户实测 Build 6：“这个试验方案简直完美”，仅剩少许溢出，Build 7 把分段与显示区一并砍到 3 行，用户判定改法不对并要求回滚；改为**渲染文字限 3 行、显示上限仍为原先 4 行**。Build 8 按此构建、签名验证、替换安装并启动（设备显示版本 8，13 段），最终外观待用户过目。灵动岛自动分段路线满足“快速调出＋查看”。

融合评估：旧融合（岛内按钮唤起 Snippet）两种衔接已失败，不再重试；可行组合为“灵动岛 3 行速览＋用户主动绑定的操作按钮 Snippet 长段查看”，两者共用分段与阅读位置，代价是卡片遮挡正文与操作按钮 opt-in。定为产品阶段可选组合，本轮不实施。详见 [Ref Island Build 6／7](../tests/apple-reference-demos/island-pager/README.md)。

### Build 8 定为首选；Build 9 融合实验

用户确认 Build 8 不再溢出，**灵动岛自动分段定为首选路线**。用户随后要求再做融合实验以确定可行性与性能。Build 9 在同一 App 内加入 iOS 26+ 系统卡片入口（App Shortcut → SnippetIntent），卡片从岛当前段起连显同页最多 3 段，卡内翻段同步写回岛；以本地事件日志记录请求、渲染、翻段耗时与进程启动时长（不记正文）。已构建、签名验证、替换安装并启动（设备显示版本 9）；不修改操作按钮绑定；真机结果待测。详见 [Ref Island Build 6–9](../tests/apple-reference-demos/island-pager/README.md#build-9融合实验2026-09-29)。

Build 9 真机：Spotlight 只搜出旧的同名“Show Reference”，新卡片入口未被调用（设备日志无 `card_requested`；岛内翻段写回 3–4 ms）。Build 10 改用唯一名称“Island Reference”并在启动时请求重新登记快捷指令，已安装待复测。

## 2026-09-29 融合版结论与决策

用户实测 Build 10：卡片能调出。设备日志 `island-device/events/fusion-events-2.jsonl`（忽略目录，只含事件、段序号与耗时）：

| 指标 | 结果 | 样本 |
| --- | --- | --- |
| 卡片请求 → 首次视图构建（热进程，已运行约 103 s） | 65 ms；系统在 96 ms 内构建 3 次 | 1 次请求 |
| 卡内翻段写回灵动岛 | 2–4 ms（中位 2.5） | 6 次，均 `hasActivity: 1` |
| 翻段后卡片重建 | 14–20 ms | 6 次 |
| 岛内翻段写回 | 3–4 ms | 6 次（Build 9 时段） |

卡片窗口按规则变化：同页剩余段数为 1–3（日志 `segments` 1／3／2 交替）。**未取得的证据：**冷启动（无低 `sinceLaunchMs` 的请求）、岛→卡片反向同步（卡片后无 `island_step`）、本轮卡片与软键盘共存细节；计时只到视图构建，屏幕出现快慢凭用户观察。

**用户决策：融合版定为首选方案**（取代单独灵动岛），本轮探索收尾，准备新开 Road。操作按钮绑定未改动（仍为用户恢复的 Show Code Scanner）；入口经 Spotlight／快捷指令验证，操作按钮入口只能由用户主动选择。

2026-09-29 清理（用户要求“除 Ref Island 之外的所有残渣统统扫除”，范围：手机＋本地构建物）：手机已卸载 Ref Editor／Ref Fusion／Ref PiP／Ref Probe／Ref Snippet，只剩 Ref Island Build 10。忽略目录 `tests/test-vault/reference-demos/` 已删除非 Ref Island 的构建包、DerivedData、日志与回执，包括 Build 5 签名包与 `build5-packages.json`、PiP 的 `pip-device/`（含事件日志）与 `pip-pager/`、`archify-visual/`、Snippet／Fusion 的 Build 1–4 包；此前文档中指向这些忽略路径的证据引用已不可复查，结论文字保留为历史记录。保留：Ref Island 各 Build 包与日志（`build-1/`、`build-2/` 的 RefIsland 部分，`island-device/`，签名 profile 路径与设备信息已移入其中）、`build-2/source/` 源码快照、全部源码目录与文档。
