# Road v00.09.01 参考小窗：路线原型与结论

状态：2026-09-26 设计原型与隔离实验；2026-09-29 取得 Ref PiP 首批真机证据。视觉原型与架构图保留 09-26 快照，最新证据以本文与 [Ref PiP README](../../tests/apple-reference-demos/pip-pager/README.md) 为准。本文不启动产品 CP0，不宣称 Road 完成，也不代表任何路线已满足持续参考目标。

- 视觉原型：[参考小窗路线原型](road-v00-09-01-reference-window-prototype.html)（设计模拟，网页绘制的手机画面不是已实现的跨应用覆盖层）。
- 代码架构：[Ref PiP 架构图](../architecture/road-v00-09-01-reference-pip.html)，规格与回执见同目录 `road-v00-09-01-reference-pip.archify.json`、`road-v00-09-01-reference-pip.receipt.json`。
- 实验源码与真机 SOP：[Ref PiP](../../tests/apple-reference-demos/pip-pager/README.md)；既有三路线见 [Demo 说明](../../tests/apple-reference-demos/README.md)，设备记录见[研究记录](../road-v00-09-01-research-brief.md)。

## 目标

即兴输入沉淀为稳定私密的 Paper；创作者主动选择直接使用只读 Paper，或整理为 flashcard。理想形态：选好一份参考后，在任意外部 iPhone 编辑器上方持续显示，惯用软键盘正常写作、正文可见；小窗只做滚动与翻页，更换整份参考回主应用。自动滚动、语音、倾斜或频繁切回应用不能静默替代手指滚动。

2026-09-29 用户调整目标（适用于所有路线）：经短时探索，“打字时持续显示参考”不切实际，验收目标改为“**可以快速被调出＋查看**”——写作中能迅速唤出参考、看清内容、再回到输入。

## 结论

1. **PiP 逐屏（Ref PiP，已暂停）。** 2026-09-29 在 iPhone 17 Pro／iOS 27.0 上已证实：小窗启动、切到 Ref Editor 后持续显示、系统前进／后退键在 Ref PiP 处于后台时回调并换屏、退出释放音频会话。用户随后手机实测：小窗一直可见，中文候选正常。手指滚动在 PiP 中不可实现；用户表述“长文本滚动显示由播放‘快进/回退 10s’按钮实现”，本路线长文阅读按此执行。
2. **已有证据最多：Snippet。** 操作按钮唤出的系统卡片在 Ref Editor 中与手机软键盘输入共存、按钮翻页正常；但 Build 4 的内层滚动失败，卡片遮住正在编辑的正文，仍未达标。
3. **灵动岛：** 2026-09-29 实测展开只占顶部约 1/5、输入与候选正常，但一碰输入区或键盘即收起；按新目标“快速调出＋查看”形态合格。Build 6／7 以自动分段（手动切点限“进一步”模式、超行打回；自动切点在溢出前最近标点截断）替代岛内滚动，Build 8 渲染文字限 3 行、显示上限仍为 4 行；用户实测评价“这个试验方案简直完美”。2026-09-29 用户确认 Build 8 不再溢出。**其后用户以 Build 10 融合版（岛速览＋系统卡片长看，共用阅读位置）取代为首选**，见 [Ref Island Build 6–10](../../tests/apple-reference-demos/island-pager/README.md)。**融合入口：** 两种衔接均只增加计数、没有卡片，已停止重试。
4. 没有任何路线满足全部要求。是否接受“按键逐屏”替代手指滚动、是否接受音频会话及审核风险，由用户决定。

## 未满足的要求

| 要求 | 现状 |
| --- | --- |
| 小窗内手指滚动 | PiP 内容不接收拖动，结构性不满足；Snippet Build 4 实测失败；灵动岛无滚动容器 |
| 惯用中文输入法 | 所有路线都没有中文候选或组合输入的设备证据 |
| 真实外部编辑器 | 只在合成的 Ref Editor 测过；备忘录等真实编辑器未测 |
| 正文可见 | Snippet 实测遮挡；PiP 可移开仅为系统行为推断，未在本 App 实测 |
| PiP 输入细节 | 软键盘共存与中文候选已由用户实测通过；正文遮挡、拖动缩放与翻页后焦点未单独记录；iOS 15–26 未验 |
| 阅读位置恢复 | 实验只存进程内存；产品需另行设计持久化 |
| 图标 | Ref PiP 使用由 Snippet 图标派生的临时标识；正式 AI 图标待生图协作 |
| 旧系统 | 部署版本 15.0 并按版本隔离 API；iOS 15–26 无真机，未运行验证 |

## 证据边界

| 证据 | 对应物 | 能证明 | 不能证明 |
| --- | --- | --- | --- |
| 真机（2026-09-22） | Ref Snippet Build 2／4、Ref Island Build 2、Ref Fusion Build 2／3，iPhone 17 Pro／iOS 27.0 | 研究记录所列的卡片呈现、拉丁字符输入、按钮翻页、滚动失败、遮挡、融合失败 | 中文输入、真实编辑器、Build 5、PiP |
| 纯逻辑（2026-09-26） | `pip-pager/check.swift` | 逐屏、跨页、循环与越界规则 | 任何系统行为 |
| 编译（2026-09-26） | RefPiP iphoneos 与 iOS 26.5 模拟器 Debug，未签名 | 源码可构建、背景模式写入 Info.plist | 设备运行 |
| 真机（2026-09-29） | Ref PiP Build 2–4，iPhone 17 Pro／iOS 27.0，镜像点按＋设备事件日志 | PiP 启动、跨应用持续显示、后台前进／后退回调、退出释放音频、`.mixWithOthers` 可启动 | 软键盘、中文、遮挡、连按、旧系统 |
| 模拟器（2026-09-26，legacy） | iOS 26.5 iPhone 17 Pro | 首帧经 `AVSampleBufferDisplayLayer` 渲染；该模拟器 `isPictureInPictureSupported()` 为 false | PiP 启动、翻页、键盘共存 |
| 设计模拟 | 视觉原型 | 流程与取舍的讨论材料 | 任何平台能力 |
| 营销描述 | Pip Up、Transparent Notes、Picture in Picture Notes | 同类产品宣称的形态 | 其小窗翻页、键盘共存或手指滚动 |

Build 5 三个 Demo 已构建签名、尚未安装，本轮未改其源码与包；其源码摘要仍与 `build5-packages.json` 一致。

## 真机最短 SOP

按 [Ref PiP README](../../tests/apple-reference-demos/pip-pager/README.md) 的“真机最短 SOP”执行：开始小窗 → 切到 Ref Editor 用中文软键盘输入 → 前进／后退换屏 → 小窗内上滑 → 回主应用换参考 → 关闭并检查音乐是否被打断。任何一步失败即停。前提是用户授权安装并补齐图标；不操作真实 Vault，不改操作按钮。
