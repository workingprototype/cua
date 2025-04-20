import ArgumentParser
import Darwin
import Foundation
import Swift
import CommonCrypto
import Compression

// Registry type definition
struct Registry {
    let host: String
    let namespace: String
    
    init(host: String, namespace: String) {
        self.host = host
        self.namespace = namespace
    }
    
    func pushBlob(fromData data: Data, completion: ((Int64) -> Void)? = nil) async throws -> String {
        // Implementation needed
        return ""
    }
    
    func pushManifest(reference: String, manifest: OCIManifest) async throws -> String {
        // Implementation needed
        return ""
    }
}

// OCIManifest and related types
struct OCIManifest {
    let config: OCIManifestConfig
    let layers: [OCIManifestLayer]
}

struct OCIManifestConfig {
    let mediaType: String
    let size: Int
    let digest: String
}

// Digest utility
enum Digest {
    static func hash(_ data: Data) -> String {
        return data.sha256String()
    }
}

// Constants
let diskImageMediaType = "application/vnd.lume.disk.image"

// Retry mechanism
enum RetryAction {
    case retry
    case `throw`
}

func withRetry<T>(
    maxAttempts: Int = 3,
    action: () async throws -> T,
    recoverFromFailure: (Error) throws -> RetryAction
) async throws -> T {
    var lastError: Error?
    
    for attempt in 1...maxAttempts {
        do {
            return try await action()
        } catch {
            lastError = error
            let decision = try recoverFromFailure(error)
            if decision == .throw || attempt == maxAttempts {
                throw error
            }
            // Add exponential backoff
            try await Task.sleep(nanoseconds: UInt64(pow(2.0, Double(attempt)) * 1_000_000_000))
        }
    }
    
    throw lastError!
}

// Compression extension
extension Data {
    func compressed() throws -> Data {
        let pageSize = 4096
        var compressedData = Data()
        
        self.withUnsafeBytes { buffer in
            var sourceBuffer = buffer.baseAddress!
            var sourceSize = buffer.count
            
            while sourceSize > 0 {
                let chunkSize = Swift.min(sourceSize, pageSize)
                var destinationBuffer = [UInt8](repeating: 0, count: chunkSize)
                let destSize = compression_encode_buffer(
                    &destinationBuffer,
                    destinationBuffer.count,
                    sourceBuffer.assumingMemoryBound(to: UInt8.self),
                    chunkSize,
                    nil,
                    COMPRESSION_LZFSE
                )
                
                if destSize > 0 {
                    compressedData.append(&destinationBuffer, count: destSize)
                }
                
                sourceBuffer += chunkSize
                sourceSize -= chunkSize
            }
        }
        
        return compressedData
    }
}

// Credentials helper
func getCredentialsFromEnvironment() -> (username: String?, password: String?) {
    return (
        ProcessInfo.processInfo.environment["GITHUB_USERNAME"],
        ProcessInfo.processInfo.environment["GITHUB_TOKEN"]
    )
}

// Sparse file handling
func decompressChunkAndWriteSparse(
    inputPath: String,
    outputHandle: FileHandle,
    startOffset: UInt64
) throws -> UInt64 {
    let inputData = try Data(contentsOf: URL(fileURLWithPath: inputPath))
    try outputHandle.seek(toOffset: startOffset)
    try outputHandle.write(contentsOf: inputData)
    return UInt64(inputData.count)
}

// Pull disk image function
func pullDiskImage(
    registry: Registry,
    diskLayers: [OCIManifestLayer],
    outputURL: URL,
    progress: Progress
) async throws {
    // Implementation needed - for now just create an empty file
    FileManager.default.createFile(atPath: outputURL.path, contents: nil)
}

// Extension to calculate SHA256 hash
extension Data {
    func sha256String() -> String {
        let hash = self.withUnsafeBytes { (bytes: UnsafeRawBufferPointer) -> [UInt8] in
            var hash = [UInt8](repeating: 0, count: Int(CC_SHA256_DIGEST_LENGTH))
            CC_SHA256(bytes.baseAddress, CC_LONG(self.count), &hash)
            return hash
        }
        return hash.map { String(format: "%02x", $0) }.joined()
    }
}

// Push-related errors
enum PushError: Error {
    case uploadInitiationFailed
    case blobUploadFailed
    case manifestPushFailed
    case authenticationFailed
    case missingToken
    case invalidURL
    case lz4NotFound // Added error case
    case invalidMediaType // Added during part refactoring
    case missingUncompressedSizeAnnotation // Added for sparse file handling
    case fileCreationFailed(String) // Added for sparse file handling
    case reassemblySetupFailed(path: String, underlyingError: Error?) // Added for sparse file handling
    case missingPart(Int) // Added for sparse file handling
    case layerDownloadFailed(String) // Added for download retries
    case manifestFetchFailed // Added for manifest fetching
    case missingDiskImage
}

// Define a specific error type for when no underlying error exists
struct NoSpecificUnderlyingError: Error, CustomStringConvertible {
    var description: String { "No specific underlying error was provided." }
}

struct ChunkMetadata: Codable {
    let uncompressedDigest: String
    let uncompressedSize: UInt64
    let compressedDigest: String
    let compressedSize: Int
}

// Define struct to decode relevant parts of config.json
struct OCIManifestLayer {
    let mediaType: String
    let size: Int
    let digest: String
    let uncompressedSize: UInt64?
    let uncompressedContentDigest: String?
    
    init(mediaType: String, size: Int, digest: String, uncompressedSize: UInt64? = nil, uncompressedContentDigest: String? = nil) {
        self.mediaType = mediaType
        self.size = size
        self.digest = digest
        self.uncompressedSize = uncompressedSize
        self.uncompressedContentDigest = uncompressedContentDigest
    }
}

struct OCIConfig: Codable {
    struct Annotations: Codable {
        let uncompressedSize: String?  // Use optional String

        enum CodingKeys: String, CodingKey {
            case uncompressedSize = "com.trycua.lume.disk.uncompressed_size"
        }
    }
    let annotations: Annotations?  // Optional annotations
}

struct Layer: Codable, Equatable {
    let mediaType: String
    let digest: String
    let size: Int
}

struct Manifest: Codable {
    let layers: [Layer]
    let config: Layer?
    let mediaType: String
    let schemaVersion: Int
}

struct RepositoryTag: Codable {
    let name: String
    let tags: [String]
}

struct RepositoryList: Codable {
    let repositories: [String]
}

struct RepositoryTags: Codable {
    let name: String
    let tags: [String]
}

struct CachedImage {
    let repository: String
    let imageId: String
    let manifestId: String
}

struct ImageMetadata: Codable {
    let image: String
    let manifestId: String
    let timestamp: Date
}

// Actor to safely collect disk part information from concurrent tasks
actor DiskPartsCollector {
    // Store tuples of (sequentialPartNum, url)
    private var diskParts: [(Int, URL)] = []
    // Restore internal counter
    private var partCounter = 0 

    // Adds a part and returns its assigned sequential number
    func addPart(url: URL) -> Int {
        partCounter += 1 // Use counter logic
        let partNum = partCounter 
        diskParts.append((partNum, url)) // Store sequential number
        return partNum // Return assigned sequential number
    }

    // Sort by the sequential part number (index 0 of tuple)
    func getSortedParts() -> [(Int, URL)] {
        return diskParts.sorted { $0.0 < $1.0 }
    }
    
    // Restore getTotalParts
    func getTotalParts() -> Int {
        return partCounter
    }
}

