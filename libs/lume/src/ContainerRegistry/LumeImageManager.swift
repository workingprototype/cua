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

    private static let holeGranularityBytes = 4 * 1024 * 1024 // 4MB block size for checking zeros
    private static let zeroChunk = Data(count: holeGranularityBytes)

    init(registry: String, organization: String, cacheDirectoryPath: String, cachingEnabled: Bool) {
        self.registry = registry
        self.organization = organization
        
        // Use the provided cache directory path
        // Path is already expanded by LumeController before passing
        self.cacheDirectory = URL(fileURLWithPath: cacheDirectoryPath)
            .appendingPathComponent("ghcr") // Still append ghcr subfolder

        // Use the provided caching enabled flag
        self.cachingEnabled = cachingEnabled

        Logger.debug("Initialized LumeImageManager with registry: \(registry), organization: \(organization)")
        Logger.debug("Cache directory: \(self.cacheDirectory.path), Caching enabled: \(cachingEnabled)")

        // Ensure cache directory structure exists (ghcr/org)
        // This can stay here as it's specific to this manager's caching logic
        do {
            try FileManager.default.createDirectory(
                at: self.cacheDirectory, withIntermediateDirectories: true)
            Logger.debug("Created or confirmed cache directory at: \(self.cacheDirectory.path)")

            let orgDir = self.cacheDirectory.appendingPathComponent(organization)
            try FileManager.default.createDirectory(at: orgDir, withIntermediateDirectories: true)
            Logger.debug("Created or confirmed organization cache directory at: \(orgDir.path)")
        } catch {
            Logger.error("Failed to create cache directory structure: \(error.localizedDescription)")
        }
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
        guard cachingEnabled else { 
            Logger.debug("Cache setup skipped: Caching disabled.")
            return 
        } 
        
        let cacheDir = getImageCacheDirectory(manifestId: manifestId)
        Logger.debug("Setting up image cache directory at: \(cacheDir.path)")
        
        if FileManager.default.fileExists(atPath: cacheDir.path) {
            Logger.debug("Removing existing cache directory: \(cacheDir.path)")
            do {
                try FileManager.default.removeItem(at: cacheDir)
                Logger.debug("Successfully removed existing cache directory")
            } catch {
                Logger.error("Error removing existing cache directory: \(error.localizedDescription)")
                // Continue with retry logic
            }
            
            // Simple retry loop in case of race conditions/delay in removal
            var attempts = 0
            while FileManager.default.fileExists(atPath: cacheDir.path) && attempts < 5 {
                 Logger.debug("Cache directory still exists, retrying removal (attempt \(attempts + 1)/5)")
                 try await Task.sleep(nanoseconds: 100_000_000) // 100ms delay
                 try? FileManager.default.removeItem(at: cacheDir)
                 attempts += 1
            }
            if FileManager.default.fileExists(atPath: cacheDir.path) {
                 Logger.error("Failed to remove existing cache directory after multiple attempts: \(cacheDir.path)")
                 // Decide if this is fatal? For now, continue, download might fail later
            }
        }
        
        do {
            try FileManager.default.createDirectory(at: cacheDir, withIntermediateDirectories: true)
            Logger.info("Created new cache directory: \(cacheDir.path)")
        } catch {
            Logger.error("Failed to create cache directory: \(error.localizedDescription)")
            throw error
        }
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
        
        // Log the cache directory path for debugging
        let cacheDir = getImageCacheDirectory(manifestId: manifestId)
        Logger.debug("Validating cache for manifest ID: \(manifestId)")
        Logger.debug("Cache directory path: \(cacheDir.path)")
        
        // Check if cache directory exists first
        guard FileManager.default.fileExists(atPath: cacheDir.path) else {
            Logger.debug("Cache validation failed: Cache directory not found at \(cacheDir.path)")
            return false
        }

        // Check for manifest file
        let manifestPath = getCachedManifestPath(manifestId: manifestId)
        Logger.debug("Checking cached manifest at: \(manifestPath.path)")
        guard FileManager.default.fileExists(atPath: manifestPath.path) else {
            Logger.debug("Cache validation failed: Manifest file not found at \(manifestPath.path)")
            return false
        }
        
        guard let cachedManifest = loadCachedManifest(manifestId: manifestId) else {
            Logger.debug("Cache validation failed: Cached manifest.json found but could not be decoded.")
            return false
        }
        
        // Simple equality check might be sufficient if Codable conformance handles it
        // Otherwise, compare critical fields like layers array
        let cachedDigests = cachedManifest.layers.map({ $0.digest }).sorted()
        let newDigests = manifest.layers.map({ $0.digest }).sorted()
        
        guard cachedManifest.layers.count == manifest.layers.count && 
              cachedDigests == newDigests else {
            Logger.debug("Cache validation failed: Layer mismatch between cached and fetched manifest.")
            Logger.debug("Cached layers count: \(cachedManifest.layers.count), Fetched layers count: \(manifest.layers.count)")
            return false
        }

        // Verify a sample of layer files exist in the cache (checking all might be too slow)
        let layersToCheck = min(manifest.layers.count, 10) // Check at most 10 layers
        var layersMissing = 0
        
        for i in 0..<layersToCheck {
            if i >= manifest.layers.count {
                break
            }
            let layer = manifest.layers[i]
            let cachedLayerPath = getCachedLayerPath(manifestId: manifestId, digest: layer.digest)
            if !FileManager.default.fileExists(atPath: cachedLayerPath.path) {
                layersMissing += 1
                Logger.debug("Cache validation found missing layer file: \(cachedLayerPath.lastPathComponent)")
                if layersMissing > 2 { // If more than 2 layers are missing, fail early
                    Logger.debug("Cache validation failed: Multiple layer files missing.")
                    return false
                }
            }
        }
        
        if layersMissing > 0 {
            Logger.debug("Cache validation failed: \(layersMissing) layer files missing.")
            return false
        }
        
        Logger.info("Cache validation successful for manifest ID: \(manifestId)")
        return true
    }

    // Saves the manifest JSON to the cache
    private func saveManifest(_ manifest: OCIManifest, manifestId: String) throws { // Use current OCIManifest
        guard cachingEnabled else { 
            Logger.debug("Manifest save skipped: Caching disabled.")
            return 
        } 
        let manifestPath = getCachedManifestPath(manifestId: manifestId)
        Logger.debug("Saving manifest to cache at: \(manifestPath.path)")
        
        let encoder = JSONEncoder()
        encoder.outputFormatting = .prettyPrinted // Make it readable
        
        do {
            let data = try encoder.encode(manifest)
            try data.write(to: manifestPath)
            Logger.debug("Successfully saved manifest.json to cache: \(manifestPath.path)")
            
            // Verify file exists after saving
            if FileManager.default.fileExists(atPath: manifestPath.path) {
                let fileSize = try FileManager.default.attributesOfItem(atPath: manifestPath.path)[.size] as? Int ?? 0
                Logger.debug("Verified manifest file exists with size: \(fileSize) bytes")
            } else {
                Logger.error("Failed to verify manifest file after saving: File does not exist")
            }
        } catch {
            Logger.error("Error encoding or saving manifest: \(error.localizedDescription)")
            throw error
        }
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
        guard imageComponents.count == 2 else { throw PullError.invalidImageFormat }
        let imageName = String(imageComponents[0])
        let imageTag = String(imageComponents[1])

        // 2. Initialize OCI Client
        let ociClient = OCIClient(host: self.registry, namespace: "\(self.organization)/\(imageName)")

        let (manifest, manifestDigest) = try await ociClient.pullManifest(reference: imageTag)
        Logger.info("Pulled manifest (\(manifestDigest)) with \(manifest.layers.count) layers.")
        let manifestId = getManifestIdentifier(manifestDigest: manifestDigest)

        // 3. Prepare Target Directory
        let vmDirURL = URL(fileURLWithPath: targetVmDirPath)
        Logger.info("Using target VM directory: \(vmDirURL.path)")
        do {
            try FileManager.default.createDirectory(at: vmDirURL, withIntermediateDirectories: false, attributes: nil)
        } catch let nsError as NSError where nsError.code == NSFileWriteFileExistsError {
            Logger.info("VM directory \(vmDirURL.path) already exists. Proceeding to overwrite contents.")
        } catch {
            Logger.error("Failed to create VM directory \(vmDirURL.path): \(error.localizedDescription)")
            throw PullError.targetDirectoryError("Failed to create VM directory: \(error.localizedDescription)")
        }

        // --- Initialize the missing variables ---
        // Dictionary to track paths to processed disk layers (index -> URL)
        var processedDiskLayerPaths: [Int: URL] = [:]
        // Track total uncompressed disk size for pre-allocation
        var totalUncompressedDiskSize: UInt64 = 0
        // Variables to store NVRAM and config data
        var nvramData: Data? = nil
        var configFileURL: URL? = nil

        // 4. Process layers and calculate total disk size
        for (_, layer) in manifest.layers.enumerated() {
            if layer.mediaType == DiskMediaTypeLZ4, 
               let sizeStr = layer.annotations?[OCIAnnotationUncompressedSize], 
               let size = UInt64(sizeStr) {
                totalUncompressedDiskSize += size
            }
        }
        
        // --- Check Cache ---
        if cachingEnabled {
            Logger.info("Cache is enabled, checking for existing cached image with manifest ID: \(manifestId)")
            
            // Log the expected cache directory path
            let expectedCacheDir = getImageCacheDirectory(manifestId: manifestId)
            if FileManager.default.fileExists(atPath: expectedCacheDir.path) {
                Logger.debug("Found cache directory at: \(expectedCacheDir.path)")
                
                // Check if manifest file exists
                let manifestPath = getCachedManifestPath(manifestId: manifestId)
                if FileManager.default.fileExists(atPath: manifestPath.path) {
                    Logger.debug("Found cached manifest file at: \(manifestPath.path)")
                } else {
                    Logger.debug("No cached manifest file found at: \(manifestPath.path)")
                }
            } else {
                Logger.debug("No cache directory found at: \(expectedCacheDir.path)")
            }
            
            // Now run actual validation
            if validateCache(manifest: manifest, manifestId: manifestId) {
                Logger.info("Valid cache found for \(manifestId). Reconstructing VM from cache...")
                do {
                    let cacheDir = getImageCacheDirectory(manifestId: manifestId)

                    // --- Copy non-disk files from cache --- 
                    // Config (corresponds to manifest.config.digest)
                    let cachedConfigPath = getCachedLayerPath(manifestId: manifestId, digest: manifest.config.digest)
                    let finalConfigPath = vmDirURL.appendingPathComponent("config.json")
                    if FileManager.default.fileExists(atPath: cachedConfigPath.path) {
                        try? FileManager.default.removeItem(at: finalConfigPath) // Remove existing if any
                        try FileManager.default.copyItem(at: cachedConfigPath, to: finalConfigPath)
                        Logger.debug("Copied config.json from cache.")
                    } else {
                        Logger.error("Cache inconsistency: config layer missing from cache directory \(cacheDir.path)")
                        // Decide if this should be fatal or try download?
                        throw PullError.vmReconstructionFailed // Treat as fatal for now
                    }

                    // NVRAM (find the layer by media type)
                    if let nvramLayer = manifest.layers.first(where: { $0.mediaType == NvramMediaTypeLZ4 }) {
                        let cachedNvramPath = getCachedLayerPath(manifestId: manifestId, digest: nvramLayer.digest)
                        let finalNvramPath = vmDirURL.appendingPathComponent("nvram.bin")
                        if FileManager.default.fileExists(atPath: cachedNvramPath.path) {
                            // NVRAM needs decompression
                            Logger.debug("Decompressing cached NVRAM...")
                            let compressedData = try Data(contentsOf: cachedNvramPath)
                            let decompressedData = try self.decompress(data: compressedData)
                            try? FileManager.default.removeItem(at: finalNvramPath)
                            try decompressedData.write(to: finalNvramPath)
                            Logger.debug("Restored nvram.bin from cache.")
                        } else {
                            Logger.error("Cache inconsistency: NVRAM layer missing from cache directory \(cacheDir.path)")
                            throw PullError.vmReconstructionFailed
                        }
                    } else {
                         Logger.info("No NVRAM layer found in manifest, skipping NVRAM restore from cache.")
                    }

                    // --- Reassemble Disk from cached layers --- 
                    let diskLayers = manifest.layers.enumerated()
                                              .filter { $0.element.mediaType == DiskMediaTypeLZ4 } 
                                              .sorted { $0.offset < $1.offset } // Ensure original order

                    if !diskLayers.isEmpty {
                        let diskURL = vmDirURL.appendingPathComponent("disk.img")
                        Logger.info("Reassembling disk image from cache at \(diskURL.path)...")
                        
                        if !FileManager.default.fileExists(atPath: diskURL.path) {
                            guard FileManager.default.createFile(atPath: diskURL.path, contents: nil) else {
                                throw PullError.fileCreationFailed(diskURL.path)
                            }
                        } else {
                            // Clear existing disk image before writing from cache
                             try FileManager.default.removeItem(at: diskURL)
                             guard FileManager.default.createFile(atPath: diskURL.path, contents: nil) else {
                                throw PullError.fileCreationFailed("Failed to recreate disk image file at \(diskURL.path).")
                             }
                        }

                        guard let diskHandle = try? FileHandle(forWritingTo: diskURL) else { 
                             throw PullError.vmReconstructionFailed 
                        }
                        defer { try? diskHandle.close() }

                        // TODO: Add progress bar for cache reassembly?
                        for (index, layer) in diskLayers { // Use enumerated, sorted results
                             Logger.debug("Processing cached disk layer \(index + 1)/\(manifest.layers.count): \(layer.digest)")
                             let cachedLayerPath = self.getCachedLayerPath(manifestId: manifestId, digest: layer.digest)
                             let compressedData = try Data(contentsOf: cachedLayerPath)
                             let decompressedData = try self.decompress(data: compressedData)
                             try diskHandle.write(contentsOf: decompressedData)
                        }
                        try? diskHandle.synchronize()
                        Logger.info("Finished reassembling disk image from cache.")
                    } else {
                         Logger.info("No disk layers found in manifest for cache reconstruction.")
                    }

                     // --- Finalize Cache Reconstruction --- 
                     let metadata = ImageMetadata(image: imageName, manifestId: manifestId, timestamp: Date())
                     let metadataURL = vmDirURL.appendingPathComponent("metadata.json")
                     let metadataData = try JSONEncoder().encode(metadata)
                     try metadataData.write(to: metadataURL)
                     Logger.info("Wrote metadata file at \(metadataURL.path)")

                    Logger.info("Successfully reconstructed VM from cache: \(vmDirURL.path)")
                    return // *** IMPORTANT: Exit pull early after cache reconstruction ***

                } catch {
                     Logger.error("Error during cache reconstruction: \(error.localizedDescription). Deleting potentially incomplete VM directory and falling back to download.")
                     // Attempt to clean up the destination directory on error
                     try? FileManager.default.removeItem(at: vmDirURL)
                     // Optionally, could also invalidate/remove the cache dir itself here
                     // Fall through to download logic
                }
            }
        }

        // --- Fallback: Download if cache invalid, disabled, or reconstruction failed ---
        if cachingEnabled {
            Logger.info("Cache miss or invalid for \(manifestId), proceeding with download and caching.")
            // Prepare cache directory for the new manifest
            try await setupImageCache(manifestId: manifestId)
            try saveManifest(manifest, manifestId: manifestId)
            try saveImageMetadata(imageName: imageName, manifestId: manifestId)
        }

        // 5. Download and process layers
        Logger.info("Downloading and processing layers...")
        
        // Create a progress object for layer downloads
        let layerProgress = Progress(totalUnitCount: Int64(manifest.layers.count))
        
        // Process each layer and store the results
        for (index, layer) in manifest.layers.enumerated() {
            Logger.info("Processing layer \(index + 1)/\(manifest.layers.count): \(layer.digest)")
            
            // Check if blob already exists in cache
            let shouldDownload = !cachingEnabled || !FileManager.default.fileExists(
                atPath: getCachedLayerPath(manifestId: manifestId, digest: layer.digest).path)
            
            // Download and process layer based on type
            if layer.mediaType == DiskMediaTypeLZ4 {
                // This is a disk layer
                let layerURL: URL
                if shouldDownload {
                    // Download and cache layer
                    layerURL = cachingEnabled ? 
                        getCachedLayerPath(manifestId: manifestId, digest: layer.digest) : 
                        FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
                    try await ociClient.pullBlob(digest: layer.digest, to: layerURL, progress: layerProgress)
                } else {
                    // Use cached layer
                    layerURL = getCachedLayerPath(manifestId: manifestId, digest: layer.digest)
                }
                processedDiskLayerPaths[index] = layerURL
                
            } else if layer.mediaType == NvramMediaTypeLZ4 {
                // NVRAM layer
                if shouldDownload {
                    let nvramURL = cachingEnabled ?
                        getCachedLayerPath(manifestId: manifestId, digest: layer.digest) :
                        FileManager.default.temporaryDirectory.appendingPathComponent("nvram.lz4")
                    try await ociClient.pullBlob(digest: layer.digest, to: nvramURL, progress: layerProgress)
                    
                    // Decompress after download
                    let compressedData = try Data(contentsOf: nvramURL)
                    nvramData = try decompress(data: compressedData)
                } else {
                    // Load from cache and decompress
                    let compressedData = try Data(contentsOf: getCachedLayerPath(manifestId: manifestId, digest: layer.digest))
                    nvramData = try decompress(data: compressedData)
                }
            } else if layer.digest == manifest.config.digest {
                // Config layer
                if shouldDownload {
                    let configURL = cachingEnabled ? 
                        getCachedLayerPath(manifestId: manifestId, digest: layer.digest) : 
                        FileManager.default.temporaryDirectory.appendingPathComponent("config.json")
                    try await ociClient.pullBlob(digest: layer.digest, to: configURL, progress: layerProgress)
                    configFileURL = configURL
                } else {
                    configFileURL = getCachedLayerPath(manifestId: manifestId, digest: layer.digest)
                }
            }
            
            // Update progress
            layerProgress.completedUnitCount += 1
        }

        // 6. Process Downloaded/Cached Data and Reconstruct VM Files
        // Use the results collected from the TaskGroup
        
        // --- Reassemble Disk (Sparse Write) --- 
        let diskURL = vmDirURL.appendingPathComponent("disk.img")
        Logger.info("Reassembling disk image at \(diskURL.path) (Expected size: \(ByteCountFormatter.string(fromByteCount: Int64(totalUncompressedDiskSize), countStyle: .file)))...")
        
        // Create/clear and pre-allocate file
        try? FileManager.default.removeItem(at: diskURL) // Ensure clean start
        guard FileManager.default.createFile(atPath: diskURL.path, contents: nil) else {
             throw PullError.fileCreationFailed(diskURL.path)
        }
        guard let diskHandle = try? FileHandle(forWritingTo: diskURL) else { 
             throw PullError.vmReconstructionFailed 
        }
        defer { try? diskHandle.close() }
        do {
             try diskHandle.truncate(atOffset: totalUncompressedDiskSize)
             Logger.debug("Pre-allocated disk image file to \(totalUncompressedDiskSize) bytes.")
        } catch {
            Logger.error("Failed to truncate disk image file: \(error.localizedDescription)")
             throw PullError.vmReconstructionFailed
        }

        // Process sorted disk layers sequentially
        let sortedDiskIndices = processedDiskLayerPaths.keys.sorted()
        var writeOffset: UInt64 = 0
        for index in sortedDiskIndices {
             guard let sourceFileURL = processedDiskLayerPaths[index] else { continue } // Should exist
             Logger.debug("Writing disk layer \(index + 1) from \(sourceFileURL.lastPathComponent) at offset \(writeOffset)")
             
             // Read the source file chunk by chunk and write ALL chunks (including zeros)
             guard let sourceHandle = try? FileHandle(forReadingFrom: sourceFileURL) else {
                 Logger.error("Failed to open source layer file for reading: \(sourceFileURL.path)")
                 throw PullError.vmReconstructionFailed
             }
             defer { try? sourceHandle.close() } // Close each source handle when done

             while true {
                 let chunkData: Data
                 do {
                     // Read in blocks of holeGranularityBytes
                      if #available(macOS 10.15.4, *) {
                          chunkData = try sourceHandle.read(upToCount: Self.holeGranularityBytes) ?? Data()
                      } else {
                          chunkData = sourceHandle.readData(ofLength: Self.holeGranularityBytes)
                      }
                 } catch {
                     Logger.error("Failed to read from source layer file \(sourceFileURL.path): \(error.localizedDescription)")
                     throw PullError.vmReconstructionFailed
                 }
                 
                 // Break if EOF
                 if chunkData.isEmpty { break }
                 
                 // Write all chunks, including zeros (removed sparse optimization)
                 do {
                      try diskHandle.seek(toOffset: writeOffset)
                      try diskHandle.write(contentsOf: chunkData)
                 } catch {
                      Logger.error("Failed to write chunk to disk image: \(error.localizedDescription)")
                      throw PullError.vmReconstructionFailed
                 }
                 
                 writeOffset += UInt64(chunkData.count)
             }
        }
        
        // Fill any remaining space with zeros for VZ Framework compatibility
        if writeOffset < totalUncompressedDiskSize {
            Logger.info("Filling remaining \(totalUncompressedDiskSize - writeOffset) bytes with zeros for VZ Framework compatibility...")
            let remainingSize = totalUncompressedDiskSize - writeOffset
            
            // Fill in chunks to avoid memory issues with large images
            var filledBytes: UInt64 = 0
            let zeroChunk = Data(count: Self.holeGranularityBytes)
            
            while filledBytes < remainingSize {
                let chunkSize = min(UInt64(Self.holeGranularityBytes), remainingSize - filledBytes)
                let finalChunk = chunkSize < UInt64(Self.holeGranularityBytes) 
                    ? Data(count: Int(chunkSize)) 
                    : zeroChunk
                
                do {
                    try diskHandle.seek(toOffset: writeOffset + filledBytes)
                    try diskHandle.write(contentsOf: finalChunk)
                } catch {
                    Logger.error("Failed to write zero-fill chunk: \(error.localizedDescription)")
                    throw PullError.vmReconstructionFailed
                }
                
                filledBytes += UInt64(finalChunk.count)
            }
            
            Logger.debug("Successfully filled remaining disk space with zeros")
        }
        
        // Ensure all data is written to disk
        do {
            try diskHandle.synchronize()
            Logger.info("Finished reassembling disk image.")
        } catch {
            Logger.error("Failed to synchronize disk file: \(error.localizedDescription)")
            throw PullError.vmReconstructionFailed
        }

        // --- Write Other Files --- 
        // Write NVRAM
        if let nvramData = nvramData {
            let nvramURL = vmDirURL.appendingPathComponent("nvram.bin") // Correct filename
            try nvramData.write(to: nvramURL)
            Logger.info("Wrote nvram file at \(nvramURL.path)")
        }

        // Copy config.json
        if let sourceConfigURL = configFileURL {
             let configJsonURL = vmDirURL.appendingPathComponent("config.json")
             do {
                  try? FileManager.default.removeItem(at: configJsonURL)
                  try FileManager.default.copyItem(at: sourceConfigURL, to: configJsonURL)
                  Logger.info("Wrote config.json from downloaded config layer at \(configJsonURL.path)")
             } catch {
                  Logger.error("Failed to write downloaded config.json: \(error.localizedDescription)")
                  // Decide if this is fatal
             }
        } else {
             Logger.error("Config layer data was not processed. Cannot write config.json.")
             // Decide if this is fatal
        }

        // Write Metadata
        let metadata = ImageMetadata(image: imageName, manifestId: manifestId, timestamp: Date())
        let metadataURL = vmDirURL.appendingPathComponent("metadata.json")
        let metadataData = try JSONEncoder().encode(metadata)
        try metadataData.write(to: metadataURL)
        Logger.info("Wrote metadata file at \(metadataURL.path)")

        Logger.info("Successfully pulled \(image) to \(vmDirURL.path)")
    }

    // ... rest of LumeImageManager ...

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

        // --- Create Temporary Directory for Dry Run Reassembly ---
        let tempDirectory: URL
        if dryRun && reassemble {
            // Create a temporary directory for dry run reassembly testing
            tempDirectory = FileManager.default.temporaryDirectory.appendingPathComponent("lume_dryrun_\(UUID().uuidString)")
            try FileManager.default.createDirectory(at: tempDirectory, withIntermediateDirectories: true)
            Logger.info("[Dry Run] Created temporary directory for reassembly testing: \(tempDirectory.path)")
        } else {
            tempDirectory = FileManager.default.temporaryDirectory // Dummy value if not used
        }

        // --- Create Layers ---
        var layers: [OCIManifestLayer] = []
        var totalUncompressedSize: Int64 = 0
        
        // Dictionary to store compressed chunks for dry run reassembly testing
        var compressedChunks: [Int: (data: Data, layer: OCIManifestLayer)] = [:]

        // 1. Config Layer (Reference only - Read local config.json)
        let configData = try Data(contentsOf: configJsonURL)
        let configDigest = Digest.hash(configData)
        let configLayer = OCIManifestConfig(mediaType: OCIConfigMediaType, size: configData.count, digest: configDigest)
        Logger.info("Using VM config.json for OCI config reference: \(configDigest)")
        
        // Save for dry run reassembly if needed
        if dryRun && reassemble {
            let configTempPath = tempDirectory.appendingPathComponent("config.json")
            try configData.write(to: configTempPath)
            Logger.debug("[Dry Run] Saved config.json to temp directory for reassembly test")
        }

        // 2. NVRAM Layer (if exists)
        var nvramCompressedData: Data? = nil
        var nvramLayer: OCIManifestLayer? = nil
        
        if FileManager.default.fileExists(atPath: nvramURL.path) {
            let nvramRawData = try Data(contentsOf: nvramURL)
            nvramCompressedData = try compress(data: nvramRawData)
            let nvramDigest = Digest.hash(nvramCompressedData!)
            let nvramUncompressedDigest = Digest.hash(nvramRawData)
            nvramLayer = OCIManifestLayer(
                mediaType: NvramMediaTypeLZ4,
                size: Int64(nvramCompressedData!.count),
                digest: nvramDigest,
                annotations: [
                    OCIAnnotationUncompressedSize: String(nvramRawData.count),
                    OCIAnnotationUncompressedDigest: nvramUncompressedDigest
                ]
            )
            layers.append(nvramLayer!)

            if !dryRun {
                let exists = try await ociClient.blobExists(nvramDigest) // Restore blob exists check
                if !exists {
                    Logger.info("Uploading nvram blob...") 
                    _ = try await ociClient.pushBlob(fromData: nvramCompressedData!, digest: nvramDigest) 
                    Logger.info("NVRAM blob uploaded.")
                } else {
                   Logger.info("NVRAM blob \(nvramDigest) already exists on registry.")
                }
            } else {
                Logger.info("[Dry Run] NVRAM layer prepared.")
                
                // Save for reassembly if needed
                if reassemble {
                    let nvramTempPath = tempDirectory.appendingPathComponent(nvramDigest.replacingOccurrences(of: ":", with: "_"))
                    try nvramCompressedData!.write(to: nvramTempPath)
                    Logger.debug("[Dry Run] Saved compressed NVRAM to temp directory for reassembly test")
                }
            }
        } else {
            Logger.info("nvram file not found at \(nvramURL.path), skipping nvram layer.")
        }

        // 3. Disk Layer(s) - Using DiskV2 Style Chunking
        Logger.info("Reading disk image file: \(diskURL.path)")
        let diskStats = try measureDiskStatistics(path: diskURL.path)
        let diskFileSize = diskStats.size
        let allocatedSize = diskStats.allocated
        
        Logger.info("Disk file statistics - Logical size: \(ByteCountFormatter.string(fromByteCount: diskFileSize, countStyle: .file)), Allocated: \(ByteCountFormatter.string(fromByteCount: allocatedSize, countStyle: .file))")
        
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
            // We'll store results from tasks here rather than modifying shared state
            var processedResults: [ChunkResult] = []
            var processedChunks: [(index: Int, data: Data, layer: OCIManifestLayer)] = []
            
            try await withThrowingTaskGroup(of: (Int, Data?, OCIManifestLayer).self) { group in
                for (index, chunk) in diskChunks.enumerated() {
                    group.addTask {
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
                            let exists = try await ociClient.blobExists(chunkCompressedDigest)
                            if !exists {
                                Logger.info("Uploading disk blob \(index + 1)/\(totalChunks)...") 
                                _ = try await ociClient.pushBlob(fromData: chunkCompressedData, chunkSizeMb: 0, digest: chunkCompressedDigest, progress: diskProgress) 
                                Logger.info("Disk blob \(index + 1)/\(totalChunks) uploaded.")
                            } else {
                                Logger.info("Disk blob \(index + 1)/\(totalChunks) \(chunkCompressedDigest) already exists.")
                                // If skipping upload, still update progress
                                diskProgress.completedUnitCount += Int64(chunk.count)
                            }
                            return (index, nil, diskLayer) // Don't need data when not in dry-run mode
                        } else {
                            Logger.info("[Dry Run] Disk layer \(index + 1)/\(totalChunks) prepared.")
                            // Simulate progress in dry run
                            diskProgress.completedUnitCount += Int64(chunk.count)
                            
                            // Return compressed data for reassembly if needed
                            return (index, reassemble ? chunkCompressedData : nil, diskLayer)
                        }
                    }
                }
                
                // Collect all results safely
                for try await (index, chunkData, layer) in group {
                    processedResults.append((index: index, layer: layer))
                    
                    // Store compressed data if in dry run mode and reassembly is requested
                    if dryRun && reassemble, let data = chunkData {
                        processedChunks.append((index: index, data: data, layer: layer))
                    }
                }
            }
            
            // Now store results safely
            processedDiskLayers = processedResults
            
            // Store compressed chunks for reassembly if needed
            if dryRun && reassemble {
                for (index, data, layer) in processedChunks {
                    compressedChunks[index] = (data: data, layer: layer)
                }
            }
            
            Logger.info("Finished processing all disk chunks.")
        } catch {
             Logger.error("Failed to process or upload disk chunks concurrently: \(error.localizedDescription)")
             if error is OCIClientError {
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
            
            // --- Reassembly Test in Dry Run Mode ---
            if reassemble {
                Logger.info("[Dry Run] Starting reassembly test to verify image integrity...")
                
                // Save manifest for reassembly
                let manifestTempPath = tempDirectory.appendingPathComponent("manifest.json")
                try manifestData.write(to: manifestTempPath)
                
                // Save compressed chunks to disk
                for (index, chunkInfo) in compressedChunks {
                    let layerDigest = chunkInfo.layer.digest
                    let layerPath = tempDirectory.appendingPathComponent(layerDigest.replacingOccurrences(of: ":", with: "_"))
                    try chunkInfo.data.write(to: layerPath)
                    Logger.debug("[Dry Run] Saved disk layer \(index) (\(layerDigest)) to temp directory")
                }
                
                // Perform reassembly to a new file
                let reassembledDiskPath = tempDirectory.appendingPathComponent("reassembled_disk.img")
                Logger.info("[Dry Run] Reassembling disk image to: \(reassembledDiskPath.path)")
                
                try await reassembleDiskImage(
                    manifest: manifest,
                    manifestId: manifestDigest.replacingOccurrences(of: ":", with: "_"),
                    layersDirectory: tempDirectory,
                    outputPath: reassembledDiskPath,
                    useSparseTechnique: true // Use sparse technique for reassembly to match pull behavior
                )
                
                // Verify reassembled image against original
                Logger.info("[Dry Run] Verifying reassembled disk image against original...")
                let comparisonResult = try compareDiskImages(
                    originalPath: diskURL.path,
                    reassembledPath: reassembledDiskPath.path,
                    expectedSize: diskFileSize
                )
                
                if comparisonResult.identical {
                    Logger.info("[Dry Run] ✅ SUCCESS: Reassembled disk image is identical to original!")
                    Logger.info("[Dry Run] Original size: \(ByteCountFormatter.string(fromByteCount: comparisonResult.originalSize, countStyle: .file)), Reassembled size: \(ByteCountFormatter.string(fromByteCount: comparisonResult.reassembledSize, countStyle: .file))")
                    Logger.info("[Dry Run] Original allocated: \(ByteCountFormatter.string(fromByteCount: comparisonResult.originalAllocated, countStyle: .file)), Reassembled allocated: \(ByteCountFormatter.string(fromByteCount: comparisonResult.reassembledAllocated, countStyle: .file))")
                    Logger.info("[Dry Run] Sparseness preserved: \(comparisonResult.sparsenessPreserved ? "Yes" : "No")")
                } else {
                    Logger.error("[Dry Run] ❌ FAILURE: Reassembled disk image differs from original!")
                    Logger.error("[Dry Run] Differences found: \(comparisonResult.diffCount) blocks")
                    Logger.error("[Dry Run] Original size: \(ByteCountFormatter.string(fromByteCount: comparisonResult.originalSize, countStyle: .file)), Reassembled size: \(ByteCountFormatter.string(fromByteCount: comparisonResult.reassembledSize, countStyle: .file))")
                    Logger.error("[Dry Run] Original allocated: \(ByteCountFormatter.string(fromByteCount: comparisonResult.originalAllocated, countStyle: .file)), Reassembled allocated: \(ByteCountFormatter.string(fromByteCount: comparisonResult.reassembledAllocated, countStyle: .file))")
                    
                    if verbose {
                        // Print some information about the first few differences
                        for (i, diff) in comparisonResult.sampleDiffs.enumerated() {
                            Logger.error("[Dry Run] Diff \(i+1): at offset \(diff.offset), length: \(diff.length)")
                        }
                    }
                }
                
                // Clean up temp directory
                if !verbose { // Keep files if verbose for inspection
                    try? FileManager.default.removeItem(at: tempDirectory)
                    Logger.debug("[Dry Run] Cleaned up temporary directory")
                } else {
                    Logger.info("[Dry Run] Keeping temporary directory for inspection: \(tempDirectory.path)")
                }
            }
            
            Logger.info("[Dry Run] Completed.")
        }
    }

    // --- Disk Reassembly & Comparison Functions for Dry Run ---
    
    private lazy var serialQueue = DispatchQueue(label: "com.lume.imagemanager.serial")
    
    private struct DiskComparisonResult {
        let identical: Bool
        let originalSize: Int64
        let reassembledSize: Int64
        let originalAllocated: Int64
        let reassembledAllocated: Int64
        let sparsenessPreserved: Bool
        let diffCount: Int
        let sampleDiffs: [(offset: UInt64, length: Int)] // Sample differences
    }
    
    private func reassembleDiskImage(
        manifest: OCIManifest,
        manifestId: String,
        layersDirectory: URL,
        outputPath: URL,
        useSparseTechnique: Bool
    ) async throws {
        // Get total size from manifest
        var totalUncompressedSize: UInt64 = 0
        let diskLayers = manifest.layers.filter { $0.mediaType == DiskMediaTypeLZ4 }
        
        for layer in diskLayers {
            if let sizeStr = layer.annotations?[OCIAnnotationUncompressedSize], 
               let size = UInt64(sizeStr) {
                totalUncompressedSize += size
            }
        }
        
        Logger.debug("[Dry Run] Reassembling disk image with total uncompressed size: \(totalUncompressedSize) bytes")
        
        // Create output file
        try? FileManager.default.removeItem(at: outputPath)
        guard FileManager.default.createFile(atPath: outputPath.path, contents: nil) else {
            throw PushError.missingDiskImage // Use existing error instead of fileCreationFailed
        }
        
        guard let diskHandle = try? FileHandle(forWritingTo: outputPath) else {
            throw PushError.missingDiskImage // Use existing error instead of vmReconstructionFailed
        }
        defer { try? diskHandle.close() }
        
        // Pre-allocate file
        try diskHandle.truncate(atOffset: totalUncompressedSize)
        
        // Process disk layers in order
        var writeOffset: UInt64 = 0
        let sortedLayers = diskLayers.sorted { a, b in
            // Sort by their index in the manifest
            let aIndex = manifest.layers.firstIndex(where: { $0.digest == a.digest }) ?? 0
            let bIndex = manifest.layers.firstIndex(where: { $0.digest == b.digest }) ?? 0
            return aIndex < bIndex
        }
        
        for layer in sortedLayers {
            let layerPath = layersDirectory.appendingPathComponent(layer.digest.replacingOccurrences(of: ":", with: "_"))
            
            guard FileManager.default.fileExists(atPath: layerPath.path) else {
                Logger.error("[Dry Run] Layer file missing during reassembly: \(layerPath.path)")
                continue
            }
            
            // Read compressed data and decompress
            let compressedData = try Data(contentsOf: layerPath)
            let decompressedData = try decompress(data: compressedData)
            
            Logger.debug("[Dry Run] Writing reassembled layer at offset \(writeOffset): \(layer.digest)")
            
            if useSparseTechnique {
                // Use sparse technique to write non-zero blocks
                var chunkOffset: UInt64 = 0
                while chunkOffset < decompressedData.count {
                    let chunkSize = min(Self.holeGranularityBytes, decompressedData.count - Int(chunkOffset))
                    let range = Int(chunkOffset)..<Int(chunkOffset + UInt64(chunkSize))
                    let chunk = decompressedData.subdata(in: range)
                    
                    // Check if chunk is all zeros
                    if chunk.count == Self.holeGranularityBytes && chunk == Self.zeroChunk {
                        // Skip writing zeros
                    } else {
                        // Write non-zero chunk
                        try diskHandle.seek(toOffset: writeOffset + chunkOffset)
                        try diskHandle.write(contentsOf: chunk)
                    }
                    
                    chunkOffset += UInt64(chunkSize)
                }
            } else {
                // Write entire decompressed data
                try diskHandle.seek(toOffset: writeOffset)
                try diskHandle.write(contentsOf: decompressedData)
            }
            
            writeOffset += UInt64(decompressedData.count)
        }
        
        try diskHandle.synchronize()
        Logger.info("[Dry Run] Completed disk image reassembly")
    }
    
    private func compareDiskImages(originalPath: String, reassembledPath: String, expectedSize: Int64) throws -> DiskComparisonResult {
        // Get file attributes
        let originalStats = try measureDiskStatistics(path: originalPath)
        let reassembledStats = try measureDiskStatistics(path: reassembledPath)
        
        let originalSize = originalStats.size
        let reassembledSize = reassembledStats.size
        
        let originalAllocated = originalStats.allocated
        let reassembledAllocated = reassembledStats.allocated
        
        // Check if logical sizes match expected
        guard originalSize == expectedSize && reassembledSize == expectedSize else {
            return DiskComparisonResult(
                identical: false,
                originalSize: originalSize,
                reassembledSize: reassembledSize,
                originalAllocated: originalAllocated,
                reassembledAllocated: reassembledAllocated,
                sparsenessPreserved: false,
                diffCount: 1,
                sampleDiffs: [(offset: 0, length: Int(abs(originalSize - reassembledSize)))]
            )
        }
        
        // Open both files for reading
        guard let originalHandle = try? FileHandle(forReadingFrom: URL(fileURLWithPath: originalPath)),
              let reassembledHandle = try? FileHandle(forReadingFrom: URL(fileURLWithPath: reassembledPath)) else {
            throw PushError.missingDiskImage // Use existing error instead of vmReconstructionFailed
        }
        defer {
            try? originalHandle.close()
            try? reassembledHandle.close()
        }
        
        // Compare chunk by chunk
        var diffCount = 0
        var sampleDiffs: [(offset: UInt64, length: Int)] = []
        var offset: UInt64 = 0
        
        while offset < UInt64(originalSize) {
            let chunkSize = min(Self.holeGranularityBytes, Int(originalSize) - Int(offset))
            
            // Read chunks from both files
            try originalHandle.seek(toOffset: offset)
            try reassembledHandle.seek(toOffset: offset)
            
            let originalChunk: Data
            let reassembledChunk: Data
            
            if #available(macOS 10.15.4, *) {
                originalChunk = try originalHandle.read(upToCount: chunkSize) ?? Data()
                reassembledChunk = try reassembledHandle.read(upToCount: chunkSize) ?? Data()
            } else {
                originalChunk = originalHandle.readData(ofLength: chunkSize)
                reassembledChunk = reassembledHandle.readData(ofLength: chunkSize)
            }
            
            // Compare chunks
            if originalChunk != reassembledChunk {
                diffCount += 1
                if sampleDiffs.count < 5 { // Collect at most 5 sample differences
                    sampleDiffs.append((offset: offset, length: chunkSize))
                }
            }
            
            offset += UInt64(chunkSize)
        }
        
        // Determine if sparseness was preserved
        let sparsenessPreserved = originalAllocated > 0 && 
                                 reassembledAllocated > 0 && 
                                 (Double(reassembledAllocated) / Double(originalAllocated) <= 1.1) // Allow 10% difference
        
        return DiskComparisonResult(
            identical: diffCount == 0,
            originalSize: originalSize,
            reassembledSize: reassembledSize,
            originalAllocated: originalAllocated,
            reassembledAllocated: reassembledAllocated,
            sparsenessPreserved: sparsenessPreserved,
            diffCount: diffCount,
            sampleDiffs: sampleDiffs
        )
    }

    // ... rest of LumeImageManager ...

    // --- Helper: Compression ---
    private static let bufferSizeBytes = 4 * 1024 * 1024 // Moved inside class

    private func compress(data: Data) throws -> Data {
        try (data as NSData).compressed(using: .lz4) as Data
    }

     private func decompress(data: Data) throws -> Data {
        try (data as NSData).decompressed(using: .lz4) as Data
    }

    // Add FileAttributeKey enum for accessing file attributes
    private enum FileAttributeKeys {
        static let size = FileAttributeKey.size
        static let allocatedSize = FileAttributeKey(rawValue: "NSFileAllocatedSize")
    }

    // Fix the code that uses allocatedSize
    private func measureDiskStatistics(path: String) throws -> (size: Int64, allocated: Int64) {
        let attributes = try FileManager.default.attributesOfItem(atPath: path)
        let size = (attributes[FileAttributeKeys.size] as? NSNumber)?.int64Value ?? 0
        let allocated = (attributes[FileAttributeKeys.allocatedSize] as? NSNumber)?.int64Value ?? 0
        return (size, allocated)
    }
} 