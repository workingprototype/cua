import ArgumentParser
import Foundation
import Virtualization

// MARK: - Shared VM Manager

@MainActor
final class SharedVM {
    static let shared: SharedVM = SharedVM()
    private var runningVMs: [String: VM] = [:]
    
    private init() {}
    
    func getVM(name: String) -> VM? {
        return runningVMs[name]
    }
    
    func setVM(name: String, vm: VM) {
        runningVMs[name] = vm
    }
    
    func removeVM(name: String) {
        runningVMs.removeValue(forKey: name)
    }
}

/// Entrypoint for Commands and API server
final class LumeController {
    // MARK: - Properties

    let home: Home
    private let imageLoaderFactory: ImageLoaderFactory
    private let vmFactory: VMFactory

    // MARK: - Initialization

    init(
        home: Home = Home(),
        imageLoaderFactory: ImageLoaderFactory = DefaultImageLoaderFactory(),
        vmFactory: VMFactory = DefaultVMFactory()
    ) {
        self.home = home
        self.imageLoaderFactory = imageLoaderFactory
        self.vmFactory = vmFactory
    }

    // MARK: - Public VM Management Methods

    /// Lists all virtual machines in the system
    @MainActor
    public func list() throws -> [VMDetails] {
        do {
            let statuses = try home.getAllVMDirectories().map { directory in
                let vm = try self.get(name: directory.name)
                return vm.details
            }
            return statuses
        } catch {
            Logger.error("Failed to list VMs", metadata: ["error": error.localizedDescription])
            throw error
        }
    }

    @MainActor
    public func clone(name: String, newName: String) throws {
        Logger.info("Cloning VM", metadata: ["source": name, "destination": newName])

        do {
            try self.validateVMExists(name)
            
            // Copy the VM directory
            try home.copyVMDirectory(from: name, to: newName)
            
            // Update MAC address in the cloned VM to ensure uniqueness
            let clonedVM = try get(name: newName)
            try clonedVM.setMacAddress(VZMACAddress.randomLocallyAdministered().string)
            
            Logger.info("VM cloned successfully", metadata: ["source": name, "destination": newName])
        } catch {
            Logger.error("Failed to clone VM", metadata: ["error": error.localizedDescription])
            throw error
        }
    }

    @MainActor
    public func get(name: String) throws -> VM {
        do {
            try self.validateVMExists(name)

            let vm = try self.loadVM(name: name)
            return vm
        } catch {
            Logger.error("Failed to get VM", metadata: ["error": error.localizedDescription])
            throw error
        }
    }

    /// Factory for creating the appropriate VM type based on the OS
    @MainActor
    public func create(
        name: String,
        os: String,
        diskSize: UInt64,
        cpuCount: Int,
        memorySize: UInt64,
        display: String,
        ipsw: String?
    ) async throws {
        Logger.info(
            "Creating VM",
            metadata: [
                "name": name,
                "os": os,
                "disk_size": "\(diskSize / 1024 / 1024)MB",
                "cpu_count": "\(cpuCount)",
                "memory_size": "\(memorySize / 1024 / 1024)MB",
                "display": display,
                "ipsw": ipsw ?? "none",
            ])

        do {
            try validateCreateParameters(name: name, os: os, ipsw: ipsw)

            let vm = try await createTempVMConfig(
                os: os,
                cpuCount: cpuCount,
                memorySize: memorySize,
                diskSize: diskSize,
                display: display
            )

            try await vm.setup(
                ipswPath: ipsw ?? "none",
                cpuCount: cpuCount,
                memorySize: memorySize,
                diskSize: diskSize,
                display: display
            )

            try vm.finalize(to: name, home: home)

            Logger.info("VM created successfully", metadata: ["name": name])
        } catch {
            Logger.error("Failed to create VM", metadata: ["error": error.localizedDescription])
            throw error
        }
    }

    @MainActor
    public func delete(name: String) async throws {
        Logger.info("Deleting VM", metadata: ["name": name])

        do {
            try self.validateVMExists(name)

            // Stop VM if it's running
            if SharedVM.shared.getVM(name: name) != nil {
                try await stopVM(name: name)
            }

            let vmDir = home.getVMDirectory(name)
            try vmDir.delete()
            Logger.info("VM deleted successfully", metadata: ["name": name])

        } catch {
            Logger.error("Failed to delete VM", metadata: ["error": error.localizedDescription])
            throw error
        }
    }

    // MARK: - VM Operations

