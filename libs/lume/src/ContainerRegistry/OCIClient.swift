import Foundation
import CryptoKit
import System
import Compression

// Custom Error for OCI Client operations (can be expanded)
enum OCIClientError: Error, LocalizedError {
    case unexpectedStatusCode(method: String, url: String, code: Int, body: String?)
    case invalidURL(String)
    case requestFailed(Error)
    case missingHeader(String)
    case invalidResponseData
    case authenticationFailed(String?)

    var errorDescription: String? {
        switch self {
        case .unexpectedStatusCode(let method, let url, let code, let body):
            return "OCIClient request [\(method) \(url)] failed with unexpected status code: \(code). Body: \(body ?? "<empty>")"
        case .invalidURL(let urlString):
            return "OCIClient: Invalid URL constructed: \(urlString)"
        case .requestFailed(let error):
            return "OCIClient request failed: \(error.localizedDescription)"
        case .missingHeader(let headerName):
            return "OCIClient: Missing expected header in response: \(headerName)"
        case .invalidResponseData:
            return "OCIClient: Invalid data received."
        case .authenticationFailed(let details):
             return "OCIClient authentication failed: \(details ?? "Unknown reason")"
        }
    }
}

// Structure to decode the JSON response from the OCI token endpoint
struct OCITokenResponse: Decodable {
    let token: String?
    let accessToken: String?
    let expiresIn: Int?
    let issuedAt: String? // Keep as String initially for decoding flexibility

    // Helper to get the actual token value
    var bearerToken: String? {
        token ?? accessToken
    }

    // Helper to calculate expiry date
    var expiresAt: Date? {
        guard let issuedAtString = issuedAt, 
              let issuedAtDate = ISO8601DateFormatter().date(from: issuedAtString) else {
            // If issue date is missing, assume it expires based on expiresIn from now
            // Default to 60s expiry if expiresIn is also missing (as per spec)
            return Date().addingTimeInterval(TimeInterval(expiresIn ?? 60))
        }
        // Default to 60s expiry if expiresIn is missing
        return issuedAtDate.addingTimeInterval(TimeInterval(expiresIn ?? 60)) 
    }
}

// OCI Registry Client
struct OCIClient {
    let host: String
    let namespace: String
    private let authenticationKeeper = AuthenticationKeeper()
    private let urlSession = URLSession.shared // Shared session

    init(host: String, namespace: String) {
        self.host = host
        self.namespace = namespace
    }

    private var baseURL: URL {
        // Assuming HTTPS, adjust if insecure option is needed
        URL(string: "https://\(host)/v2/")!
    }

    // --- Authentication Handling ---
    actor AuthenticationKeeper {
        private var currentAuth: Authentication? = nil // Store the current Authentication object

        // Method to get the current valid authentication header
        func validHeader() -> (String, String)? {
            guard let auth = currentAuth, auth.isValid() else {
                return nil // No valid/current token
            }
            return auth.header()
        }

        // Method to update the stored authentication mechanism
        func set(authentication: Authentication) {
            self.currentAuth = authentication
            Logger.debug("Authentication Keeper updated with new credentials.")
        }
    }

    protocol Authentication {
      func header() -> (String, String)
      func isValid() -> Bool
    }

    // Implementation for Bearer token authentication using the registry-issued token
    struct RegistryBearerAuthentication: Authentication {
        let tokenResponse: OCITokenResponse

        func header() -> (String, String) {
            let tokenValue = tokenResponse.bearerToken ?? ""
            return ("Authorization", "Bearer \(tokenValue)")
        }

        func isValid() -> Bool {
            guard let expiry = tokenResponse.expiresAt else {
                return true // Assume valid if no expiry info
            }
            // Check if current date + buffer is before expiry
            return Date().addingTimeInterval(30) < expiry
        }
    }

