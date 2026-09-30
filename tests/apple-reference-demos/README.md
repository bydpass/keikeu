# 三条参考入口 Demo

Road v00.09.01 的隔离机制实验，非产品实现。三个独立 App 使用相同三页合成内容；不读取 Vault，不保存输入，不接云、不使用推送或后台保活。复用已安装的 Ref Editor 作为独立进程的输入区，源码见[原探针](../apple-reference-probe/README.md)。

| Demo | 包标识 | 入口和用途 |
| --- | --- | --- |
| Ref Snippet | `app.keikeu.refsnippet` | App Shortcut 显示系统结果卡；操作按钮入口由用户主动选择；Build 4 增加正文滚动实验 |
| Ref Island | `app.keikeu.refisland` | App 主动开始 standard Live Activity，长按灵动岛展开、按钮翻页 |
| Ref Fusion | `app.keikeu.reffusion` | 灵动岛保留当前页；“展开参考”按钮尝试唤起系统 Snippet，卡片翻页更新活动页码 |

融合版是公开接口组合实验：编译成功不保证系统接受从 Live Activity 按钮呈现 Snippet。Build 2 返回卡片结果；当前 Fusion Build 3 改为点击时调用一次 `ReferenceSnippet.reload()`，不再同时返回卡片，分开验证两种机制。不用 App 内仿制浮层替代这个结果，也不自动跳回主 App 掩盖入口失败。

## 手机操作

每次只运行一条路线。测试 Island／Fusion 前，在另一个 Demo 中点“结束本 Demo 的参考”，避免两个活动使系统切换到最小呈现。

操作按钮绑定必须由用户主动 opt-in。首次安装、首次启动和普通打开应用均不提示或建议启用，不弹窗、不自动跳转系统设置。主页面只提供中性的“入口设置”；用户主动进入后才能看到占用原用途、配置与恢复说明。打开设置页本身不是更改授权；代操作仍须用户明确选择。无需新增持久化同意框架。

以后每个 Demo 都使用可区分的 AI 生成图标，便于识别安装项与系统入口；图标更换保持原 bundle ID，不用重建应用身份或卸载旧包来替换图标。生成、打包和实机显示分别核实，不把计划记为已经安装。

1. **Snippet**：仅在用户主动选择操作按钮实验后，验证 **Action button → Shortcut → Ref Snippet → Show Reference**。先记录原操作按钮绑定，取得临时更改授权后配置；在 Ref Editor 唤起手机惯用软键盘，长按实体操作按钮一次。若卡片出现，不先关闭卡片，直接在原文末尾输入 `AB-01`；分别记录卡片出现、输入时留存及编辑器实际接收内容，不以预期字符数代替实际观察。没有卡片就停止该轮，不反复按。测试后恢复原绑定。Spotlight 可独立检查系统呈现；Siri 是另一对照，不保证显示自定义卡片。不选择操作按钮不影响这些入口。
2. **Island**：打开 Ref Island → 开始参考 → 切到 Ref Editor、点输入区 → 长按灵动岛展开 → 尝试输入 `REF-001`。记录第一次点击键盘是否收回卡片、文字是否进入编辑器。展开时再单独检查下一页。
3. **Fusion（历史失败路径，暂不复试）**：打开 Ref Fusion → 开始参考 → 在 Ref Editor 长按灵动岛 → 翻到 2/3 → 点“展开参考”。先观察“已执行请求”是否增加，再观察是否出现系统卡片。若出现，检查是否为第 2 页；卡内翻到 3/3，再检查岛上页码。随后尝试原软键盘输入，分别记录卡片、岛和文字接收位置。

只有参考持续可见、文字实际进入 Ref Editor 且计数增加，才算所测入口的输入共存通过。背景看得见、光标闪烁、Mirroring／硬件键盘输入都不能替代。入口不呈现卡片与呈现后阻断输入分别记录；一条入口失败不否定所有其他入口。

Snippet 自定义视图最高 400pt。旧 Build 2／Fusion Build 3 的长页可能被 Demo 自身裁切，不能据此判定系统不支持滚动。独立 Ref Snippet Build 4 的正文改为 180pt ScrollView，文字保留完整高度，页码和下一页按钮放在滚动区域外；换页回到页首，不保存阅读位置。内存回退页、连点并发和渲染延迟不作产品保证；按顺序点击即可完成本轮机制筛查。

