# Center-only navigation experiment

The live private follow test stopped near (-18.3,-125.3), aiming at (-17.6,-128.5). The selected waypoint is outside every original mesh polygon in a static polygon audit. This establishes a grid-padding error at that point, not the complete cause of live collision.

Optional gen_navgrid.py --center-only excludes cells whose centers are outside their source polygon, including subcell slivers. Default behavior remains unchanged. Narrow passages can disconnect; this is an experiment, not the production default.

A private Port San d Oria grid generated at 0.5-yalm spacing has 63,559 occupied cells. The production Lua search still finds a 26-point route to the Northern crossing (4,032 expansions), with intermediate waypoints around the known outside-mesh point. No live pass is claimed. Synthetic triangle, open-interior and sliver regressions pass. No derived grid is published.

Next validate client collision along the route in an isolated local session, then compare connectivity across city grids before considering any default change. Merely retaining a route does not establish its traversability.

Copyright (c) 2026 Daniel Bates / Bates LLC. All rights reserved.
https://batesai.org · help@batesai.org