    @MainActor
    public func updateSettings(
        name: String,
        cpu: Int? = nil,
        memory: UInt64? = nil,
        diskSize: UInt64? = nil
    ) throws {
        Logger.info(
            "Updating VM settings",
            metadata: [
                "name": name,
                "cpu": cpu.map { "\($0)" } ?? "unchanged",
                "memory": memory.map { "\($0 / 1024 / 1024)MB" } ?? "unchanged",
                "disk_size": diskSize.map { "\($0 / 1024 / 1024)MB" } ?? "unchanged",
            ])
        do {
            try self.validateVMExists(name)

            let vm = try get(name: name)

            // Apply settings in order
            if let cpu = cpu {
                try vm.setCpuCount(cpu)
            }
            if let memory = memory {
                try vm.setMemorySize(memory)
            }
            if let diskSize = diskSize {
                try vm.setDiskSize(diskSize)
            }

            Logger.info("VM settings updated successfully", metadata: ["name": name])
        } catch {
            Logger.error(
                "Failed to update VM settings", metadata: ["error": error.localizedDescription])
            throw error
        }
    }

    @MainActor
    public func stopVM(name: String) async throws {
        Logger.info("Stopping VM", metadata: ["name": name])

        do {
            try self.validateVMExists(name)

            // Try to get VM from cache first
            let vm: VM
            if let cachedVM = SharedVM.shared.getVM(name: name) {
                vm = cachedVM
            } else {
                vm = try get(name: name)
            }

            try await vm.stop()
            // Remove VM from cache after stopping
            SharedVM.shared.removeVM(name: name)
            Logger.info("VM stopped successfully", metadata: ["name": name])
        } catch {
            // Clean up cache even if stop fails
            SharedVM.shared.removeVM(name: name)
            Logger.error("Failed to stop VM", metadata: ["error": error.localizedDescription])
            throw error
        }
    }

    @MainActor
    public func runVM(
        name: String,
        noDisplay: Bool = false,
        sharedDirectories: [SharedDirectory] = [],
        mount: Path? = nil
    ) async throws {
        Logger.info(
            "Running VM",
            metadata: [
                "name": name,
                "no_display": "\(noDisplay)",
                "shared_directories": "\(sharedDirectories.map( { $0.string } ).joined(separator: ", "))",
                "mount": mount?.path ?? "none",
            ])

        do {
            try validateRunParameters(
                name: name, sharedDirectories: sharedDirectories, mount: mount)

            let vm = try get(name: name)
            SharedVM.shared.setVM(name: name, vm: vm)
            try await vm.run(noDisplay: noDisplay, sharedDirectories: sharedDirectories, mount: mount)
            Logger.info("VM started successfully", metadata: ["name": name])
        } catch {
            SharedVM.shared.removeVM(name: name)
            Logger.error("Failed to run VM", metadata: ["error": error.localizedDescription])
            throw error
        }
    }

    // MARK: - Image Management

    @MainActor
    public func getLatestIPSWURL() async throws -> URL {
        Logger.info("Fetching latest supported IPSW URL")

        do {
            let imageLoader = DarwinImageLoader()
            let url = try await imageLoader.fetchLatestSupportedURL()
            Logger.info("Found latest IPSW URL", metadata: ["url": url.absoluteString])
            return url
        } catch {
            Logger.error(
                "Failed to fetch IPSW URL", metadata: ["error": error.localizedDescription])
            throw error
        }
    }

    @MainActor
    public func pullImage(image: String, name: String?, registry: String, organization: String)
        async throws
    {
        do {
            let vmName: String = name ?? image.split(separator: ":").first.map(String.init) ?? image

            Logger.info(
                "Pulling image",
                metadata: [
                    "image": image,
                    "name": name ?? "default",
                    "registry": registry,
                    "organization": organization,
                ])

            try self.validatePullParameters(
                image: image, name: vmName, registry: registry, organization: organization)

            let imageContainerRegistry = ImageContainerRegistry(
                registry: registry, organization: organization)
            try await imageContainerRegistry.pull(image: image, name: vmName)

            Logger.info("Setting new VM mac address")

            // Update MAC address in the cloned VM to ensure uniqueness
            let vm = try get(name: vmName)
            try vm.setMacAddress(VZMACAddress.randomLocallyAdministered().string)

            Logger.info(
                "Image pulled successfully",
                metadata: [
                    "image": image,
                    "name": vmName,
                    "registry": registry,
                    "organization": organization,
                ])
        } catch {
            Logger.error("Failed to pull image", metadata: ["error": error.localizedDescription])
            throw error
        }
    }

    @MainActor
    public func pruneImages() async throws {
        Logger.info("Pruning cached images")
        
        do {
            let home = FileManager.default.homeDirectoryForCurrentUser
            let cacheDir = home.appendingPathComponent(".lume/cache/ghcr")
            
            if FileManager.default.fileExists(atPath: cacheDir.path) {
                try FileManager.default.removeItem(at: cacheDir)
                try FileManager.default.createDirectory(at: cacheDir, withIntermediateDirectories: true)
                Logger.info("Successfully removed cached images")
            } else {
                Logger.info("No cached images found")
            }
        } catch {
            Logger.error("Failed to prune images", metadata: ["error": error.localizedDescription])
            throw error
        }
    }

    public struct ImageInfo: Codable {
        public let repository: String
        public let imageId: String  // This will be the shortened manifest ID
    }

