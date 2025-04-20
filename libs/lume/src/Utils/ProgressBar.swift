import Foundation

/// Simple CLI Progress Bar Controller using Foundation.Progress
actor ProgressBarController {
    private let progress: Progress
    private let description: String
    private let barWidth: Int
    private var timerTask: Task<Void, Never>?
    private var lastOutputLength: Int = 0

    /// Initializes the progress bar controller.
    /// - Parameters:
    ///   - progress: The `Foundation.Progress` object to observe.
    ///   - description: Text label to display before the progress bar.
    ///   - barWidth: The character width of the progress bar itself.
    init(progress: Progress, description: String = "Progress", barWidth: Int = 40) {
        self.progress = progress
        self.description = description
        self.barWidth = barWidth
    }

    /// Starts periodically drawing the progress bar to the console.
    func start() {
        guard timerTask == nil else { return } // Prevent multiple starts
        
        // Use a detached task for the timer loop
        timerTask = Task.detached { [weak self] in
            while !(self?.progress.isFinished ?? true) && !Task.isCancelled {
                await self?.redraw()
                // Update roughly twice per second
                try? await Task.sleep(nanoseconds: 500_000_000) 
            }
            // Ensure one final draw upon completion if task wasn't cancelled
             if !(Task.isCancelled) {
                await self?.redraw(forceComplete: true)
             }
        }
    }

    /// Stops the periodic updates and redraws the bar one last time at 100%.
    func finish() {
        timerTask?.cancel()
        timerTask = nil
        // Final redraw ensures 100% is displayed
        redraw(forceComplete: true)
        // Print a newline to move cursor after the progress bar
        Swift.print()
        fflush(stdout) // Ensure output is flushed
    }

    /// Redraws the progress bar based on the current progress state.
    private func redraw(forceComplete: Bool = false) {
        let fraction = forceComplete ? 1.0 : progress.fractionCompleted
        let percentage = Int(fraction * 100)
        
        let completedWidth = Int(Double(barWidth) * fraction)
        let remainingWidth = barWidth - completedWidth
        
        let completedChars = String(repeating: "█", count: completedWidth)
        let remainingChars = String(repeating: "░", count: remainingWidth)
        
        let progressBar = "[\(completedChars)\(remainingChars)]"
        
        // ETA Calculation (optional, based on Progress object)
        var etaString = ""
        if let remaining = progress.estimatedTimeRemaining, !forceComplete {
            etaString = " ETA: \(formatTimeInterval(remaining))"
        }
        
        // Prepare output string
        let output = "\r\(description): \(progressBar) \(percentage)%\(etaString)"
        
        // Clear previous line and print new one
        let clearLine = String(repeating: " ", count: lastOutputLength)
        Swift.print("\r\(clearLine)\r\(output)", terminator: "")
        lastOutputLength = output.count // Store length for next clear
        fflush(stdout) // Ensure immediate display
    }

    private func formatTimeInterval(_ interval: TimeInterval) -> String {
        guard interval.isFinite && interval > 0 else { return "-:--" }
        let formatter = DateComponentsFormatter()
        formatter.allowedUnits = [.hour, .minute, .second]
        formatter.unitsStyle = .positional
        formatter.zeroFormattingBehavior = .pad
        return formatter.string(from: interval) ?? "-:--"
    }
} 