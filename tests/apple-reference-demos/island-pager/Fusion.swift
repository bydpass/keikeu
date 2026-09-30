import AppIntents
import SwiftUI

/// Fusion: the island is the 3-line glance, a system snippet card is the longer view.
/// Both read and write one reading position, the island's segment index.
@available(iOS 26.0, *)
@MainActor
enum CardPosition {
    // ponytail: process memory only; used when no island runs, a product reader would persist it.
    static var fallback = 0
    static var shownAt: Date?

    static var current: Int { IslandActivities.current() ?? IslandSegments.normalized(fallback) }
}

@available(iOS 26.0, *)
struct ShowIslandReference: AppIntent {
    // Unique wording: Ref Snippet/Fusion already register "Show Reference", and Spotlight showed theirs instead.
    static let title: LocalizedStringResource = "Island Reference Card"
    static let description = IntentDescription("Show the island's synthetic reference in a larger system card.")
    static let openAppWhenRun = false

    @MainActor
    func perform() async throws -> some IntentResult & ShowsSnippetIntent {
        CardPosition.shownAt = Date()
        FusionLog.write("card_requested", [
            "index": CardPosition.current,
            "hasActivity": IslandActivities.current() == nil ? 0 : 1,
        ])
        return .result(snippetIntent: IslandReferenceCard())
    }
}

@available(iOS 26.0, *)
struct CardStep: AppIntent {
    static let title: LocalizedStringResource = "参考卡片翻段"
    static let isDiscoverable: Bool = false
    static let openAppWhenRun: Bool = false

    @Parameter(title: "向后") var forward: Bool

    init() {}
    init(forward: Bool) { self.forward = forward }

    @MainActor
    func perform() async throws -> some IntentResult {
        let begin = Date()
        let next = IslandSegments.step(CardPosition.current, by: forward ? 1 : -1)
        CardPosition.fallback = next
        let synced = await IslandActivities.set(next)
        CardPosition.shownAt = Date()
        FusionLog.write("card_step", ["index": next, "ms": FusionLog.ms(since: begin), "hasActivity": synced ? 1 : 0])
        return .result()
    }
}

@available(iOS 26.0, *)
struct IslandReferenceCard: SnippetIntent {
    static let title: LocalizedStringResource = "Island Reference Card"
    static let isDiscoverable = false

    @MainActor
    func perform() async throws -> some IntentResult & ShowsSnippetView {
        let window = IslandSegments.window(from: CardPosition.current)
        let first = window[0]
        FusionLog.write("card_rendered", [
            "index": IslandSegments.normalized(CardPosition.current),
            "segments": window.count,
            "ms": CardPosition.shownAt.map { FusionLog.ms(since: $0) } ?? -1,
        ])
        let range = window.count > 1 ? "\(first.part + 1)–\(first.part + window.count)" : "\(first.part + 1)"
        return .result(view:
            VStack(alignment: .leading, spacing: 10) {
                HStack {
                    Button(intent: CardStep(forward: false)) {
                        Image(systemName: "chevron.left").accessibilityLabel("上一段")
                    }
                    Spacer()
                    Text("参考 \(first.page + 1)/\(IslandSegments.pages.count) · 段 \(range)/\(first.parts)")
                        .font(.caption).monospacedDigit()
                    Spacer()
                    Button(intent: CardStep(forward: true)) {
                        Image(systemName: "chevron.right").accessibilityLabel("下一段")
                    }
                }
                .buttonStyle(.bordered)
                // The first segment is what the island shows; the rest continue the same page.
                ForEach(window, id: \.self) { segment in
                    Text(segment.text)
                        .font(.callout)
                        .foregroundStyle(segment == first ? .primary : .secondary)
                        .lineLimit(IslandSegments.displayLines)
                        .frame(maxWidth: .infinity, alignment: .leading)
                }
            }
            .padding()
            .frame(maxHeight: 400, alignment: .top)
        )
    }
}

@available(iOS 26.0, *)
struct IslandShortcuts: AppShortcutsProvider {
    static var appShortcuts: [AppShortcut] {
        AppShortcut(
            intent: ShowIslandReference(),
            phrases: ["Show island reference in \(.applicationName)", "Open \(.applicationName) card"],
            shortTitle: "Island Reference",
            systemImageName: "text.rectangle"
        )
    }
}