    // --- Network Request Helpers ---
    private func makeURL(endpoint: String, parameters: [String: String] = [:]) -> URL? {
        guard var components = URLComponents(url: baseURL.appendingPathComponent(endpoint), resolvingAgainstBaseURL: true) else {
            return nil
        }
        if !parameters.isEmpty {
            components.queryItems = parameters.map { URLQueryItem(name: $0.key, value: $0.value) }
        }
        return components.url
    }

    private func dataRequest(
        _ method: String,
        endpoint: String? = nil,
        url: URL? = nil,
        headers: [String: String] = [:],
        parameters: [String: String] = [:],
        body: Data? = nil,
        expectedStatusCodes: Swift.Set<Int> = [200],
        timeoutInterval: TimeInterval? = nil
    ) async throws -> (Data, HTTPURLResponse) {
        let requestURL: URL
        if let fullURL = url {
            guard var components = URLComponents(url: fullURL, resolvingAgainstBaseURL: true) else {
                throw OCIClientError.invalidURL(fullURL.absoluteString)
            }
            if !parameters.isEmpty {
                var queryItems = components.queryItems ?? []
                queryItems.append(contentsOf: parameters.map { URLQueryItem(name: $0.key, value: $0.value) })
                components.queryItems = queryItems
            }
            guard let finalURL = components.url else {
                 throw OCIClientError.invalidURL("Failed to add parameters to \(fullURL.absoluteString)")
            }
            requestURL = finalURL
        } else if let endpoint = endpoint {
            guard let constructedURL = makeURL(endpoint: endpoint, parameters: parameters) else {
                throw OCIClientError.invalidURL("\(baseURL.absoluteString)\(endpoint)")
            }
            requestURL = constructedURL
        } else {
            throw OCIClientError.invalidURL("Either endpoint or url must be provided")
        }

        var request = URLRequest(url: requestURL)
        request.httpMethod = method
        if let timeout = timeoutInterval {
            request.timeoutInterval = timeout
        }

        // Common headers
        request.setValue("LumeClient/1.0", forHTTPHeaderField: "User-Agent") 
        if let authHeader = await authenticationKeeper.validHeader() {
            request.setValue(authHeader.1, forHTTPHeaderField: authHeader.0)
        }

        // Request-specific headers
        for (key, value) in headers {
            request.setValue(value, forHTTPHeaderField: key)
        }

        // Body
        if let body = body {
            request.httpBody = body
            if request.value(forHTTPHeaderField: "Content-Type") == nil {
                request.setValue("application/octet-stream", forHTTPHeaderField: "Content-Type")
            }
             request.setValue("\(body.count)", forHTTPHeaderField: "Content-Length")
        }
        
        Logger.debug("OCIClient Request: \(method) \(requestURL.absoluteString)")

        do {
            let (data, response) = try await urlSession.data(for: request)
            guard let httpResponse = response as? HTTPURLResponse else {
                throw OCIClientError.requestFailed(NSError(domain: NSURLErrorDomain, code: NSURLErrorBadServerResponse, userInfo: nil))
            }
            
            Logger.debug("OCIClient Response: \(httpResponse.statusCode) for \(method) \(requestURL.absoluteString)")

            if !expectedStatusCodes.contains(httpResponse.statusCode) {
                let bodyString = String(data: data, encoding: .utf8)
                if httpResponse.statusCode == 401 {
                     Logger.error("OCIClient authentication failed (401) for \(method) \(requestURL.absoluteString)")
                     throw OCIClientError.authenticationFailed(bodyString)
                }
                throw OCIClientError.unexpectedStatusCode(method: method, url: requestURL.absoluteString, code: httpResponse.statusCode, body: bodyString)
            }
            
            return (data, httpResponse)
        } catch {
            // Don't wrap OCIClientErrors again
            if error is OCIClientError { throw error }
            
            Logger.error("OCIClient request error for \(method) \(requestURL.absoluteString): \(error.localizedDescription)")
            throw OCIClientError.requestFailed(error)
        }
    }

