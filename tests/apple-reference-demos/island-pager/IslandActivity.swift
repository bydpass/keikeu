import ActivityKit
import AppIntents

/// Same type name and a subset of Build 2's state keys, so an activity left running by Build 2 still decodes.
/// `page` now holds the index into `IslandSegments.all`.
@available(iOS 17.0, *)
struct ReferenceAttributes: ActivityAttributes {
    struct ContentState: Codable, Hashable {
        var page: Int
    }
}

@available(iOS 17.0, *)
@MainActor
enum IslandActivities {
    static func start() throws {
        guard Activity<ReferenceAttributes>.activities.isEmpty else { return }
        _ = try Activity<ReferenceAttributes>.request(
            attributes: ReferenceAttributes(),
            content: ActivityContent(state: .init(page: 0), staleDate: nil),
            pushType: nil
        )
    }

    static func end() async {
        for activity in Activity<ReferenceAttributes>.activities {
            await activity.end(nil, dismissalPolicy: .immediate)
        }
    }

    /// The shared reading position while an island is running; nil otherwise.
    static func current() -> Int? {
        Activity<ReferenceAttributes>.activities.first.map { IslandSegments.normalized($0.content.state.page) }
    }

    /// Moves every running island to `index`; returns false when none is running.
    @discardableResult
    static func set(_ index: Int) async -> Bool {
        let activities = Activity<ReferenceAttributes>.activities
        for activity in activities {
            await activity.update(ActivityContent(state: .init(page: IslandSegments.normalized(index)), staleDate: nil))
        }
        return !activities.isEmpty
    }
}

@available(iOS 17.0, *)
struct IslandStep: LiveActivityIntent {
    static let title: LocalizedStringResource = "参考翻段"
    static let isDiscoverable: Bool = false
    static let openAppWhenRun: Bool = false

    @Parameter(title: "向后") var forward: Bool

    init() {}
    init(forward: Bool) { self.forward = forward }

    @MainActor
    func perform() async throws -> some IntentResult {
        let begin = Date()
        guard let current = IslandActivities.current() else { return .result() }
        let next = IslandSegments.step(current, by: forward ? 1 : -1)
        await IslandActivities.set(next)
        FusionLog.write("island_step", ["index": next, "ms": FusionLog.ms(since: begin)])
        return .result()
    }
}
