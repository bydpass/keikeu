import Darwin
import Foundation

/// Evidence log for the fusion experiment: event names, segment indices and timings only, never reference text.
/// Written to Documents/fusion-events.jsonl of whichever process runs the code (intents run in the app).
enum FusionLog {
    /// Kernel start time of this process, so a cold launch caused by an intent is visible in `sinceLaunchMs`.
    static let processStart: Date = {
        var info = kinfo_proc()
        var size = MemoryLayout<kinfo_proc>.stride
        var mib: [Int32] = [CTL_KERN, KERN_PROC, KERN_PROC_PID, getpid()]
        guard sysctl(&mib, 4, &info, &size, nil, 0) == 0 else { return Date() }
        let start = info.kp_proc.p_un.__p_starttime
        return Date(timeIntervalSince1970: Double(start.tv_sec) + Double(start.tv_usec) / 1_000_000)
    }()

    static func ms(since start: Date) -> Int {
        Int(Date().timeIntervalSince(start) * 1000)
    }

    static func write(_ event: String, _ fields: [String: Int] = [:], source: String? = nil) {
        var line: [String: Any] = fields
        line["event"] = event
        line["sinceLaunchMs"] = ms(since: processStart)
        if let source { line["source"] = source }
        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        line["t"] = formatter.string(from: Date())
        guard var data = try? JSONSerialization.data(withJSONObject: line, options: [.sortedKeys]),
              let dir = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask).first else { return }
        data.append(0x0A)
        let url = dir.appendingPathComponent("fusion-events.jsonl")
        // ponytail: open-append-close per event; fine for a handful of taps, batch if events get frequent.
        if let handle = try? FileHandle(forWritingTo: url) {
            defer { try? handle.close() }
            _ = try? handle.seekToEnd()
            try? handle.write(contentsOf: data)
        } else {
            try? data.write(to: url)
        }
    }
}