    // Helper for streaming requests
    private func streamRequest(
        _ method: String,
        endpoint: String? = nil,
        url: URL? = nil,
        headers: [String: String] = [:],
        parameters: [String: String] = [:],
        expectedStatusCodes: Swift.Set<Int> = [200],
        timeoutInterval: TimeInterval? = nil
    ) async throws -> (URLSession.AsyncBytes, HTTPURLResponse) {
        let requestURL: URL
        if let fullURL = url {
            guard var components = URLComponents(url: fullURL, resolvingAgainstBaseURL: true) else {
                throw OCIClientError.invalidURL(fullURL.absoluteString)
            }
            if !parameters.isEmpty {
                var queryItems = components.queryItems ?? []
                queryItems.append(contentsOf: parameters.map { URLQueryItem(name: $0.key, value: $0.value) })
                components.queryItems = queryItems
            }
            guard let finalURL = components.url else {
                 throw OCIClientError.invalidURL("Failed to add parameters to \(fullURL.absoluteString)")
            }
            requestURL = finalURL
        } else if let endpoint = endpoint {
            guard let constructedURL = makeURL(endpoint: endpoint, parameters: parameters) else {
                throw OCIClientError.invalidURL("\(baseURL.absoluteString)\(endpoint)")
            }
            requestURL = constructedURL
        } else {
            throw OCIClientError.invalidURL("Either endpoint or url must be provided")
        }

        var request = URLRequest(url: requestURL)
        request.httpMethod = method
        if let timeout = timeoutInterval {
            request.timeoutInterval = timeout
        }

        // Common headers
        request.setValue("LumeClient/1.0", forHTTPHeaderField: "User-Agent")
        if let authHeader = await authenticationKeeper.validHeader() {
            request.setValue(authHeader.1, forHTTPHeaderField: authHeader.0)
        }

        // Request-specific headers
        for (key, value) in headers {
            request.setValue(value, forHTTPHeaderField: key)
        }
        
        Logger.debug("OCIClient Stream Request: \(method) \(requestURL.absoluteString)")

        do {
            let (byteStream, response) = try await urlSession.bytes(for: request)
            guard let httpResponse = response as? HTTPURLResponse else {
                throw OCIClientError.requestFailed(NSError(domain: NSURLErrorDomain, code: NSURLErrorBadServerResponse, userInfo: nil))
            }
            
            Logger.debug("OCIClient Stream Response: \(httpResponse.statusCode) for \(method) \(requestURL.absoluteString)")

            if !expectedStatusCodes.contains(httpResponse.statusCode) {
                // Attempt to read some data from the stream for error details
                var bodyString: String? = nil
                var errorData = Data()
                var iterator = byteStream.makeAsyncIterator()
                for _ in 0..<1024 {
                    if let byte = try await iterator.next() {
                        errorData.append(byte)
                    } else {
                        break
                    }
                }
                bodyString = String(data: errorData, encoding: .utf8) ?? "<non-utf8 data>"
                
                // Handle 401 separately - this indicates potential need for token refresh
                if httpResponse.statusCode == 401 {
                    Logger.error("OCIClient authentication failed (401) for \(method) \(requestURL.absoluteString)")
                    throw OCIClientError.authenticationFailed(bodyString)
                }
                throw OCIClientError.unexpectedStatusCode(method: method, url: requestURL.absoluteString, code: httpResponse.statusCode, body: bodyString)
            }

            return (byteStream, httpResponse)
        } catch {
            // Don't wrap OCIClientErrors again
            if error is OCIClientError { throw error }
            
            Logger.error("OCIClient stream request error for \(method) \(requestURL.absoluteString): \(error.localizedDescription)")
            throw OCIClientError.requestFailed(error)
        }
    }

