#!/usr/bin/env python3
# Copyright (c) 2026 Daniel Bates / Bates LLC. All rights reserved.
"""Package only tracked addon code/static data, never local character settings."""
import argparse, hashlib, subprocess, zipfile
from pathlib import Path
root = Path(__file__).resolve().parents[1]
p = argparse.ArgumentParser()
p.add_argument('output', type=Path)
a = p.parse_args()
files = subprocess.check_output(['git', '-C', str(root), 'ls-files', '-z', 'Vanaguide'], text=True).split('\0')
a.output.parent.mkdir(parents=True, exist_ok=True)
with zipfile.ZipFile(a.output, 'w', zipfile.ZIP_DEFLATED) as z:
    for name in files:
        if name and name.endswith('.lua'):
            z.write(root / name, name)
    for name in ['LICENSE', 'docs/SERVERS.md', 'docs/NM-DETAILS.md']:
        z.write(root / name, name)
    z.writestr('START HERE.txt', '''VanaGuide (Beta) - Windows Ashita v4 addon\r\n\r\nThis is the in-game Ashita addon, not the standalone macOS companion.\r\nRequires Windows, FFXI and an existing working Ashita v4 installation.\r\n1. Close the addon if loaded.\r\n2. Copy the included Vanaguide folder into Ashita's addons folder.\r\n3. In your own local LSB game, enter /addon load vanaguide, then /vg.\r\nDo not run it on a hosted server without that server's approval.\r\nHorizonXI has not approved this addon. Use the macOS external companion there.\r\nThe native companion's settings, search and step-star UI are not in this addon.\r\nVerified by offline Lua checks; no Windows gameplay validation for this release.\r\nHelp: help@batesai.org | https://batesai.org\r\n''')
print(a.output, hashlib.sha256(a.output.read_bytes()).hexdigest())
