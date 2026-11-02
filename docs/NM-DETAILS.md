# NM source coverage (beta 112)

The native companion displays NM details beside matching gear drop sources and in monster
search results. `data/nm_details.lua` contains 3,567 standard LSB name/zone records, with
full decimal IDs, zone-local hexadecimal IDs, SQL spawn coordinates, and lottery/placeholder
information where the source script can be resolved. Coordinates are reference spawn points,
not guaranteed camp boundaries. Missing spawn rules are explicitly marked undocumented.
This is not exhaustive wiki verification of every NM.

`data/servers/<server>/nm_details.lua` overrides individual name/zone records. The Horizon
Tom Tit Tat record supplies wiki camp grids and distinguishes the wiki's local placeholder
IDs from standard LSB full IDs. Its wiki source contains malformed full placeholder IDs;
these are not repeated as verified Horizon IDs. No respawn timer is invented.

Regenerate standard data with `python3 -B tools/gen_nm_details.py /path/to/public/LSB`.
The generator pins source URLs to the checkout commit. Preserve authored server overrides.

Public Windows download is the existing Ashita v4 addon, not the macOS SwiftUI companion.
It requires an already configured Ashita installation and explicit server permission; it is
not an approved Horizon addon. The native macOS interface changes are not Windows parity.
