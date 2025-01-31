import ArgumentParser
import Foundation

struct Get: AsyncParsableCommand {
    static let configuration = CommandConfiguration(
        abstract: "Get detailed information about a virtual machine"
    )

    @Argument(help: "Name of the virtual machine", completion: .custom(completeVMName))
    var name: String
    
    init() {
    }
    
    @MainActor
    func run() async throws {
        let vmController = LumeController()
        let vm = try vmController.get(name: name)
        VMDetailsPrinter.printStatus([vm.details])
    }
} 