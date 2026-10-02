#!/bin/zsh
# Build the read-only companion and keep the previous Applications copy until verification.
# Copyright (c) 2026 Daniel Bates / Bates LLC. All rights reserved.
set -euo pipefail
HERE="${0:A:h}"
REPO="${HERE:h}"
OUT="${VG_OUT:-$REPO/companion/build}"
APP="$OUT/Vanaguide.app"
SCRATCH="$OUT/.swift-build"
mkdir -p "$OUT" "$HERE/Resources"
cd "$REPO"
luajit tools/export_companion.lua companion/Resources/catalog.json
cd "$HERE"
swift build -c release --scratch-path "$SCRATCH"
BIN="$SCRATCH/release/VanaguideCompanion"
[[ -x "$BIN" ]] || { print -u2 "build produced no app binary"; exit 1; }
rm -rf "$APP"
mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources"
cp "$BIN" "$APP/Contents/MacOS/Vanaguide"
cp "$HERE/Resources/catalog.json" "$APP/Contents/Resources/catalog.json"
cat > "$APP/Contents/Info.plist" <<'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
<key>CFBundleName</key><string>Vanaguide</string>
<key>CFBundleDisplayName</key><string>Vanaguide</string>
<key>CFBundleExecutable</key><string>Vanaguide</string>
<key>CFBundleIdentifier</key><string>org.batesai.vanaguide.companion</string>
<key>CFBundlePackageType</key><string>APPL</string>
<key>CFBundleShortVersionString</key><string>0.3.0</string>
<key>CFBundleVersion</key><string>3</string>
<key>LSMinimumSystemVersion</key><string>14.0</string>
<key>NSHighResolutionCapable</key><true/>
<key>NSScreenCaptureUsageDescription</key><string>Vanaguide reads a visible zone name from the Final Fantasy XI window when you press Read game screen.</string>
</dict></plist>
PLIST
find "$APP" -exec xattr -c {} \; 2>/dev/null || true
codesign --force -s - "$APP"
codesign --verify --strict "$APP"

if [[ "${VG_INSTALL:-1}" == "1" ]]; then
  DEST=/Applications/Vanaguide.app
  PENDING=/Applications/.Vanaguide.pending.app
  rm -rf "$PENDING"
  ditto "$APP" "$PENDING"
  codesign --verify --strict "$PENDING"
  if [[ -d "$DEST" ]]; then
    mkdir -p "$OUT/archive"
    ditto "$DEST" "$OUT/archive/Vanaguide-$(date +%Y%m%d-%H%M%S).app"
    rm -rf "$DEST"
  fi
  mv "$PENDING" "$DEST"
  print "installed $DEST"
fi
print "built $APP"
