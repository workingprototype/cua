import Foundation
import Network

struct DiskSize: Codable {
    let allocated: UInt64
    let total: UInt64
}

extension DiskSize {
    var formattedAllocated: String {
        formatBytes(allocated)
    }
    
    var formattedTotal: String {
        formatBytes(total)
    }
    
    private func formatBytes(_ bytes: UInt64) -> String {
        let units = ["B", "KB", "MB", "GB", "TB"]
        var size = Double(bytes)
        var unitIndex = 0
        
        while size >= 1024 && unitIndex < units.count - 1 {
            size /= 1024
            unitIndex += 1
        }
        
        return String(format: "%.1f%@", size, units[unitIndex])
    }
}

struct VMDetails: Codable {
    let name: String
    let os: String
    let cpuCount: Int
    let memorySize: UInt64
    let diskSize: DiskSize
    let status: String
    let vncUrl: String?
    let ipAddress: String?
}