actor ProgressTracker {
    private var totalBytes: Int64 = 0
    private var downloadedBytes: Int64 = 0
    private var progressLogger = ProgressLogger(threshold: 0.01)
    private var totalFiles: Int = 0
    private var completedFiles: Int = 0

    // Download speed tracking
    private var startTime: Date = Date()
    private var lastUpdateTime: Date = Date()
    private var lastUpdateBytes: Int64 = 0
    private var speedSamples: [Double] = []
    private var peakSpeed: Double = 0
    private var totalElapsedTime: TimeInterval = 0

    // Smoothing factor for speed calculation
    private var speedSmoothing: Double = 0.3
    private var smoothedSpeed: Double = 0

    func setTotal(_ total: Int64, files: Int) {
        totalBytes = total
        totalFiles = files
        startTime = Date()
        lastUpdateTime = startTime
        smoothedSpeed = 0
    }

    func addProgress(_ bytes: Int64) {
        downloadedBytes += bytes
        let now = Date()
        let elapsed = now.timeIntervalSince(lastUpdateTime)

        // Show first progress update immediately, then throttle updates
        let shouldUpdate = (downloadedBytes <= bytes) || (elapsed >= 0.5)

        if shouldUpdate {
            let currentSpeed = Double(downloadedBytes - lastUpdateBytes) / max(elapsed, 0.001)
            speedSamples.append(currentSpeed)

            // Cap samples array to prevent memory growth
            if speedSamples.count > 20 {
                speedSamples.removeFirst(speedSamples.count - 20)
            }

            // Update peak speed
            peakSpeed = max(peakSpeed, currentSpeed)

            // Apply exponential smoothing to the speed
            if smoothedSpeed == 0 {
                smoothedSpeed = currentSpeed
            } else {
                smoothedSpeed = speedSmoothing * currentSpeed + (1 - speedSmoothing) * smoothedSpeed
            }

            // Calculate average speed over the last few samples
            let recentAvgSpeed = calculateAverageSpeed()

            // Calculate overall average
            let totalElapsed = now.timeIntervalSince(startTime)
            let overallAvgSpeed = totalElapsed > 0 ? Double(downloadedBytes) / totalElapsed : 0

            let progress = Double(downloadedBytes) / Double(totalBytes)
            logSpeedProgress(
                current: progress,
                currentSpeed: currentSpeed,
                averageSpeed: recentAvgSpeed,
                smoothedSpeed: smoothedSpeed,
                overallSpeed: overallAvgSpeed,
                peakSpeed: peakSpeed,
                context: "Downloading Image"
            )

            // Update tracking variables
            lastUpdateTime = now
            lastUpdateBytes = downloadedBytes
            totalElapsedTime = totalElapsed
        }
    }

    private func calculateAverageSpeed() -> Double {
        guard !speedSamples.isEmpty else { return 0 }

        // Use weighted average giving more emphasis to recent samples
        var totalWeight = 0.0
        var weightedSum = 0.0

        let samples = speedSamples.suffix(min(8, speedSamples.count))
        for (index, speed) in samples.enumerated() {
            let weight = Double(index + 1)
            weightedSum += speed * weight
            totalWeight += weight
        }

        return totalWeight > 0 ? weightedSum / totalWeight : 0
    }

    func getDownloadStats() -> DownloadStats {
        let avgSpeed = totalElapsedTime > 0 ? Double(downloadedBytes) / totalElapsedTime : 0
        return DownloadStats(
            totalBytes: totalBytes,
            downloadedBytes: downloadedBytes,
            elapsedTime: totalElapsedTime,
            averageSpeed: avgSpeed,
            peakSpeed: peakSpeed
        )
    }

    private func logSpeedProgress(
        current: Double,
        currentSpeed: Double,
        averageSpeed: Double,
        smoothedSpeed: Double,
        overallSpeed: Double,
        peakSpeed: Double,
        context: String
    ) {
        let progressPercent = Int(current * 100)
        let currentSpeedStr = formatByteSpeed(currentSpeed)
        let avgSpeedStr = formatByteSpeed(averageSpeed)
        let peakSpeedStr = formatByteSpeed(peakSpeed)

        // Calculate ETA based on the smoothed speed which is more stable
        // This provides a more realistic estimate that doesn't fluctuate as much
        let remainingBytes = totalBytes - downloadedBytes
        let speedForEta = max(smoothedSpeed, averageSpeed * 0.8)  // Use the higher of smoothed or 80% of avg
        let etaSeconds = speedForEta > 0 ? Double(remainingBytes) / speedForEta : 0
        let etaStr = formatTimeRemaining(etaSeconds)

        let progressBar = createProgressBar(progress: current)

        print(
            "\r\(progressBar) \(progressPercent)% | Current: \(currentSpeedStr) | Avg: \(avgSpeedStr) | Peak: \(peakSpeedStr) | ETA: \(etaStr)     ",
            terminator: "")
        fflush(stdout)
    }

    private func createProgressBar(progress: Double, width: Int = 30) -> String {
        let completedWidth = Int(progress * Double(width))
        let remainingWidth = width - completedWidth

        let completed = String(repeating: "█", count: completedWidth)
        let remaining = String(repeating: "░", count: remainingWidth)

        return "[\(completed)\(remaining)]"
    }

    private func formatByteSpeed(_ bytesPerSecond: Double) -> String {
        let units = ["B/s", "KB/s", "MB/s", "GB/s"]
        var speed = bytesPerSecond
        var unitIndex = 0

        while speed > 1024 && unitIndex < units.count - 1 {
            speed /= 1024
            unitIndex += 1
        }

        return String(format: "%.1f %@", speed, units[unitIndex])
    }

    private func formatTimeRemaining(_ seconds: Double) -> String {
        if seconds.isNaN || seconds.isInfinite || seconds <= 0 {
            return "calculating..."
        }

        let hours = Int(seconds) / 3600
        let minutes = (Int(seconds) % 3600) / 60
        let secs = Int(seconds) % 60

        if hours > 0 {
            return String(format: "%d:%02d:%02d", hours, minutes, secs)
        } else {
            return String(format: "%d:%02d", minutes, secs)
        }
    }
}

struct DownloadStats {
    let totalBytes: Int64
    let downloadedBytes: Int64
    let elapsedTime: TimeInterval
    let averageSpeed: Double
    let peakSpeed: Double

    func formattedSummary() -> String {
        let bytesStr = ByteCountFormatter.string(fromByteCount: downloadedBytes, countStyle: .file)
        let avgSpeedStr = formatSpeed(averageSpeed)
        let peakSpeedStr = formatSpeed(peakSpeed)
        let timeStr = formatTime(elapsedTime)

        return """
            Download Statistics:
            - Total downloaded: \(bytesStr)
            - Elapsed time: \(timeStr)
            - Average speed: \(avgSpeedStr)
            - Peak speed: \(peakSpeedStr)
            """
    }

    private func formatSpeed(_ bytesPerSecond: Double) -> String {
        let formatter = ByteCountFormatter()
        formatter.countStyle = .file
        let bytesStr = formatter.string(fromByteCount: Int64(bytesPerSecond))
        return "\(bytesStr)/s"
    }

    private func formatTime(_ seconds: TimeInterval) -> String {
        let hours = Int(seconds) / 3600
        let minutes = (Int(seconds) % 3600) / 60
        let secs = Int(seconds) % 60

        if hours > 0 {
            return String(format: "%d hours, %d minutes, %d seconds", hours, minutes, secs)
        } else if minutes > 0 {
            return String(format: "%d minutes, %d seconds", minutes, secs)
        } else {
            return String(format: "%d seconds", secs)
        }
    }
}

// Renamed struct
struct UploadStats {
    let totalBytes: Int64
    let uploadedBytes: Int64 // Renamed
    let elapsedTime: TimeInterval
    let averageSpeed: Double
    let peakSpeed: Double

    func formattedSummary() -> String {
        let bytesStr = ByteCountFormatter.string(fromByteCount: uploadedBytes, countStyle: .file)
        let avgSpeedStr = formatSpeed(averageSpeed)
        let peakSpeedStr = formatSpeed(peakSpeed)
        let timeStr = formatTime(elapsedTime)
        return """
            Upload Statistics:
            - Total uploaded: \(bytesStr)
            - Elapsed time: \(timeStr)
            - Average speed: \(avgSpeedStr)
            - Peak speed: \(peakSpeedStr)
            """
    }
    private func formatSpeed(_ bytesPerSecond: Double) -> String {
        let formatter = ByteCountFormatter()
        formatter.countStyle = .file
        let bytesStr = formatter.string(fromByteCount: Int64(bytesPerSecond))
        return "\(bytesStr)/s"
    }
    private func formatTime(_ seconds: TimeInterval) -> String {
        let hours = Int(seconds) / 3600
        let minutes = (Int(seconds) % 3600) / 60
        let secs = Int(seconds) % 60
        if hours > 0 { return String(format: "%d hours, %d minutes, %d seconds", hours, minutes, secs) }
        else if minutes > 0 { return String(format: "%d minutes, %d seconds", minutes, secs) }
        else { return String(format: "%d seconds", secs) }
    }
}

actor TaskCounter {
    private var count: Int = 0

    func increment() { count += 1 }
    func decrement() { count -= 1 }
    func current() -> Int { count }
}

class ImageContainerRegistry: @unchecked Sendable {
    private let registry: String
    private let organization: String
    private let downloadProgress = ProgressTracker() // Renamed for clarity
    private let uploadProgress = UploadProgressTracker() // Added upload tracker
    private let cacheDirectory: URL
    private let downloadLock = NSLock()
    private var activeDownloads: [String] = []
    private let cachingEnabled: Bool

    // Constants for zero-skipping write logic
    private static let holeGranularityBytes = 4 * 1024 * 1024 // 4MB block size for checking zeros
    private static let zeroChunk = Data(count: holeGranularityBytes)

    // Add the createProgressBar function here as a private method
    private func createProgressBar(progress: Double, width: Int = 30) -> String {
        let completedWidth = Int(progress * Double(width))
        let remainingWidth = width - completedWidth

        let completed = String(repeating: "█", count: completedWidth)
        let remaining = String(repeating: "░", count: remainingWidth)

        return "[\(completed)\(remaining)]"
    }

    init(registry: String, organization: String) {
        self.registry = registry
        self.organization = organization

        // Get cache directory from settings
        let cacheDir = SettingsManager.shared.getCacheDirectory()
        let expandedCacheDir = (cacheDir as NSString).expandingTildeInPath
        self.cacheDirectory = URL(fileURLWithPath: expandedCacheDir)
            .appendingPathComponent("ghcr")

        // Get caching enabled setting
        self.cachingEnabled = SettingsManager.shared.isCachingEnabled()

        try? FileManager.default.createDirectory(
            at: cacheDirectory, withIntermediateDirectories: true)

        // Create organization directory
        let orgDir = cacheDirectory.appendingPathComponent(organization)
        try? FileManager.default.createDirectory(at: orgDir, withIntermediateDirectories: true)
    }

    private func getManifestIdentifier(_ manifest: Manifest, manifestDigest: String) -> String {
        // Use the manifest's own digest as the identifier
        return manifestDigest.replacingOccurrences(of: ":", with: "_")
    }

    private func getShortImageId(_ digest: String) -> String {
        // Take first 12 characters of the digest after removing the "sha256:" prefix
        let id = digest.replacingOccurrences(of: "sha256:", with: "")
        return String(id.prefix(12))
    }

    private func getImageCacheDirectory(manifestId: String) -> URL {
        return
            cacheDirectory
            .appendingPathComponent(organization)
            .appendingPathComponent(manifestId)
    }

