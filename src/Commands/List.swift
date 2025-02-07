import ArgumentParser
import Foundation

struct List: AsyncParsableCommand {
    static let configuration: CommandConfiguration = CommandConfiguration(
        commandName: "ls",
        abstract: "List virtual machines"
    )
    
    @Flag(name: .long, help: "Outputs the images as a machine-readable JSON.")
    var json = false
    
    init() {
    }
    
    @MainActor
    func run() async throws {
        let manager = LumeController()
        let vms = try manager.list()
        if vms.isEmpty && !json {
            print("No virtual machines found")
        } else {
            try VMDetailsPrinter.printStatus(vms, json: self.json)
        }
    }
}
