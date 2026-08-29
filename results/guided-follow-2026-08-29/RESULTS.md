# Guided run -- guide 10, 2 steps, 2026-08-29 09:21

Walk mode: **follow** (the client's own runner, see docs/WALK.md) with server nudges on the
local world. Narrator: VanaVoice 1.5, one voice. `guided-follow.mp4` is the whole run at 4x
(one captured frame per second); `step44-walking.png` / `step44-talk.png` /
`step45-norejaie.png` are stills from it.

Step 44 was walked (the character had already run 55 yalms to Ceraulian in the
measurement before this run: 27 s, 2 nudges). Step 45 needed Southern San d'Oria and the zone
table has no Port → Southern line, so the harness teleported after its 300 s timeout; the talk
and the narration (3 lines) then went normally. The "talk (attempt 1)" line for step 44 quotes
Arminibit because the harness's pattern matched the word "talk" inside the dialogue; the event
ran on index 72.

Loaded: loaded "San d'Oria - every quest" (59 steps, on step 44)

## Step 44: Chasing Quotas (DRG AF2)
- target: zone=232 pos=(0, -8, -122) npc="Ceraulian" quest=sandoria,95
- before: mode=here dist=0.0 bearing=-136 deg  0 yalms
- walked there: walk: idle (arrived) in 8s
- on arrival: mode=here dist=0.0 bearing=-136 deg  0 yalms
- talk (attempt 1): [66200] Arminibit : You hear more and more talk of the Dragon King Ranperre these days. They say that his top vassal was a dragoon. I wonder what ever happened to all the dragoons...
- NPC said (3 chat lines, 0 narrator lines): [662] Arminibit : You hear more and more talk of the Dragon King Ranperre these days. They say that his top vassal was a dragoon. I wonder what ever happened to all the dragoons...
- advance: advance: event 24 on index 72: end, option 0
- server after advance: Test's status for San d'Oria quest ID 95 is: AVAILABLE
- after !completequest: window=true arrow=true guide=San d'Oria - every quest step=45/59 imgui=true

## Step 45: Eco-Warrior (San d'Oria)
- target: zone=230 pos=(83.9, 1, 110.5) npc="Norejaie" quest=sandoria,97
- before: mode=travel dist=- bearing=- deg  Zone into Southern San d'Oria
- walk did not arrive in 300s (walk: the step has no place to walk to (Zone into Southern San d'Oria)) -- teleporting
- on arrival: mode=here dist=0.0 bearing=180 deg  0 yalms
- talk (attempt 1): talk -> Norejaie (index 236, server id 17719532) at 0.0 yalms
- NPC said (3 chat lines, 3 narrator lines): [662] Norejaie : May I speak with you for a moment about the ecology of Vana'diel?
- advance: advance: event 677 on index 236: end, option 0
- server after advance: Test's status for San d'Oria quest ID 97 is: AVAILABLE
- after !completequest: window=true arrow=true guide=San d'Oria - every quest step=46/59 imgui=true

Done. Screenshots in /Users/daniel/Downloads/vanaguide-repo/results/guided-follow-2026-08-29
