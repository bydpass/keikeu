import Foundation
import SwiftUI

@_silgen_name("keikeu_probe") private func rustProbe() -> Int32

private func argument(_ name: String) -> String? {
    let args = ProcessInfo.processInfo.arguments
    guard let i = args.firstIndex(of: name), i + 1 < args.count else { return nil }
    return args[i + 1]
}

private let payload = Data("keikeu CP1 synthetic 中文\n\u{0}raw bytes\n".utf8)

@_cdecl("keikeu_apple_roundtrip")
func nativeRoundtrip() -> Int32 {
    do {
        let base = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask)[0]
        guard let run = argument("--run"), UUID(uuidString: run) != nil else { return 7 }
        let directory = base.appendingPathComponent("CP1-" + run)
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
        var values = URLResourceValues()
        values.isExcludedFromBackup = true
        var privateDirectory = directory
        try privateDirectory.setResourceValues(values)
        let file = directory.appendingPathComponent("fixture.bytes")
        try AppleFiles.create(payload, at: file)
        guard try AppleFiles.read(file) == payload else { return 2 }
        // One negative check ensures exclusive creation cannot silently replace bytes.
        do {
            try AppleFiles.create(Data("different".utf8), at: file)
            return 3
        } catch AppleFileError.mismatch { }
        guard try AppleFiles.read(file) == payload else { return 4 }
        guard let version = NSFileVersion.currentVersionOfItem(at: file) else { return 5 }
        let preserved = try AppleFiles.preserve(version, directory: directory)
        guard try AppleFiles.read(preserved) == payload else { return 6 }
        return 0
    } catch { return 1 }
}

@MainActor
final class ProbeState: ObservableObject {
    @Published var status = "Starting / 启动中"
    private let query = NSMetadataQuery()
    private var timer: Timer?
    private var ticks = 0
    private var root: URL?
    private var role = ""
    private var run = ""
    private var nativePassed = false
    private var started = false

    func start() {
        guard !started else { return }
        started = true
        guard let id = argument("--run"), UUID(uuidString: id) != nil,
              let requestedRole = argument("--role"), ["seed", "reply", "verify", "local"].contains(requestedRole) else {
            finish("invalid_probe_arguments", passed: false)
            return
        }
        run = id
        role = requestedRole
        let nativeResult = rustProbe()
        guard nativeResult == 0 else { finish("rust_native_local_failed_\(nativeResult)", passed: false); return }
        nativePassed = true
        if role == "local" { finish("rust_native_local_passed", passed: true); return }
        status = "Rust/native local passed; connecting iCloud"
        // Apple can block while obtaining a container; keep the visible UI responsive.
        DispatchQueue.global().async {
            let container = FileManager.default.url(forUbiquityContainerIdentifier: "iCloud.app.keikeu.v08probe")
            DispatchQueue.main.async { self.connect(container) }
        }
    }

    private func connect(_ container: URL?) {
        guard FileManager.default.ubiquityIdentityToken != nil else {
            finish("icloud_account_unavailable", passed: false); return
        }
        guard let container else { finish("icloud_container_unavailable", passed: false); return }
        root = container.appendingPathComponent("Documents/CP1-" + run)
        query.searchScopes = [NSMetadataQueryUbiquitousDocumentsScope]
        query.predicate = NSPredicate(format: "%K CONTAINS %@", NSMetadataItemPathKey, "CP1-" + run)
        guard query.start() else { finish("metadata_start_failed", passed: false); return }
        timer = Timer.scheduledTimer(withTimeInterval: 1, repeats: true) { _ in
            Task { @MainActor in self.step() }
        }
    }

    private func step() {
        ticks += 1
        guard let root else { return }
        do {
            let request = root.appendingPathComponent("request.bytes")
            let reply = root.appendingPathComponent("reply.bytes")
            if role == "seed" {
                try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
                try AppleFiles.create(payload, at: request)
                finish("seed_coordinated_and_verified", passed: true)
                return
            }
            let target = role == "reply" ? request : reply
            query.disableUpdates()
            let discovered = query.results.compactMap { $0 as? NSMetadataItem }.contains {
                ($0.value(forAttribute: NSMetadataItemURLKey) as? URL)?.standardizedFileURL == target.standardizedFileURL
            }
            query.enableUpdates()
            guard discovered, try AppleFiles.available(target) else {
                status = "Waiting for native metadata/download (\(ticks)/45)"
                if ticks >= 45 { finish("provider_not_ready", passed: false) }
                return
            }
            guard try AppleFiles.read(target) == payload else { throw AppleFileError.mismatch }
            if role == "reply" { try AppleFiles.create(payload, at: reply) }
            finish(role == "reply" ? "iphone_read_reply_verified" : "mac_roundtrip_verified", passed: true)
        } catch {
            // Errors do not include paths, account identity, or author data.
            finish("coordinated_bytes_failed", passed: false)
        }
    }

    private func finish(_ result: String, passed: Bool) {
        timer?.invalidate()
        query.stop()
        status = result
        let record: [String: Any] = ["run": run, "role": role, "result": result,
                                    "passed": passed, "native_rust_boundary": nativePassed]
        do {
            let documents = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0]
            try FileManager.default.createDirectory(at: documents, withIntermediateDirectories: true)
            let bytes = try JSONSerialization.data(withJSONObject: record, options: [.sortedKeys])
            try bytes.write(to: documents.appendingPathComponent("cp1-\(run)-\(role).json"), options: .atomic)
            print(String(decoding: bytes, as: UTF8.self))
            fflush(stdout)
        } catch { status = "receipt_write_failed" }
    }
}

@main
struct ProbeApp: App {
    @StateObject private var state = ProbeState()
    var body: some Scene {
        WindowGroup {
            VStack(alignment: .leading, spacing: 20) {
                Text("keikeu CP1 probe").font(.title)
                Text("Synthetic test only / 仅合成测试")
                Text(state.status).textSelection(.enabled).accessibilityIdentifier("probe-status")
            }.padding(24).task { state.start() }
        }
    }
}