    // Modified dataRequest to handle retries after authentication
    private func retryingDataRequest(
        _ method: String,
        endpoint: String? = nil,
        url: URL? = nil,
        headers: [String: String] = [:],
        parameters: [String: String] = [:],
        body: Data? = nil,
        expectedStatusCodes: Swift.Set<Int> = [200],
        timeoutInterval: TimeInterval? = nil
    ) async throws -> (Data, HTTPURLResponse) {
        // Initial attempt
        do {
            return try await dataRequest(
                method, endpoint: endpoint, url: url, headers: headers,
                parameters: parameters, body: body, expectedStatusCodes: expectedStatusCodes,
                timeoutInterval: timeoutInterval
            )
        } catch OCIClientError.authenticationFailed(_) {
            // Authentication failed, attempt to refresh token
            Logger.info("Initial request failed with auth error, attempting token refresh...")
            guard await refreshToken() else {
                 Logger.error("Token refresh failed.")
                 throw OCIClientError.authenticationFailed("Token refresh failed")
            }
            
            // Retry the request once with the new token
            Logger.info("Retrying request with new token...")
            do {
                return try await dataRequest(
                    method, endpoint: endpoint, url: url, headers: headers,
                    parameters: parameters, body: body, expectedStatusCodes: expectedStatusCodes,
                    timeoutInterval: timeoutInterval
                )
            } catch {
                 Logger.error("Request failed even after token refresh: \(error.localizedDescription)")
                 throw error // Throw the error from the second attempt
            }
        } catch {
            // Non-auth error, just re-throw
            throw error
        }
    }

    // Modified streamRequest to handle retries after authentication
    private func retryingStreamRequest(
        _ method: String,
        endpoint: String? = nil,
        url: URL? = nil,
        headers: [String: String] = [:],
        parameters: [String: String] = [:],
        expectedStatusCodes: Swift.Set<Int> = [200],
        timeoutInterval: TimeInterval? = nil
    ) async throws -> (URLSession.AsyncBytes, HTTPURLResponse) {
         // Initial attempt
        do {
            return try await streamRequest(
                method, endpoint: endpoint, url: url, headers: headers,
                parameters: parameters, expectedStatusCodes: expectedStatusCodes,
                timeoutInterval: timeoutInterval
            )
        } catch OCIClientError.authenticationFailed(_) {
            // Authentication failed, attempt to refresh token
            Logger.info("Initial stream request failed with auth error, attempting token refresh...")
            guard await refreshToken() else {
                 Logger.error("Token refresh failed.")
                 throw OCIClientError.authenticationFailed("Token refresh failed")
            }
            
            // Retry the request once with the new token
            Logger.info("Retrying stream request with new token...")
            do {
                 return try await streamRequest(
                     method, endpoint: endpoint, url: url, headers: headers,
                     parameters: parameters, expectedStatusCodes: expectedStatusCodes,
                     timeoutInterval: timeoutInterval
                 )
            } catch {
                 Logger.error("Stream request failed even after token refresh: \(error.localizedDescription)")
                 throw error // Throw the error from the second attempt
            }
         } catch {
             // Non-auth error, just re-throw
             throw error
         }
    }