**Build 4 的手机验收（需主动选择操作按钮入口）**：在 Ref Editor 唤起原键盘，从操作按钮显示卡片，连续点两次下一页到 3/3。在正文内手指上滑，从“长页观察”滚到“十、这是本页末尾。”；只有正文移动、页码及按钮位置不变，才计为内层滚动通过。整张系统卡片移动另记为外层滚动。再翻到 1/3，保持卡片并输入中文，分别记录卡片留存与文字进入编辑器。通过后才到备忘录等真实编辑器复验。

Build 2 起，岛内正文最多两行、锁屏摘要最多三行；它们只作入口预览，不代表完整阅读通过。展开岛中的“已执行请求”只在 `OpenReferenceSnippet.perform()` 执行时累加，翻页保留计数。计数增加而卡片未出现，证明动作执行但该次没有呈现结果；计数没变还需考虑活动刷新延迟，不能单凭它断言没有点击。没有用计数冒充 Snippet 显示回执。

## 构建与检查

使用已有 XcodeGen、Xcode 27 SDK；最低部署版本 26.0。生成物全部位于忽略目录。

```sh
rtk proxy mkdir -p tests/test-vault/reference-demos
rtk proxy xcodegen generate --spec tests/apple-reference-demos/project.yml --project-root tests/test-vault/reference-demos --project tests/test-vault/reference-demos
rtk proxy xcrun swiftc tests/apple-reference-demos/Sample.swift tests/apple-reference-demos/check.swift -o tests/test-vault/reference-demos/page-check
rtk proxy tests/test-vault/reference-demos/page-check
rtk proxy xcodebuild -project tests/test-vault/reference-demos/ReferenceDemos.xcodeproj -scheme RefSnippet -configuration Debug -sdk iphoneos -destination generic/platform=iOS -derivedDataPath tests/test-vault/reference-demos/build build
```

将最后一条 scheme 分别替换为 `RefIsland`、`RefFusion`，顺序构建，避免共用 DerivedData 的数据库锁。Island／Fusion 各嵌入一个 Widget 扩展；App 声明 `NSSupportsLiveActivities`，没有 App Group 或推送 entitlement。

以上构建默认不签名。实机包沿用本机有效、覆盖测试设备的 wildcard 开发 profile，以各自具体 bundle ID 配置 application identifier；先签 dylib 和扩展，再签宿主，并做 strict／deep 验证。个人 profile、签名身份、设备标识及安装回执只留忽略目录，不提交。

## 2026-09-22 工程记录

- 工作树：`/Users/chenxi/.codex/worktrees/keikeu-reference-demos/keikeu`；分支：`codex/road-v00-09-01-reference-demos`；基础 HEAD：`d0a557a`。接入原规划文件和探针源码的当前副本，原主工作树保持不变。
- 页码检查通过，覆盖三页循环、负数及整数边界。
- 三个 iphoneos Debug 构建通过，两个 Widget 扩展随宿主构建。首次 Island 构建发现 Swift 6 静态可变属性并发检查，改为不可变常量后重新通过。
- 三份宿主与嵌入扩展签名验证通过。逐文件包摘要与源码摘要在 `tests/test-vault/reference-demos/signed-packages.json`；构建和安装回执也在该目录。
- 设备观察及输入共存结论以[研究记录](../../docs/road-v00-09-01-research-brief.md)后续条目为准。早先 Ref Probe 的通过结论不转移到三个新包。

用户随后报告融合按钮无响应、按钮下沿被黑边裁切。Build 2 将页码／标题移至灵动岛 leading／trailing 区域，正文限制两行，按钮保留布局空间并增加底部边距；另加入上述动作计数，保持“返回 Snippet 结果”的原实验路径，不增加定时器或重弹。三个 Build 2 构建、签名和更新安装通过；已启动融合活动并确认 Ref Editor 原 14 字符测试输入仍在。按钮完整性、计数及结果卡片呈现仍待本次手机复验，不能标为两个问题都已修复。Build 1 包与回执保留在忽略目录 `tests/test-vault/reference-demos/build-1/`。

后续复验：用户确认裁切解决、卡片依然没出现；主代理通过镜像看到按钮完整，并点击后观察“已执行请求”由 3 增至 4，未显示 Snippet。因此 Build 2 的按钮执行与布局已得到证据，此结果卡片路径未通过。Fusion Build 3 已单独构建、签名安装并重新启动活动，用户回报仍无效，主代理观察到“已执行请求 3”但没有系统卡片；此路径也未通过，停止重复尝试。Snippet／Island 仍为 Build 2。Build 2 包、源码、清单保留在 `tests/test-vault/reference-demos/build-2/`，Build 3 包摘要为同上级目录的 `fusion-build3-packages.json`。

