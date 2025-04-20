import Foundation

// --- OCI Media Types ---
let OCIImageManifestV1MediaType = "application/vnd.oci.image.manifest.v1+json"
let OCIConfigMediaType = "application/vnd.lume.config+json"
let DiskMediaTypeLZ4 = "application/vnd.lume.disk.lz4"
let NvramMediaTypeLZ4 = "application/vnd.lume.nvram.lz4"

// --- OCI Annotations ---
let OCIAnnotationUncompressedSize = "org.lume.uncompressed-size"
let OCIAnnotationUncompressedDigest = "org.lume.uncompressed-content-digest"


// --- Core OCI Data Structures ---
struct OCIManifest: Codable {
    let mediaType: String
    let schemaVersion: Int
    let config: OCIManifestConfig
    let layers: [OCIManifestLayer]

    init(config: OCIManifestConfig, layers: [OCIManifestLayer]) {
        self.mediaType = OCIImageManifestV1MediaType // Use constant
        self.schemaVersion = 2
        self.config = config
        self.layers = layers
    }
}

struct OCIManifestConfig: Codable {
    let mediaType: String
    let size: Int
    let digest: String
}

struct OCIManifestLayer: Codable {
    let mediaType: String
    let size: Int64
    let digest: String
    let annotations: [String: String]?
}

// --- Simple OCI Config Struct (for lume-specific config layer) ---
struct SimpleOCIConfig: Codable {
    struct ConfigDetail: Codable {
        var Labels: [String: String]?
    }
    var architecture: String = "arm64"
    var os: String = "darwin"
    var config: ConfigDetail?
} 