    // --- Token Refresh Logic ---
    private func refreshToken() async -> Bool {
        // Use Basic Auth with GITHUB_USERNAME / GITHUB_TOKEN (as password)
        guard let username = ProcessInfo.processInfo.environment["GITHUB_USERNAME"], !username.isEmpty,
              let pat = ProcessInfo.processInfo.environment["GITHUB_TOKEN"], !pat.isEmpty else {
            Logger.error("Cannot refresh token: GITHUB_USERNAME and/or GITHUB_TOKEN not found in environment.")
            return false
        }

        // Construct the token endpoint URL (GHCR specific - may need adjustment for others)
        // Scope determines permissions for the new token
        // We need pull and push access for the repository namespace
        let scope = "repository:\(namespace):pull,push"
        let tokenEndpoint = "https://ghcr.io/token"
        guard let tokenURL = URL(string: tokenEndpoint) else { return false }

        guard var components = URLComponents(url: tokenURL, resolvingAgainstBaseURL: false) else {
             Logger.error("Failed to create URL components for token endpoint.")
             return false
        }
        components.queryItems = [
            URLQueryItem(name: "service", value: "ghcr.io"),
            URLQueryItem(name: "scope", value: scope)
        ]

        guard let finalTokenURL = components.url else {
             Logger.error("Failed to create final URL for token endpoint.")
             return false
        }

        var request = URLRequest(url: finalTokenURL)
        request.httpMethod = "GET"
        let creds = Data("\(username):\(pat)".utf8).base64EncodedString()
        request.setValue("Basic \(creds)", forHTTPHeaderField: "Authorization")
        request.setValue("application/json", forHTTPHeaderField: "Accept")

        Logger.info("Requesting new token from \(tokenEndpoint) with scope '\(scope)'")

        do {
            let (data, response) = try await urlSession.data(for: request)
            guard let httpResponse = response as? HTTPURLResponse, httpResponse.statusCode == 200 else {
                 let code = (response as? HTTPURLResponse)?.statusCode ?? -1
                 let body = String(data: data, encoding: .utf8)
                 Logger.error("Token endpoint request failed. Status: \(code). Body: \(body ?? "<empty>")")
                return false
            }

            let decoder = JSONDecoder()
            decoder.keyDecodingStrategy = .convertFromSnakeCase // Handle potential snake_case keys
            let tokenResponse = try decoder.decode(OCITokenResponse.self, from: data)

            guard tokenResponse.bearerToken != nil else {
                 Logger.error("Token endpoint response missing 'token' or 'access_token'.")
                 return false
            }

            // Store the new token information
            await authenticationKeeper.set(authentication: RegistryBearerAuthentication(tokenResponse: tokenResponse))
            Logger.info("Successfully obtained and stored new registry token.")
            return true

        } catch {
            Logger.error("Error during token refresh request: \(error.localizedDescription)")
            return false
        }
    }

    // --- Public API Methods ---

