# Recover generated route wiring

Copyright © 2026 Daniel Bates / Bates LLC. All rights reserved.
[batesai.org](https://batesai.org) · help@batesai.org

The bounded private LSB walkthrough accepted its first quest in Port San d'Oria, then the
next Northern San d'Oria step recommended West Ronfaure without an arrow target. Walking
correctly refused because that recommended leg had no coordinate. This was a routing defect,
not evidence that a coordinate should be guessed or that a new grid was required.

Both the shipped coordinate table and the private fixture's static `zonelines.sql` already
record the Port (232) → Northern (231) crossing. The SQL position is x=-111.802,
z=-136.498, y=-11.876; the generated table rounds these to one decimal place. The graph
ignored both generated routing tables and used the old hand-written travel seed alone.
That seed omitted the real crossing and included nonexistent Port → West Ronfaure and
Port → Southern shortcuts. The previously implemented generated-graph wiring existed on
other Git history branches, but was absent from the current guide beta lineage.

Recovered the relevant graph behavior without changing generated coordinates:

- Load directed generated exits, including event doors, and the generated pair fallback
  for zones without coordinate coverage. Known one-way exits gain no invented return edge.
- Exclude hand-written shortcuts contradicted by generated data; retain uncovered custom
  zones and observation-based learning.
- Load generated transit gaps while preserving authored pass requirements and wait costs.
- Deduplicate edges and increment the graph version after every rebuild. The router uses
  this version to invalidate cached answers when a new crossing is learned.

`luajit tools/test_zonegraph.lua` now passes 16 checks against the real shipped tables and
small synthetic direction/fallback fixtures. The original graph fails the first actual
Port → Northern route assertion. Tests verify a direct crossing, an arrow target with
bearing/distance, routes through Northern instead of phantom shortcuts, distant generated
crossings, event doors, transit requirements and learned-route cache invalidation. The
existing 1,418 offline assertions, walking contracts and navigation smoothing checks also
pass. No game, database or app was started by these checks.

The private walkthrough is still partial acceptance evidence. These offline results do not
prove an actual unassisted city crossing, visual arrow rendering or audible narration.
Rebuild the beta bundle with this clean guide revision, then repeat the guarded local route
when the Mac is available. Keep the public app release behind its stability gates.
