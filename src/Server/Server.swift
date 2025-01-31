import Foundation
import Network

// MARK: - Server Class
@MainActor
final class Server {
    
    // MARK: - Route Type
    private struct Route {
        let method: String
        let path: String
        let handler: (HTTPRequest) async throws -> HTTPResponse
        
        func matches(_ request: HTTPRequest) -> Bool {
            if method != request.method { return false }
            
            // Handle path parameters
            let routeParts = path.split(separator: "/")
            let requestParts = request.path.split(separator: "/")
            
            if routeParts.count != requestParts.count { return false }
            
            for (routePart, requestPart) in zip(routeParts, requestParts) {
                if routePart.hasPrefix(":") { continue }  // Path parameter
                if routePart != requestPart { return false }
            }
            
            return true
        }
        
        func extractParams(_ request: HTTPRequest) -> [String: String] {
            var params: [String: String] = [:]
            let routeParts = path.split(separator: "/")
            let requestParts = request.path.split(separator: "/")
            
            for (routePart, requestPart) in zip(routeParts, requestParts) {
                if routePart.hasPrefix(":") {
                    let paramName = String(routePart.dropFirst())
                    params[paramName] = String(requestPart)
                }
            }
            
            return params
        }
    }
    
    // MARK: - Properties
    private let port: NWEndpoint.Port
    private let controller: LumeController
    private var isRunning = false
    private var listener: NWListener?
    private var routes: [Route]
    
    // MARK: - Initialization
    init(port: UInt16 = 3000) {
        self.port = NWEndpoint.Port(rawValue: port)!
        self.controller = LumeController()
        self.routes = []
        
        // Define API routes after self is fully initialized
        self.setupRoutes()
    }
    
    // MARK: - Route Setup
    private func setupRoutes() {
        routes = [
            Route(method: "GET", path: "/lume/vms", handler: { [weak self] _ in
                guard let self else { throw HTTPError.internalError }
                return try await self.handleListVMs()
            }),
            Route(method: "GET", path: "/lume/vms/:name", handler: { [weak self] request in
                guard let self else { throw HTTPError.internalError }
                let params = Route(method: "GET", path: "/lume/vms/:name", handler: { _ in
                    HTTPResponse(statusCode: .ok, body: "")
                }).extractParams(request)
                guard let name = params["name"] else {
                    return HTTPResponse(statusCode: .badRequest, body: "Missing VM name")
                }
                return try await self.handleGetVM(name: name)
            }),
            Route(method: "DELETE", path: "/lume/vms/:name", handler: { [weak self] request in
                guard let self else { throw HTTPError.internalError }
                let params = Route(method: "DELETE", path: "/lume/vms/:name", handler: { _ in
                    HTTPResponse(statusCode: .ok, body: "")
                }).extractParams(request)
                guard let name = params["name"] else {
                    return HTTPResponse(statusCode: .badRequest, body: "Missing VM name")
                }
                return try await self.handleDeleteVM(name: name)
            }),
            Route(method: "POST", path: "/lume/vms", handler: { [weak self] request in
                guard let self else { throw HTTPError.internalError }
                return try await self.handleCreateVM(request.body)
            }),
            Route(method: "POST", path: "/lume/vms/clone", handler: { [weak self] request in
                guard let self else { throw HTTPError.internalError }
                return try await self.handleCloneVM(request.body)
            }),
            Route(method: "PATCH", path: "/lume/vms/:name", handler: { [weak self] request in
                guard let self else { throw HTTPError.internalError }
                let params = Route(method: "PATCH", path: "/lume/vms/:name", handler: { _ in
                    HTTPResponse(statusCode: .ok, body: "")
                }).extractParams(request)
                guard let name = params["name"] else {
                    return HTTPResponse(statusCode: .badRequest, body: "Missing VM name")
                }
                return try await self.handleSetVM(name: name, body: request.body)
            }),
            Route(method: "POST", path: "/lume/vms/:name/run", handler: { [weak self] request in
                guard let self else { throw HTTPError.internalError }
                let params = Route(method: "POST", path: "/lume/vms/:name/run", handler: { _ in
                    HTTPResponse(statusCode: .ok, body: "")
                }).extractParams(request)
                guard let name = params["name"] else {
                    return HTTPResponse(statusCode: .badRequest, body: "Missing VM name")
                }
                return try await self.handleRunVM(name: name, body: request.body)
            }),
            Route(method: "POST", path: "/lume/vms/:name/stop", handler: { [weak self] request in
                guard let self else { throw HTTPError.internalError }
                let params = Route(method: "POST", path: "/lume/vms/:name/stop", handler: { _ in
                    HTTPResponse(statusCode: .ok, body: "")
                }).extractParams(request)
                guard let name = params["name"] else {
                    return HTTPResponse(statusCode: .badRequest, body: "Missing VM name")
                }
                return try await self.handleStopVM(name: name)
            }),
            Route(method: "GET", path: "/lume/ipsw", handler: { [weak self] _ in
                guard let self else { throw HTTPError.internalError }
                return try await self.handleIPSW()
            }),
            Route(method: "POST", path: "/lume/pull", handler: { [weak self] request in
                guard let self else { throw HTTPError.internalError }
                return try await self.handlePull(request.body)
            }),
            Route(method: "POST", path: "/lume/prune", handler: { [weak self] _ in
                guard let self else { throw HTTPError.internalError }
                return try await self.handlePruneImages()
            }),
            Route(method: "GET", path: "/lume/images", handler: { [weak self] request in
                guard let self else { throw HTTPError.internalError }
                return try await self.handleGetImages(request)
            })
        ]
    }
    