    func pushBlob(fromData data: Data, chunkSizeMb: Int = 0, digest: String? = nil, progress: Progress? = nil) async throws -> String {
        let finalDigest = digest ?? Digest.hash(data)
        Logger.debug("Starting blob push for digest: \(finalDigest), size: \(data.count), chunk size: \(chunkSizeMb)MB")

        // 1. Initiate Upload
        let initiateEndpoint = "\(namespace)/blobs/uploads/"
        var currentLocation: URL
        do {
            let (_, response) = try await retryingDataRequest(
                "POST",
                endpoint: initiateEndpoint,
                headers: ["Content-Length": "0"], 
                expectedStatusCodes: [202]
            )
            guard let locationString = response.value(forHTTPHeaderField: "Location") else {
                throw OCIClientError.missingHeader("Location")
            }
            guard let uploadURL = URL(string: locationString, relativeTo: baseURL.deletingLastPathComponent().deletingLastPathComponent()) else {
                 throw OCIClientError.invalidURL("Could not resolve Location header: \(locationString)")
             }
             currentLocation = uploadURL
             Logger.debug("Blob upload initiated. Location: \(currentLocation.absoluteString)")
        } catch {
            Logger.error("Failed to initiate blob upload for \(finalDigest): \(error.localizedDescription)")
             if let registryError = error as? OCIClientError, case .authenticationFailed = registryError {
                 throw PushError.authenticationFailed // Map to PushError
             }
             throw PushError.uploadInitiationFailed // Map to PushError
        }

        // 2. Upload Data (Monolithic or Chunked)
        let chunkSize = chunkSizeMb * 1024 * 1024
        if chunkSize <= 0 || data.count <= chunkSize {
            // Monolithic Upload
            Logger.debug("Performing monolithic upload for \(finalDigest)...")
            do {
                _ = try await retryingDataRequest(
                    "PUT",
                    url: currentLocation, 
                    parameters: ["digest": finalDigest], 
                    body: data,
                    expectedStatusCodes: [201]
                )
                progress?.completedUnitCount = Int64(data.count) 
                Logger.info("Monolithic blob upload successful for \(finalDigest).")
            } catch {
                Logger.error("Monolithic blob upload failed for \(finalDigest): \(error.localizedDescription)")
                throw PushError.blobUploadFailed // Map error
            }
        } else {
            // Chunked Upload
            Logger.debug("Performing chunked upload for \(finalDigest)...")
            let chunks = data.chunks(ofCount: chunkSize)
            var uploadedBytes: Int64 = 0

            for (index, chunk) in chunks.enumerated() {
                let isLastChunk = index == chunks.count - 1
                let rangeStart = uploadedBytes
                let rangeEnd = uploadedBytes + Int64(chunk.count) - 1
                let contentRange = "\(rangeStart)-\(rangeEnd)"
                let method = isLastChunk ? "PUT" : "PATCH"
                let expectedStatus = isLastChunk ? 201 : 202
                let parameters = isLastChunk ? ["digest": finalDigest] : [:]

                Logger.debug("Uploading chunk \(index + 1)/\(chunks.count) (\(method)), Range: \(contentRange), Location: \(currentLocation.absoluteString)")

                do {
                    let (_, response) = try await retryingDataRequest(
                        method,
                        url: currentLocation,
                        headers: [
                            "Content-Type": "application/octet-stream",
                            "Content-Range": contentRange
                        ],
                        parameters: parameters,
                        body: chunk,
                        expectedStatusCodes: [expectedStatus]
                    )

                    uploadedBytes += Int64(chunk.count)
                    progress?.completedUnitCount = uploadedBytes 

                    if !isLastChunk {
                        guard let locationString = response.value(forHTTPHeaderField: "Location") else {
                            Logger.error("Missing or invalid Location header after PATCH chunk \(index + 1) for \(finalDigest)")
                            throw OCIClientError.missingHeader("Location")
                        }
                         guard let nextURL = URL(string: locationString, relativeTo: baseURL.deletingLastPathComponent().deletingLastPathComponent()) else {
                             throw OCIClientError.invalidURL("Could not resolve next chunk Location header: \(locationString)")
                         }
                         currentLocation = nextURL
                    }
                    Logger.debug("Chunk \(index + 1)/\(chunks.count) uploaded successfully.")
                } catch {
                    Logger.error("Chunked upload failed at chunk \(index + 1) for \(finalDigest): \(error.localizedDescription)")
                    throw PushError.blobUploadFailed // Map error
                }
            }
             Logger.info("Chunked blob upload successful for \(finalDigest).")
        }

        return finalDigest
    }

     func blobExists(_ digest: String) async throws -> Bool {
        Logger.debug("Checking if blob exists: \(digest)")
        do {
            _ = try await retryingDataRequest(
                "HEAD",
                endpoint: "\(namespace)/blobs/\(digest)",
                expectedStatusCodes: [200]
            )
            Logger.debug("Blob \(digest) exists.")
            return true
        } catch let OCIClientError.unexpectedStatusCode(_, _, code, _) where code == 404 {
            Logger.debug("Blob \(digest) does not exist (404).")
            return false
        } catch {
             Logger.error("Failed to check blob existence for \(digest): \(error.localizedDescription)")
            throw error // Re-throw other errors (network, auth etc)
        }
    }

