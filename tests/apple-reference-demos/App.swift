import SwiftUI
#if !DEMO_ISLAND
import AppIntents
#endif

@main
struct ReferenceDemoApp: App {
    @State private var status = "尚未开始"
    @State private var busy = false

    private var title: String {
        #if DEMO_ISLAND
        "Ref Island"
        #elseif DEMO_FUSION
        "Ref Fusion"
        #else
        "Ref Snippet"
        #endif
    }

    var body: some Scene {
        WindowGroup {
            NavigationStack {
                Form {
                    Section("合成参考实验") {
                        Text("只显示固定示例，不读取或保存你的文稿。")
                        #if DEMO_ISLAND
                        Text("开始后切到 Ref Editor，唤起手机键盘，长按灵动岛查看参考。")
                        #elseif DEMO_FUSION
                        Text("当前融合按钮未能显示系统卡片；保留此实验供对照。")
                        Text("实验 3：单次 reload，不再返回卡片结果。")
                        Text("“已执行请求”增加只证明按钮动作执行，不代表系统卡片已经出现。")
                        #else
                        Text("第三页正文用于手动滚动实验，页码和下一页按钮固定。")
                        #endif
                    }
                    #if DEMO_ISLAND || DEMO_FUSION
                    Section("灵动岛会话") {
                        Button("开始参考") {
                            busy = true
                            Task { @MainActor in
                                defer { busy = false }
                                do {
                                    try await ReferenceActivities.start()
                                    status = "已请求显示；切换应用观察灵动岛"
                                } catch {
                                    status = "未能开始：\(error.localizedDescription)"
                                }
                            }
                        }
                        .disabled(busy)
                        Button("结束本 Demo 的参考") {
                            busy = true
                            Task { @MainActor in
                                await ReferenceActivities.end()
                                status = "已结束本 Demo 的参考"
                                busy = false
                            }
                        }
                        .disabled(busy)
                        Text(status).accessibilityIdentifier("activity-status")
                    }
                    #endif
                    #if !DEMO_ISLAND
                    Section {
                        NavigationLink("入口设置") {
                            Form {
                                Section("系统卡片") {
                                    ShortcutsLink()
                                    Text("Spotlight 搜索 Show Reference，按应用名选择 \(title) 的动作。")
                                    Text("Siri 可尝试：Show reference in \(title)。没有显示卡片时，只记录入口未触发。")
                                }
                                Section("操作按钮（可选）") {
                                    Text("绑定本 Demo 会替换操作按钮原来的用途；是否更改由你决定。打开此页不会修改系统设置。")
                                    Text("若决定使用：先记下原绑定，再到系统设置的“操作按钮”选择快捷指令，选取 \(title) 的 Show Reference。")
                                    Text("恢复原用途：回到系统设置的“操作按钮”，重新选择你记录的原绑定。")
                                }
                            }
                            .navigationTitle("入口设置")
                        }
                    }
                    #endif
                    Section("观察什么") {
                        Text("显示参考后，在 Ref Editor 用手机原键盘输入 REF-001。记录参考是否消失、文字是否进入编辑器。")
                        #if DEMO_ISLAND || DEMO_FUSION
                        Text("三页合成内容可循环翻页。本 Demo 限制卡片高度，长页可能截断；本轮不测试滚动能力。")
                        #else
                        Text("翻到 3/3，从“长页观察”手动滚到“十、这是本页末尾。”；观察页码和按钮是否保持原位。再翻到 1/3，并继续用手机键盘输入。")
                        #endif
                    }
                }
                .navigationTitle(title)
            }
        }
    }
}
