// swift-tools-version:5.9
import PackageDescription

let package = Package(
    name: "VanaguideCompanion",
    platforms: [.macOS(.v14)],
    targets: [.executableTarget(name: "VanaguideCompanion", path: "Sources")]
)
