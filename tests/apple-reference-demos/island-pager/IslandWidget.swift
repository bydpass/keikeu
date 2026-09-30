import ActivityKit
import SwiftUI
import WidgetKit

private func label(_ segment: IslandSegment) -> String {
    let page = "\(segment.page + 1)/\(IslandSegments.pages.count)"
    return segment.parts > 1 ? "参考 \(page) · 段 \(segment.part + 1)/\(segment.parts)" : "参考 \(page)"
}

private struct StepButton: View {
    let forward: Bool
    var body: some View {
        Button(intent: IslandStep(forward: forward)) {
            Image(systemName: forward ? "chevron.right" : "chevron.left")
                .frame(width: 36, height: 30)
                .accessibilityLabel(forward ? "下一段" : "上一段")
        }
        .buttonStyle(.bordered)
    }
}

/// Segments hold `renderLines`; the view reserves `displayLines`, so the text never needs to scroll or push the buttons.
private struct SegmentText: View {
    let segment: IslandSegment
    var body: some View {
        Text(segment.text)
            .font(.footnote)
            .lineLimit(IslandSegments.displayLines, reservesSpace: true)
            .frame(maxWidth: .infinity, alignment: .topLeading)
    }
}

@main
struct IslandPagerWidget: Widget {
    var body: some WidgetConfiguration {
        ActivityConfiguration(for: ReferenceAttributes.self) { context in
            let segment = IslandSegments.all[IslandSegments.normalized(context.state.page)]
            VStack(alignment: .leading, spacing: 8) {
                HStack {
                    StepButton(forward: false)
                    Spacer()
                    Text(label(segment)).font(.caption).monospacedDigit()
                    Spacer()
                    StepButton(forward: true)
                }
                SegmentText(segment: segment)
            }
            .padding()
        } dynamicIsland: { context in
            let segment = IslandSegments.all[IslandSegments.normalized(context.state.page)]
            return DynamicIsland {
                // Buttons live beside the camera, so the whole bottom region is free for text.
                DynamicIslandExpandedRegion(.leading) { StepButton(forward: false) }
                DynamicIslandExpandedRegion(.trailing) { StepButton(forward: true) }
                DynamicIslandExpandedRegion(.center) {
                    Text(label(segment)).font(.caption2).monospacedDigit().lineLimit(1)
                }
                DynamicIslandExpandedRegion(.bottom) { SegmentText(segment: segment) }
            } compactLeading: {
                Image(systemName: "text.rectangle")
                    .accessibilityLabel("合成参考")
            } compactTrailing: {
                Text("\(segment.page + 1)·\(segment.part + 1)")
                    .monospacedDigit()
            } minimal: {
                Text("\(segment.page + 1)")
                    .monospacedDigit()
                    .accessibilityLabel("参考第 \(segment.page + 1) 页")
            }
            .contentMargins(.horizontal, 16, for: .expanded)
            .contentMargins(.bottom, 10, for: .expanded)
        }
    }
}