    private func getCachedManifestPath(manifestId: String) -> URL {
        return getImageCacheDirectory(manifestId: manifestId).appendingPathComponent(
            "manifest.json")
    }

    private func getCachedLayerPath(manifestId: String, digest: String) -> URL {
        return getImageCacheDirectory(manifestId: manifestId).appendingPathComponent(
            digest.replacingOccurrences(of: ":", with: "_"))
    }

    private func setupImageCache(manifestId: String) throws {
        let cacheDir = getImageCacheDirectory(manifestId: manifestId)
        // Remove existing cache if it exists
        if FileManager.default.fileExists(atPath: cacheDir.path) {
            try FileManager.default.removeItem(at: cacheDir)
            // Ensure it's completely removed
            while FileManager.default.fileExists(atPath: cacheDir.path) {
                try? FileManager.default.removeItem(at: cacheDir)
            }
        }
        try FileManager.default.createDirectory(at: cacheDir, withIntermediateDirectories: true)
    }

    private func loadCachedManifest(manifestId: String) -> Manifest? {
        let manifestPath = getCachedManifestPath(manifestId: manifestId)
        guard let data = try? Data(contentsOf: manifestPath) else { return nil }
        return try? JSONDecoder().decode(Manifest.self, from: data)
    }

    private func validateCache(manifest: Manifest, manifestId: String) -> Bool {
        // Skip cache validation if caching is disabled
        if !cachingEnabled {
            return false
        }

        // First check if manifest exists and matches
        guard let cachedManifest = loadCachedManifest(manifestId: manifestId),
            cachedManifest.layers == manifest.layers
        else {
            return false
        }

        // Then verify all layer files exist
        for layer in manifest.layers {
            let cachedLayer = getCachedLayerPath(manifestId: manifestId, digest: layer.digest)
            if !FileManager.default.fileExists(atPath: cachedLayer.path) {
                return false
            }
        }

        return true
    }

    private func saveManifest(_ manifest: Manifest, manifestId: String) throws {
        // Skip saving manifest if caching is disabled
        if !cachingEnabled {
            return
        }

        let manifestPath = getCachedManifestPath(manifestId: manifestId)
        try JSONEncoder().encode(manifest).write(to: manifestPath)
    }

    private func isDownloading(_ digest: String) -> Bool {
        downloadLock.lock()
        defer { downloadLock.unlock() }
        return activeDownloads.contains(digest)
    }

    private func markDownloadStarted(_ digest: String) {
        downloadLock.lock()
        if !activeDownloads.contains(digest) {
            activeDownloads.append(digest)
        }
        downloadLock.unlock()
    }

    private func markDownloadComplete(_ digest: String) {
        downloadLock.lock()
        activeDownloads.removeAll { $0 == digest }
        downloadLock.unlock()
    }

    private func waitForExistingDownload(_ digest: String, cachedLayer: URL) async throws {
        while isDownloading(digest) {
            try await Task.sleep(nanoseconds: 1_000_000_000)  // Sleep for 1 second
            if FileManager.default.fileExists(atPath: cachedLayer.path) {
                return  // File is now available
            }
        }
    }

    private func saveImageMetadata(image: String, manifestId: String) throws {
        // Skip saving metadata if caching is disabled
        if !cachingEnabled {
            return
        }

        let metadataPath = getImageCacheDirectory(manifestId: manifestId).appendingPathComponent(
            "metadata.json")
        let metadata = ImageMetadata(
            image: image,
            manifestId: manifestId,
            timestamp: Date()
        )
        try JSONEncoder().encode(metadata).write(to: metadataPath)
    }

    private func cleanupOldVersions(currentManifestId: String, image: String) throws {
        // Skip cleanup if caching is disabled
        if !cachingEnabled {
            return
        }

        Logger.info(
            "Checking for old versions of image to clean up",
            metadata: [
                "image": image,
                "current_manifest_id": currentManifestId,
            ])

        let orgDir = cacheDirectory.appendingPathComponent(organization)
        guard FileManager.default.fileExists(atPath: orgDir.path) else { return }

        let contents = try FileManager.default.contentsOfDirectory(atPath: orgDir.path)
        for item in contents {
            if item == currentManifestId { continue }

            let itemPath = orgDir.appendingPathComponent(item)
            let metadataPath = itemPath.appendingPathComponent("metadata.json")

            if let metadataData = try? Data(contentsOf: metadataPath),
                let metadata = try? JSONDecoder().decode(ImageMetadata.self, from: metadataData)
            {
                if metadata.image == image {
                    try FileManager.default.removeItem(at: itemPath)
                    Logger.info(
                        "Removed old version of image",
                        metadata: [
                            "image": image,
                            "old_manifest_id": item,
                        ])
                }
                continue
            }

            Logger.info(
                "Skipping cleanup check for item without metadata", metadata: ["item": item])
        }
    }

    private func optimizeNetworkSettings() {
        // Set global URLSession configuration properties for better performance
        URLSessionConfiguration.default.httpMaximumConnectionsPerHost = 10
        URLSessionConfiguration.default.httpShouldUsePipelining = true
        URLSessionConfiguration.default.timeoutIntervalForResource = 3600

        // Pre-warm DNS resolution
        let preWarmTask = URLSession.shared.dataTask(with: URL(string: "https://\(self.registry)")!)
        preWarmTask.resume()
    }

    public func pull(image: String, name: String?, locationName: String? = nil) async throws {
        guard !image.isEmpty else {
            throw ValidationError("Image name cannot be empty")
        }

        let home = Home()

        // Use provided name or derive from image
        let vmName = name ?? image.split(separator: ":").first.map(String.init) ?? ""
        let vmDirURL = URL(fileURLWithPath: try home.getVMDirectory(vmName, storage: locationName).dir.path)

        // Optimize network early in the process
        optimizeNetworkSettings()

        // Parse image name and tag
        let components = image.split(separator: ":")
        guard components.count == 2, let tag = components.last else {
            throw ValidationError("Invalid image format. Expected format: name:tag")
        }

        let imageName = String(components.first!)
        let imageTag = String(tag)

        Logger.info(
            "Pulling image",
            metadata: [
                "image": image,
                "name": vmName,
                "location": locationName ?? "default",
                "registry": registry,
                "organization": organization,
            ])

        // Get anonymous token
        Logger.info("Getting registry authentication token")
        let token = try await getToken(repository: "\(self.organization)/\(imageName)")

        // Fetch manifest
        Logger.info("Fetching Image manifest")
        let (manifest, manifestDigest): (Manifest, String) = try await fetchManifest(
            repository: "\(self.organization)/\(imageName)",
            tag: imageTag,
            token: token
        )

        // Get manifest identifier using the manifest's own digest
        let manifestId = getManifestIdentifier(manifest, manifestDigest: manifestDigest)

        Logger.info(
            "Pulling image",
            metadata: [
                "repository": imageName,
                "manifest_id": manifestId,
            ])

        // Create temporary directory for the entire VM setup
        let tempVMDir = FileManager.default.temporaryDirectory.appendingPathComponent(
            "lume_vm_\(UUID().uuidString)")
        try FileManager.default.createDirectory(at: tempVMDir, withIntermediateDirectories: true)
        defer {
            try? FileManager.default.removeItem(at: tempVMDir)
        }

        // Set total size and file count for progress tracking
        let totalFiles = manifest.layers.filter {
            $0.mediaType != "application/vnd.oci.empty.v1+json"
        }.count
        let totalSize = manifest.layers.reduce(0) { $0 + Int64($1.size) }
        await downloadProgress.setTotal(totalSize, files: totalFiles)

        // Process layers
        Logger.info("Processing Image layers")
        
        // Group layers by type
        var configLayer: Layer? = nil
        var diskLayers: [OCIManifestLayer] = []
        var nvramLayer: Layer? = nil
        
        for layer in manifest.layers {
            switch layer.mediaType {
            case "application/vnd.oci.image.config.v1+json":
                configLayer = layer
            case "application/octet-stream":
                if manifest.config != nil {
                    nvramLayer = layer // Assume nvram if config exists
                } else {
                    // Convert to OCIManifestLayer for disk handling
                    diskLayers.append(OCIManifestLayer(
                        mediaType: layer.mediaType,
                        size: layer.size,
                        digest: layer.digest
                    ))
                }
            case "application/vnd.lume.disk.image",
                 "application/octet-stream+gzip":
                // Convert to OCIManifestLayer for disk handling
                diskLayers.append(OCIManifestLayer(
                    mediaType: layer.mediaType,
                    size: layer.size,
                    digest: layer.digest
                ))
            default:
                Logger.info("Skipping unsupported layer media type: \(layer.mediaType)")
                continue
            }
        }

        // Pull and process disk layers using DiskV2 style handling
        if !diskLayers.isEmpty {
            let diskURL = tempVMDir.appendingPathComponent("disk.img")
            let progress = Progress(totalUnitCount: Int64(totalSize))
            try await pullDiskImage(
                registry: Registry(host: registry, namespace: "\(organization)/\(imageName)"),
                diskLayers: diskLayers,
                outputURL: diskURL,
                progress: progress
            )
        }

        // Pull config and nvram if present
        if let configLayer = configLayer {
            let configURL = tempVMDir.appendingPathComponent("config.json")
            try await downloadLayer(
                repository: "\(organization)/\(imageName)",
                digest: configLayer.digest,
                mediaType: configLayer.mediaType,
                token: token,
                to: configURL,
                maxRetries: 5,
                progress: downloadProgress,
                manifestId: manifestId
            )
        }

        if let nvramLayer = nvramLayer {
            let nvramURL = tempVMDir.appendingPathComponent("nvram.bin")
            try await downloadLayer(
                repository: "\(organization)/\(imageName)",
                digest: nvramLayer.digest,
                mediaType: nvramLayer.mediaType,
                token: token,
                to: nvramURL,
                maxRetries: 5,
                progress: downloadProgress,
                manifestId: manifestId
            )
        }

        // Move files to final location
        if FileManager.default.fileExists(atPath: vmDirURL.path) {
            try FileManager.default.removeItem(at: vmDirURL)
        }
        try FileManager.default.moveItem(at: tempVMDir, to: vmDirURL)

        Logger.info("Image pulled successfully", metadata: ["name": vmName])
    }

