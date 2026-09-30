// Pure reading-position rules for the Ref PiP experiment; no UIKit or AVKit.
struct ReaderPosition: Equatable, Sendable {
    var page = 0
    var screen = 0
}

enum ReaderStep {
    /// Screens needed to show a page body through a fixed viewport, advancing
    /// `step` points per screen; the last screen is clamped to the page end.
    static func screenCount(bodyHeight: Double, viewport: Double, step: Double) -> Int {
        let hidden = bodyHeight - viewport
        guard hidden > 0, step > 0 else { return 1 }
        return Int((hidden / step).rounded(.up)) + 1
    }

    static func offset(screen: Int, bodyHeight: Double, viewport: Double, step: Double) -> Double {
        min(Double(max(screen, 0)) * step, max(0, bodyHeight - viewport))
    }

    /// One system skip press: move a screen inside the page, then cross to the
    /// neighbouring page, cycling like the other demos.
    /// ponytail: stepped button reading, not finger scrolling. The PiP window
    /// forwards no drag gestures, so this cannot satisfy the finger-scroll goal.
    static func move(_ position: ReaderPosition, forward: Bool, screenCounts: [Int]) -> ReaderPosition {
        guard !screenCounts.isEmpty else { return position }
        let count = screenCounts.count
        let page = (position.page % count + count) % count
        let last = max(1, screenCounts[page]) - 1
        let screen = min(max(position.screen, 0), last)
        if forward {
            return screen < last
                ? ReaderPosition(page: page, screen: screen + 1)
                : ReaderPosition(page: (page + 1) % count, screen: 0)
        }
        if screen > 0 { return ReaderPosition(page: page, screen: screen - 1) }
        let previous = (page + count - 1) % count
        return ReaderPosition(page: previous, screen: max(1, screenCounts[previous]) - 1)
    }
}