    // MARK: - Server Lifecycle
    func start() async throws {
        let parameters = NWParameters.tcp
        listener = try NWListener(using: parameters, on: port)
        
        listener?.newConnectionHandler = { [weak self] connection in
            Task { @MainActor [weak self] in
                guard let self else { return }
                self.handleConnection(connection)
            }
        }
        
        listener?.start(queue: .main)
        isRunning = true
        
        Logger.info("Server started", metadata: ["port": "\(port.rawValue)"])
        
        // Keep the server running
        while isRunning {
            try await Task.sleep(nanoseconds: 1_000_000_000)
        }
    }
    
    func stop() {
        isRunning = false
        listener?.cancel()
    }
    
    // MARK: - Connection Handling
    private func handleConnection(_ connection: NWConnection) {
        connection.stateUpdateHandler = { [weak self] state in
            switch state {
            case .ready:
                Task { @MainActor [weak self] in
                    guard let self else { return }
                    self.receiveData(connection)
                }
            case .failed(let error):
                Logger.error("Connection failed", metadata: ["error": error.localizedDescription])
                connection.cancel()
            case .cancelled:
                // Connection is already cancelled, no need to cancel again
                break
            default:
                break
            }
        }
        connection.start(queue: .main)
    }
    
    private func receiveData(_ connection: NWConnection) {
        connection.receive(minimumIncompleteLength: 1, maximumLength: 65536) { [weak self] content, _, isComplete, error in
            if let error = error {
                Logger.error("Receive error", metadata: ["error": error.localizedDescription])
                connection.cancel()
                return
            }
            
            guard let data = content, !data.isEmpty else {
                if isComplete {
                    connection.cancel()
                }
                return
            }
            
            Task { @MainActor [weak self] in
                guard let self else { return }
                do {
                    let response = try await self.handleRequest(data)
                    self.send(response, on: connection)
                } catch {
                    let errorResponse = self.errorResponse(error)
                    self.send(errorResponse, on: connection)
                }
            }
        }
    }
    
    private func send(_ response: HTTPResponse, on connection: NWConnection) {
        let data = response.serialize()
        Logger.info("Serialized response", metadata: ["data": String(data: data, encoding: .utf8) ?? ""])
        connection.send(content: data, completion: .contentProcessed { [weak connection] error in
            if let error = error {
                Logger.error("Failed to send response", metadata: ["error": error.localizedDescription])
            } else {
                Logger.info("Response sent successfully")
            }
            if connection?.state != .cancelled {
                connection?.cancel()
            }
        })
    }
    
    // MARK: - Request Handling
    private func handleRequest(_ data: Data) async throws -> HTTPResponse {
        Logger.info("Received request data", metadata: ["data": String(data: data, encoding: .utf8) ?? ""])
        
        guard let request = HTTPRequest(data: data) else {
            Logger.error("Failed to parse request")
            return HTTPResponse(statusCode: .badRequest, body: "Invalid request")
        }
        
        Logger.info("Parsed request", metadata: [
            "method": request.method,
            "path": request.path,
            "headers": "\(request.headers)",
            "body": String(data: request.body ?? Data(), encoding: .utf8) ?? ""
        ])
        
        // Find matching route
        guard let route = routes.first(where: { $0.matches(request) }) else {
            return HTTPResponse(statusCode: .notFound, body: "Not found")
        }
        
        // Handle the request
        let response = try await route.handler(request)
        
        Logger.info("Sending response", metadata: [
            "statusCode": "\(response.statusCode.rawValue)",
            "headers": "\(response.headers)",
            "body": String(data: response.body ?? Data(), encoding: .utf8) ?? ""
        ])
        
        return response
    }
    
    private func errorResponse(_ error: Error) -> HTTPResponse {
        HTTPResponse(
            statusCode: .internalServerError,
            headers: ["Content-Type": "application/json"],
            body: try! JSONEncoder().encode(APIError(message: error.localizedDescription))
        )
    }
}