import AppKit
import ScreenCaptureKit
import Vision

// One user-triggered read of the game window. Never polls, injects, or sends input to FFXI.
// Copyright (c) 2026 Daniel Bates / Bates LLC. All rights reserved.
enum ScreenZoneReader {
    static func detect() async -> (id: Int, name: String)? {
        let options: CGWindowListOption = [.optionAll]
        guard let windows = CGWindowListCopyWindowInfo(options, kCGNullWindowID) as? [[String: Any]] else {
            return nil
        }
        let gameWindow = windows.compactMap { row -> (CGWindowID, Double)? in
            let owner = (row[kCGWindowOwnerName as String] as? String ?? "").lowercased()
            guard owner == "wine" || owner.contains("ffxi") || owner.contains("horizon") else { return nil }
            guard let id = row[kCGWindowNumber as String] as? CGWindowID,
                  let bounds = row[kCGWindowBounds as String] as? [String: Double],
                  let width = bounds["Width"], let height = bounds["Height"],
                  width >= 640, height >= 400 else { return nil }
            return (id, width * height)
        }.max { $0.1 < $1.1 }
        guard let windowID = gameWindow?.0 else { return nil }
        do {
            let content = try await SCShareableContent.excludingDesktopWindows(false, onScreenWindowsOnly: false)
            guard let window = content.windows.first(where: { $0.windowID == windowID }) else { return nil }
            let filter = SCContentFilter(desktopIndependentWindow: window)
            let config = SCStreamConfiguration()
            config.width = Int(window.frame.width * 2)
            config.height = Int(window.frame.height * 2)
            config.showsCursor = false
            let image = try await SCScreenshotManager.captureImage(contentFilter: filter, configuration: config)
            let request = VNRecognizeTextRequest()
            request.recognitionLevel = .accurate
            request.usesLanguageCorrection = false
            try VNImageRequestHandler(cgImage: image, options: [:]).perform([request])
            let lines = (request.results ?? []).compactMap { $0.topCandidates(1).first?.string }
            let names = Dictionary(grouping: Catalog.entries.compactMap { entry -> (Int, String)? in
                guard let id = entry.zone, let name = entry.zoneName, name.count >= 6 else { return nil }
                return (id, name)
            }, by: { $0.0 }).compactMap { $0.value.first }
            // Longer names win when one zone name contains another. Require a full visible
            // phrase; a partial OCR match could silently point the arrow to the wrong world.
            return names.filter { candidate in
                let target = candidate.1.lowercased()
                return lines.contains { line in
                    let text = line.trimmingCharacters(in: .whitespacesAndNewlines).lowercased()
                    return text == target || text == "zone: " + target || text == "area: " + target
                }
            }.max { $0.1.count < $1.1.count }
        } catch {
            return nil
        }
    }
}
