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
        Logger.info("Using target VM directory: \(vmDirURL.path)") // Updated log

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

        // 4. Download and Process Layers Concurrently
        typealias LayerDownloadResult = (index: Int, mediaType: String, data: Data)

        let totalSize = manifest.layers.reduce(0) { $0 + $1.size }
        let progress = Progress(totalUnitCount: totalSize)
        // Create and start the progress bar
        let progressBar = ProgressBarController(progress: progress, description: "Pulling Layers")
        await progressBar.start()

        // Ensure progress bar finishes even if errors occur
        defer { Task { await progressBar.finish() } }

        // Use temporary directory for individual layer downloads before processing
        let tempDownloadDir = FileManager.default.temporaryDirectory.appendingPathComponent("lume_pull_\(UUID().uuidString)")
        try FileManager.default.createDirectory(at: tempDownloadDir, withIntermediateDirectories: true)
        // Ensure cleanup of temp dir
        defer { Task { try? FileManager.default.removeItem(at: tempDownloadDir) } }

        // Store results: index, mediaType, final processed data URL (or just indicate completion)
        typealias LayerProcessResult = (index: Int, mediaType: String, finalDataURL: URL)
        var processedLayers: [LayerProcessResult] = []
        processedLayers.reserveCapacity(manifest.layers.count)

        Logger.info("Starting concurrent download of \(manifest.layers.count) layers...")

        do {
            // Use TaskGroup to download/decompress concurrently
            // Note: Decompressing directly after download might still use significant memory
            // if many large layers finish decompression around the same time.
            // A more advanced approach might limit concurrent *decompression* tasks.
            try await withThrowingTaskGroup(of: LayerProcessResult.self) { group in
                for (index, layer) in manifest.layers.enumerated() {
                    group.addTask { [self] in // Capture self to call decompress
                        Logger.debug("Starting download for layer \(index + 1)/\(manifest.layers.count): \(layer.digest) (\(layer.mediaType))")
                        
                        // Define final path within temp dir for the *processed* layer data
                        let finalDataPath = tempDownloadDir.appendingPathComponent("layer_\(index)_\(layer.digest.replacingOccurrences(of: ":", with: "_"))_final")

                        // Decompress if necessary, writing to finalDataPath
                        switch layer.mediaType {
                        case DiskMediaTypeLZ4, NvramMediaTypeLZ4:
                            // Download directly to a temp *compressed* path first
                            let downloadedFilePath = tempDownloadDir.appendingPathComponent("layer_\(index)_\(layer.digest.replacingOccurrences(of: ":", with: "_"))_compressed")
                            try await ociClient.pullBlob(digest: layer.digest, to: downloadedFilePath, progress: progress)
                            Logger.debug("Decompressing layer \(index + 1) (\(layer.mediaType))...")
                            let compressedData = try Data(contentsOf: downloadedFilePath)
                            let decompressedData = try self.decompress(data: compressedData)
                            try decompressedData.write(to: finalDataPath)
                            // Clean up compressed file
                            try? FileManager.default.removeItem(at: downloadedFilePath)
                            Logger.debug("Decompressed layer \(index + 1) (\(layer.mediaType)), original size: \(compressedData.count), decompressed: \(decompressedData.count)")
                        case OCIConfigMediaType:
                            // Config is not compressed, download directly to final path
                            try await ociClient.pullBlob(digest: layer.digest, to: finalDataPath, progress: progress)
                            Logger.debug("Processed config layer \(index + 1)")
                        default:
                            Logger.info("Unknown layer media type \(layer.mediaType) for layer \(index + 1), downloading raw data.")
                            // Download raw data directly to final path
                            try await ociClient.pullBlob(digest: layer.digest, to: finalDataPath, progress: progress)
                        }
                        Logger.debug("Finished processing layer \(index + 1)/\(manifest.layers.count): \(layer.digest)")
                        return (index: index, mediaType: layer.mediaType, finalDataURL: finalDataPath)
                    }
                }
                
                for try await result in group {
                    processedLayers.append(result)
                    // Increment main progress after a layer (and its decompression) completes
                    // Use the *original* manifest layer size for progress increment,
                    // as totalUnitCount is based on these sizes.
                    if manifest.layers.indices.contains(result.index) {
                         let originalLayerSize = manifest.layers[result.index].size
                         progress.completedUnitCount += originalLayerSize
                    } else {
                         Logger.error("Result index \(result.index) out of bounds for manifest layers.")
                    }
                }
            }
            Logger.info("All layers downloaded and processed successfully.")
        } catch {
             Logger.error("Failed to download or process layers concurrently: \(error.localizedDescription)")
            throw error 
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