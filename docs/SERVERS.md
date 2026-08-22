# Before you load this on a private server

On most FFXI private servers, running an addon the server has not approved is a bannable
offence, and the lists are published and enforced. **Vanaguide is on nobody's list**,
because it was written this week.

As of 2026-08-22, from the allowlists the FFXI-on-Mac launcher cites:

| server | Vanaguide allowed? |
| --- | --- |
| HorizonXI | **no** — it publishes an allowlist (horizonxi.info/addons) and Vanaguide is not on it |
| CatsEyeXI | **no** — same, their wiki's approved list |
| FFEra | **no** — same |
| Your own LandSandBoat world | yes — it is your world |
| Eden, Supernova, ValhallaXI, OmicronXI, Gaia XI, Tabula Rasa XI | unknown — no published list to check |

"Unknown" means *ask them*, not *probably fine*.

Nothing in Vanaguide automates play: it does not move your character, target, cast, or send
a packet of any kind. It reads the log the server already sent you and draws on your own
screen. That is a reasonable case to make to a server admin, and making it is how the top
row of that table changes. It is not a reason to load it and hope.

The FFXI-on-Mac launcher will not offer Vanaguide on a server whose allowlist excludes it,
and that filtering is deliberate — see that project's `docs/ADDON-POLICY.md`.
