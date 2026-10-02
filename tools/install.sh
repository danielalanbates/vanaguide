#!/bin/sh
# Vanaguide :: tools/install.sh — copy the addon into an Ashita install.
#
#   tools/install.sh "/path/to/FFXI"        # <path>/addons/Vanaguide
#
# Copyright (c) 2026 Bates LLC.  All rights reserved.
set -eu

here=$(cd "$(dirname "$0")/.." && pwd)
target=${1:-}

if [ -z "$target" ]; then
    echo "usage: tools/install.sh <path to your FFXI install>" >&2
    exit 2
fi
if [ ! -d "$target/addons" ]; then
    echo "no addons/ folder in $target — is that an Ashita install?" >&2
    exit 1
fi

# The addon folder is not only code: cmd.txt is the channel a script drives the client
# through, and verify.csv is a sweep's results. Wiping the folder mid-sweep throws away the
# run and leaves the driver writing commands into a file nothing reads.
#
# data/nav is kept for a different reason: it is minutes of work per install, it is not in
# this repository and never will be (docs/NAVMESH.md), and re-copying the addon after a
# one-line fix should not silently throw away every navigation grid on the machine.
dest="$target/addons/Vanaguide"
keep=$(mktemp -d)
for f in cmd.txt verify.csv marks.txt; do
    [ -f "$dest/$f" ] && cp "$dest/$f" "$keep/$f"
done
[ -d "$dest/data/nav" ] && cp -R "$dest/data/nav" "$keep/nav"
rm -rf "$dest"
mkdir -p "$dest"
cp -R "$here/Vanaguide/." "$dest/"
for f in cmd.txt verify.csv marks.txt; do
    [ -f "$keep/$f" ] && cp "$keep/$f" "$dest/$f"
done
[ -d "$keep/nav" ] && mkdir -p "$dest/data" && cp -R "$keep/nav" "$dest/data/nav"
rm -rf "$keep"
echo "installed -> $dest"
echo "now: /addon load vanaguide   then   /vg"
echo
echo "NOTE: check the server's addon policy first — see docs/SERVERS.md."
