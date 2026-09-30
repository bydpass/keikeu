import ActivityKit
import AppIntents

struct ReferenceAttributes: ActivityAttributes {
    struct ContentState: Codable, Hashable {
        var page: Int
        // Optional so an activity started by build 1 still decodes.
        var snippetRequests: Int?
    }
}

@MainActor
enum ReferenceActivities {
    static func start() async throws {
        guard Activity<ReferenceAttributes>.activities.isEmpty else { return }
        _ = try Activity<ReferenceAttributes>.request(
            attributes: ReferenceAttributes(),
            content: ActivityContent(state: .init(page: 0), staleDate: nil),
            pushType: nil,
            style: .standard
        )
    }

    static func end() async {
        for activity in Activity<ReferenceAttributes>.activities {
            await activity.end(nil, dismissalPolicy: .immediate)
        }
    }

    static func currentPage() -> Int? {
        Activity<ReferenceAttributes>.activities.first.map {
            ReferenceSample.normalizedPage($0.content.state.page)
        }
    }

    static func setPage(_ page: Int) async {
        for activity in Activity<ReferenceAttributes>.activities {
            var state = activity.content.state
            state.page = ReferenceSample.normalizedPage(page)
            await activity.update(ActivityContent(state: state, staleDate: nil))
        }
    }

    static func recordSnippetRequest() async {
        for activity in Activity<ReferenceAttributes>.activities {
            var state = activity.content.state
            state.snippetRequests = (state.snippetRequests ?? 0) + 1
            await activity.update(ActivityContent(state: state, staleDate: nil))
        }
    }
}

struct IslandNextPage: LiveActivityIntent {
    static let title: LocalizedStringResource = "参考下一页"
    static let isDiscoverable: Bool = false
    static let openAppWhenRun: Bool = false

    @MainActor
    func perform() async throws -> some IntentResult {
        if let page = ReferenceActivities.currentPage() {
            await ReferenceActivities.setPage(ReferenceSample.nextPage(page))
        }
        return .result()
    }
}
