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

    private func getImageCacheDirectory(manifestId: String) -> URL {
        return cacheDirectory
            .appendingPathComponent(organization)
            .appendingPathComponent(manifestId)
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
                        
                        // Define path for the downloaded (potentially compressed) layer data
                        let downloadedFilePath = tempDownloadDir.appendingPathComponent("layer_\(index)_\(layer.digest.replacingOccurrences(of: ":", with: "_"))_compressed")

                        // Download the blob to the temporary file path
                        try await ociClient.pullBlob(digest: layer.digest, to: downloadedFilePath, progress: progress)

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
                         case OCIConfigMediaType:
                             // Config not compressed, just move to final path
                              try FileManager.default.moveItem(at: downloadResult.downloadedFilePath, to: finalDataPath)
                         default:
                             // Unknown type, just move the downloaded file
                              try FileManager.default.moveItem(at: downloadResult.downloadedFilePath, to: finalDataPath)
                         }
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