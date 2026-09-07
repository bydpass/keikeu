import Foundation
import CryptoKit

/// All calls originate on the Rust host worker. Native query callbacks use the main queue.
enum Cloud {
    static let containerID = "iCloud.app.keikeu.v08probe"
    struct Version {
        let value: NSFileVersion
        let root: URL
        let account: String
    }
    static var versions: [String: Version] = [:]
    static func version(_ token: String, root: URL, account: String) throws -> NSFileVersion {
        guard let record = versions[token], record.root == root, record.account == account else { throw CloudError.staleVersion }
        return record.value
    }

    static func identity() throws -> String {
        guard let token = FileManager.default.ubiquityIdentityToken else { throw CloudError.accountUnavailable }
        let bytes = try NSKeyedArchiver.archivedData(withRootObject: token, requiringSecureCoding: false)
        return SHA256.hash(data: bytes).map { String(format: "%02x", $0) }.joined()
    }
    static func location(_ request: [String: String]) throws -> (URL, URL, String) {
        let account = try identity()
        if let expected = request["account"], expected != account { throw CloudError.accountChanged }
        guard let container = FileManager.default.url(forUbiquityContainerIdentifier: containerID) else { throw CloudError.containerUnavailable }
        guard try identity() == account else { throw CloudError.accountChanged }
        let name = request["vault"] ?? "keikeu"
        guard !name.isEmpty, name.allSatisfy({ $0.isASCII && ($0.isLetter || $0.isNumber || $0 == "-") }) else { throw CloudError.invalidPath }
        return (container, container.appendingPathComponent("Documents").appendingPathComponent(name), account)
    }
    static func request(_ request: [String: String]) -> [String: Any] {
        do {
            let method = request["method"] ?? ""
            if method == "cloud.identity" { return ["state": "ready", "account": try identity()] }
            let (container, root, account) = try location(request)
            if method == "cloud.inspect" {
                return ["state": "ready", "account": account, "container": container.path, "root": root.path]
            }
            if method == "cloud.status" {
                let items = try discover(root)
                guard try identity() == account else { throw CloudError.accountChanged }
                return ["state": "ready", "account": account, "items": items]
            }
            if method == "cloud.download" {
                let url = try child(root, request["path"] ?? "")
                try FileManager.default.startDownloadingUbiquitousItem(at: url)
                return ["state": "requested"]
            }
            if method == "cloud.conflicts" {
                let items = try discover(root)
                var found: [[String: Any]] = []
                for item in items where item["state"] as? String == "available" {
                    guard let path = item["path"] as? String else { continue }
                    let url = try child(root, path)
                    var error: NSError?
                    var current: [NSFileVersion] = []
                    NSFileCoordinator().coordinate(readingItemAt: url, options: .withoutChanges, error: &error) { coordinated in
                        current = NSFileVersion.unresolvedConflictVersionsOfItem(at: coordinated) ?? []
                    }
                    if error != nil { throw CloudError.coordinationFailed }
                    for version in current {
                        let token = UUID().uuidString
                        versions[token] = Version(value: version, root: root, account: account)
                        found.append(["token": token, "path": path, "local": version.hasLocalContents])
                    }
                }
                return ["state": "ready", "versions": found, "items": items]
            }
            if method == "cloud.version.read" {
                guard let token = request["token"] else { throw CloudError.staleVersion }
                let version = try version(token, root: root, account: account)
                let bytes = try AppleFiles.read(version.url)
                return ["state": "read", "bytes": Array(bytes), "digest": digest(bytes)]
            }
            if method == "cloud.versions.resolve" {
                guard let text = request["preserved"], let data = text.data(using: .utf8),
                      let records = try JSONSerialization.jsonObject(with: data) as? [[String: String]], !records.isEmpty else { throw CloudError.staleVersion }
                var verified: [NSFileVersion] = []
                // Verify the complete batch before changing any native resolved flag.
                for record in records {
                    guard let token = record["token"] else { throw CloudError.staleVersion }
                    let version = try version(token, root: root, account: account)
                    guard digest(try AppleFiles.read(version.url)) == record["digest"] else { throw CloudError.staleVersion }
                    verified.append(version)
                }
                guard try identity() == account else { throw CloudError.accountChanged }
                for version in verified { version.isResolved = true }
                return ["state": "resolved"]
            }
            return ["state": "unsupported"]
        } catch let error as CloudError {
            return ["state": "unavailable", "code": error.rawValue]
        } catch {
            return ["state": "unavailable", "code": "cloud_operation_failed"]
        }
    }
    static func digest(_ bytes: Data) -> String { SHA256.hash(data: bytes).map { String(format: "%02x", $0) }.joined() }
    static func child(_ root: URL, _ path: String) throws -> URL {
        let parts = path.split(separator: "/", omittingEmptySubsequences: false)
        guard (parts.count == 2 || parts.count == 3), parts[0] == "cache",
              parts.allSatisfy({ !$0.isEmpty && $0 != "." && $0 != ".." }), path.hasSuffix(".md") else { throw CloudError.invalidPath }
        return root.appendingPathComponent(path)
    }
    static func describe(_ url: URL, root: URL) throws -> [String: Any]? {
        let prefix = root.path + "/"
        guard url.path.hasPrefix(prefix) else { return nil }
        let path = String(url.path.dropFirst(prefix.count))
        guard (try? child(root, path)) != nil else { return nil }
        let values = try url.resourceValues(forKeys: [.isSymbolicLinkKey, .isRegularFileKey, .isUbiquitousItemKey,
            .ubiquitousItemDownloadingStatusKey, .ubiquitousItemIsUploadingKey, .ubiquitousItemIsUploadedKey,
            .ubiquitousItemHasUnresolvedConflictsKey])
        if values.isSymbolicLink == true { return ["path": path, "state": "unsafe"] }
        let available = values.isRegularFile == true && values.ubiquitousItemDownloadingStatus != .notDownloaded
        return ["path": path, "state": available ? "available" : "not_downloaded",
                "current": values.ubiquitousItemDownloadingStatus == .current,
                "uploading": values.ubiquitousItemIsUploading ?? false,
                "uploaded": values.ubiquitousItemIsUploaded ?? false,
                "has_native_conflicts": values.ubiquitousItemHasUnresolvedConflicts ?? false]
    }
    static func discover(_ root: URL) throws -> [[String: Any]] {
        for directory in [root.deletingLastPathComponent(), root] where FileManager.default.fileExists(atPath: directory.path) {
            let values = try directory.resourceValues(forKeys: [.isSymbolicLinkKey, .isDirectoryKey])
            guard values.isSymbolicLink != true, values.isDirectory == true else { throw CloudError.invalidPath }
        }
        let semaphore = DispatchSemaphore(value: 0)
        var metadataURLs: [URL] = []
        var completed = false
        DispatchQueue.main.async {
            let query = NSMetadataQuery()
            query.searchScopes = [NSMetadataQueryUbiquitousDocumentsScope]
            query.predicate = NSPredicate(format: "%K BEGINSWITH %@", NSMetadataItemPathKey, root.path + "/")
            var observer: NSObjectProtocol?
            var finished = false
            func stop(_ success: Bool) {
                guard !finished else { return }; finished = true
                if success {
                    metadataURLs = query.results.compactMap { ($0 as? NSMetadataItem)?.value(forAttribute: NSMetadataItemURLKey) as? URL }
                    completed = true
                }
                query.stop()
                if let observer { NotificationCenter.default.removeObserver(observer) }
                semaphore.signal()
            }
            observer = NotificationCenter.default.addObserver(forName: .NSMetadataQueryDidFinishGathering, object: query, queue: .main) { _ in stop(true) }
            if !query.start() { stop(false); return }
            DispatchQueue.main.asyncAfter(deadline: .now() + 15) { stop(false) }
        }
        semaphore.wait()
        guard completed else { throw CloudError.discoveryUnavailable }
        var urls = Set(metadataURLs)
        // Include just-created local files before metadata indexing catches up.
        // Never enter symlink directories; metadata-only entries stay in the merged result.
        let cache = root.appendingPathComponent("cache")
        if FileManager.default.fileExists(atPath: cache.path) {
            let values = try cache.resourceValues(forKeys: [.isSymbolicLinkKey, .isDirectoryKey])
            guard values.isSymbolicLink != true, values.isDirectory == true else { throw CloudError.invalidPath }
            let children = try FileManager.default.contentsOfDirectory(at: cache, includingPropertiesForKeys: [.isDirectoryKey, .isSymbolicLinkKey], options: [.skipsHiddenFiles])
            for url in children {
                let values = try url.resourceValues(forKeys: [.isDirectoryKey, .isSymbolicLinkKey])
                if values.isDirectory == true && values.isSymbolicLink != true {
                    urls.formUnion(try FileManager.default.contentsOfDirectory(at: url, includingPropertiesForKeys: nil, options: [.skipsHiddenFiles]).filter { $0.pathExtension == "md" })
                } else if url.pathExtension == "md" { urls.insert(url) }
            }
        }
        return try urls.sorted { $0.path < $1.path }.compactMap { url in
            // A metadata entry may not yet have locally readable NSURL resource values.
            do { return try describe(url, root: root) }
            catch {
                let prefix = root.path + "/"
                guard url.path.hasPrefix(prefix) else { return nil }
                let path = String(url.path.dropFirst(prefix.count))
                guard (try? child(root, path)) != nil else { return nil }
                return ["path": path, "state": "not_downloaded"]
            }
        }
    }
}

