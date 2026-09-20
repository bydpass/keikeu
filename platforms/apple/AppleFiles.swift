import Foundation
import Darwin

enum AppleFileError: Error {
    case unavailable, unsafePath, mismatch, missing
}

/// Native coordinated bytes only. Paper parsing and business rules belong to Rust.
enum AppleFiles {
    static func read(_ url: URL) throws -> Data {
        var coordinationError: NSError?
        var result: Result<Data, Error> = .failure(AppleFileError.missing)
        NSFileCoordinator().coordinate(readingItemAt: url, options: .withoutChanges,
                                       error: &coordinationError) { coordinated in
            result = Result {
                try regularFile(coordinated)
                return try Data(contentsOf: coordinated)
            }
        }
        if let error = coordinationError { throw error }
        return try result.get()
    }

    static func regularFile(_ url: URL) throws {
        let values = try url.resourceValues(forKeys: [.isRegularFileKey, .isSymbolicLinkKey])
        guard values.isRegularFile == true, values.isSymbolicLink != true else {
            throw AppleFileError.unsafePath
        }
    }

    /// Probe creation is exclusive. Existing files must have the exact expected bytes.
    static func create(_ bytes: Data, at url: URL) throws {
        var coordinationError: NSError?
        var result: Result<Void, Error> = .failure(AppleFileError.missing)
        NSFileCoordinator().coordinate(writingItemAt: url, options: [],
                                       error: &coordinationError) { coordinated in
            result = Result {
                if FileManager.default.fileExists(atPath: coordinated.path) {
                    try regularFile(coordinated)
                    guard try Data(contentsOf: coordinated) == bytes else { throw AppleFileError.mismatch }
                } else {
                    // Foundation disallows combining .atomic and .withoutOverwriting.
                    // A same-directory exclusive rename publishes only complete bytes.
                    let temporary = coordinated.deletingLastPathComponent()
                        .appendingPathComponent(".cp1-" + UUID().uuidString)
                    defer { try? FileManager.default.removeItem(at: temporary) }
                    try bytes.write(to: temporary, options: .withoutOverwriting)
                    let fd = open(temporary.path, O_RDONLY | O_NOFOLLOW)
                    guard fd >= 0 else { throw POSIXError(.EIO) }
                    let synced = fsync(fd)
                    close(fd)
                    guard synced == 0 else { throw POSIXError(.EIO) }
                    guard renamex_np(temporary.path, coordinated.path, UInt32(RENAME_EXCL)) == 0 else {
                        throw POSIXError(POSIXErrorCode(rawValue: errno) ?? .EIO)
                    }
                }
                guard try Data(contentsOf: coordinated) == bytes else { throw AppleFileError.mismatch }
            }
        }
        if let error = coordinationError { throw error }
        try result.get()
    }

    static func available(_ url: URL) throws -> Bool {
        guard FileManager.default.fileExists(atPath: url.path) else {
            // A metadata-only item can exist before its contents are materialized.
            try? FileManager.default.startDownloadingUbiquitousItem(at: url)
            return false
        }
        let values = try url.resourceValues(forKeys: [.isUbiquitousItemKey,
                                                     .ubiquitousItemDownloadingStatusKey])
        if values.isUbiquitousItem == true,
           values.ubiquitousItemDownloadingStatus != .current {
            try FileManager.default.startDownloadingUbiquitousItem(at: url)
            return false
        }
        return true
    }

    /// Preserve bytes, not a writable version URL or an archived native identifier.
    static func preserve(_ version: NSFileVersion, directory: URL) throws -> URL {
        let original = try read(version.url)
        let copy = directory.appendingPathComponent(UUID().uuidString + ".bytes")
        try create(original, at: copy)
        guard try read(copy) == original else { throw AppleFileError.mismatch }
        return copy
    }
}
