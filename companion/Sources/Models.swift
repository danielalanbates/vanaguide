import Foundation
import Security

// Copyright (c) 2026 Daniel Bates / Bates LLC. All rights reserved.
struct GuideEntry: Codable, Identifiable {
    let id: String
    let kind: String
    let area: String
    let number: Int
    let title: String
    let zone: Int?
    let zoneName: String?
    let npc: String?
    let x: Double?
    let z: Double?
    let y: Double?
    let level: Int?
}

enum Catalog {
    static let entries: [GuideEntry] = {
        guard let url = Bundle.main.url(forResource: "catalog", withExtension: "json"),
              let data = try? Data(contentsOf: url),
              let entries = try? JSONDecoder().decode([GuideEntry].self, from: data) else { return [] }
        return entries.sorted {
            if $0.area != $1.area { return $0.area < $1.area }
            if $0.kind != $1.kind { return $0.kind < $1.kind }
            return $0.number < $1.number
        }
    }()
}

enum APIKey {
    private static let service = "org.batesai.vanaguide.retroachievements"
    private static let account = "web-api-key"

    static func read() -> String {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: account,
            kSecReturnData as String: true,
            kSecMatchLimit as String: kSecMatchLimitOne,
        ]
        var result: CFTypeRef?
        guard SecItemCopyMatching(query as CFDictionary, &result) == errSecSuccess,
              let data = result as? Data else { return "" }
        return String(data: data, encoding: .utf8) ?? ""
    }

    static func save(_ value: String) {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: account,
        ]
        SecItemDelete(query as CFDictionary)
        guard !value.isEmpty else { return }
        var item = query
        item[kSecValueData as String] = Data(value.utf8)
        item[kSecAttrAccessible as String] = kSecAttrAccessibleAfterFirstUnlockThisDeviceOnly
        SecItemAdd(item as CFDictionary, nil)
    }
}

struct Achievement: Identifiable {
    let id: Int
    let set: String
    let title: String
    let detail: String
    let points: Int
    let order: Int
    let earned: Bool
}

@MainActor
final class AchievementStore: ObservableObject {
    @Published private(set) var entries: [Achievement] = []
    @Published private(set) var loading = false
    @Published private(set) var message = ""
    @Published private(set) var refreshed: Date?

    // Every currently populated set in the official HorizonXI hub. Empty future sets are
    // intentionally omitted until RetroAchievements publishes an achievement in them.
    static let sets: [(Int, String)] = [
        (28275, "Final Fantasy XI"),
        (28317, "Rise of the Zilart"),
        (28359, "Chains of Promathia"),
        (28303, "Hero of Nations"),
        (28547, "Hardcore Hero"),
    ]

    func refresh(username: String, key: String) async {
        guard !loading else { return }
        let user = username.trimmingCharacters(in: .whitespacesAndNewlines)
        let token = key.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !user.isEmpty, !token.isEmpty else { message = "Enter a RetroAchievements user and Web API key."; return }
        loading = true
        defer { loading = false }
        var found: [Achievement] = []
        var failures: [String] = []
        for (gameID, label) in Self.sets {
            do {
                var url = URLComponents(string: "https://retroachievements.org/API/API_GetGameInfoAndUserProgress.php")!
                url.queryItems = [
                    URLQueryItem(name: "g", value: String(gameID)),
                    URLQueryItem(name: "u", value: user),
                    URLQueryItem(name: "y", value: token),
                ]
                var request = URLRequest(url: url.url!)
                request.timeoutInterval = 20
                request.setValue("Vanaguide/1.0 (https://batesai.org)", forHTTPHeaderField: "User-Agent")
                let (data, response) = try await URLSession.shared.data(for: request)
                guard let http = response as? HTTPURLResponse, http.statusCode == 200,
                      let root = try JSONSerialization.jsonObject(with: data) as? [String: Any],
                      let rows = root["Achievements"] as? [String: [String: Any]] else {
                    throw NSError(domain: "RetroAchievements", code: gameID,
                                  userInfo: [NSLocalizedDescriptionKey: "No achievement data returned"])
                }
                for (rawID, row) in rows {
                    guard let id = Int(rawID) ?? row["ID"] as? Int,
                          let title = row["Title"] as? String else { continue }
                    let earned = ["DateEarned", "DateEarnedHardcore"].contains {
                        guard let date = row[$0] as? String else { return false }
                        return !date.isEmpty
                    }
                    found.append(Achievement(
                        id: id, set: label, title: title,
                        detail: row["Description"] as? String ?? "",
                        points: row["Points"] as? Int ?? 0,
                        order: row["DisplayOrder"] as? Int ?? 0,
                        earned: earned
                    ))
                }
            } catch {
                failures.append(label)
            }
        }
        // Keep the previous complete list if a network failure would leave an empty screen.
        if !found.isEmpty {
            entries = found.sorted {
                if $0.set != $1.set { return $0.set < $1.set }
                if $0.order != $1.order { return $0.order < $1.order }
                return $0.id < $1.id
            }
            refreshed = Date()
        }
        message = failures.isEmpty ? "" : "Could not refresh: " + failures.joined(separator: ", ")
    }
}
