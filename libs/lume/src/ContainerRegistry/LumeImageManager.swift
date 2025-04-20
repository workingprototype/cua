import ArgumentParser
import Darwin
import Foundation
import Swift
import CommonCrypto
import Compression
import CryptoKit
import System

// Manages Lume VM images in relation to an OCI registry
class LumeImageManager: @unchecked Sendable {
    private let registry: String
    private let organization: String
    private let cacheDirectory: URL
    private let cachingEnabled: Bool

    init(registry: String, organization: String, cacheDirectoryPath: String, cachingEnabled: Bool) {
        self.registry = registry
        self.organization = organization
        
        // Use the provided cache directory path
        // Path is already expanded by LumeController before passing
        self.cacheDirectory = URL(fileURLWithPath: cacheDirectoryPath)
            .appendingPathComponent("ghcr") // Still append ghcr subfolder

        // Use the provided caching enabled flag
        self.cachingEnabled = cachingEnabled

        // Ensure cache directory structure exists (ghcr/org)
        // This can stay here as it's specific to this manager's caching logic
        try? FileManager.default.createDirectory(
            at: self.cacheDirectory, withIntermediateDirectories: true)

        let orgDir = self.cacheDirectory.appendingPathComponent(organization)
        try? FileManager.default.createDirectory(at: orgDir, withIntermediateDirectories: true)
    }

    // --- Cache Helper Methods (Adapted from old snippet) ---

    // Creates an identifier suitable for directory names from a digest
    private func getManifestIdentifier(manifestDigest: String) -> String {
        return manifestDigest.replacingOccurrences(of: ":", with: "_")
    }

    private func getImageCacheDirectory(manifestId: String) -> URL {
        return cacheDirectory
            .appendingPathComponent(organization)
            .appendingPathComponent(manifestId)
    }

    private func getCachedManifestPath(manifestId: String) -> URL {
        return getImageCacheDirectory(manifestId: manifestId).appendingPathComponent("manifest.json")
    }

    private func getCachedLayerPath(manifestId: String, digest: String) -> URL {
        return getImageCacheDirectory(manifestId: manifestId).appendingPathComponent(
            digest.replacingOccurrences(of: ":", with: "_")
        )
    }

    // Creates the cache directory for a specific manifest ID, removing old if present
    private func setupImageCache(manifestId: String) async throws {
        guard cachingEnabled else { return } // Only setup if caching
        let cacheDir = getImageCacheDirectory(manifestId: manifestId)
        if FileManager.default.fileExists(atPath: cacheDir.path) {
            Logger.debug("Removing existing cache directory: \(cacheDir.path)")
            try FileManager.default.removeItem(at: cacheDir)
            // Simple retry loop in case of race conditions/delay in removal
            var attempts = 0
            while FileManager.default.fileExists(atPath: cacheDir.path) && attempts < 5 {
                 try await Task.sleep(nanoseconds: 100_000_000) // 100ms delay
                 try? FileManager.default.removeItem(at: cacheDir)
                 attempts += 1
            }
            if FileManager.default.fileExists(atPath: cacheDir.path) {
                 Logger.error("Failed to remove existing cache directory after multiple attempts: \(cacheDir.path)")
                 // Decide if this is fatal? For now, continue, download might fail later
            }
        }
        try FileManager.default.createDirectory(at: cacheDir, withIntermediateDirectories: true)
         Logger.info("Created new cache directory: \(cacheDir.path)")
    }

    // Loads the cached manifest file
    private func loadCachedManifest(manifestId: String) -> OCIManifest? { // Use current OCIManifest
        guard cachingEnabled else { return nil }
        let manifestPath = getCachedManifestPath(manifestId: manifestId)
        guard let data = try? Data(contentsOf: manifestPath) else { return nil }
        // Use current OCIManifest type
        return try? JSONDecoder().decode(OCIManifest.self, from: data) 
    }

