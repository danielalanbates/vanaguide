import SwiftUI
import Combine

// Copyright (c) 2026 Daniel Bates / Bates LLC. All rights reserved.
@main
struct VanaguideCompanionApp: App {
    var body: some Scene {
        WindowGroup("Vanaguide") { CompanionView().frame(minWidth: 860, minHeight: 550) }
            .windowResizability(.contentMinSize)
    }
}

struct CompanionView: View {
    @AppStorage("completedGuideIDs") private var completedJSON = "[]"
    @AppStorage("currentZone") private var currentZone = 230
    @AppStorage("currentX") private var currentX = 0.0
    @AppStorage("currentZ") private var currentZ = 0.0
    @AppStorage("raUsername") private var username = ""
    @State private var apiKey = APIKey.read()
    @State private var search = ""
    @State private var selectedID: String?
    @State private var page = 0
    @State private var showEarned = false
    @State private var screenStatus = ""
    @State private var screenBusy = false
    @StateObject private var achievements = AchievementStore()
    private let refreshTick = Timer.publish(every: 300, on: .main, in: .common).autoconnect()

    private var completed: Set<String> {
        guard let data = completedJSON.data(using: .utf8),
              let values = try? JSONDecoder().decode([String].self, from: data) else { return [] }
        return Set(values)
    }

    private var filtered: [GuideEntry] {
        let needle = search.trimmingCharacters(in: .whitespacesAndNewlines)
        if needle.isEmpty { return Catalog.entries }
        return Catalog.entries.filter {
            $0.title.localizedCaseInsensitiveContains(needle) ||
            $0.area.localizedCaseInsensitiveContains(needle) ||
            ($0.zoneName?.localizedCaseInsensitiveContains(needle) ?? false) ||
            ($0.npc?.localizedCaseInsensitiveContains(needle) ?? false)
        }
    }

    private var selected: GuideEntry? {
        Catalog.entries.first { $0.id == selectedID }
    }

    var body: some View {
        VStack(spacing: 0) {
            HStack {
                Text("VANAGUIDE").font(.system(size: 22, weight: .semibold, design: .serif))
                Spacer()
                Picker("", selection: $page) {
                    Text("Guide").tag(0)
                    Text("Achievements").tag(1)
                }.pickerStyle(.segmented).frame(width: 260)
            }.padding()
            Divider()
            if page == 0 { guidePage } else { achievementPage }
        }
        .task {
            if !username.isEmpty && !apiKey.isEmpty {
                await achievements.refresh(username: username, key: apiKey)
            }
        }
        .onReceive(refreshTick) { _ in
            guard !username.isEmpty, !apiKey.isEmpty else { return }
            Task { await achievements.refresh(username: username, key: apiKey) }
        }
    }

