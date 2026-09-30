@main
struct ReaderCheck {
    static func main() {
        // Viewport 200, step 180: a 450-point page needs offsets 0, 180, 250.
        precondition(ReaderStep.screenCount(bodyHeight: 100, viewport: 200, step: 180) == 1)
        precondition(ReaderStep.screenCount(bodyHeight: 450, viewport: 200, step: 180) == 3)
        precondition(ReaderStep.screenCount(bodyHeight: 560, viewport: 200, step: 180) == 3)
        precondition(ReaderStep.screenCount(bodyHeight: 450, viewport: 200, step: 0) == 1)
        precondition(ReaderStep.offset(screen: 1, bodyHeight: 450, viewport: 200, step: 180) == 180)
        precondition(ReaderStep.offset(screen: 2, bodyHeight: 450, viewport: 200, step: 180) == 250)
        precondition(ReaderStep.offset(screen: -1, bodyHeight: 450, viewport: 200, step: 180) == 0)

        let counts = [1, 1, 3]
        var position = ReaderPosition()
        var forward: [ReaderPosition] = []
        for _ in 0..<5 {
            position = ReaderStep.move(position, forward: true, screenCounts: counts)
            forward.append(position)
        }
        precondition(forward == [
            ReaderPosition(page: 1, screen: 0),
            ReaderPosition(page: 2, screen: 0),
            ReaderPosition(page: 2, screen: 1),
            ReaderPosition(page: 2, screen: 2),
            ReaderPosition(page: 0, screen: 0),
        ])

        // Backward from the first page lands on the last screen of the last page.
        position = ReaderStep.move(ReaderPosition(), forward: false, screenCounts: counts)
        precondition(position == ReaderPosition(page: 2, screen: 2))
        position = ReaderStep.move(position, forward: false, screenCounts: counts)
        precondition(position == ReaderPosition(page: 2, screen: 1))

        // Stale positions after a reference change are clamped, never trapped.
        precondition(ReaderStep.move(ReaderPosition(page: 7, screen: 9), forward: true, screenCounts: [1])
            == ReaderPosition(page: 0, screen: 0))
        // Int.min % 3 == -2, so it normalises to page 1 before stepping back.
        precondition(ReaderStep.move(ReaderPosition(page: Int.min, screen: Int.max), forward: false, screenCounts: counts)
            == ReaderPosition(page: 0, screen: 0))
        precondition(ReaderStep.move(ReaderPosition(page: 3, screen: 4), forward: true, screenCounts: [])
            == ReaderPosition(page: 3, screen: 4))
        print("Reader step checks passed")
    }
}