    private func copyFromCache(manifest: Manifest, manifestId: String, to destination: URL)
        async throws
    {
        Logger.info("Copying from cache...")
        
        // Define output URL and expected size variable scope here
        let outputURL = destination.appendingPathComponent("disk.img")
        var expectedTotalSize: UInt64? = nil // Use optional to handle missing config

        // Instantiate collector
        let diskPartsCollector = DiskPartsCollector()
        // Remove totalDiskParts
        // var totalDiskParts: Int? = nil
        var lz4LayerCount = 0 // Count lz4 layers found

        // First identify disk parts and non-disk files
        for layer in manifest.layers {
            let cachedLayer = getCachedLayerPath(manifestId: manifestId, digest: layer.digest)

            // Identify disk parts simply by media type
            if layer.mediaType == "application/octet-stream+lz4" {
                 lz4LayerCount += 1 // Increment count
                 // Add to collector. It will assign the sequential part number.
                 let collectorPartNum = await diskPartsCollector.addPart(url: cachedLayer) 
                 Logger.info("Adding cached lz4 layer (part \(lz4LayerCount)) -> Collector #\(collectorPartNum): \(cachedLayer.lastPathComponent)")
            }
            else {
                 // --- Handle Non-Disk-Part Layer (from cache) ---
                let fileName: String
                switch layer.mediaType {
                case "application/vnd.oci.image.config.v1+json":
                    fileName = "config.json"
                case "application/octet-stream":
                    // Assume nvram if config layer exists, otherwise assume single disk image
                    fileName = manifest.config != nil ? "nvram.bin" : "disk.img"
                case "application/vnd.oci.image.layer.v1.tar", 
                     "application/octet-stream+gzip":
                     // Assume disk image for these types as well if encountered in cache scenario
                     fileName = "disk.img"
                default:
                     Logger.info("Skipping unsupported cached layer media type: \(layer.mediaType)")
                    continue
                }
                // Copy the non-disk file directly from cache to destination
                try FileManager.default.copyItem(
                    at: cachedLayer,
                    to: destination.appendingPathComponent(fileName)
                )
            }
        }

        // --- Safely retrieve parts AFTER loop --- 
        let diskPartSources = await diskPartsCollector.getSortedParts() // Sorted by assigned sequential number
        let totalParts = await diskPartsCollector.getTotalParts() // Get total count from collector

        // Remove old guard check
        /*
        guard let totalParts = totalDiskParts else {
            Logger.info("No cached layers with valid part information found. Assuming single-part image or non-lz4 parts.")
        }
        */
        Logger.info("Found \(totalParts) lz4 disk parts in cache to reassemble.")
        // --- End retrieving parts --- 

        // Reassemble disk parts if needed
        // Use the count from the collector
        if !diskPartSources.isEmpty {
            // Use totalParts from collector directly
            Logger.info("Reassembling \(totalParts) disk image parts using sparse file technique...") 
            
            // Get uncompressed size from cached config file (needs to be copied first)
            let configURL = destination.appendingPathComponent("config.json")
            // Parse config.json to get uncompressed size *before* reassembly
            let uncompressedSize = getUncompressedSizeFromConfig(configPath: configURL)

            // Now also try to get disk size from VM config if OCI annotation not found
            var vmConfigDiskSize: UInt64? = nil
            if uncompressedSize == nil && FileManager.default.fileExists(atPath: configURL.path) {
                do {
                    let configData = try Data(contentsOf: configURL)
                    let decoder = JSONDecoder()
                    if let vmConfig = try? decoder.decode(VMConfig.self, from: configData) {
                        vmConfigDiskSize = vmConfig.diskSize
                        if let size = vmConfigDiskSize {
                            Logger.info("Found diskSize from VM config.json: \(size) bytes")
                        }
                    }
                } catch {
                    Logger.error("Failed to parse VM config.json for diskSize: \(error)")
                }
            }

            // Determine the size to use for the sparse file
            // Use: annotation size > VM config diskSize > fallback (error)
            if let size = uncompressedSize {
                Logger.info("Using uncompressed size from annotation: \(size) bytes")
                expectedTotalSize = size
            } else if let size = vmConfigDiskSize {
                Logger.info("Using diskSize from VM config: \(size) bytes")
                expectedTotalSize = size
            } else {
                // If neither is found in cache scenario, throw error as we cannot determine the size
                Logger.error(
                    "Missing both uncompressed size annotation and VM config diskSize for cached multi-part image." 
                    + " Cannot reassemble."
                )
                throw PullError.missingUncompressedSizeAnnotation
            }

            // Now that expectedTotalSize is guaranteed to be non-nil, proceed with setup
            guard let sizeForTruncate = expectedTotalSize else {
                 // This should not happen due to the checks above, but safety first
                 let nilError: Error? = nil
                 // Use nil-coalescing to provide a default error, appeasing the compiler
                 throw PullError.reassemblySetupFailed(path: outputURL.path, underlyingError: nilError ?? NoSpecificUnderlyingError())
            }

            // Wrap file handle setup and sparse file creation within this block
            let outputHandle: FileHandle
            do {
                // Ensure parent directory exists
                try FileManager.default.createDirectory(at: outputURL.deletingLastPathComponent(), withIntermediateDirectories: true)
                // Explicitly create the file first, removing old one if needed
                if FileManager.default.fileExists(atPath: outputURL.path) {
                    try FileManager.default.removeItem(at: outputURL)
                }
                guard FileManager.default.createFile(atPath: outputURL.path, contents: nil) else {
                    throw PullError.fileCreationFailed(outputURL.path)
                }
                // Open handle for writing
                outputHandle = try FileHandle(forWritingTo: outputURL)
                // Set the file size (creates sparse file)
                try outputHandle.truncate(atOffset: sizeForTruncate)
                Logger.info("Sparse file initialized for cache reassembly with size: \(ByteCountFormatter.string(fromByteCount: Int64(sizeForTruncate), countStyle: .file))")
            } catch {
                 Logger.error("Failed during setup for cached disk image reassembly: \(error.localizedDescription)", metadata: ["path": outputURL.path])
                 throw PullError.reassemblySetupFailed(path: outputURL.path, underlyingError: error)
            }

            // Ensure handle is closed when exiting this scope
            defer { try? outputHandle.close() }

            // ... (Get uncompressed size etc.) ...

            var reassemblyProgressLogger = ProgressLogger(threshold: 0.05)
            var currentOffset: UInt64 = 0

            // Iterate from 1 up to the total number of parts found by the collector
            for collectorPartNum in 1...totalParts {
                // Find the source URL from our collected parts using the sequential collectorPartNum
                guard let sourceInfo = diskPartSources.first(where: { $0.0 == collectorPartNum }) else {
                    Logger.error("Missing required cached part number \(collectorPartNum) in collected parts during reassembly.")
                    throw PullError.missingPart(collectorPartNum)
                }
                let sourceURL = sourceInfo.1 // Get URL from tuple

                // Log using the sequential collector part number
                Logger.info(
                    "Decompressing part \(collectorPartNum) of \(totalParts) from cache: \(sourceURL.lastPathComponent) at offset \(currentOffset)..."
                )

                // Always use the correct sparse decompression function
                let decompressedBytesWritten = try decompressChunkAndWriteSparse(
                    inputPath: sourceURL.path,
                    outputHandle: outputHandle,
                    startOffset: currentOffset
                )
                currentOffset += decompressedBytesWritten
                // Update progress (using sizeForTruncate which should be available)
                reassemblyProgressLogger.logProgress(
                        current: Double(currentOffset) / Double(sizeForTruncate), 
                        context: "Reassembling Cache")
                
                try outputHandle.synchronize() // Optional: Synchronize after each chunk
            }

            // Finalize progress, close handle (done by defer)
            reassemblyProgressLogger.logProgress(current: 1.0, context: "Reassembly Complete")

            // Ensure output handle is closed before post-processing
            // No need for explicit close here, defer handles it
            // try outputHandle.close()

            // Verify final size
            let finalSize =
                (try? FileManager.default.attributesOfItem(atPath: outputURL.path)[.size]
                    as? UInt64) ?? 0
            Logger.info(
                "Final disk image size from cache (before sparse file optimization): \(ByteCountFormatter.string(fromByteCount: Int64(finalSize), countStyle: .file))"
            )

            // Use the calculated sizeForTruncate for comparison
            if finalSize != sizeForTruncate {
                Logger.info(
                    "Warning: Final reported size (\(finalSize) bytes) differs from expected size (\(sizeForTruncate) bytes), but this doesn't affect functionality"
                )
            }

            Logger.info("Disk image reassembly completed")
        }

        Logger.info("Cache copy complete")
    }

