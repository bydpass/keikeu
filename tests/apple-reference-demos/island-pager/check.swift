@main
struct SegmentCheck {
    static func main() {
        let all = IslandSegments.all
        precondition(!all.isEmpty)
        precondition(IslandSegments.renderLines < IslandSegments.displayLines)
        for segment in all {
            let lines = segment.text.split(separator: "\n", omittingEmptySubsequences: false)
                .reduce(0) { $0 + IslandSegments.visualLines($1) }
            precondition(lines <= IslandSegments.renderLines, "segment overflows: \(segment)")
        }
        // Splitting only drops line breaks and manual marks; every character survives in order.
        for (page, text) in IslandSegments.pages.enumerated() {
            let joined = all.filter { $0.page == page }.map(\.text).joined()
            let kept: (Character) -> Bool = { !$0.isNewline && $0 != IslandSegments.manualMark }
            precondition(joined.filter(kept) == text.filter(kept))
        }
        // Automatic cuts land right after punctuation and never exceed the island.
        let pieces = IslandSegments.split(IslandSegments.longPage)
        precondition(pieces.count > 1)
        for piece in pieces.dropLast() {
            precondition(IslandSegments.units(Substring(piece)) <= IslandSegments.maxCutUnits)
            precondition(IslandSegments.breakMarks.contains(piece.last!), "cut not at punctuation: \(piece)")
        }
        // No punctuation in reach: hard cut exactly at the limit.
        let full = String(repeating: "字", count: IslandSegments.maxCutUnits / 2)   // exactly renderLines
        let over = full + "字"
        precondition(IslandSegments.split(over).map { IslandSegments.units(Substring($0)) } == [IslandSegments.maxCutUnits, 2])
        // Manual cuts: accepted spans are used as-is; an oversized span rejects the whole set.
        precondition(IslandSegments.manualSplit("甲。｜" + full) == .accepted(["甲。", full]))
        precondition(IslandSegments.manualSplit("甲。｜" + over) == .rejected(span: 2, lines: IslandSegments.renderLines + 1))
        precondition(IslandSegments.segments(IslandSegments.manualPage).count == 3)
        precondition(IslandSegments.segments("短。｜" + over) == IslandSegments.split("短。" + over))
        // Card window: starts at the island's segment, never crosses into the next page.
        for index in all.indices {
            let window = IslandSegments.window(from: index)
            precondition(window.first == all[index] && (1...3).contains(window.count))
            precondition(window.allSatisfy { $0.page == all[index].page })
        }
        precondition(IslandSegments.window(from: -1) == [all[all.count - 1]])
        precondition(IslandSegments.step(0, by: -1) == all.count - 1)
        precondition(IslandSegments.step(all.count - 1, by: 1) == 0)
        precondition((0..<all.count).contains(IslandSegments.step(Int.max, by: 1)))
        precondition((0..<all.count).contains(IslandSegments.step(Int.min, by: -1)))
        print("Island segment checks passed: \(all.count) segments")
        for segment in all { print("[\(segment.page + 1).\(segment.part + 1)/\(segment.parts)] \(segment.text.split(separator: "\n").joined(separator: " ⏎ "))") }
    }
}
