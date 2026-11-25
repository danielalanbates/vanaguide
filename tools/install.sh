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
# through, verify.csv is a sweep's results and marks.txt is what /vg mark wrote. Wiping the
# folder mid-sweep throws away the run and leaves the driver writing commands into a file
# nothing reads.
#
# data/nav is kept for a different reason: it is minutes of work per install, it is not in
# this repository and never will be (docs/NAVMESH.md), and re-copying the addon after a
# one-line fix should not silently throw away every navigation grid on the machine.
dest="$target/addons/Vanaguide"
keep=$(mktemp -d)
for f in cmd.txt verify.csv marks.txt; do
    if [ -f "$dest/$f" ]; then cp "$dest/$f" "$keep/$f"; fi
done
if [ -d "$dest/data/nav" ]; then cp -R "$dest/data/nav" "$keep/nav"; fi
rm -rf "$dest"
mkdir -p "$dest"
cp -R "$here/Vanaguide/." "$dest/"
for f in cmd.txt verify.csv marks.txt; do
    if [ -f "$keep/$f" ]; then cp "$keep/$f" "$dest/$f"; fi
done
if [ -d "$keep/nav" ]; then
    mkdir -p "$dest/data"
    rm -rf "$dest/data/nav"
    cp -R "$keep/nav" "$dest/data/nav"
fi
rm -rf "$keep"
echo "installed -> $dest"
echo "now: /addon load vanaguide   then   /vg"
echo
echo "NOTE: check the server's addon policy first — see docs/SERVERS.md."