    private func getToken(repository: String) async throws -> String {
        let encodedRepo = repository.addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed) ?? repository
        // Request both pull and push scope for uploads
        let url = URL(string: "https://\(self.registry)/token?scope=repository:\(encodedRepo):pull,push&service=\(self.registry)")!
        
        var request = URLRequest(url: url)
        request.httpMethod = "GET" // Token endpoint uses GET
        request.setValue("application/json", forHTTPHeaderField: "Accept")

        // *** Add Basic Authentication Header if credentials exist ***
        let (username, password) = getCredentialsFromEnvironment()
        if let username = username, let password = password, !username.isEmpty, !password.isEmpty {
            let authString = "\(username):\(password)"
            if let authData = authString.data(using: .utf8) {
                let base64Auth = authData.base64EncodedString()
                request.setValue("Basic \(base64Auth)", forHTTPHeaderField: "Authorization")
                Logger.info("Adding Basic Authentication header to token request.")
            } else {
                Logger.error("Failed to encode credentials for Basic Auth.")
            }
        } else {
            Logger.info("No credentials found in environment for token request.")
            // Allow anonymous request for pull scope, but push scope likely requires auth
        }
        // *** End Basic Auth addition ***

        let (data, response) = try await URLSession.shared.data(for: request)
        
        // Check response status code *before* parsing JSON
        guard let httpResponse = response as? HTTPURLResponse else {
            throw PushError.authenticationFailed // Or a more generic network error
        }
        
        guard httpResponse.statusCode == 200 else {
            // Log detailed error including status code and potentially response body
            let responseBody = String(data: data, encoding: .utf8) ?? "(Could not decode body)"
            Logger.error("Token request failed with status code: \(httpResponse.statusCode). Response: \(responseBody)")
            // Throw specific error based on status if needed (e.g., 401 for unauthorized)
            throw PushError.authenticationFailed 
        }
        
        let jsonResponse = try JSONSerialization.jsonObject(with: data) as? [String: Any]
        guard let token = jsonResponse?["token"] as? String ?? jsonResponse?["access_token"] as? String else {
            Logger.error("Token not found in registry response.")
            throw PushError.missingToken
        }
        