    public struct ImageList: Codable {
        public let local: [ImageInfo]
        public let remote: [String]  // Keep this for future remote registry support
    }

    @MainActor
    public func getImages(organization: String = "trycua") async throws -> ImageList {
        Logger.info("Listing local images", metadata: ["organization": organization])
        
        let imageContainerRegistry = ImageContainerRegistry(registry: "ghcr.io", organization: organization)
        let cachedImages = try await imageContainerRegistry.getImages()
        
        let imageInfos = cachedImages.map { image in
            ImageInfo(
                repository: image.repository,
                imageId: String(image.manifestId.prefix(12))
            )
        }
        
        ImagesPrinter.print(images: imageInfos.map { "\($0.repository):\($0.imageId)" })
        return ImageList(local: imageInfos, remote: [])
    }

    // MARK: - Private Helper Methods

    @MainActor
    private func createTempVMConfig(
        os: String,
        cpuCount: Int,
        memorySize: UInt64,
        diskSize: UInt64,
        display: String
    ) async throws -> VM {
        let config = try VMConfig(
            os: os,
            cpuCount: cpuCount,
            memorySize: memorySize,
            diskSize: diskSize,
            macAddress: VZMACAddress.randomLocallyAdministered().string,
            display: display
        )

        let vmDirContext = VMDirContext(
            dir: try home.createTempVMDirectory(),
            config: config,
            home: home
        )

        let imageLoader = os.lowercased() == "macos" ? imageLoaderFactory.createImageLoader() : nil
        return try vmFactory.createVM(vmDirContext: vmDirContext, imageLoader: imageLoader)
    }

    @MainActor
    private func loadVM(name: String) throws -> VM {
        let vmDir = home.getVMDirectory(name)
        guard vmDir.initialized() else {
            throw VMError.notInitialized(name)
        }

        let config: VMConfig = try vmDir.loadConfig()
        let vmDirContext = VMDirContext(dir: vmDir, config: config, home: home)

        let imageLoader =
            config.os.lowercased() == "macos" ? imageLoaderFactory.createImageLoader() : nil
        return try vmFactory.createVM(vmDirContext: vmDirContext, imageLoader: imageLoader)
    }

    // MARK: - Validation Methods

    private func validateCreateParameters(name: String, os: String, ipsw: String?) throws {
        if os.lowercased() == "macos" {
            guard let ipsw = ipsw else {
                throw ValidationError("IPSW path required for macOS VM")
            }
            if ipsw != "latest" && !FileManager.default.fileExists(atPath: ipsw) {
                throw ValidationError("IPSW file not found")
            }
        } else if os.lowercased() == "linux" {
            if ipsw != nil {
                throw ValidationError("IPSW path not supported for Linux VM")
            }
        } else {
            throw ValidationError("Unsupported OS type: \(os)")
        }

        let vmDir = home.getVMDirectory(name)
        if vmDir.exists() {
            throw VMError.alreadyExists(name)
        }
    }

    private func validateSharedDirectories(_ directories: [SharedDirectory]) throws {
        for dir in directories {
            var isDirectory: ObjCBool = false
            guard FileManager.default.fileExists(atPath: dir.hostPath, isDirectory: &isDirectory),
                isDirectory.boolValue
            else {
                throw ValidationError(
                    "Host path does not exist or is not a directory: \(dir.hostPath)")
            }
        }
    }

    public func validateVMExists(_ name: String) throws {
        let vmDir = home.getVMDirectory(name)
        guard vmDir.initialized() else {
            throw VMError.notFound(name)
        }
    }

    private func validatePullParameters(
        image: String, name: String, registry: String, organization: String
    ) throws {
        guard !image.isEmpty else {
            throw ValidationError("Image name cannot be empty")
        }
        guard !name.isEmpty else {
            throw ValidationError("VM name cannot be empty")
        }
        guard !registry.isEmpty else {
            throw ValidationError("Registry cannot be empty")
        }
        guard !organization.isEmpty else {
            throw ValidationError("Organization cannot be empty")
        }

        let vmDir = home.getVMDirectory(name)
        if vmDir.exists() {
            throw VMError.alreadyExists(name)
        }
    }

    private func validateRunParameters(
        name: String, sharedDirectories: [SharedDirectory]?, mount: Path?
    ) throws {
        try self.validateVMExists(name)
        if let dirs: [SharedDirectory] = sharedDirectories {
            try self.validateSharedDirectories(dirs)
        }
        let vmConfig = try home.getVMDirectory(name).loadConfig()
        switch vmConfig.os.lowercased() {
        case "macos":
            if mount != nil {
                throw ValidationError(
                    "Mounting disk images is not supported for macOS VMs. If you are looking to mount a IPSW, please use the --ipsw option in the create command."
                )
            }
        case "linux":
            if let mount = mount, !FileManager.default.fileExists(atPath: mount.path) {
                throw ValidationError("Mount file not found: \(mount.path)")
            }
        default:
            break
        }
    }
}
