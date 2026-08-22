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

rm -rf "$target/addons/Vanaguide"
mkdir -p "$target/addons/Vanaguide"
cp -R "$here/Vanaguide/." "$target/addons/Vanaguide/"
echo "installed -> $target/addons/Vanaguide"
echo "now: /addon load vanaguide   then   /vg"
echo
echo "NOTE: check the server's addon policy first — see docs/SERVERS.md."