    func pushManifest(reference: String, manifest: OCIManifest) async throws -> String {
        Logger.debug("Pushing manifest for reference: \(reference)")

        do {
            let encoder = JSONEncoder()
            let manifestData = try encoder.encode(manifest)
            let manifestDigest = Digest.hash(manifestData)
            
            let endpoint = "\(namespace)/manifests/\(reference)"
            let headers = ["Content-Type": manifest.mediaType] 
            
            let (_, response) = try await retryingDataRequest(
                "PUT",
                endpoint: endpoint,
                headers: headers,
                body: manifestData,
                expectedStatusCodes: [201]
            )
            
            if let returnedDigest = response.value(forHTTPHeaderField: "Docker-Content-Digest"), returnedDigest != manifestDigest {
                 Logger.info("Registry returned digest \(returnedDigest) differs from calculated digest \(manifestDigest) for manifest \(reference)")
                return returnedDigest 
            }
            
            Logger.debug("Manifest push successful for \(reference), digest: \(manifestDigest)")
            return manifestDigest

        } catch let error as EncodingError {
            Logger.error("Failed to encode manifest for \(reference): \(error.localizedDescription)")
            throw OCIClientError.invalidResponseData
        } catch let error as OCIClientError {
            Logger.error("OCIClient error pushing manifest for \(reference): \(error.localizedDescription)")
             if case .authenticationFailed = error {
                 throw PushError.authenticationFailed
             }
             // Add other mappings if needed
             throw PushError.manifestPushFailed 
        } catch {
            Logger.error("Unknown error pushing manifest for \(reference): \(error.localizedDescription)")
            throw PushError.manifestPushFailed
        }
    }

    func pullManifest(reference: String) async throws -> (OCIManifest, String) {
        Logger.debug("Pulling manifest for reference: \(reference)")
        
        let endpoint = "\(namespace)/manifests/\(reference)"
        let headers = ["Accept": OCIImageManifestV1MediaType] 
        
        do {
            let (data, _) = try await retryingDataRequest("GET", endpoint: endpoint, headers: headers, expectedStatusCodes: [200])
            
            let decoder = JSONDecoder()
            let manifest = try decoder.decode(OCIManifest.self, from: data)
            
            let manifestDigest = Digest.hash(data)
            
            Logger.debug("Manifest pull successful for \(reference), digest: \(manifestDigest)")
            return (manifest, manifestDigest)
            
        } catch let error as DecodingError {
            Logger.error("Failed to decode manifest for \(reference): \(error.localizedDescription)")
            throw OCIClientError.invalidResponseData
        } catch let error as OCIClientError {
            Logger.error("OCIClient error pulling manifest for \(reference): \(error.localizedDescription)")
             if case .authenticationFailed = error {
                 throw PullError.tokenFetchFailed // Map to PullError
             }
             throw PullError.manifestFetchFailed // Map to PullError
        } catch {
            Logger.error("Unknown error pulling manifest for \(reference): \(error.localizedDescription)")
            throw PullError.manifestFetchFailed
        }
    }

     func pullBlob(_ digest: String, progress: Progress? = nil) async throws -> Data {
         Logger.debug("Pulling blob: \(digest)")
         
         let endpoint = "\(namespace)/blobs/\(digest)"
         var downloadedData = Data()
         var receivedBytes: Int64 = 0
         
         do {
             let (byteStream, httpResponse) = try await retryingStreamRequest(
                 "GET",
                 endpoint: endpoint,
                 expectedStatusCodes: [200],
                 timeoutInterval: 3600
             )
             
             let expectedLength = httpResponse.expectedContentLength
             if expectedLength > 0 { 
                 progress?.totalUnitCount = expectedLength
             }

             for try await byte in byteStream {
                 downloadedData.append(byte)
                 receivedBytes += 1
                 progress?.completedUnitCount = receivedBytes 
             }
             
             progress?.completedUnitCount = receivedBytes
             if progress?.totalUnitCount == 0 && receivedBytes > 0 {
                 progress?.totalUnitCount = receivedBytes
             }
             
             Logger.debug("Blob pull successful for \(digest), size: \(downloadedData.count)")
             return downloadedData
             
         } catch let error as OCIClientError {
             Logger.error("OCIClient error pulling blob \(digest): \(error.localizedDescription)")
             if case .authenticationFailed = error {
                  throw PullError.tokenFetchFailed // Map to PullError
             }
             throw PullError.layerDownloadFailed(digest) // Map to PullError
         } catch {
             Logger.error("Unknown error pulling blob \(digest): \(error.localizedDescription)")
             throw PullError.layerDownloadFailed(digest)
         }
     }
} 