    // Validates if the cache for a manifest ID is present and complete
    private func validateCache(manifest: OCIManifest, manifestId: String) -> Bool {
        guard cachingEnabled else {
             Logger.debug("Cache validation skipped: Caching disabled.")
             return false 
        }

        guard let cachedManifest = loadCachedManifest(manifestId: manifestId) else {
            Logger.debug("Cache validation failed: Cached manifest.json not found or invalid.")
            return false
        }
        
        // Simple equality check might be sufficient if Codable conformance handles it
        // Otherwise, compare critical fields like layers array
        guard cachedManifest.layers.count == manifest.layers.count && 
              cachedManifest.layers.map({ $0.digest }) == manifest.layers.map({ $0.digest }) else {
            Logger.debug("Cache validation failed: Layer mismatch between cached and fetched manifest.")
            return false
        }

        // Verify all layer files exist in the cache
        for layer in manifest.layers {
            let cachedLayerPath = getCachedLayerPath(manifestId: manifestId, digest: layer.digest)
            if !FileManager.default.fileExists(atPath: cachedLayerPath.path) {
                 Logger.debug("Cache validation failed: Missing layer file \(cachedLayerPath.lastPathComponent)")
                return false
            }
        }
        
        Logger.info("Cache validation successful for manifest ID: \(manifestId)")
        return true
    }

    // Saves the manifest JSON to the cache
    private func saveManifest(_ manifest: OCIManifest, manifestId: String) throws { // Use current OCIManifest
        guard cachingEnabled else { return } 
        let manifestPath = getCachedManifestPath(manifestId: manifestId)
        let encoder = JSONEncoder()
        encoder.outputFormatting = .prettyPrinted // Make it readable
        try encoder.encode(manifest).write(to: manifestPath)
        Logger.debug("Saved manifest.json to cache: \(manifestPath.path)")
    }

    // Saves image metadata (linking image name to manifest ID) to the cache
    private func saveImageMetadata(imageName: String, manifestId: String) throws {
        guard cachingEnabled else { return }
        let metadataPath = getImageCacheDirectory(manifestId: manifestId).appendingPathComponent("metadata.json")
        // Use current ImageMetadata struct
        let metadata = ImageMetadata( 
            image: imageName, // Store the base image name
            manifestId: manifestId, 
            timestamp: Date()
        )
        let encoder = JSONEncoder()
        encoder.outputFormatting = .prettyPrinted
        try encoder.encode(metadata).write(to: metadataPath)
        Logger.debug("Saved metadata.json to cache: \(metadataPath.path)")
    }

    // Removes cache directories for older versions of the same image repository
    private func cleanupOldVersions(currentManifestId: String, imageName: String) async throws {
        guard cachingEnabled else { return }
        Logger.info("Checking for old image versions to clean up...", metadata: ["image": imageName])
        let orgDir = cacheDirectory.appendingPathComponent(organization)
        guard FileManager.default.fileExists(atPath: orgDir.path) else { 
            Logger.debug("Organization cache directory not found, skipping cleanup.")
            return 
        }

        let contents = try FileManager.default.contentsOfDirectory(atPath: orgDir.path)
        var cleanedCount = 0
        for item in contents {
            // Skip the current manifest ID and non-directory items
            if item == currentManifestId { continue }
            let itemPath = orgDir.appendingPathComponent(item)
            var isDirectory: ObjCBool = false
            guard FileManager.default.fileExists(atPath: itemPath.path, isDirectory: &isDirectory), isDirectory.boolValue else { continue }

            // Check metadata file
            let metadataPath = itemPath.appendingPathComponent("metadata.json")
            if let metadataData = try? Data(contentsOf: metadataPath),
               let metadata = try? JSONDecoder().decode(ImageMetadata.self, from: metadataData) {
                // If metadata matches the image name, remove the old cache directory
                if metadata.image == imageName {
                    Logger.info("Removing old cached version: \(itemPath.lastPathComponent)")
                    try FileManager.default.removeItem(at: itemPath)
                    cleanedCount += 1
                }
            } else {
                // If no metadata, consider removing orphaned cache directories (optional, riskier)
                 Logger.debug("Orphaned cache directory found (no metadata): \(itemPath.lastPathComponent). Skipping removal.")
            }
        }
         if cleanedCount > 0 {
              Logger.info("Cleaned up \(cleanedCount) old cached version(s) for image '\(imageName)'.")
         } else {
              Logger.info("No old cached versions found for image '\(imageName)'.")
         }
    }

    // --- Public API Methods ---

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
                else {
                    continue
                }

