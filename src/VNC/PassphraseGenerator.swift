import Foundation

final class PassphraseGenerator {
    private let words: [String]
    
    init(words: [String] = PassphraseGenerator.defaultWords) {
        self.words = words
    }
    
    func prefix(_ count: Int) -> [String] {
        guard count > 0 else { return [] }
        return (0..<count).map { _ in words.randomElement() ?? words[0] }
    }
    
    private static let defaultWords = [
        "apple", "banana", "cherry", "date",
        "elder", "fig", "grape", "honey"
    ]
}