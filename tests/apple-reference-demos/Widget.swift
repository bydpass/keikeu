import ActivityKit
import SwiftUI
import WidgetKit

private struct ReferenceControls: View {
    var body: some View {
        HStack(spacing: 12) {
            Button(intent: IslandNextPage()) {
                Text("下一页").frame(minHeight: 36)
            }
#if DEMO_FUSION
            Button(intent: OpenReferenceSnippet()) {
                Text("展开参考").frame(minHeight: 36)
            }
#endif
        }
        .font(.subheadline)
        .buttonStyle(.bordered)
        .fixedSize(horizontal: false, vertical: true)
        .layoutPriority(1)
    }
}

@main
struct ReferenceActivityWidget: Widget {
    var body: some WidgetConfiguration {
        ActivityConfiguration(for: ReferenceAttributes.self) { context in
            let page = ReferenceSample.normalizedPage(context.state.page)
            VStack(alignment: .leading, spacing: 8) {
                Text("合成参考 · \(page + 1)/\(ReferenceSample.pages.count)").font(.headline)
                Text(ReferenceSample.pages[page]).lineLimit(3)
#if DEMO_FUSION
                Text("已执行请求 \(context.state.snippetRequests ?? 0)").font(.caption)
#endif
                ReferenceControls()
            }
            .padding()
        } dynamicIsland: { context in
            let page = ReferenceSample.normalizedPage(context.state.page)
            return DynamicIsland {
                DynamicIslandExpandedRegion(.leading) {
#if DEMO_FUSION
                    Text("已执行请求 \(context.state.snippetRequests ?? 0)").font(.caption)
#else
                    Text("合成参考").font(.caption)
#endif
                }
                DynamicIslandExpandedRegion(.trailing) {
                    Text("\(page + 1)/\(ReferenceSample.pages.count)")
                        .font(.caption).monospacedDigit()
                }
                DynamicIslandExpandedRegion(.bottom) {
                    VStack(alignment: .leading, spacing: 4) {
                        // The island is a summary; long text must not displace controls.
                        Text(ReferenceSample.pages[page])
                            .font(.subheadline)
                            .lineLimit(2)
                            .frame(maxWidth: .infinity, alignment: .leading)
                        ReferenceControls()
                    }
                }
            } compactLeading: {
                Image(systemName: "text.rectangle")
                    .accessibilityLabel("合成参考")
            } compactTrailing: {
                Text("\(page + 1)/\(ReferenceSample.pages.count)")
                    .monospacedDigit()
            } minimal: {
                Text("\(page + 1)")
                    .monospacedDigit()
                    .accessibilityLabel("参考第 \(page + 1) 页")
            }
            .contentMargins(.horizontal, 16, for: .expanded)
            .contentMargins(.bottom, 12, for: .expanded)
        }
    }
}
