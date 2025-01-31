import ArgumentParser
import Foundation
import Virtualization

struct Run: AsyncParsableCommand {
    static let configuration = CommandConfiguration(
        abstract: "Run a virtual machine"
    )
    
    @Argument(help: "Name of the virtual machine or image to pull and run (format: name or name:tag)", completion: .custom(completeVMName))
    var name: String
    
    @Flag(name: [.short, .long], help: "Do not start the VNC client")
    var noDisplay: Bool = false
    
    @Option(name: [.customLong("shared-dir")], help: "Directory to share with the VM. Can be just a path for read-write access (e.g. ~/src) or path:tag where tag is 'ro' for read-only or 'rw' for read-write (e.g. ~/src:ro)")
    var sharedDirectories: [String] = []

    @Option(help: "For Linux VMs only, a read-only disk image to attach to the VM (e.g. --mount=\"ubuntu.iso\")", completion: .file())
    var mount: Path?
    
    @Option(help: "Github Container Registry to pull the images from. Defaults to ghcr.io")
    var registry: String = "ghcr.io"

    @Option(help: "Organization to pull the images from. Defaults to trycua")
    var organization: String = "trycua"
    
    private var parsedSharedDirectories: [SharedDirectory] {
        get throws {
            try sharedDirectories.map { dirString -> SharedDirectory in
                let components = dirString.split(separator: ":", maxSplits: 1)
                let hostPath = String(components[0])
                
                // If no tag is provided, default to read-write
                if components.count == 1 {
                    return SharedDirectory(
                        hostPath: hostPath,
                        tag: VZVirtioFileSystemDeviceConfiguration.macOSGuestAutomountTag,
                        readOnly: false
                    )
                }
                
                // Parse the tag if provided
                let tag = String(components[1])
                let readOnly: Bool
                switch tag.lowercased() {
                case "ro":
                    readOnly = true
                case "rw":
                    readOnly = false
                default:
                    throw ValidationError("Invalid tag value. Must be either 'ro' for read-only or 'rw' for read-write")
                }
                
                return SharedDirectory(
                    hostPath: hostPath,
                    tag: VZVirtioFileSystemDeviceConfiguration.macOSGuestAutomountTag,
                    readOnly: readOnly
                )
            }
        }
    }
    
    init() {
    }

    @MainActor
    func run() async throws {
        let vmController = LumeController()
        let dirs = try parsedSharedDirectories

        var vmName = name
        
        // Shorthand for pulling an image directly during run
        let components = name.split(separator: ":")
        if components.count == 2 {
            // This is an image reference, try to pull it first
            let image = name
            vmName = "\(components[0])_\(components[1])"
            
            do {
                try vmController.validateVMExists(vmName)
            }
            catch {
                // If the VM doesn't exist, try to pull the image
                try await vmController.pullImage(image: image, name: vmName, registry: registry, organization: organization)
            }
        } 
        
        try await vmController.runVM(
            name: vmName,
            noDisplay: noDisplay,
            sharedDirectories: dirs,
            mount: mount
        )
    }
}