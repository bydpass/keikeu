import AppIntents
import SwiftUI

@MainActor
enum SnippetPage {
    // ponytail: standalone demo state lasts only for this process; a product
    // reader would restore its selected Paper and page from its own store.
    static var value = 0
}

struct ShowReference: AppIntent {
    static let title: LocalizedStringResource = "Show Reference"
    static let description = IntentDescription("Show synthetic reference text in a system snippet.")
    static let openAppWhenRun = false

    @MainActor
    func perform() async throws -> some IntentResult & ShowsSnippetIntent {
        #if DEMO_FUSION
        SnippetPage.value = ReferenceSample.normalizedPage(ReferenceActivities.currentPage() ?? SnippetPage.value)
        #else
        SnippetPage.value = 0
        #endif
        return .result(snippetIntent: ReferenceSnippet())
    }
}

#if DEMO_FUSION
struct OpenReferenceSnippet: LiveActivityIntent {
    static let title: LocalizedStringResource = "Open Reference Card"
    static let isDiscoverable = false
    static let openAppWhenRun = false

    @MainActor
    func perform() async throws -> some IntentResult {
        await ReferenceActivities.recordSnippetRequest()
        SnippetPage.value = ReferenceSample.normalizedPage(ReferenceActivities.currentPage() ?? SnippetPage.value)
        // Build 3 tests only this user-initiated reload, separately from build 2's
        // returned snippet result. No retries, timers, or background keep-alive.
        ReferenceSnippet.reload()
        return .result()
    }
}

struct TurnReferencePage: LiveActivityIntent {
    static let title: LocalizedStringResource = "Next Reference Page"
    static let isDiscoverable = false
    static let openAppWhenRun = false

    @MainActor
    func perform() async throws -> some IntentResult {
        let current = ReferenceActivities.currentPage() ?? SnippetPage.value
        let page = ReferenceSample.nextPage(current)
        SnippetPage.value = page
        await ReferenceActivities.setPage(page)
        return .result()
    }
}
#else
struct TurnReferencePage: AppIntent {
    static let title: LocalizedStringResource = "Next Reference Page"
    static let isDiscoverable = false
    static let openAppWhenRun = false

    @MainActor
    func perform() async throws -> some IntentResult {
        SnippetPage.value = ReferenceSample.nextPage(SnippetPage.value)
        return .result()
    }
}
#endif

struct ReferenceSnippet: SnippetIntent {
    static let title: LocalizedStringResource = "Reference Card"
    static let isDiscoverable = false

    @MainActor
    func perform() async throws -> some IntentResult & ShowsSnippetView {
        #if DEMO_FUSION
        let page = ReferenceSample.normalizedPage(ReferenceActivities.currentPage() ?? SnippetPage.value)
        #else
        let page = ReferenceSample.normalizedPage(SnippetPage.value)
        #endif
        return .result(view:
            VStack(alignment: .leading, spacing: 12) {
                HStack {
                    Text("合成参考").font(.caption)
                    Spacer()
                    Text("\(page + 1) / \(ReferenceSample.pages.count)").monospacedDigit()
                }
                #if DEMO_FUSION
                Text(ReferenceSample.pages[page])
                    .font(.body)
                    .frame(maxWidth: .infinity, alignment: .leading)
                #else
                ScrollView {
                    Text(ReferenceSample.pages[page])
                        .font(.body)
                        .fixedSize(horizontal: false, vertical: true)
                        .frame(maxWidth: .infinity, alignment: .leading)
                }
                .frame(height: 180)
                // Each page starts at its top; this probe does not restore scroll positions.
                .id(page)
                #endif
                Button(intent: TurnReferencePage()) {
                    Label("下一页", systemImage: "arrow.right")
                }
                .layoutPriority(1)
            }
            .padding()
            // A system-sized card; only a device test can show whether the
            // standalone body's ScrollView accepts gestures in this host.
            .frame(maxHeight: 400, alignment: .top)
            .clipped()
        )
    }
}

#if !WIDGET_EXTENSION
struct SnippetShortcuts: AppShortcutsProvider {
    static var appShortcuts: [AppShortcut] {
        AppShortcut(
            intent: ShowReference(),
            phrases: ["Show reference in \(.applicationName)"],
            shortTitle: "Show Reference",
            systemImageName: "text.rectangle"
        )
    }
}
#endif