    private var guidePage: some View {
        HStack(spacing: 0) {
            VStack(spacing: 8) {
                TextField("Find quest, mission, NPC or zone", text: $search)
                    .textFieldStyle(.roundedBorder).padding([.top, .horizontal], 12)
                Text("\(completed.count) / \(Catalog.entries.count) complete")
                    .font(.caption).foregroundStyle(.secondary)
                List(filtered, selection: $selectedID) { entry in
                    HStack {
                        Image(systemName: completed.contains(entry.id) ? "checkmark.circle.fill" : "circle")
                            .foregroundStyle(completed.contains(entry.id) ? .green : .secondary)
                        VStack(alignment: .leading) {
                            Text(entry.title).lineLimit(1)
                            Text("\(entry.kind.capitalized) · \(entry.area.capitalized)")
                                .font(.caption2).foregroundStyle(.secondary)
                        }
                    }.tag(entry.id)
                }
            }.frame(width: 350)
            Divider()
            if let entry = selected {
                ScrollView {
                    VStack(alignment: .leading, spacing: 16) {
                        Text(entry.title).font(.title2)
                        Text("\(entry.kind.capitalized) · \(entry.area.capitalized) #\(entry.number)")
                            .foregroundStyle(.secondary)
                        if let level = entry.level { Text("Level \(level)+") }
                        if let zone = entry.zone, let name = entry.zoneName {
                            Text("Go to \(name) (zone \(zone))").font(.headline)
                        } else {
                            Text("No location recorded for this step.").foregroundStyle(.secondary)
                        }
                        if let npc = entry.npc { Text("Talk to \(npc)") }
                        if let x = entry.x, let z = entry.z {
                            Text(String(format: "Target: X %.1f, Z %.1f", x, z))
                                .monospacedDigit()
                            if currentZone == entry.zone {
                                let dx = x - currentX, dz = z - currentZ
                                let distance = hypot(dx, dz)
                                HStack {
                                    Image(systemName: "arrow.up")
                                        .font(.system(size: 38, weight: .semibold))
                                        .rotationEffect(.degrees(atan2(dx, -dz) * 180 / .pi))
                                    Text(String(format: "%.0f yalms · %@", distance, direction(dx: dx, dz: dz)))
                                        .font(.headline)
                                }
                            }
                        }
                        Button(completed.contains(entry.id) ? "Mark unfinished" : "Mark done") {
                            var ids = completed
                            if ids.contains(entry.id) { ids.remove(entry.id) }
                            else { ids.insert(entry.id) }
                            if let data = try? JSONEncoder().encode(ids.sorted()),
                               let value = String(data: data, encoding: .utf8) { completedJSON = value }
                        }
                        Divider()
                        Text("Your position").font(.headline)
                        HStack {
                            TextField("Zone ID", value: $currentZone, format: .number).frame(width: 110)
                            TextField("X", value: $currentX, format: .number).frame(width: 100)
                            TextField("Z", value: $currentZ, format: .number).frame(width: 100)
                        }.textFieldStyle(.roundedBorder)
                        Button("Read game screen") {
                            screenBusy = true
                            Task {
                                if let zone = await ScreenZoneReader.detect() {
                                    currentZone = zone.id
                                    screenStatus = "Detected \(zone.name)"
                                } else {
                                    screenStatus = "No zone name found on the game screen."
                                }
                                screenBusy = false
                            }
                        }.disabled(screenBusy)
                        if !screenStatus.isEmpty { Text(screenStatus).font(.caption) }
                        Text("Enter X and Z from the game. Screen reading only works when a zone name is visible; the companion never sends input to FFXI.")
                            .font(.caption).foregroundStyle(.secondary)
                    }.frame(maxWidth: .infinity, alignment: .leading).padding(24)
                }
            } else {
                ContentUnavailableView("Choose a quest or mission", systemImage: "map")
            }
        }
    }

    private func direction(dx: Double, dz: Double) -> String {
        if hypot(dx, dz) < 2 { return "at target" }
        let eastWest = abs(dx) > 2 ? (dx > 0 ? "east" : "west") : ""
        let northSouth = abs(dz) > 2 ? (dz > 0 ? "south" : "north") : ""
        return [northSouth, eastWest].filter { !$0.isEmpty }.joined(separator: "-")
    }

    private var achievementPage: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                TextField("RetroAchievements username", text: $username)
                    .textFieldStyle(.roundedBorder).frame(width: 200)
                SecureField("Web API key", text: $apiKey)
                    .textFieldStyle(.roundedBorder).frame(width: 260)
                Button("Save & refresh") {
                    APIKey.save(apiKey)
                    Task { await achievements.refresh(username: username, key: apiKey) }
                }
                .disabled(achievements.loading)
                if achievements.loading { ProgressView().controlSize(.small) }
            }
            HStack {
                Text("\(achievements.entries.filter(\.earned).count) / \(achievements.entries.count) unlocked")
                Toggle("Show unlocked", isOn: $showEarned).toggleStyle(.checkbox)
                Spacer()
                if let date = achievements.refreshed {
                    Text("Updated \(date.formatted(date: .omitted, time: .shortened))")
                        .foregroundStyle(.secondary)
                }
            }.font(.caption)
            if !achievements.message.isEmpty {
                Text(achievements.message).font(.caption).foregroundStyle(.orange)
            }
            List(achievements.entries.filter { showEarned || !$0.earned }) { achievement in
                HStack(alignment: .top, spacing: 10) {
                    Image(systemName: achievement.earned ? "checkmark.circle.fill" : "circle")
                        .foregroundStyle(achievement.earned ? .green : .secondary)
                    VStack(alignment: .leading, spacing: 3) {
                        Text(achievement.title).font(.headline)
                        Text(achievement.detail).font(.caption).foregroundStyle(.secondary)
                        Text("\(achievement.set) · \(achievement.points) points")
                            .font(.caption2).foregroundStyle(.secondary)
                    }
                    Spacer()
                }.padding(.vertical, 3)
            }
            Text("Live unlocks come from RetroAchievements. The API key stays in this Mac's Keychain.")
                .font(.caption).foregroundStyle(.secondary)
        }.padding(16)
    }
}
