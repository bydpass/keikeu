# 参考卡片输入共存探针

仅验证系统承载的 App Intents result Snippet 能否与另一个进程的惯用软键盘输入共存。`Ref Probe` 提供固定合成参考，`Ref Editor` 提供原生 UITextView 和已接收字符计数。无网络代码、云容器、Vault 访问或文稿保存，不代替产品实现。

使用已安装的 XcodeGen 与 SDK；不下载依赖，不写开发者门户。生成工程和产物放入忽略的 `tests/test-vault/reference-probe/`：

```sh
rtk proxy mkdir -p tests/test-vault/reference-probe
rtk proxy xcodegen generate --spec tests/apple-reference-probe/project.yml --project-root tests/test-vault/reference-probe --project tests/test-vault/reference-probe
rtk proxy xcodebuild -project tests/test-vault/reference-probe/ReferenceProbe.xcodeproj -scheme ReferenceProbe -configuration Debug -sdk iphoneos -destination generic/platform=iOS -derivedDataPath tests/test-vault/reference-probe/build build
rtk proxy xcodebuild -project tests/test-vault/reference-probe/ReferenceProbe.xcodeproj -scheme ReferenceEditor -configuration Debug -sdk iphoneos -destination generic/platform=iOS -derivedDataPath tests/test-vault/reference-probe/build build
```

上列只构建未签名包。实机安装前使用当前有效且覆盖设备的本机 wildcard 开发 profile，以各自独立 bundle ID 签名并验证；不使用旧候选或旧文件协调探针的包身份。签名与设备回执仅保存在忽略目录，不提交个人标识或 profile。

## 验证顺序

1. 在系统快捷指令中确认 `Ref Probe` 的 `Show Reference` 可发现。需要快捷方式时只新建实验专用项，不改用户原有快捷键／Action button。直接调用 `perform()` 或在应用内展示相似界面不算系统 Snippet。
2. 先单独调用，确认两页内容及按钮更新；记录具体系统入口。没有出现卡片只说明该入口／配置未成功，不证明输入共存失败。
3. 打开 `Ref Editor`，触碰合成输入区唤起惯用软键盘。通过上一项确认的系统入口显示 Snippet，再尝试在原编辑器输入 `REF-001`。
4. 分别记录触发时键盘是否仍在、第一次点击原键盘是否关闭卡片、字符是否进入原编辑器及计数是否增加。卡片保持可见且软键盘输入进入编辑器才通过。Siri／系统输入框收到文字、底层光标闪烁、硬件键盘输入都不能代替此条件。
5. 若卡片关闭或输入受阻，该入口停止；不开发长文滚动。仅本项通过后才添加滚动样本，验证当前系统的可达内容、分页、阅读位置与组合输入。不用失败入口否定所有其他系统承载入口。

`Ref Editor` 是隔离机制筛查；即使通过，仍需在系统备忘录等真实外部编辑器用合成文稿复验。当前结果见 Road 研究记录；构建成功不表示交互通过。
