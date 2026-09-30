# Ref PiP：画中画逐屏参考实验

Road v00.09.01 隔离实验，非产品实现。回答一个问题：**系统画中画（PiP）能否承载预选的文字参考，用系统后退／前进键在小窗内翻页和逐屏阅读，同时外部编辑器继续用手机惯用软键盘输入？** 2026-09-29 起有真机证据（见下）；2026-09-26 的模拟器与编译结果降为 legacy 历史证据，不代替真机验收。

## 边界

- **不是任意可交互跨应用覆盖层。** 窗口由系统 PiP 承载，内容是本 App 渲染的视频帧；小窗内容不接收拖动或点按。手指滚动这项原始要求在 PiP 中**不可实现**；2026-09-29 用户表述“长文本滚动显示由播放‘快进/回退 10s’按钮实现”，本路线的长文阅读按此执行。
- 内容只用 [`Sample.swift`](../Sample.swift) 的三页合成文本（只读引用）和一张合成卡片。不读 Vault、不保存输入、不联网，没有推送、定时刷新或额外保活。
- 独立 bundle ID `app.keikeu.refpip`，独立 XcodeGen 规格；构建输出在忽略目录 `tests/test-vault/reference-demos/pip-device/`。上级 Build 5 的源码、工程与包不修改、不重建。
- **图标是临时标识，不是新 AI 图标。** `Icons/PiP.xcassets` 由已授权的 Ref Snippet 图标去色并加橙色“PiP 临时图标”横条生成（脚本 `pip-device/make-temp-icon.swift`）。正式 AI 图标仍需生图协作。

## iOS 15–27 兼容性

部署版本 15.0，是 Xcode 27 SDK 的最低值。能安装不等于所有能力可用：

| 能力 | 可用版本 | 旧版回退 |
| --- | --- | --- |
| 样本缓冲 PiP 内容源、`invalidatePlaybackState` | iOS 15.0+ | 无需回退；这是本路线的下限 |
| `AVSampleBufferDisplayLayer.sampleBufferRenderer` | iOS 17.0+ | iOS 15–16 用层级 `enqueue`／`flush`，`#available` 隔离，两条路径不混用 |
| `CMTimebase(sourceClock:)` 控制时基 | iOS 15.0+ | 无需回退 |
| `NavigationStack`、`LabeledContent` | iOS 16.0+ | 不使用；改用 `NavigationView` 与普通行 |
| `isPictureInPictureSupported()` | 设备决定 | 不支持时只显示原因，回退为应用内翻看再返回 |

实测只有 iPhone 17 Pro／iOS 27.0（24A435）。iOS 15–26 真机与 iOS 17 以下的层级路径**均未运行验证**；只证明编译通过。

## 链路

| 步骤 | 实现 | 说明 |
| --- | --- | --- |
| 选择参考 | `PiPPager.select` | 回到第一屏并重算屏数；小窗打开时也可在主应用更换整份参考 |
| 渲染 | `PiPRenderer.sample` | UIKit 文本画进 600×800 BGRA `CVPixelBuffer`，时间戳固定在控制时基的 12 小时处；每帧先 flush（保留当前画面）再入队 |
| 启动 | `PiPPager.start` | 仅由“开始小窗”触发：先激活 `.playback` 音频会话，等 `isPictureInPicturePossible` 变为 true 再启动；退到后台不自动弹出 |
| 翻页／逐屏 | `skipByInterval` → `ReaderStep.move` | 正向＝前进，负向＝后退；页内逐屏，页尾换页并循环；每次都调用 completion |
| 退出 | `didStop` | 小窗关闭或“退出小窗”后释放音频会话 |
| 证据 | `EventLog` | 应用 Documents 下 `pip-events.jsonl`，只记事件名、页／屏、应用状态与音频状态，不记正文 |

## 音频会话

- 启动 App 不触碰音频会话；点“开始小窗”才激活，退出或启动失败以 `.notifyOthersOnDeactivation` 释放；等待期间可“取消启动”。
- **真机确认：** 音频会话激活前 `possible` 一直为 false，激活后约 1 秒变为 true；默认 `.mixWithOthers` 可以启动 PiP。独占模式未测。
- 从不产生声音。分发风险（推断）：审核指南 2.5.4 要求后台服务用于本来用途。

## 构建、签名与安装

```sh
rtk proxy xcrun swiftc -swift-version 6 tests/apple-reference-demos/pip-pager/Reader.swift tests/apple-reference-demos/pip-pager/check.swift -o tests/test-vault/reference-demos/pip-pager/reader-check
rtk proxy tests/test-vault/reference-demos/pip-pager/reader-check
rtk proxy xcodegen generate --spec tests/apple-reference-demos/pip-pager/project.yml --project-root tests/test-vault/reference-demos/pip-pager --project tests/test-vault/reference-demos/pip-pager
rtk proxy xcodebuild -project tests/test-vault/reference-demos/pip-pager/ReferencePiP.xcodeproj -scheme RefPiP -configuration Debug -sdk iphoneos -destination generic/platform=iOS -derivedDataPath tests/test-vault/reference-demos/pip-device/build build
```

