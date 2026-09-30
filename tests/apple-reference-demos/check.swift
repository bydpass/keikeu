@main
struct SampleCheck {
    static func main() {
        precondition(ReferenceSample.pages.count == 3)
        precondition(ReferenceSample.normalizedPage(-1) == 2)
        precondition(ReferenceSample.normalizedPage(3) == 0)
        precondition(ReferenceSample.nextPage(0) == 1)
        precondition(ReferenceSample.nextPage(2) == 0)
        precondition((0..<3).map { ReferenceSample.pages[$0] }.allSatisfy { !$0.isEmpty })
        precondition((0..<3).contains(ReferenceSample.nextPage(Int.max)))
        precondition((0..<3).contains(ReferenceSample.nextPage(Int.min)))
        print("Reference page checks passed")
    }
}