enum CloudError: String, Error {
    case accountUnavailable = "icloud_account_unavailable"
    case accountChanged = "icloud_account_changed"
    case containerUnavailable = "icloud_container_unavailable"
    case invalidPath = "unsafe_cloud_path"
    case coordinationFailed = "coordination_failed"
    case discoveryUnavailable = "metadata_unavailable"
    case staleVersion = "stale_version"
}

/// One native batch encloses every enlisted Rust read and the optional exact target write.
/// No callback runs on coordination failure; the caller treats any post-callback error as unknown.
@_cdecl("keikeu_coordinate")
public func keikeuCoordinate(_ input: UnsafePointer<CChar>, _ context: UnsafeMutableRawPointer?,
                            _ callback: @convention(c) (UnsafeMutableRawPointer?) -> Void) -> Int32 {
    do {
        guard let request = try JSONSerialization.jsonObject(with: Data(String(cString: input).utf8)) as? [String: Any],
              let root = request["root"] as? String, let paths = request["paths"] as? [String] else { return 1 }
        let url = URL(fileURLWithPath: root)
        let writePath = request["write"] as? String
        let reads = request["initialize"] as? Bool == true ? [] : [url] + (try paths.filter { $0 != writePath }.map { try Cloud.child(url, $0) })
        let writes = request["initialize"] as? Bool == true ? [url] : try writePath.map { [try Cloud.child(url, $0)] } ?? []
        var error: NSError?
        NSFileCoordinator().prepare(forReadingItemsAt: reads, options: .withoutChanges,
                                    writingItemsAt: writes, options: [], error: &error) { done in
            defer { done() }
            callback(context)
        }
        return error == nil ? 0 : 1
    } catch { return 1 }
}
