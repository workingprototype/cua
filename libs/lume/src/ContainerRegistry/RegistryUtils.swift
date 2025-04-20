import Foundation
import CryptoKit

// --- Hashing Helper ---

// Errors related to digest calculation
enum DigestError: Error, LocalizedError {
    case invalidOffset
    case invalidSize
    case fileReadError(Error)

    var errorDescription: String? {
        switch self {
        case .invalidOffset: return "Invalid offset provided for file hashing."
        case .invalidSize: return "Invalid size provided for file hashing (extends beyond file size)."
        case .fileReadError(let underlying):
             return "Failed to read file range for hashing: \(underlying.localizedDescription)"
        }
    }
}

class Digest {
    static func hash(_ data: Data) -> String {
        "sha256:" + SHA256.hash(data: data).map { String(format: "%02x", $0) }.joined()
    }

    static func hash(contentsOf url: URL) throws -> String {
        let data = try Data(contentsOf: url)
        return hash(data)
    }
    
    // Hashes a specific byte range within a file
    static func hash(_ url: URL, offset: UInt64, size: UInt64) throws -> String {
        let fileHandle = try FileHandle(forReadingFrom: url)
        defer { try? fileHandle.close() }

        // Get file size for validation
        let fileSize = try fileHandle.seekToEnd()
        // Important: Seek back to start or original position if needed elsewhere,
        // but here we only need the size and will seek explicitly next.

        // Validate range
        guard offset <= fileSize else {
            throw DigestError.invalidOffset
        }
        guard (offset + size) <= fileSize else {
            // Check for potential overflow before adding
            if offset > UInt64.max - size {
                 throw DigestError.invalidSize // Prevent overflow before comparison
            }
            throw DigestError.invalidSize
        }
        
        // Handle zero size case (hash of empty data)
        if size == 0 {
             return hash(Data())
        }

        // Seek and read the specified range
        try fileHandle.seek(toOffset: offset)
        
        // Read exactly 'size' bytes
        let data: Data
        do {
             // read(upToCount:) might return less than requested if EOF is hit early,
             // but our guard checks should prevent this unless the file shrinks.
             // Let's try reading exactly `size` bytes if possible with FileHandle
             if #available(macOS 10.15.4, *) { // Check availability for read(count:)
                 data = try fileHandle.read(upToCount: Int(size)) ?? Data() // Read data or empty if error/EOF
                 if data.count != Int(size) {
                      // This case implies the file shrunk after size check or another read error
                      throw DigestError.fileReadError(NSError(domain: NSPOSIXErrorDomain, code: Int(EIO), userInfo: nil)) 
                 }
             } else {
                 // Fallback for older OS - less safe if file shrinks during read
                 guard let readData = try fileHandle.read(upToCount: Int(size)), readData.count == Int(size) else {
                      throw DigestError.fileReadError(NSError(domain: NSPOSIXErrorDomain, code: Int(EIO), userInfo: nil)) 
                 }
                 data = readData
             }
        } catch {
             throw DigestError.fileReadError(error)
        }

        // Calculate and return hash
        return hash(data)
    }
}

// --- Data Chunking Helper ---
extension Data {
    func chunks(ofCount size: Int) -> [Data] {
        guard count > 0, size > 0 else { return [self] } // Return self if size is 0 or less
        var chunks: [Data] = []
        var offset = 0
        while offset < count {
            let chunkSize = Swift.min(size, count - offset)
            let chunk = subdata(in: offset ..< offset + chunkSize)
            chunks.append(chunk)
            offset += chunkSize
        }
        return chunks
    }
} 