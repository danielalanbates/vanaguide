# archive/

Empty, deliberately. Nothing written for v0.1.0 was abandoned: everything that was tried is
in the addon and covered by `tools/test_offline.lua`.

Two things were considered and **not** built, which is different from being archived — the
reasoning is in [../docs/PATHWAYS.md](../docs/PATHWAYS.md):

* a world-space marker projected with `IDirect3DDevice8::GetTransform`, because nobody has
  confirmed that path works under DXVK on the Mac port, and
* a hand-written complete zone-line table, because the addon learning zone lines from play
  is honest where a table written from memory would not be.

When something here does get abandoned, move it into this folder with a note saying what it
was for and why it stopped.
