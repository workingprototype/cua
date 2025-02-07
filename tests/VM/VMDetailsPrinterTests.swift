import Testing
import Foundation
@testable import lume

struct VMDetailsPrinterTests {
    
    @Test func printStatus_whenJSON() throws {
        // Given
        let vms: [VMDetails] = [VMDetails(name: "name",
                                         os: "os",
                                         cpuCount: 2,
                                         memorySize: 1024,
                                         diskSize: .init(allocated: 24, total: 30),
                                         status: "status",
                                         vncUrl: "vncUrl",
                                         ipAddress: "0.0.0.0")]
        let jsonEncoder = JSONEncoder()
        jsonEncoder.outputFormatting = .prettyPrinted
        let expectedOutput = try String(data: jsonEncoder.encode(vms), encoding: .utf8)!
        
        // When
        var printedStatus: String?
        try VMDetailsPrinter.printStatus(vms, json: true, print: { printedStatus = $0 })

        // Then
        #expect(printedStatus == expectedOutput)
    }
    
    @Test func printStatus_whenNotJSON() throws {
        // Given
        let vms: [VMDetails] = [VMDetails(name: "name",
                                         os: "os",
                                         cpuCount: 2,
                                         memorySize: 1024,
                                         diskSize: .init(allocated: 24, total: 30),
                                         status: "status",
                                         vncUrl: "vncUrl",
                                         ipAddress: "0.0.0.0")]
        
        // When
        var printedLines: [String] = []
        try VMDetailsPrinter.printStatus(vms, json: false, print: { printedLines.append($0) })

        // Then
        #expect(printedLines.popLast() == "name                              os      2       0.00G   24.0B/30.0B     status          0.0.0.0         vncUrl                                            ")
        #expect(printedLines.popLast() == "name                              os      cpu     memory  disk            status          ip              vnc                                               ")
    }
}
