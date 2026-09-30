/// Auto-splits reference pages into island-sized segments, replacing in-island scrolling.
/// Pure logic shared by the app and the widget; only the segment index is stored in the activity.
struct IslandSegment: Hashable {
    let page: Int
    let part: Int
    let parts: Int
    let text: String
}

enum IslandSegments {
    // ponytail: fixed budget measured for iPhone 17 Pro footnote text; measure per width if other devices matter.
    static let lineUnits = 44   // half-width units per island line; CJK counts 2
    /// Text budget per segment. Kept one line below `displayLines` because widths are estimated, not measured.
    static let renderLines = 3
    /// Lines the island reserves for text (Build 6 value); the spare line absorbs estimate error.
    static let displayLines = 4
    /// A paragraph heavier than this cannot fit the island and must be cut.
    static let maxCutUnits = lineUnits * renderLines
    /// Automatic cuts land right after one of these; a line break is always a cut.
    static let breakMarks: Set<Character> = ["。", "！", "？", "；", "，", "、", "：", "…", "”", "」", "』", "）", "!", "?", ";", ",", ":"]
    // ponytail: in-text mark stands in for cursor positions saved by the 进一步 mode; store offsets once a real editor exists.
    static let manualMark: Character = "｜"

    /// Synthetic long paragraph that exercises sub-cuts; the shared sample only has short lines.
    static let longPage = "长段观察 · 合成内容：她把信放回抽屉，又拿出来，反复三次，最后决定先不寄；窗外的雨一直没有停，楼下的店铺陆续关门，街灯一盏一盏亮起来，她听见有人上楼的脚步声，停在隔壁门口，钥匙转了两圈，门开了又关上；她想，如果那个人今晚回来，也会是这样的脚步，不快也不慢，像是知道有人在等，又像是完全不知道；于是她把灯调暗一点，把椅子转向门口，把最想说的那句话写在信的最后一行，然后划掉，再写一遍，这是本段末尾。"

    /// Synthetic page cut by hand in 进一步 mode.
    static let manualPage = "手动切点 · 合成内容\n先写门外的雨，再写屋里的灯。｜灯下有一封没寄出的信，信纸折了两次。｜最后一句，留给楼道里的脚步声。"

    static let pages = ReferenceSample.pages + [longPage, manualPage]

    static let all: [IslandSegment] = pages.enumerated().flatMap { page, text in
        let parts = segments(text)
        return parts.enumerated().map {
            IslandSegment(page: page, part: $0.offset, parts: parts.count, text: $0.element)
        }
    }

    static func normalized(_ value: Int) -> Int {
        let remainder = value % all.count
        return remainder < 0 ? remainder + all.count : remainder
    }

    static func step(_ index: Int, by delta: Int) -> Int {
        normalized(normalized(index) + delta.signum())
    }

    /// Segments the larger card shows: the island's current one plus the rest of its page, at most `count`.
    static func window(from index: Int, count: Int = 3) -> [IslandSegment] {
        let start = normalized(index)
        let page = all[start].page
        return Array(all[start...].prefix { $0.page == page }.prefix(count))
    }

    static func units(_ text: Substring) -> Int {
        text.reduce(0) { $0 + ($1.isASCII ? 1 : 2) }
    }

    static func visualLines(_ line: Substring) -> Int {
        max(1, (units(line) + lineUnits - 1) / lineUnits)
    }

    static func visualLines(of text: Substring) -> Int {
        text.split(separator: "\n", omittingEmptySubsequences: false).reduce(0) { $0 + visualLines($1) }
    }

    enum ManualResult: Equatable {
        case accepted([String])
        /// 1-based span that does not fit; the editor rejects the marks and shows this.
        case rejected(span: Int, lines: Int)
    }

    /// Manual cuts: every span between marks must fit the expanded island, otherwise the whole set is rejected.
    static func manualSplit(_ text: String) -> ManualResult {
        let spans = text.split(separator: manualMark, omittingEmptySubsequences: false)
        for (offset, span) in spans.enumerated() {
            let lines = visualLines(of: span)
            if lines > renderLines { return .rejected(span: offset + 1, lines: lines) }
        }
        return .accepted(spans.map(String.init))
    }

    /// Manual marks win when they are accepted; otherwise fall back to automatic cuts.
    static func segments(_ text: String) -> [String] {
        guard text.contains(manualMark) else { return split(text) }
        if case .accepted(let spans) = manualSplit(text) { return spans }
        return split(text.filter { $0 != manualMark })
    }

    /// Greedy packing of source lines into segments of at most `renderLines` visual lines.
    static func split(_ text: String) -> [String] {
        var pieces: [Substring] = []
        for line in text.split(separator: "\n", omittingEmptySubsequences: false) {
            var rest = line
            while units(rest) > maxCutUnits {
                let cut = cutIndex(in: rest)
                pieces.append(rest[..<cut])
                rest = rest[cut...]
            }
            pieces.append(rest)
        }
        var segments: [[Substring]] = []
        var used = 0
        for piece in pieces {
            let lines = visualLines(piece)
            if segments.isEmpty || used + lines > renderLines {
                segments.append([piece])
                used = lines
            } else {
                segments[segments.count - 1].append(piece)
                used += lines
            }
        }
        return segments.map { $0.joined(separator: "\n") }
    }

    /// Automatic cut: right after the last punctuation that still fits; hard cut at the limit if none does.
    static func cutIndex(in line: Substring) -> Substring.Index {
        var total = 0
        var lastBreak: Substring.Index?
        for index in line.indices {
            total += units(line[index...index])
            if total > maxCutUnits { return lastBreak ?? index }
            if breakMarks.contains(line[index]) { lastBreak = line.index(after: index) }
        }
        return line.endIndex
    }
}
