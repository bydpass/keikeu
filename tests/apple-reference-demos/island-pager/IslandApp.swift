import SwiftUI

@main
struct IslandPagerApp: App {
    @State private var status = "尚未开始"
    @State private var busy = false

    init() {
        // Ask the system to (re)index this app's shortcut so Spotlight lists the new card entry.
        if #available(iOS 26.0, *) { IslandShortcuts.updateAppShortcutParameters() }
    }

    private func manualStatus(_ text: String) -> String {
        switch IslandSegments.manualSplit(text) {
        case .accepted(let spans):
            return "已接受，共 \(spans.count) 段"
        case .rejected(let span, let lines):
            return "已打回：第 \(span) 段约 \(lines) 行，超过每段 \(IslandSegments.renderLines) 行的渲染上限，请在这段中间再加一个切点"
        }
    }

    var body: some Scene {
        WindowGroup {
            NavigationView {
                Form {
                    Section("用法提示") {
                        Text("只显示固定合成示例，不读取或保存你的文稿。")
                        Text("开始后切到 Ref Editor。需要参考时长按灵动岛展开，用左右箭头逐段翻看；看完点输入区继续写，岛会按系统规则收起。")
                        Text("长文已按岛内 \(IslandSegments.renderLines) 行自动分段，不需要在岛内滚动。")
                        Text("融合实验（iOS 26+）：在 Spotlight 搜“Island Reference”，或用快捷指令调出大卡片；卡片从岛当前段开始连显 3 段，卡片里翻段会同步到岛。操作按钮入口需你自行在系统设置中选择。")
                    }
                    Section("灵动岛会话") {
                        if #available(iOS 17.0, *) {
                            Button("开始参考") {
                                do {
                                    try IslandActivities.start()
                                    status = "已开始；切换应用后长按灵动岛"
                                } catch {
                                    status = "未能开始：\(error.localizedDescription)"
                                }
                            }
                            Button("结束参考") {
                                busy = true
                                Task { @MainActor in
                                    await IslandActivities.end()
                                    status = "已结束"
                                    busy = false
                                }
                            }
                            .disabled(busy)
                            Text(status)
                        } else {
                            Text("岛内翻段按钮需要 iOS 17 及以上；本系统只能在下方预览中翻看。")
                        }
                    }
                    Section("手动切点（进一步模式）") {
                        Text("第 5 页用手动标记切分：\(manualStatus(IslandSegments.manualPage))")
                        // Synthetic oversized span, so the rejection message itself can be seen on device.
                        Text("超长示例：\(manualStatus("短句。｜" + String(repeating: "字", count: IslandSegments.maxCutUnits / 2 + 1)))")
                    }
                    Section("分段预览（共 \(IslandSegments.all.count) 段）") {
                        ForEach(IslandSegments.all, id: \.self) { segment in
                            VStack(alignment: .leading, spacing: 4) {
                                Text("第 \(segment.page + 1) 页 · 段 \(segment.part + 1)/\(segment.parts)")
                                    .font(.caption).foregroundColor(.secondary)
                                Text(segment.text).font(.footnote)
                            }
                        }
                    }
                }
                .navigationTitle("Ref Island")
            }
            .navigationViewStyle(.stack)
        }
    }
}
