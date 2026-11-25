# Observed walking diagnostics

The prior distance counter integrated requested speed while the client was blocked. Its reported 24 yalms was not proof of actual travel. Active status now reports distance accumulated from position samples, excluding zone transitions and missing-position gaps. This measures sampled displacement, including wall bounce; it does not prove progress along a route or distinguish a same-zone teleport.

Explicit `/vg walk status` additionally prints the movement mode, observed distance, commanded distance, and selected waypoint/source. The last steering snapshot remains available after a stuck stop. These diagnostics add no timer, capture, file output, or periodic chat. They support the next isolated collision/steering investigation.

Verification: stationary commands accumulate zero observed distance; a 3-by-4 displacement measures five yalms; a zone transition adds no distance. Walking contracts, corridor/detour and addon lifecycle checks pass. Live retest is pending; installed apps remain unchanged.

Copyright (c) 2026 Daniel Bates / Bates LLC. All rights reserved.
https://batesai.org · help@batesai.org