                let metadataPath = itemPath.appendingPathComponent("metadata.json")
                if let metadataData = try? Data(contentsOf: metadataPath),
                   let metadata = try? JSONDecoder().decode(ImageMetadata.self, from: metadataData)
                {
                    images.append(CachedImage(
                        repository: metadata.image,
                        imageId: item,
                        manifestId: metadata.manifestId
                    ))
                }
            }
        }

        return images
    }

    func pull(image: String, name: String, targetVmDirPath: String) async throws {
        Logger.info("Pulling image \(image) as \(name) to \(targetVmDirPath)")

        // 1. Parse Image Reference
        let imageComponents = image.split(separator: ":", maxSplits: 1)
        guard imageComponents.count == 2 else {
            throw PullError.invalidImageFormat
        }
        let imageName = String(imageComponents[0])
        let imageTag = String(imageComponents[1])

        // 2. Initialize OCI Client
        let ociClient = OCIClient(host: self.registry, namespace: "\(self.organization)/\(imageName)")

        let (manifest, manifestDigest) = try await ociClient.pullManifest(reference: imageTag)
        Logger.info("Pulled manifest (\(manifestDigest)) with \(manifest.layers.count) layers.")

        // Calculate manifest ID for caching
        let manifestId = getManifestIdentifier(manifestDigest: manifestDigest)

        // 3. Prepare Target Directory (Path is now directly provided)
        let vmDirURL = URL(fileURLWithPath: targetVmDirPath)
        Logger.info("Using target VM directory: \(vmDirURL.path)")

        // Create the specific VM directory (don't allow intermediate here, parent should exist)
         do {
              try FileManager.default.createDirectory(at: vmDirURL, withIntermediateDirectories: false, attributes: nil)
         } catch let nsError as NSError where nsError.code == NSFileWriteFileExistsError {
              Logger.info("VM directory \(vmDirURL.path) already exists. Proceeding to overwrite contents.")
         } catch {
              Logger.error("Failed to create VM directory \(vmDirURL.path): \(error.localizedDescription)")
              throw PullError.targetDirectoryError("Failed to create VM directory: \(error.localizedDescription)")
         }
        // Logger.info("VM will be stored at: \(vmDirURL.path)") // Redundant log

        // --- CACHING LOGIC --- 
        if cachingEnabled && validateCache(manifest: manifest, manifestId: manifestId) {
             Logger.info("Valid cache found for \(manifestId), reconstructing from cache.")
             // TODO: Implement reconstruction from cache (Step 2b)
             // For now, we will just log and continue to download phase
             // This prevents the pull from actually *using* the cache yet
             Logger.info("Cache hit detected, but reconstruction from cache is not yet implemented. Proceeding with download.")
             // In a full implementation, we would skip the download/decompress below
             // and instead call a function like `reconstructVMFromCache(manifest: manifest, manifestId: manifestId, vmDirURL: vmDirURL)`
        }
        // --- END CACHING CHECK ---

        // If cache miss or caching disabled, proceed with download:
        if !(cachingEnabled && validateCache(manifest: manifest, manifestId: manifestId)) { // Re-check condition
             if cachingEnabled {
                 Logger.info("Cache miss or invalid for \(manifestId), proceeding with download and caching.")
                 // Prepare cache directory for the new manifest
                 try await cleanupOldVersions(currentManifestId: manifestId, imageName: imageName)
                 try await setupImageCache(manifestId: manifestId)
                 try saveManifest(manifest, manifestId: manifestId)
                 try saveImageMetadata(imageName: imageName, manifestId: manifestId) // Use imageName
             } else {
                 Logger.info("Caching disabled, proceeding with download without caching.")
             }

            // 4. Download Layers Concurrently
            // Define result type for download tasks (path to downloaded file)
            typealias LayerDownloadResult = (index: Int, mediaType: String, layerDigest: String, downloadedFilePath: URL)

            let totalSize = manifest.layers.reduce(0) { $0 + $1.size }
            let progress = Progress(totalUnitCount: totalSize)
            // Create and start the progress bar
            let progressBar = ProgressBarController(progress: progress, description: "Pulling Layers")
            await progressBar.start()

            var downloadedLayersData: [LayerDownloadResult] = []
            downloadedLayersData.reserveCapacity(manifest.layers.count)

            // Use temporary directory for individual layer downloads before processing
            let tempDownloadDir = FileManager.default.temporaryDirectory.appendingPathComponent("lume_pull_\(UUID().uuidString)")
            try FileManager.default.createDirectory(at: tempDownloadDir, withIntermediateDirectories: true)
            // Ensure cleanup of temp dir
            defer { Task { try? FileManager.default.removeItem(at: tempDownloadDir) } }

            Logger.info("Starting concurrent download of \(manifest.layers.count) layers...")

            // Define a limit for concurrent downloads
            let maxConcurrentDownloads = 10 // Example limit, adjust as needed
            var runningDownloadTasks = 0

            do {
                try await withThrowingTaskGroup(of: LayerDownloadResult.self) { group in
                    for (index, layer) in manifest.layers.enumerated() {
                        // Wait for a slot if concurrency limit is reached
                        while runningDownloadTasks >= maxConcurrentDownloads {
                            if try await group.next() != nil {
                                runningDownloadTasks -= 1
                            } else {
                                // Should not happen unless group is empty, but break defensively
                                break
                            }
                        }
                        
                        // We have a slot, add the new download task
                        runningDownloadTasks += 1
                        
                        group.addTask { // No need to capture self here anymore
                            Logger.debug("Queueing download for layer \(index + 1)/\(manifest.layers.count): \(layer.digest) (\(layer.mediaType))")
                            
                            let downloadedFilePath = tempDownloadDir.appendingPathComponent("layer_\(index)_\(layer.digest.replacingOccurrences(of: ":", with: "_"))_compressed")

                            // Download the blob to the temporary file path
                            try await ociClient.pullBlob(digest: layer.digest, to: downloadedFilePath, progress: progress)

                            // --- ADD CACHING STEP --- 
                            if self.cachingEnabled {
                                let cachedLayerPath = self.getCachedLayerPath(manifestId: manifestId, digest: layer.digest)
                                 do {
                                     // Copy downloaded file to cache *before* potential decompression/move
                                     try FileManager.default.copyItem(at: downloadedFilePath, to: cachedLayerPath)
                                     Logger.debug("Cached layer \(index + 1) to \(cachedLayerPath.lastPathComponent)")
                                 } catch {
                                     Logger.error("Failed to copy layer \(layer.digest) to cache: \(error.localizedDescription)")
                                     // Non-fatal, continue with processing the downloaded file
                                 }
                            }
                            // --- END CACHING STEP --- 

                            Logger.debug("Finished download for layer \(index + 1)/\(manifest.layers.count): \(layer.digest)")
                            // Return path to the downloaded file (might still be compressed)
                            return (index: index, mediaType: layer.mediaType, layerDigest: layer.digest, downloadedFilePath: downloadedFilePath)
                        }
                    }
                    
                    // Wait for any remaining tasks to complete after the loop
                    while let _ = try await group.next() {
                         runningDownloadTasks -= 1 // Decrement count as remaining tasks finish
                    }
                }
                Logger.info("All layers downloaded successfully.")
            } catch {
                 Logger.error("Failed to download or process layers concurrently: \(error.localizedDescription)")
                throw error 
            }
            
            // Ensure progress bar finishes after download phase
            await progressBar.finish()
            
            // --- Step 4b: Decompress downloaded layers concurrently (limited) ---
            Logger.info("Starting decompression of downloaded layers...")
            // Define result type for decompression tasks
            typealias DecompressResult = (index: Int, mediaType: String, finalDataURL: URL)
            var processedLayers: [DecompressResult] = []
            processedLayers.reserveCapacity(downloadedLayersData.count)
            
            // Limit decompression concurrency (e.g., half the cores)
            let maxDecompressTasks = ProcessInfo.processInfo.processorCount / 2 + 1 
            var runningDecompressTasks = 0
            
            do {
                try await withThrowingTaskGroup(of: DecompressResult.self) { group in
                    for downloadResult in downloadedLayersData {
                        // Wait for a slot if concurrency limit is reached
                        while runningDecompressTasks >= maxDecompressTasks {
                            // Wait for *any* running task to finish
                            if try await group.next() != nil {
                                runningDecompressTasks -= 1 
                            } else {
                                break // Group is empty, shouldn't happen here
                            }
                        }

                        // Add new decompression task
                        runningDecompressTasks += 1

                        // Submit decompression task
                         group.addTask { [self] in // Capture self for decompress method
                             Logger.debug("Processing downloaded layer \(downloadResult.index + 1): digest=\(downloadResult.layerDigest), mediaType=\(downloadResult.mediaType)") 
                             let finalDataPath = tempDownloadDir.appendingPathComponent("layer_\(downloadResult.index)_\(downloadResult.layerDigest.replacingOccurrences(of: ":", with: "_"))_final")
                             
                             switch downloadResult.mediaType {
                             case DiskMediaTypeLZ4, NvramMediaTypeLZ4:
                                 Logger.debug("Decompressing layer \(downloadResult.index + 1) (\(downloadResult.mediaType))...")
                                 let compressedData = try Data(contentsOf: downloadResult.downloadedFilePath)
                                 let decompressedData = try self.decompress(data: compressedData)
                                 try decompressedData.write(to: finalDataPath)
                                 // Clean up compressed file now
                                 try? FileManager.default.removeItem(at: downloadResult.downloadedFilePath)
                                 Logger.debug("Decompressed layer \(downloadResult.index + 1) size: \(decompressedData.count)")
                             case OCIConfigMediaType, "application/vnd.oci.image.config.v1+json":
                                 // Config not compressed, just move to final path
                                  try FileManager.default.moveItem(at: downloadResult.downloadedFilePath, to: finalDataPath)
                                  Logger.debug("Processed config layer \(downloadResult.index + 1)")
                             default:
                                 // Unknown type, just move the downloaded file
                                  try FileManager.default.moveItem(at: downloadResult.downloadedFilePath, to: finalDataPath)
                                  Logger.info("Unknown layer type \(downloadResult.mediaType) processed by moving.")
                             }
                             // Return must be outside the switch to capture all cases
                             return (index: downloadResult.index, mediaType: downloadResult.mediaType, finalDataURL: finalDataPath)
                         }
                     }
                     
                     // Wait for and collect results from all remaining tasks after loop finishes
                     while let result = try await group.next() {
                         processedLayers.append(result)
                         Logger.debug("Finished processing layer \(result.index + 1) for final assembly.")
                         // Counter doesn't strictly need decrementing here as we exit loop when group is empty
                         // runningDecompressTasks -= 1 
                     }
                }
                Logger.info("All layers decompressed/processed successfully.")
            } catch {
                 Logger.error("Failed during layer decompression/processing: \(error.localizedDescription)")
                 throw error // Rethrow
            }

            // 5. Process Downloaded Data and Reconstruct VM Files
            var diskChunks: [Int: Data] = [:]
            var nvramData: Data? = nil
            var configFileURL: URL? = nil

            for result in processedLayers {
                switch result.mediaType {
                case DiskMediaTypeLZ4:
                    // Read the final (decompressed) data for this chunk
                    // This still loads chunk into memory, but only one at a time during assembly
                    diskChunks[result.index] = try Data(contentsOf: result.finalDataURL)
                case NvramMediaTypeLZ4:
                    nvramData = try Data(contentsOf: result.finalDataURL)
                case OCIConfigMediaType:
                    configFileURL = result.finalDataURL // Keep track of the final config file URL
                    Logger.debug("Ignoring config layer content for VM reconstruction.")
                default:
                     Logger.info("Ignoring layer \(result.index) with unknown media type \(result.mediaType) during VM reconstruction.")
                }
            }

            let diskURL = vmDirURL.appendingPathComponent("disk.img")
            Logger.info("Reassembling disk image at \(diskURL.path)...")
            
            // Explicitly create/clear the file before opening handle
            if !FileManager.default.fileExists(atPath: diskURL.path) {
                guard FileManager.default.createFile(atPath: diskURL.path, contents: nil) else {
                     Logger.error("Failed to create initial disk image file at \(diskURL.path).")
                     throw PullError.fileCreationFailed(diskURL.path)
                }
            } else {
                 // If it exists, maybe clear it first (optional, depends on desired overwrite behavior)
                 // try? FileManager.default.removeItem(at: diskURL)
                 // guard FileManager.default.createFile(atPath: diskURL.path, contents: nil) else { ... }
            }

            guard let diskHandle = try? FileHandle(forWritingTo: diskURL) else { 
                 Logger.error("Failed to open \(diskURL.path) for writing.")
                 throw PullError.vmReconstructionFailed 
            }
            defer { try? diskHandle.close() }

            let sortedIndices = diskChunks.keys.sorted()
            var expectedNextIndex = -1 
            for index in sortedIndices {
                 if manifest.layers.indices.contains(index) && manifest.layers[index].mediaType == DiskMediaTypeLZ4 {
                     if expectedNextIndex == -1 {
                         expectedNextIndex = index + 1
                     } else if index != expectedNextIndex {
                         Logger.error("Disk chunk indices are not contiguous. Expected \(expectedNextIndex), got \(index). Cannot reassemble reliably.")
                         throw PullError.vmReconstructionFailed
                     } else {
                         expectedNextIndex += 1
                     }
                     
                     if let chunk = diskChunks[index] {
                         do {
                             try diskHandle.write(contentsOf: chunk)
                         } catch {
                             Logger.error("Failed to write disk chunk \(index) to \(diskURL.path): \(error.localizedDescription)")
                             throw PullError.vmReconstructionFailed
                         }
                     } else {
                         Logger.error("Internal error: Missing disk chunk data for index \(index)")
                         throw PullError.vmReconstructionFailed
                     }
                } 
            }
            try? diskHandle.synchronize()
            Logger.info("Finished reassembling disk image.")

            if let nvramData = nvramData {
                let nvramURL = vmDirURL.appendingPathComponent("nvram")
                try nvramData.write(to: nvramURL)
                Logger.info("Wrote nvram file at \(nvramURL.path)")
            }

            // Copy config.json from its temporary final location
            if let sourceConfigURL = configFileURL {
                 let configJsonURL = vmDirURL.appendingPathComponent("config.json")
                 do {
                      // Remove existing destination if present before copying
                      try? FileManager.default.removeItem(at: configJsonURL)
                      try FileManager.default.copyItem(at: sourceConfigURL, to: configJsonURL)
                      Logger.info("Wrote config.json from downloaded config layer at \(configJsonURL.path)")
                 } catch {
                      Logger.error("Failed to write downloaded config.json: \(error.localizedDescription)")
                      // Optional: Throw an error here? Depends on how critical config.json is.
                      // throw PullError.vmReconstructionFailed 
                 }
            } else {
                 // This case should ideally not happen if the manifest includes a config layer
                 Logger.error("Config layer data was not downloaded. Cannot write config.json.")
                 // Optional: Throw an error here?
                 // throw PullError.vmReconstructionFailed 
            }

            let metadata = ImageMetadata(image: image, manifestId: manifestDigest, timestamp: Date())
            let metadataURL = vmDirURL.appendingPathComponent("metadata.json")
            let metadataData = try JSONEncoder().encode(metadata)
            try metadataData.write(to: metadataURL)
            Logger.info("Wrote metadata file at \(metadataURL.path)")

            Logger.info("Successfully pulled \(image) to \(vmDirURL.path)")
        } // End of cache miss / download block
        
        // --- RECONSTRUCTION PHASE (Moved outside cache conditional for now) ---
        // This part runs regardless of cache hit/miss in this *intermediate* step
        // TODO: Implement actual reconstruction *from cache* in the cache hit block above.
    }

    func push(vmDirPath: String, imageName: String, tags: [String], chunkSizeMb: Int = 512, verbose: Bool = false, dryRun: Bool = false, reassemble: Bool = true) async throws {
        Logger.info("Pushing VM from \(vmDirPath) as \(imageName) with tags: \(tags.joined(separator: ", "))")
        Logger.debug("Chunk size: \(chunkSizeMb)MB, Dry run: \(dryRun), Reassemble: \(reassemble)")

        let vmDirURL = URL(fileURLWithPath: vmDirPath)
        guard FileManager.default.fileExists(atPath: vmDirURL.path) else {
            throw PushError.missingDiskImage
        }

        let diskURL = vmDirURL.appendingPathComponent("disk.img")
        let nvramURL = vmDirURL.appendingPathComponent("nvram.bin")
        let configJsonURL = vmDirURL.appendingPathComponent("config.json") // Path for config.json

        guard FileManager.default.fileExists(atPath: diskURL.path) else {
            throw PushError.missingDiskImage
        }
        // Ensure config.json exists
        guard FileManager.default.fileExists(atPath: configJsonURL.path) else {
            Logger.error("Missing essential config.json in VM directory: \(configJsonURL.path)")
            throw PushError.missingDiskImage // Or a more specific error like missingConfigFile
        }

        let ociClient = OCIClient(host: self.registry, namespace: "\(self.organization)/\(imageName)")

        // --- Create Layers ---
        var layers: [OCIManifestLayer] = []
        var totalUncompressedSize: Int64 = 0

        // 1. Config Layer (Reference only - Read local config.json)
        let configData = try Data(contentsOf: configJsonURL)
        let configDigest = Digest.hash(configData)
        let configLayer = OCIManifestConfig(mediaType: OCIConfigMediaType, size: configData.count, digest: configDigest)
        Logger.info("Using VM config.json for OCI config reference: \(configDigest)")
        // Config blob itself is not pushed as a layer per OCI spec

        // 2. NVRAM Layer (if exists)
        if FileManager.default.fileExists(atPath: nvramURL.path) {
            let nvramRawData = try Data(contentsOf: nvramURL)
            let nvramCompressedData = try compress(data: nvramRawData)
            let nvramDigest = Digest.hash(nvramCompressedData)
            let nvramUncompressedDigest = Digest.hash(nvramRawData)
            let nvramLayer = OCIManifestLayer(
                mediaType: NvramMediaTypeLZ4,
                size: Int64(nvramCompressedData.count),
                digest: nvramDigest,
                annotations: [
                    OCIAnnotationUncompressedSize: String(nvramRawData.count),
                    OCIAnnotationUncompressedDigest: nvramUncompressedDigest
                ]
            )
            layers.append(nvramLayer)

            if !dryRun {
                let exists = try await ociClient.blobExists(nvramDigest) // Restore blob exists check
                if !exists {
                    Logger.info("Uploading nvram blob...") 
                    _ = try await ociClient.pushBlob(fromData: nvramCompressedData, digest: nvramDigest) 
                    Logger.info("NVRAM blob uploaded.")
                } else {
                   Logger.info("NVRAM blob \(nvramDigest) already exists on registry.")
                }
            } else {
                Logger.info("[Dry Run] NVRAM layer prepared.")
            }
        } else {
            Logger.info("nvram file not found at \(nvramURL.path), skipping nvram layer.")
        }


        // 3. Disk Layer(s) - Using DiskV2 Style Chunking
        let diskRawData = try Data(contentsOf: diskURL, options: [.alwaysMapped]) 
        let layerLimitBytes = chunkSizeMb * 1024 * 1024 
        let diskChunks = diskRawData.chunks(ofCount: layerLimitBytes)
        let totalChunks = diskChunks.count
        Logger.info("Disk image size: \(diskRawData.count) bytes. Splitting into \(totalChunks) chunks (max size: \(layerLimitBytes) bytes).")

        let diskProgress = Progress(totalUnitCount: Int64(diskRawData.count))
        // Create and start the progress bar for disk operations
        let diskProgressBar = ProgressBarController(progress: diskProgress, description: "Processing/Uploading Disk")
        await diskProgressBar.start()
        
        // Ensure progress bar finishes even if errors occur
        defer { Task { await diskProgressBar.finish() } }

        typealias ChunkResult = (index: Int, layer: OCIManifestLayer)
        var processedDiskLayers: [ChunkResult] = []
        processedDiskLayers.reserveCapacity(totalChunks)

        Logger.info("Starting concurrent processing of \(totalChunks) disk chunks...")
        do {
            try await withThrowingTaskGroup(of: ChunkResult.self) { group in
                for (index, chunk) in diskChunks.enumerated() {
                    group.addTask { [self, diskProgress] in // Capture self and diskProgress
                        Logger.debug("Processing disk chunk \(index + 1)/\(totalChunks)...")
                        let chunkUncompressedDigest = Digest.hash(chunk)
                        let chunkCompressedData = try self.compress(data: chunk)
                        let chunkCompressedDigest = Digest.hash(chunkCompressedData)

                        let diskLayer = OCIManifestLayer(
                            mediaType: DiskMediaTypeLZ4,
                            size: Int64(chunkCompressedData.count),
                            digest: chunkCompressedDigest,
                            annotations: [
                                OCIAnnotationUncompressedSize: String(chunk.count),
                                OCIAnnotationUncompressedDigest: chunkUncompressedDigest
                            ]
                        )

                        Logger.info("Created disk layer \(index + 1)/\(totalChunks): \(chunkCompressedDigest)")

                        if !dryRun {
                            let exists = try await ociClient.blobExists(chunkCompressedDigest) // Restore blob exists check
                            if !exists {
                                Logger.info("Uploading disk blob \(index + 1)/\(totalChunks)...") 
                                _ = try await ociClient.pushBlob(fromData: chunkCompressedData, chunkSizeMb: 0, digest: chunkCompressedDigest, progress: diskProgress) 
                                Logger.info("Disk blob \(index + 1)/\(totalChunks) uploaded.")
                            } else {
                                Logger.info("Disk blob \(index + 1)/\(totalChunks) \(chunkCompressedDigest) already exists.")
                                // If skipping upload, still update progress based on original chunk size
                                diskProgress.completedUnitCount += Int64(chunk.count)
                            }
                        } else {
                            Logger.info("[Dry Run] Disk layer \(index + 1)/\(totalChunks) prepared.")
                            // Simulate progress in dry run
                            diskProgress.completedUnitCount += Int64(chunk.count)

                            if reassemble {
                                Logger.debug("[Dry Run] Reassembly check not yet implemented.")
                            }
                        }
                        return (index: index, layer: diskLayer)
                    }
                }
                
                for try await result in group {
                    processedDiskLayers.append(result)
                }
            }
            Logger.info("Finished processing all disk chunks.")
        } catch {
             Logger.error("Failed to process or upload disk chunks concurrently: \(error.localizedDescription)")
             if error is OCIClientError { // Use OCIClientError
                 throw PushError.blobUploadFailed
             } else {
                 throw error
             }
        }

        let sortedDiskLayers = processedDiskLayers.sorted { $0.index < $1.index }.map { $0.layer }
        layers.append(contentsOf: sortedDiskLayers)
        totalUncompressedSize = layers.reduce(0) { sum, layer in
            if let sizeStr = layer.annotations?[OCIAnnotationUncompressedSize], let size = Int64(sizeStr) {
                return sum + size
            } else {
                 Logger.info("Warning: Missing uncompressed size annotation for layer \(layer.digest). Using compressed size for total.")
                 return sum + layer.size 
            }
        }

        // --- Create and Push Manifest ---
        let manifest = OCIManifest(config: configLayer, layers: layers)
        let manifestData = try JSONEncoder().encode(manifest)
        let manifestDigest = Digest.hash(manifestData)
        Logger.info("Created final manifest (\(layers.count) layers), total uncompressed size: \(totalUncompressedSize), digest: \(manifestDigest)")

        if !dryRun {
            Logger.info("Pushing manifest for tags: \(tags.joined(separator: ", "))")
            for tag in tags {
                 Logger.info("Pushing manifest for tag: \(tag)...")
                _ = try await ociClient.pushManifest(reference: tag, manifest: manifest) // Use ociClient
                 Logger.info("Manifest pushed for tag: \(tag)")
            }
             Logger.info("Image push completed successfully.")
        } else {
            Logger.info("[Dry Run] Manifest prepared. Skipping manifest push.")
            if verbose {
                print("--- Manifest JSON (Dry Run) ---")
                print(String(data: manifestData, encoding: .utf8) ?? "Error decoding manifest JSON")
                print("-------------------------------")
            }
            Logger.info("[Dry Run] Completed.")
        }
    }

    // --- Helper: Compression ---
    private static let bufferSizeBytes = 4 * 1024 * 1024 // Moved inside class

    private func compress(data: Data) throws -> Data {
        try (data as NSData).compressed(using: .lz4) as Data
    }

     private func decompress(data: Data) throws -> Data {
        try (data as NSData).decompressed(using: .lz4) as Data
    }
} 