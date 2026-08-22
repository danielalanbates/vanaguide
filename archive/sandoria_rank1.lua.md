# archive/sandoria_rank1.lua — retired 2026-08-22, same day it was written

The hand-written *"San d'Oria — Rank 1"* seed guide. Its step text was fine; **its mission
ids were wrong**, which for a linear storyline means a step that waits forever or completes
early. It said Mission 1-1 was id 1 and Bat Hunt was id 2; the server's own enum says
`SMASH_THE_ORCISH_SCOUTS = 0`, `BAT_HUNT = 1`, `SAVE_THE_CHILDREN = 2`.

That is exactly the failure `docs/VERIFICATION.md` warned about under "seed content", and it
is why `tools/gen_missions.py` exists. The generated *"San d'Oria missions — in order"*
guide replaces it with all 24 missions, the real ids, and the coordinates of the NPC each
one starts with.

Kept here because the step *prose* — "kill orcs in Ghelsba Outpost", "collect the bat wings
in King Ranperre's Tomb" — is the walkthrough detail a generator cannot produce. Whoever
writes proper hand-authored mission guides should start from this text and the generated
ids, not from either alone.