官方依据：[Live Activity 生命周期](https://developer.apple.com/documentation/activitykit/displaying-live-data-with-live-activities)、[活动按钮](https://developer.apple.com/documentation/widgetkit/adding-interactivity-to-widgets-and-live-activities)、[系统 Snippet](https://developer.apple.com/documentation/appintents/displaying-static-and-interactive-snippets)、[Snippet 设计](https://developer.apple.com/design/human-interface-guidelines/snippets)。公开机制说明不代替本设备实测。

当前结论：Fusion 的“展开参考”按钮仅用于保留失败实验，不能作为可用的卡片入口。按钮布局已修复；直接返回结果和单次 reload 均未显示卡片。该结果不代替独立 Snippet 或灵动岛输入共存验收。

操作按钮补充实验：用户确认 Ref Snippet Build 2 经该入口显示卡片，并可保留卡片继续用手机软键盘输入；主代理重连看到 Ref Editor 计数 14→19。原 Show Code Scanner 绑定曾恢复并核实。随后仅 Ref Snippet 升至 Build 4，iphoneos 构建、现有开发签名 strict/deep 验证及安装回执均成功；当时再次临时绑定 Ref Snippet 供滚动实验；完成结果及第二轮恢复见下段。代码复核确认 Fusion 分支行为保留。此轮包摘要见 `tests/test-vault/reference-demos/snippet-build4-packages.json`，不沿用旧包输入共存结论直接接受新版。


Build 4 手机结果：用户明确在 **Ref Editor** 中测试，正文上滑失败、翻回 1/3 正常、输入正常但卡片遮住编辑正文。主代理重连看到计数 19→26 与新增拉丁字符；没有中文候选或保存测试。滚动失败仅限本次 180pt ScrollView 实现及设备宿主，遮挡另列为持续参考体验缺口。第二轮操作按钮已恢复为 **Shortcut → Show Code Scanner**，CUA 直接核实设置页；原临时绑定不再保留。

Build 5：三个 Demo 已统一构建并签名，加入三枚 AI 图标与用户主动访问的“入口设置”；包与源码摘要见忽略目录 `build5-packages.json`，签名日志为 `signing-build5.log`。截至 2026-09-26 尚未安装，图标实机显示未验证。首次安装、启动、普通打开不建议绑定操作按钮。不宣称滚动、遮挡或融合入口已经修复。既有 bundle ID 与历史实验包绑定保持不变。

## 第四条候选：Ref PiP（2026-09-26）

系统画中画逐屏实验放在独立子目录 [`pip-pager/`](pip-pager/README.md)：独立 XcodeGen 规格与 bundle ID `app.keikeu.refpip`，只读引用本目录 `Sample.swift`，不改动上述 Build 5 的源码、工程或包。部署版本 15.0；2026-09-29 Build 4 已签名安装到 iPhone 17 Pro／iOS 27.0，并取得启动、跨应用持续显示与后台翻页回调的真机证据；用户手机实测小窗持续可见、中文候选正常。模拟器结果仅作 legacy。路线比较见[设计说明](../../docs/design/road-v00-09-01-reference-window-design.md)。

## Ref Island Build 6：自动分段（2026-09-29）

目标改为“快速调出＋查看”后，灵动岛正文布局重构与分段规则放在独立子目录 [`island-pager/`](island-pager/README.md)，不改 Build 5 源码。已构建、签名验证，Build 6 经用户实测仅少许溢出，Build 8 改为渲染文字限 3 行、显示上限仍为 4 行，已替换安装（设备显示版本 8），用户定为首选；Build 10 融合版（岛速览＋系统卡片）真机可调出，用户定为首选。

2026-09-29 清理（用户要求“除 Ref Island 之外的所有残渣统统扫除”，范围：手机＋本地构建物）：手机已卸载 Ref Editor／Ref Fusion／Ref PiP／Ref Probe／Ref Snippet，只剩 Ref Island Build 10。忽略目录 `tests/test-vault/reference-demos/` 已删除非 Ref Island 的构建包、DerivedData、日志与回执，包括 Build 5 签名包与 `build5-packages.json`、PiP 的 `pip-device/`（含事件日志）与 `pip-pager/`、`archify-visual/`、Snippet／Fusion 的 Build 1–4 包；此前文档中指向这些忽略路径的证据引用已不可复查，结论文字保留为历史记录。保留：Ref Island 各 Build 包与日志（`build-1/`、`build-2/` 的 RefIsland 部分，`island-device/`，签名 profile 路径与设备信息已移入其中）、`build-2/source/` 源码快照、全部源码目录与文档。
