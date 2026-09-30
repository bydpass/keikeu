import AppIntents
import SwiftUI

// Synthetic content only. The system must present the result; an in-app overlay
// cannot establish whether another app still receives keyboard input.
@MainActor
enum ReferenceState {
    static var page = 0
    static let pages = [
        "她在等一个不会回来的人。\n表面目标：寄出这封信。\n真实愿望：有人告诉她，不必再等。",
        "雨声忽然停了，她却没有抬头。\n先写灯光，再写脚步。\n把答案留在门外，让读者先听见它。",
    ]
}

struct ShowReference: AppIntent {
    static let title: LocalizedStringResource = "Show Reference"
    static let description = IntentDescription("Show a synthetic reference card for an input coexistence experiment.")
    static let openAppWhenRun = false

    @MainActor
    func perform() async throws -> some IntentResult & ShowsSnippetIntent {
        ReferenceState.page = 0
        return .result(snippetIntent: ReferenceSnippet())
    }
}

struct TurnReferencePage: AppIntent {
    static let title: LocalizedStringResource = "Turn Reference Page"
    static let isDiscoverable = false

    @MainActor
    func perform() async throws -> some IntentResult {
        ReferenceState.page = (ReferenceState.page + 1) % ReferenceState.pages.count
        return .result()
    }
}

struct ReferenceSnippet: SnippetIntent {
    static let title: LocalizedStringResource = "Reference Card"
    static let isDiscoverable = false

    @MainActor
    func perform() async throws -> some IntentResult & ShowsSnippetView {
        let page = ReferenceState.page
        return .result(view:
            VStack(alignment: .leading, spacing: 12) {
                HStack {
                    Text("KEIKEU · 合成参考").font(.caption)
                    Spacer()
                    Text("\(page + 1) / 2").monospacedDigit()
                }
                Text(ReferenceState.pages[page]).font(.body)
                Button(intent: TurnReferencePage()) {
                    Label("翻页", systemImage: "arrow.right")
                }
            }
            .padding()
        )
    }
}

struct ReferenceShortcuts: AppShortcutsProvider {
    static var appShortcuts: [AppShortcut] {
        AppShortcut(
            intent: ShowReference(),
            phrases: ["Show reference in \(.applicationName)"],
            shortTitle: "Show Reference",
            systemImageName: "text.rectangle"
        )
    }
}

@main
struct ReferenceProbeApp: App {
    var body: some Scene {
        WindowGroup {
            NavigationStack {
                List {
                    Section("Snippet 输入共存实验") {
                        Text("本应用只提供两页合成内容，不读取或保存作者文稿。")
                        Text("通过系统快捷指令运行 Show Reference；本页不模拟系统卡片。")
                        ShortcutsLink()
                    }
                    Section("停止条件") {
                        Text("在 Ref Editor 唤起原软键盘，再触发参考卡片。若卡片关闭、键盘消失或输入被截获，该入口不满足持续参考。")
                    }
                }
                .navigationTitle("Ref Probe")
            }
        }
    }
}
