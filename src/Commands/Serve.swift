import ArgumentParser
import Foundation

struct Serve: AsyncParsableCommand {
    static let configuration = CommandConfiguration(
        abstract: "Start the VM management server"
    )
    
    @Option(help: "Port to listen on")
    var port: UInt16 = 3000
    
    func run() async throws {
        let server = await Server(port: port)
        Logger.info("Starting server", metadata: ["port": "\(port)"])
        try await server.start()
    }
}