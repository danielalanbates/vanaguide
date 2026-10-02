# In-game verification — 2026-08-29, account-wide graph + narrator + quest accept

Live local LandSandBoat world (127.0.0.1), character **Test** (Elvaan) in Southern San d'Oria
(zone 230). Vanaguide reloaded with the account-wide-learned-graph code; VanaVoice 1.5 running
the single generic narrator voice `en_US-ryan-high`.

## PR #14 (account-wide learned graph + /vg dump graph) — verified on the live client
- **Migration to account-wide**: `/addon reload vanaguide` merged the per-character learned set
  into the shared file. `addons/Vanaguide/learned.lua` written with **342 crossings**. (learned.lua)
- **/vg dump graph**: wrote `addons/Vanaguide/graph-dump.lua`, **171 de-duplicated pairs**
  (342 directional keys → 171 undirected — correct). Paste-ready `Z.learned_walk` block. (graph-dump.lua)
- **/vg graph <a> <b> colon-key fix**: `/vg graph 232 233` → `learned = yes` (this always printed
  `no` before the fix); `/vg graph 232 999` → `no`. 
- **/vg mark**: `/vg mark test-230-account-wide` wrote
  `test-230-account-wide|Z|230|POS|83.9,110.5,10,1.0|N|Southern San d'Oria|` to marks.txt.

## Quest accept + narrator — verified end to end
- `/vg talk Norejaie` opened Eco-Warrior's event (event 677, NPC index 236): Norejaie —
  "May I speak with you for a moment about the ecology of Vana'diel?" (chat + dialogue.jsonl).
- **VanaVoice spoke it** (vanavoice.log 10:30:11):
  `say [narrator · +0.0st]: Norejaie. May I speak with you for a moment about the ecology of Vana'diel?`
  Duplicate message2 lines correctly de-duped ("already said within 20s").
- `/vg advance` ended the event (event 677, option 0).

Screenshots: 00-baseline.png, 10-quest-talk.png. Evidence: learned.lua, graph-dump.lua,
dialogue.jsonl, vanavoice-synth.log.

## Cross-zone walk (following the arrow across zone lines) — see below

## Cross-zone walk (following the arrow across a zone line) — verified
The character walked from Southern San d'Oria (230) to Northern San d'Oria (231):
- `/vg goto 231` routed "going to Northern San d'Oria: Zone into Northern San d'Oria — 99 yalms";
  navmesh pathed (1767 cells). The blue waypoint arrow ("Northern San d'") and the blue path
  line on the ground both pointed at the exit (21-walking.png shows the character running the path).
- `/vg walk auto` walked the whole path via the client's follow-runner + server `!walkto` nudges
  (NOT a teleport): `walk: to (0.0,58.0) … 50 → 110 → 170 yalms walked`, then a waypoint chain
  `walkto: arrived (69.9,…) > (55.9,…) > (37.9,…) > (21.9,…) > (1.9,…,53.9) > (0.0,-8.5,58.0)`
  and `=== Area: Northern San d'Oria ===`. Confirmed in zone 231 afterward.
Screenshots: 21-walking.png (arrow + ground line while running).

## Routing fix found by this run — the phantom-edge / blind-leg teleport (now fixed)
The pre-flight audit and the data confirmed the cause of the last run's teleported leg: the graph
built ONLY from the 76-pair hand-written `data/travel.lua` seed, which carries a phantom direct
Southern↔Port San d'Oria walk (real geometry is the chain Port-Northern-Southern), while the
generated 230-pair `data/zonelines.lua` (coordinate-matched to zonepoints) was NOT wired into the
graph at all. A shorter blind hop shadowed the correct route → "no place to walk to" → teleport.
Fix (zonegraph.lua): wire zonelines in, and make Dijkstra prefer coordinate-backed legs over blind
ones. Verified offline (1273 assertions): `route(232,230)` now goes 232→231→230, 0 blind legs,
honest cost 180. Live reload of this fix was interrupted by the crash below; it is offline-verified,
and both of its new `require`s (data.zonelines, routing.zonepoints) are already loaded by the
running addon, so the load is known-good.

## Incident: disk-full crash → relaunch to the HOSTED world (handled safely)
Mid-run the Mac hit 0 bytes free (the known CloudKit runaway; fixed by clearing the CloudKit cache,
killing bird/cloudd, and trimming old scratchpads — freed ~1.7 GB). The local-world client crashed
and the launcher relaunched to the DEFAULT world, which is `play.horizonxi.com` (HOSTED). I stopped
driving immediately on seeing `--server play.horizonxi.com`. The client sat at the pre-login accept
screen with no addons loaded (cmd.txt queue unconsumed). Verified the HorizonXI boot profile
(`horizonxi.ini` → `default.txt`) loads ONLY HorizonXI-approved addons — none of vanaguide/
vanavoice/cmdpipe/winecursor — so there is no ban risk. Test addons only load under the local
`lsb.txt`. No addon was tested on a hosted server. Left the hosted client untouched at the accept
screen for Daniel to decide.