        return token
    }

    private func fetchManifest(repository: String, tag: String, token: String) async throws -> (
        Manifest, String
    ) {
        var request = URLRequest(
            url: URL(string: "https://\(self.registry)/v2/\(repository)/manifests/\(tag)")!)
        request.addValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        request.addValue("application/vnd.oci.image.manifest.v1+json", forHTTPHeaderField: "Accept")

        let (data, response) = try await URLSession.shared.data(for: request)
        guard let httpResponse = response as? HTTPURLResponse,
            httpResponse.statusCode == 200,
            let digest = httpResponse.value(forHTTPHeaderField: "Docker-Content-Digest")
        else {
            throw PullError.manifestFetchFailed
        }

        let manifest = try JSONDecoder().decode(Manifest.self, from: data)
        return (manifest, digest)
    }

    private func downloadLayer(
        repository: String,
        digest: String,
        mediaType: String,
        token: String,
        to url: URL,
        maxRetries: Int = 5,
        progress: isolated ProgressTracker,
        manifestId: String? = nil
    ) async throws {
        var lastError: Error?

        // Create a shared session configuration for all download attempts
        let config = URLSessionConfiguration.default
        config.timeoutIntervalForRequest = 60
        config.timeoutIntervalForResource = 3600
        config.waitsForConnectivity = true
        config.httpMaximumConnectionsPerHost = 6
        config.httpShouldUsePipelining = true
        config.requestCachePolicy = .reloadIgnoringLocalCacheData

        // Enable HTTP/2 when available
        if #available(macOS 13.0, *) {
            config.httpAdditionalHeaders = ["Connection": "keep-alive"]
        }

        // Check for TCP window size and optimize if possible
        if getTCPReceiveWindowSize() != nil {
            config.networkServiceType = .responsiveData
        }

        // Create one session to be reused across retries
        let session = URLSession(configuration: config)

        for attempt in 1...maxRetries {
            do {
                var request = URLRequest(
                    url: URL(string: "https://\(self.registry)/v2/\(repository)/blobs/\(digest)")!)
                request.addValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
                request.addValue(mediaType, forHTTPHeaderField: "Accept")
                request.timeoutInterval = 60

                // Add Accept-Encoding for compressed transfer if content isn't already compressed
                if !mediaType.contains("gzip") && !mediaType.contains("compressed") {
                    request.addValue("gzip, deflate", forHTTPHeaderField: "Accept-Encoding")
                }

                let (tempURL, response) = try await session.download(for: request)
                guard let httpResponse = response as? HTTPURLResponse,
                    httpResponse.statusCode == 200
                else {
                    throw PullError.layerDownloadFailed(digest)
                }

                try FileManager.default.createDirectory(
                    at: url.deletingLastPathComponent(), withIntermediateDirectories: true)
                try FileManager.default.moveItem(at: tempURL, to: url)
                progress.addProgress(Int64(httpResponse.expectedContentLength))

                // Cache the downloaded layer if caching is enabled
                if cachingEnabled, let manifestId = manifestId {
                    let cachedLayer = getCachedLayerPath(manifestId: manifestId, digest: digest)
                    if FileManager.default.fileExists(atPath: cachedLayer.path) {
                        try FileManager.default.removeItem(at: cachedLayer)
                    }
                    try FileManager.default.copyItem(at: url, to: cachedLayer)
                }

                // Mark download as complete regardless of caching
                markDownloadComplete(digest)
                return

            } catch {
                lastError = error
                if attempt < maxRetries {
                    // Exponential backoff with jitter for retries
                    let baseDelay = Double(attempt) * 2
                    let jitter = Double.random(in: 0...1)
                    let delay = baseDelay + jitter
                    try await Task.sleep(nanoseconds: UInt64(delay * 1_000_000_000))

                    Logger.info("Retrying download (attempt \(attempt+1)/\(maxRetries)): \(digest)")
                }
            }
        }

        throw lastError ?? PullError.layerDownloadFailed(digest)
    }

    // Function removed as it's not applicable to the observed manifest format
    /*
    private func extractPartInfo(from mediaType: String) -> (partNum: Int, total: Int)? {
        let pattern = #"part\\.number=(\\d+);part\\.total=(\\d+)"#
        guard let regex = try? NSRegularExpression(pattern: pattern),
            let match = regex.firstMatch(
                in: mediaType,
                range: NSRange(mediaType.startIndex..., in: mediaType)
            ),
            let partNumRange = Range(match.range(at: 1), in: mediaType),
            let totalRange = Range(match.range(at: 2), in: mediaType),
            let partNum = Int(mediaType[partNumRange]),
            let total = Int(mediaType[totalRange])
        else {
            return nil
        }
        return (partNum, total)
    }
    */

    private func listRepositories() async throws -> [String] {
        var request = URLRequest(
            url: URL(string: "https://\(registry)/v2/\(organization)/repositories/list")!)
        request.setValue("application/json", forHTTPHeaderField: "Accept")

        let (data, response) = try await URLSession.shared.data(for: request)
        guard let httpResponse = response as? HTTPURLResponse else {
            throw PullError.manifestFetchFailed
        }

        if httpResponse.statusCode == 404 {
            return []
        }

        guard httpResponse.statusCode == 200 else {
            throw PullError.manifestFetchFailed
        }

        let repoList = try JSONDecoder().decode(RepositoryList.self, from: data)
        return repoList.repositories
    }

    func getImages() async throws -> [CachedImage] {
        Logger.info("Scanning for cached images in \(cacheDirectory.path)")
        var images: [CachedImage] = []
        let orgDir = cacheDirectory.appendingPathComponent(organization)

        if FileManager.default.fileExists(atPath: orgDir.path) {
            let contents = try FileManager.default.contentsOfDirectory(atPath: orgDir.path)
            Logger.info("Found \(contents.count) items in cache directory")

            for item in contents {
                let itemPath = orgDir.appendingPathComponent(item)
                var isDirectory: ObjCBool = false

                guard
                    FileManager.default.fileExists(
                        atPath: itemPath.path, isDirectory: &isDirectory),
                    isDirectory.boolValue
                else { continue }

                // First try to read metadata file
                let metadataPath = itemPath.appendingPathComponent("metadata.json")
                if let metadataData = try? Data(contentsOf: metadataPath),
                    let metadata = try? JSONDecoder().decode(ImageMetadata.self, from: metadataData)
                {
                    Logger.info(
                        "Found metadata for image",
                        metadata: [
                            "image": metadata.image,
                            "manifest_id": metadata.manifestId,
                        ])
                    images.append(
                        CachedImage(
                            repository: metadata.image,
                            imageId: String(metadata.manifestId.prefix(12)),
                            manifestId: metadata.manifestId
                        ))
                    continue
                }

                // Fallback to checking manifest if metadata doesn't exist
                Logger.info("No metadata found for \(item), checking manifest")
                let manifestPath = itemPath.appendingPathComponent("manifest.json")
                guard FileManager.default.fileExists(atPath: manifestPath.path),
                    let manifestData = try? Data(contentsOf: manifestPath),
                    let manifest = try? JSONDecoder().decode(Manifest.self, from: manifestData)
                else {
                    Logger.info("No valid manifest found for \(item)")
                    continue
                }

                let manifestId = item

                // Verify the manifest ID matches
                let currentManifestId = getManifestIdentifier(manifest, manifestDigest: "")
                Logger.info(
                    "Manifest check",
                    metadata: [
                        "item": item,
                        "current_manifest_id": currentManifestId,
                        "matches": "\(currentManifestId == manifestId)",
                    ])
                if currentManifestId == manifestId {
                    // Skip if we can't determine the repository name
                    // This should be rare since we now save metadata during pull
                    Logger.info("Skipping image without metadata: \(item)")
                    continue
                }
            }
        } else {
            Logger.info("Cache directory does not exist")
        }

        Logger.info("Found \(images.count) cached images")
        return images.sorted {
            $0.repository == $1.repository ? $0.imageId < $1.imageId : $0.repository < $1.repository
        }
    }

    private func listRemoteImageTags(repository: String) async throws -> [String] {
        var request = URLRequest(
            url: URL(string: "https://\(registry)/v2/\(organization)/\(repository)/tags/list")!)
        request.setValue("application/json", forHTTPHeaderField: "Accept")

        let (data, response) = try await URLSession.shared.data(for: request)
        guard let httpResponse = response as? HTTPURLResponse else {
            throw PullError.manifestFetchFailed
        }

        if httpResponse.statusCode == 404 {
            return []
        }

        guard httpResponse.statusCode == 200 else {
            throw PullError.manifestFetchFailed
        }

        let repoTags = try JSONDecoder().decode(RepositoryTags.self, from: data)
        return repoTags.tags
    }

    // Determine appropriate chunk size based on available system memory on macOS
    private func getOptimalChunkSize() -> Int {
        // Try to get system memory info
        var stats = vm_statistics64_data_t()
        var size = mach_msg_type_number_t(
            MemoryLayout<vm_statistics64_data_t>.size / MemoryLayout<integer_t>.size)
        let hostPort = mach_host_self()

        let result = withUnsafeMutablePointer(to: &stats) { statsPtr in
            statsPtr.withMemoryRebound(to: integer_t.self, capacity: Int(size)) { ptr in
                host_statistics64(hostPort, HOST_VM_INFO64, ptr, &size)
            }
        }

        // Define chunk size parameters
        let safeMinimumChunkSize = 128 * 1024  // Reduced minimum for constrained systems
        let defaultChunkSize = 512 * 1024  // Standard default / minimum for non-constrained
        let constrainedCap = 512 * 1024  // Lower cap for constrained systems
        let standardCap = 2 * 1024 * 1024  // Standard cap for non-constrained systems

        // If we can't get memory info, return a reasonable default
        guard result == KERN_SUCCESS else {
            Logger.info(
                "Could not get VM statistics, using default chunk size: \(defaultChunkSize) bytes")
            return defaultChunkSize
        }

        // Calculate free memory in bytes
        let pageSize = 4096  // Use a constant page size assumption
        let freeMemory = UInt64(stats.free_count) * UInt64(pageSize)
        let isConstrained = determineIfMemoryConstrained()  // Check if generally constrained

        // Extremely constrained (< 512MB free) -> use absolute minimum
        if freeMemory < 536_870_912 {  // 512MB
            Logger.info(
                "System extremely memory constrained (<512MB free), using minimum chunk size: \(safeMinimumChunkSize) bytes"
            )
            return safeMinimumChunkSize
        }

        // Generally constrained -> use adaptive size with lower cap
        if isConstrained {
            let adaptiveSize = min(
                max(Int(freeMemory / 1000), safeMinimumChunkSize), constrainedCap)
            Logger.info(
                "System memory constrained, using adaptive chunk size capped at \(constrainedCap) bytes: \(adaptiveSize) bytes"
            )
            return adaptiveSize
        }

        // Not constrained -> use original adaptive logic with standard cap
        let adaptiveSize = min(max(Int(freeMemory / 1000), defaultChunkSize), standardCap)
        Logger.info(
            "System has sufficient memory, using adaptive chunk size capped at \(standardCap) bytes: \(adaptiveSize) bytes"
        )
        return adaptiveSize
    }

    // Check if system is memory constrained for more aggressive memory management
    private func determineIfMemoryConstrained() -> Bool {
        var stats = vm_statistics64_data_t()
        var size = mach_msg_type_number_t(
            MemoryLayout<vm_statistics64_data_t>.size / MemoryLayout<integer_t>.size)
        let hostPort = mach_host_self()

        let result = withUnsafeMutablePointer(to: &stats) { statsPtr in
            statsPtr.withMemoryRebound(to: integer_t.self, capacity: Int(size)) { ptr in
                host_statistics64(hostPort, HOST_VM_INFO64, ptr, &size)
            }
        }

        guard result == KERN_SUCCESS else {
            // If we can't determine, assume constrained for safety
            return true
        }

        // Calculate free memory in bytes using a fixed page size
        // Standard page size on macOS is 4KB or 16KB
        let pageSize = 4096  // Use a constant instead of vm_kernel_page_size
        let freeMemory = UInt64(stats.free_count) * UInt64(pageSize)

        // Consider memory constrained if less than 2GB free
        return freeMemory < 2_147_483_648  // 2GB
    }

    // Helper method to determine network quality
    private func determineNetworkQuality() -> Int {
        // Default quality is medium (3)
        var quality = 3

        // A simple ping test to determine network quality
        let process = Process()
        process.executableURL = URL(fileURLWithPath: "/sbin/ping")
        process.arguments = ["-c", "3", "-q", self.registry]

        let outputPipe = Pipe()
        process.standardOutput = outputPipe
        process.standardError = outputPipe

        do {
            try process.run()
            process.waitUntilExit()

            let outputData = try outputPipe.fileHandleForReading.readToEnd() ?? Data()
            if let output = String(data: outputData, encoding: .utf8) {
                // Check for average ping time
                if let avgTimeRange = output.range(
                    of: "= [0-9.]+/([0-9.]+)/", options: .regularExpression)
                {
                    let avgSubstring = output[avgTimeRange]
                    if let avgString = avgSubstring.split(separator: "/").dropFirst().first,
                        let avgTime = Double(avgString)
                    {

                        // Classify network quality based on ping time
                        if avgTime < 50 {
                            quality = 5  // Excellent
                        } else if avgTime < 100 {
                            quality = 4  // Good
                        } else if avgTime < 200 {
                            quality = 3  // Average
                        } else if avgTime < 300 {
                            quality = 2  // Poor
                        } else {
                            quality = 1  // Very poor
                        }
                    }
                }
            }
        } catch {
            // Default to medium if ping fails
            Logger.info("Failed to determine network quality, using default settings")
        }

        return quality
    }

    // Helper method to calculate optimal concurrency based on system capabilities
    private func calculateOptimalConcurrency(memoryConstrained: Bool, networkQuality: Int) -> Int {
        // Base concurrency based on network quality (1-5)
        let baseThreads = min(networkQuality * 2, 8)

        if memoryConstrained {
            // Reduce concurrency for memory-constrained systems
            return max(2, baseThreads / 2)
        }

        // Physical cores available on the system
        let cores = ProcessInfo.processInfo.processorCount

        // Adaptive approach: 1-2 threads per core depending on network quality
        let threadsPerCore = (networkQuality >= 4) ? 2 : 1
        let systemBasedThreads = min(cores * threadsPerCore, 12)

        // Take the larger of network-based and system-based concurrency
        return max(baseThreads, systemBasedThreads)
    }

    // Helper to get optimal TCP window size
    private func getTCPReceiveWindowSize() -> Int? {
        // Try to query system TCP window size
        let process = Process()
        process.executableURL = URL(fileURLWithPath: "/usr/sbin/sysctl")
        process.arguments = ["net.inet.tcp.recvspace"]

        let outputPipe = Pipe()
        process.standardOutput = outputPipe

        do {
            try process.run()
            process.waitUntilExit()

            let outputData = try outputPipe.fileHandleForReading.readToEnd() ?? Data()
            if let output = String(data: outputData, encoding: .utf8),
                let valueStr = output.split(separator: ":").last?.trimmingCharacters(
                    in: .whitespacesAndNewlines),
                let value = Int(valueStr)
            {
                return value
            }
        } catch {
            // Ignore errors, we'll use defaults
        }

        return nil
    }

    // Add helper to check media type and get decompress command
    private func getDecompressionCommand(for mediaType: String) -> String? {
        // Determine appropriate decompression command based on layer media type
        Logger.info("Determining decompression command for media type: \(mediaType)")

        // For the specific format that appears in our GHCR repository, skip decompression attempts
        // These files are labeled +lzfse but aren't actually in Apple Archive format
        if mediaType.contains("+lzfse;part.number=") {
            Logger.info("Detected LZFSE part file, using direct copy instead of decompression")
            return nil
        }

        // Check for LZFSE or Apple Archive format anywhere in the media type string
        // The format may include part information like: application/octet-stream+lzfse;part.number=1;part.total=38
        if mediaType.contains("+lzfse") || mediaType.contains("+aa") {
            // Apple Archive format requires special handling
            if let aaPath = findExecutablePath(for: "aa") {
                Logger.info("Found Apple Archive tool at: \(aaPath)")
                return "apple_archive:\(aaPath)"
            } else {
                Logger.error(
                    "Apple Archive tool (aa) not found in PATH, falling back to default path")

                // Check if the default path exists
                let defaultPath = "/usr/bin/aa"
                if FileManager.default.isExecutableFile(atPath: defaultPath) {
                    Logger.info("Default Apple Archive tool exists at: \(defaultPath)")
                } else {
                    Logger.error("Default Apple Archive tool not found at: \(defaultPath)")
                }

                return "apple_archive:/usr/bin/aa"
            }
        } else {
            Logger.info(
                "Unsupported media type: \(mediaType) - only Apple Archive (+lzfse/+aa) is supported"
            )
            return nil
        }
    }

    // Helper to find executables (optional, or hardcode paths)
    private func findExecutablePath(for executableName: String) -> String? {
        let pathEnv =
            ProcessInfo.processInfo.environment["PATH"]
            ?? "/usr/bin:/bin:/usr/sbin:/sbin:/usr/local/bin:/opt/homebrew/bin"
        let paths = pathEnv.split(separator: ":")
        for path in paths {
            let executablePath = URL(fileURLWithPath: String(path)).appendingPathComponent(
                executableName
            ).path
            if FileManager.default.isExecutableFile(atPath: executablePath) {
                return executablePath
            }
        }
        return nil
    }

    // Helper function to extract uncompressed disk size from config.json
    private func getUncompressedSizeFromConfig(configPath: URL) -> UInt64? {
        guard FileManager.default.fileExists(atPath: configPath.path) else {
            Logger.info("Config file not found: \(configPath.path)")
            return nil
        }

        do {
            let configData = try Data(contentsOf: configPath)
            let decoder = JSONDecoder()
            let ociConfig = try decoder.decode(OCIConfig.self, from: configData)

            if let sizeString = ociConfig.annotations?.uncompressedSize,
                let size = UInt64(sizeString)
            {
                Logger.info("Found uncompressed disk size annotation: \(size) bytes")
                return size
            } else {
                Logger.info("No uncompressed disk size annotation found in config.json")
                return nil
            }
        } catch {
            Logger.error("Failed to parse config.json for uncompressed size: \(error)")
            return nil
        }
    }

    // Helper function to find formatted file with potential extensions
    private func findFormattedFile(tempFormatted: URL) -> URL? {
        // Check for the exact path first
        if FileManager.default.fileExists(atPath: tempFormatted.path) {
            return tempFormatted
        }

        // Check with .dmg extension
        let dmgPath = tempFormatted.path + ".dmg"
        if FileManager.default.fileExists(atPath: dmgPath) {
            return URL(fileURLWithPath: dmgPath)
        }

        // Check with .sparseimage extension
        let sparsePath = tempFormatted.path + ".sparseimage"
        if FileManager.default.fileExists(atPath: sparsePath) {
            return URL(fileURLWithPath: sparsePath)
        }

        // Try to find any file with the same basename
        do {
            let files = try FileManager.default.contentsOfDirectory(
                at: tempFormatted.deletingLastPathComponent(),
                includingPropertiesForKeys: nil)
            if let matchingFile = files.first(where: {
                $0.lastPathComponent.starts(with: tempFormatted.lastPathComponent)
            }) {
                return matchingFile
            }
        } catch {
            Logger.error("Failed to list directory contents: \(error)")
        }

        return nil
    }

    // Helper function to decompress LZFSE compressed disk image
    @discardableResult
    private func decompressLZFSEImage(inputPath: String, outputPath: String? = nil) -> Bool {
        Logger.info("Attempting to decompress LZFSE compressed disk image using sparse pipe...")

        let finalOutputPath = outputPath ?? inputPath  // If outputPath is nil, we'll overwrite input
        let tempFinalPath = finalOutputPath + ".ddsparse.tmp"  // Temporary name during dd operation

        // Ensure the temporary file doesn't exist from a previous failed run
        try? FileManager.default.removeItem(atPath: tempFinalPath)

        // Process 1: compression_tool
        let process1 = Process()
        process1.executableURL = URL(fileURLWithPath: "/usr/bin/compression_tool")
        process1.arguments = [
            "-decode",
            "-i", inputPath,
            "-o", "/dev/stdout",  // Write to standard output
        ]

        // Process 2: dd
        let process2 = Process()
        process2.executableURL = URL(fileURLWithPath: "/bin/dd")
        process2.arguments = [
            "if=/dev/stdin",  // Read from standard input
            "of=\(tempFinalPath)",  // Write to the temporary final path
            "conv=sparse",  // Use sparse conversion
            "bs=1m",  // Use a reasonable block size (e.g., 1MB)
        ]

        // Create pipes
        let pipe = Pipe()  // Connects process1 stdout to process2 stdin
        let errorPipe1 = Pipe()
        let errorPipe2 = Pipe()

        process1.standardOutput = pipe
        process1.standardError = errorPipe1

        process2.standardInput = pipe
        process2.standardError = errorPipe2

        do {
            Logger.info("Starting decompression pipe: compression_tool | dd conv=sparse...")
            // Start processes
            try process1.run()
            try process2.run()

            // Close the write end of the pipe for process2 to prevent hanging
            // This might not be strictly necessary if process1 exits cleanly, but safer.
            // Note: Accessing fileHandleForWriting after run can be tricky.
            // We rely on process1 exiting to signal EOF to process2.

            process1.waitUntilExit()
            process2.waitUntilExit()  // Wait for dd to finish processing the stream

            // --- Check for errors ---
            let errorData1 = errorPipe1.fileHandleForReading.readDataToEndOfFile()
            if !errorData1.isEmpty,
                let errorString = String(data: errorData1, encoding: .utf8)?.trimmingCharacters(
                    in: .whitespacesAndNewlines), !errorString.isEmpty
            {
                Logger.error("compression_tool stderr: \(errorString)")
            }
            let errorData2 = errorPipe2.fileHandleForReading.readDataToEndOfFile()
            if !errorData2.isEmpty,
                let errorString = String(data: errorData2, encoding: .utf8)?.trimmingCharacters(
                    in: .whitespacesAndNewlines), !errorString.isEmpty
            {
                // dd often reports blocks in/out to stderr, filter that if needed, but log for now
                Logger.info("dd stderr: \(errorString)")
            }

            // Check termination statuses
            let status1 = process1.terminationStatus
            let status2 = process2.terminationStatus

            if status1 != 0 || status2 != 0 {
                Logger.error(
                    "Pipe command failed. compression_tool status: \(status1), dd status: \(status2)"
                )
                try? FileManager.default.removeItem(atPath: tempFinalPath)  // Clean up failed attempt
                return false
            }

            // --- Validation ---
            if FileManager.default.fileExists(atPath: tempFinalPath) {
                let fileSize =
                    (try? FileManager.default.attributesOfItem(atPath: tempFinalPath)[.size]
                        as? UInt64) ?? 0
                let actualUsage = getActualDiskUsage(path: tempFinalPath)
                Logger.info(
                    "Piped decompression successful - Allocated: \(ByteCountFormatter.string(fromByteCount: Int64(fileSize), countStyle: .file)), Actual Usage: \(ByteCountFormatter.string(fromByteCount: Int64(actualUsage), countStyle: .file))"
                )

                // Basic header validation
                var isValid = false
                if let fileHandle = FileHandle(forReadingAtPath: tempFinalPath) {
                    if let data = try? fileHandle.read(upToCount: 512), data.count >= 512,
                        data[510] == 0x55 && data[511] == 0xAA
                    {
                        isValid = true
                    }
                    // Ensure handle is closed regardless of validation outcome
                    try? fileHandle.close()
                } else {
                    Logger.error(
                        "Validation Error: Could not open decompressed file handle for reading.")
                }

                if isValid {
                    Logger.info("Decompressed file appears to be a valid disk image.")

                    // Move the final file into place
                    // If outputPath was nil, we need to replace the original inputPath
                    if outputPath == nil {
                        // Backup original only if it's different from the temp path
                        if inputPath != tempFinalPath {
                            try? FileManager.default.copyItem(
                                at: URL(fileURLWithPath: inputPath),
                                to: URL(fileURLWithPath: inputPath + ".compressed.bak"))
                            try? FileManager.default.removeItem(at: URL(fileURLWithPath: inputPath))
                        }
                        try FileManager.default.moveItem(
                            at: URL(fileURLWithPath: tempFinalPath),
                            to: URL(fileURLWithPath: inputPath))
                        Logger.info("Replaced original file with sparsely decompressed version.")
                    } else {
                        // If outputPath was specified, move it there (overwrite if needed)
                        try? FileManager.default.removeItem(
                            at: URL(fileURLWithPath: finalOutputPath))  // Remove existing if overwriting
                        try FileManager.default.moveItem(
                            at: URL(fileURLWithPath: tempFinalPath),
                            to: URL(fileURLWithPath: finalOutputPath))
                        Logger.info("Moved sparsely decompressed file to: \(finalOutputPath)")
                    }
                    return true
                } else {
                    Logger.error(
                        "Validation failed: Decompressed file header is invalid or file couldn't be read. Cleaning up."
                    )
                    try? FileManager.default.removeItem(atPath: tempFinalPath)
                    return false
                }
            } else {
                Logger.error(
                    "Piped decompression failed: Output file '\(tempFinalPath)' not found after dd completed."
                )
                return false
            }

        } catch {
            Logger.error("Error running decompression pipe command: \(error)")
            try? FileManager.default.removeItem(atPath: tempFinalPath)  // Clean up on error
            return false
        }
    }

    // Helper function to get actual disk usage of a file
    private func getActualDiskUsage(path: String) -> UInt64 {
        let task = Process()
        task.executableURL = URL(fileURLWithPath: "/usr/bin/du")
        task.arguments = ["-k", path]  // -k for 1024-byte blocks

        let pipe = Pipe()
        task.standardOutput = pipe

        do {
            try task.run()
            task.waitUntilExit()

            let data = pipe.fileHandleForReading.readDataToEndOfFile()
            if let output = String(data: data, encoding: .utf8),
                let size = UInt64(output.split(separator: "\t").first ?? "0")
            {
                return size * 1024  // Convert from KB to bytes
            }
        } catch {
            Logger.error("Failed to get actual disk usage: \(error)")
        }

        return 0
    }

    // New push method
    public func push(
        vmDirPath: String,
        imageName: String,
        tags: [String],
        chunkSizeMb: Int = 512,
        verbose: Bool = false,
        dryRun: Bool = false,
        reassemble: Bool = false
    ) async throws {
        let vmDir = URL(fileURLWithPath: vmDirPath)
        let diskURL = vmDir.appendingPathComponent("disk.img")

        // Validate required files exist
        guard FileManager.default.fileExists(atPath: diskURL.path) else {
            throw PushError.missingDiskImage
        }

        // Create registry instance for pushing
        let registry = Registry(host: self.registry, namespace: "\(self.organization)/\(imageName)")

        // Initialize layers array
        var layers: [OCIManifestLayer] = []

        // Process disk image in chunks
        var pushedLayers: [(index: Int, layer: OCIManifestLayer)] = []
        let diskData = try Data(contentsOf: diskURL)
        let chunkSize = chunkSizeMb * 1024 * 1024
        let chunks = stride(from: 0, to: diskData.count, by: chunkSize).map {
            diskData[$0..<min($0 + chunkSize, diskData.count)]
        }

        let progress = Progress(totalUnitCount: Int64(diskData.count))
        Logger.info("Pushing disk image in \(chunks.count) chunks")

        try await withThrowingTaskGroup(of: (index: Int, layer: OCIManifestLayer).self) { group in
            for (index, chunk) in chunks.enumerated() {
                group.addTask {
                    // Compress chunk
                    let compressedData = try chunk.compressed()
                    
                    // Push chunk with retry logic
                    let digest = try await withRetry {
                        try await registry.pushBlob(fromData: compressedData) { uploadedBytes in
                            Logger.debug("Uploaded \(uploadedBytes) bytes for chunk \(index + 1)/\(chunks.count)")
                        }
                    } recoverFromFailure: { error in
                        if error is URLError {
                            Logger.error("Network error while pushing layer: \(error.localizedDescription)")
                            Logger.info("Retrying...")
                            return .retry
                        }
                        return .throw
                    }
                    
                    return (index: index, layer: OCIManifestLayer(
                        mediaType: diskImageMediaType,
                        size: compressedData.count,
                        digest: digest,
                        uncompressedSize: UInt64(chunk.count),
                        uncompressedContentDigest: Digest.hash(chunk)
                    ))
                }
            }
            
            // Collect results
            for try await result in group {
                pushedLayers.append(result)
                progress.completedUnitCount += Int64(chunks[result.0].count)
            }
        }

        // Sort layers by index and add to layers array
        layers.append(contentsOf: pushedLayers.sorted { $0.0 < $1.0 }.map { $0.1 })

        // Create and push manifest
        let manifest = OCIManifest(
            config: OCIManifestConfig(
                mediaType: "application/vnd.oci.image.config.v1+json",
                size: 0,
                digest: ""
            ),
            layers: layers
        )

        // Push manifest for each tag
        for tag in tags {
            Logger.info("Pushing manifest for tag: \(tag)")
            _ = try await registry.pushManifest(reference: tag, manifest: manifest)
        }

        Logger.info("Image pushed successfully", metadata: ["name": imageName])
    }
}

