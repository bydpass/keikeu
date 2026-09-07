import Foundation
#if os(iOS)
import UIKit
#else
import AppKit
#endif

// Rust calls from a worker. Only UI presentation hops onto the main queue.
@_cdecl("keikeu_host_native")
public func keikeuHostNative(_ input: UnsafePointer<CChar>) -> UnsafeMutablePointer<CChar>? {
    do {
        let request = try JSONSerialization.jsonObject(with: Data(String(cString: input).utf8)) as? [String: String] ?? [:]
        var result: [String: Any]
        switch request["method"] {
        case "locale":
            result = ["locale": Locale.preferredLanguages.first ?? "en"]
        case "exclude_backup":
            var url = URL(fileURLWithPath: request["path"] ?? "")
            var values = URLResourceValues()
            values.isExcludedFromBackup = true
            try url.setResourceValues(values)
            guard try url.resourceValues(forKeys: [.isExcludedFromBackupKey]).isExcludedFromBackup == true else {
                throw CocoaError(.fileWriteUnknown)
            }
            result = ["state": "excluded"]
        case "export":
            let url: URL
            if let content = request["content"] {
                url = FileManager.default.temporaryDirectory.appendingPathComponent("keikeu-\(UUID().uuidString).json")
                try Data(content.utf8).write(to: url, options: .withoutOverwriting)
            } else {
                url = URL(fileURLWithPath: request["path"] ?? "")
            }
            let semaphore = DispatchSemaphore(value: 0)
            var outcome = "failed"
            DispatchQueue.main.async {
                #if os(iOS)
                guard let scene = UIApplication.shared.connectedScenes.compactMap({ $0 as? UIWindowScene }).first(where: { $0.activationState == .foregroundActive }),
                      let root = scene.windows.first(where: { $0.isKeyWindow })?.rootViewController else {
                    semaphore.signal(); return
                }
                var presenter = root
                while let presented = presenter.presentedViewController { presenter = presented }
                let controller = UIActivityViewController(activityItems: [url], applicationActivities: nil)
                controller.completionWithItemsHandler = { _, completed, _, error in
                    outcome = error != nil ? "failed" : completed ? "exported" : "cancelled"
                    semaphore.signal()
                }
                controller.popoverPresentationController?.sourceView = presenter.view
                controller.popoverPresentationController?.sourceRect = presenter.view.bounds
                presenter.present(controller, animated: true)
                #else
                let panel = NSSavePanel()
                panel.nameFieldStringValue = url.lastPathComponent
                panel.begin { response in
                    defer { semaphore.signal() }
                    guard response == .OK, let target = panel.url else { outcome = "cancelled"; return }
                    do {
                        // Export creates a copy; existing destinations stay untouched.
                        try FileManager.default.copyItem(at: url, to: target)
                        outcome = "exported"
                    } catch { outcome = "failed" }
                }
                #endif
            }
            semaphore.wait()
            result = ["state": outcome]
        default:
            result = request["method"]?.hasPrefix("cloud.") == true ? Cloud.request(request) : ["state": "unsupported"]
        }
        let data = try JSONSerialization.data(withJSONObject: result)
        return strdup(String(decoding: data, as: UTF8.self))
    } catch {
        return strdup("{\"state\":\"failed\"}")
    }
}
