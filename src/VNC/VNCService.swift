import Foundation
import Dynamic
import Virtualization

/// Protocol defining the interface for VNC server operations
@MainActor
protocol VNCService {
    var url: String? { get }
    func start(port: Int, virtualMachine: Any?) async throws
    func stop()
    func openClient(url: String) async throws
}

/// Default implementation of VNCService
@MainActor
final class DefaultVNCService: VNCService {
    private var vncServer: Any?
    private let vmDirectory: VMDirectory
    
    init(vmDirectory: VMDirectory) {
        self.vmDirectory = vmDirectory
    }
    
    var url: String? {
        get {
            return try? vmDirectory.loadSession().url
        }
    }
    
    func start(port: Int, virtualMachine: Any?) async throws {
        let password = Array(PassphraseGenerator().prefix(4)).joined(separator: "-")
        let securityConfiguration = Dynamic._VZVNCAuthenticationSecurityConfiguration(password: password)
        let server = Dynamic._VZVNCServer(port: port, queue: DispatchQueue.main,
                                      securityConfiguration: securityConfiguration)
        if let vm = virtualMachine as? VZVirtualMachine {
            server.virtualMachine = vm
        }
        server.start()
        
        vncServer = server
        
        // Wait for port to be assigned
        while true {
            if let port: UInt16 = server.port.asUInt16, port != 0 {
                let url = "vnc://:\(password)@127.0.0.1:\(port)"
                
                // Save session information
                let session = VNCSession(
                    url: url
                )
                try vmDirectory.saveSession(session)
                break
            }
            try await Task.sleep(nanoseconds: 50_000_000)
        }
    }
    
    func stop() {
        if let server = vncServer as? Dynamic {
            server.stop()
        }
        vncServer = nil
        vmDirectory.clearSession()
    }
    
    func openClient(url: String) async throws {
        let processRunner = DefaultProcessRunner()
        try processRunner.run(executable: "/usr/bin/open", arguments: [url])
    }
} 