actor UploadProgressTracker {
    private var totalBytes: Int64 = 0
    private var uploadedBytes: Int64 = 0 // Renamed
    private var progressLogger = ProgressLogger(threshold: 0.01) 
    private var totalFiles: Int = 0 // Keep track of total items
    private var completedFiles: Int = 0 // Keep track of completed items

    // Upload speed tracking
    private var startTime: Date = Date()
    private var lastUpdateTime: Date = Date()
    private var lastUpdateBytes: Int64 = 0
    private var speedSamples: [Double] = []
    private var peakSpeed: Double = 0
    private var totalElapsedTime: TimeInterval = 0

    // Smoothing factor for speed calculation
    private var speedSmoothing: Double = 0.3
    private var smoothedSpeed: Double = 0

    func setTotal(_ total: Int64, files: Int) {
        totalBytes = total
        totalFiles = files
        startTime = Date()
        lastUpdateTime = startTime
        uploadedBytes = 0 // Reset uploaded bytes
        completedFiles = 0 // Reset completed files
        smoothedSpeed = 0
        speedSamples = []
        peakSpeed = 0
        totalElapsedTime = 0
    }

    func addProgress(_ bytes: Int64) {
        uploadedBytes += bytes
        completedFiles += 1 // Increment completed files count
        let now = Date()
        let elapsed = now.timeIntervalSince(lastUpdateTime)

        // Show first progress update immediately, then throttle updates
        let shouldUpdate = (uploadedBytes <= bytes) || (elapsed >= 0.5) || (completedFiles == totalFiles)

        if shouldUpdate && totalBytes > 0 { // Ensure totalBytes is set
            let currentSpeed = Double(uploadedBytes - lastUpdateBytes) / max(elapsed, 0.001)
            speedSamples.append(currentSpeed)

            // Cap samples array
            if speedSamples.count > 20 {
                speedSamples.removeFirst(speedSamples.count - 20)
            }

            peakSpeed = max(peakSpeed, currentSpeed)

            // Apply exponential smoothing
            if smoothedSpeed == 0 { smoothedSpeed = currentSpeed } 
            else { smoothedSpeed = speedSmoothing * currentSpeed + (1 - speedSmoothing) * smoothedSpeed }

            let recentAvgSpeed = calculateAverageSpeed()
            let totalElapsed = now.timeIntervalSince(startTime)
            let overallAvgSpeed = totalElapsed > 0 ? Double(uploadedBytes) / totalElapsed : 0

            let progress = totalBytes > 0 ? Double(uploadedBytes) / Double(totalBytes) : 1.0 // Avoid division by zero
            logSpeedProgress(
                current: progress,
                currentSpeed: currentSpeed,
                averageSpeed: recentAvgSpeed,
                smoothedSpeed: smoothedSpeed,
                overallSpeed: overallAvgSpeed,
                peakSpeed: peakSpeed,
                context: "Uploading Image" // Changed context
            )

            lastUpdateTime = now
            lastUpdateBytes = uploadedBytes
            totalElapsedTime = totalElapsed
        }
    }

    private func calculateAverageSpeed() -> Double {
        guard !speedSamples.isEmpty else { return 0 }
        var totalWeight = 0.0
        var weightedSum = 0.0
        let samples = speedSamples.suffix(min(8, speedSamples.count))
        for (index, speed) in samples.enumerated() {
            let weight = Double(index + 1)
            weightedSum += speed * weight
            totalWeight += weight
        }
        return totalWeight > 0 ? weightedSum / totalWeight : 0
    }

    // Use the UploadStats struct
    func getUploadStats() -> UploadStats {
        let avgSpeed = totalElapsedTime > 0 ? Double(uploadedBytes) / totalElapsedTime : 0
        return UploadStats(
            totalBytes: totalBytes,
            uploadedBytes: uploadedBytes, // Renamed
            elapsedTime: totalElapsedTime,
            averageSpeed: avgSpeed,
            peakSpeed: peakSpeed
        )
    }

    private func logSpeedProgress(
        current: Double,
        currentSpeed: Double,
        averageSpeed: Double,
        smoothedSpeed: Double,
        overallSpeed: Double,
        peakSpeed: Double,
        context: String
    ) {
        let progressPercent = Int(current * 100)
        // let currentSpeedStr = formatByteSpeed(currentSpeed) // Removed unused
        let avgSpeedStr = formatByteSpeed(averageSpeed)
        // let peakSpeedStr = formatByteSpeed(peakSpeed) // Removed unused
        let remainingBytes = totalBytes - uploadedBytes
        let speedForEta = max(smoothedSpeed, averageSpeed * 0.8)
        let etaSeconds = speedForEta > 0 ? Double(remainingBytes) / speedForEta : 0
        let etaStr = formatTimeRemaining(etaSeconds)
        let progressBar = createProgressBar(progress: current)
        let fileProgress = "(\(completedFiles)/\(totalFiles))" // Add file count

        print(
            "\r\(progressBar) \(progressPercent)% \(fileProgress) | Speed: \(avgSpeedStr) (Avg) | ETA: \(etaStr)     ", // Simplified output
            terminator: "")
        fflush(stdout)
    }

    // Helper methods (createProgressBar, formatByteSpeed, formatTimeRemaining) remain the same
    private func createProgressBar(progress: Double, width: Int = 30) -> String {
        let completedWidth = Int(progress * Double(width))
        let remainingWidth = width - completedWidth
        let completed = String(repeating: "█", count: completedWidth)
        let remaining = String(repeating: "░", count: remainingWidth)
        return "[\(completed)\(remaining)]"
    }
    private func formatByteSpeed(_ bytesPerSecond: Double) -> String {
        let units = ["B/s", "KB/s", "MB/s", "GB/s"]
        var speed = bytesPerSecond
        var unitIndex = 0
        while speed > 1024 && unitIndex < units.count - 1 { speed /= 1024; unitIndex += 1 }
        return String(format: "%.1f %@", speed, units[unitIndex])
    }
    private func formatTimeRemaining(_ seconds: Double) -> String {
        if seconds.isNaN || seconds.isInfinite || seconds <= 0 { return "calculating..." }
        let hours = Int(seconds) / 3600
        let minutes = (Int(seconds) % 3600) / 60
        let secs = Int(seconds) % 60
        if hours > 0 { return String(format: "%d:%02d:%02d", hours, minutes, secs) }
        else { return String(format: "%d:%02d", minutes, secs) }
    }
}