签名沿用 Build 5 的 wildcard 开发 profile（按包内 profile 摘要匹配）：先签两个 dylib，再用 `application-identifier` 为 `app.keikeu.refpip` 的 entitlements 签宿主，strict／deep 验证后以 `devicectl device install app` 安装。profile、身份与设备标识只留忽略目录。事件日志用 `devicectl device copy from --domain-type appDataContainer --domain-identifier app.keikeu.refpip --source Documents/pip-events.jsonl` 取回。

## 2026-09-29 真机证据（iPhone 17 Pro，iOS 27.0 24A435）

包：Build 2–4 各自签名验证与安装成功，摘要见 `pip-device/refpip-build{2,3,4}-packages.json`，Build 3／4 包另存 `build-3/`、`build-4/`。操作经 iPhone Mirroring 点按；日志取自设备。

| 检查 | 结果 | 边界 |
| --- | --- | --- |
| 启动 | `pipSupported: true`，渲染走 `sampleBufferRenderer` | 与模拟器的 false 不同 |
| 首帧 | Build 2 首帧空白；Build 3 在加入窗口时重绘后正常 | 已修复 |
| 按钮可达 | Build 2 开始按钮在折叠线下；Build 3 移到预览上方 | 已修复 |
| 启动 PiP | 音频激活后 `possible` 转 true，`pip_started`；窗口 285×380 px | 通过 |
| 跨应用持续显示 | 切到 Ref Editor 后小窗保持在上方（截图） | 通过；镜像观察 |
| 后退键 | 在 Ref Editor 前台时 `skip forward:false`，`appState: background`，画面换到 3/3 | 通过 |
| 前进键 | Build 3 时 ⏩ 置灰、进度条满；Build 4 加暂停控制时基后可用，`skip forward:true`，`appState: background` | 通过 |
| 连按 | 镜像点按间隔 1.5 秒时丢失跳转；用户手指连按时 19:06:22–39 共 35 次后台跳转全部到达，同一秒内多次也生效 | 丢失来自镜像点按，非系统限制 |
| 退出与音频 | 点 ✕ 后 `pip_stopped` 与 `audio_released`（无错误） | 通过（Build 3） |
| 软键盘共存、中文候选 | 用户手机实测：小窗一直可见，中文候选正常 | 通过（用户回报；日志含同期后台跳转） |
| 拖动、翻页后焦点 | 用户实测：可拖到角落，翻页后光标仍在 | 通过 |
| 遮挡与系统控件 | 播放／暂停等控件遮挡；切页使控件频繁常态显示；收起到侧边后不能当小抄 | **体验不合格，用户决定暂停本路线** |
| 手指滚动 | PiP 内容不接收拖动 | **未满足** |

本轮开始时 Ref Editor 进程已不在运行，原 26 字符内存输入在本轮操作前已丢失；之后按需启动为新进程（计数从 0 起）。

用户决定（2026-09-29，原话）：“长文本滚动显示由播放‘快进/回退 10s’按钮实现”。据此，PiP 路线的长文阅读以系统 ±10 秒键逐屏推进为准；手指拖动滚动在 PiP 中仍不可实现，这一技术事实保留记录。

## 真机最短 SOP：软键盘与中文

前提：Ref PiP Build 4 小窗已开在 Ref Editor 上方；不操作真实 Vault，不改操作按钮。

1. 在手机上点 Ref Editor 输入区，用惯用中文输入法输入“参考小窗”，从候选词中选字上屏，再输入 `PIP-01`。
2. 分别记录：小窗是否一直可见；候选栏是否正常；文字是否进入编辑器（计数变化）；小窗是否挡住正在输入的行；能否用手指把小窗拖到角落或缩小。
3. 键盘仍在时点小窗显示控件，按一次前进键；记录键盘是否收起、输入焦点是否保留。
4. 在小窗内容上手指上滑，记录正文是否滚动（预期不滚动）。

任何一步使小窗消失或输入受阻即停止并回报。完成后告诉主代理，由其取回事件日志。

## 来源与许可

- 本目录代码为本仓库原创，未复制第三方代码，无需附第三方许可文本。
- 参考阅读：[uakihir0/UIPiPView](https://github.com/uakihir0/UIPiPView)，MIT，Copyright (c) 2021 Akihiro Urushiara，固定 commit `55994ac410ec29d81958f689b22eae0917445da9`（2023-02-09，无 tag）。只借思路；未采用其 `try!` 音频会话、定时刷新和已弃用的层级调用。其 `skipByInterval` 只调用 completion，本实验的按键映射为自写。
- [CaiWanFeng/PiP](https://github.com/CaiWanFeng/PiP)（HEAD `c97832744a9bf6af005561e1f9fdcd9686bafb62`）未见项目自身许可证，未复制。[owngoal-dev/Letterpress](https://github.com/owngoal-dev/Letterpress) 为 MIT，但依赖 TrollStore 且已 EOL。
