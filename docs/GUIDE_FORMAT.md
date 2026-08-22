# Writing a Vanaguide guide

A guide is a Lua file in `Vanaguide/guides/` that calls `G.register{...}` and lists its
steps as lines of text. One line, one step.

```lua
local G = require('core.guide')

G.register({
    name   = "San d'Oria — Rank 1",
    author = 'you',
    nation = 'sandoria',
    levels = '1-10',
    steps  = [[
t Take a mission from the Gate Guard|Z|230|POS|-140,120,8|N|By the fountain.|
C Mission 1-1: kill orcs in Ghelsba Outpost|M|sandoria,1|Z|140|
]],
})
```

Add the file's name to `guides/init.lua`.

## The line

    <verb><space><text shown to the player>|TAG|value|TAG|value|

### Verbs

| | |
| --- | --- |
| `A` | accept a quest / mission |
| `T` | turn one in |
| `C` | complete an objective |
| `K` | kill something |
| `B` | buy something |
| `t` | talk to someone |
| `R` | run to a place — completes on arrival |
| `U` | use an item |
| `F` | travel (airship, ferry) — completes on arrival |
| `N` | a note; never completes on its own |
| `L` | reach a level |

### Tags

| tag | meaning |
| --- | --- |
| `Z` | zone: an id (`230`) or a name (`Southern San d'Oria`, `Port_Jeuno`) |
| `POS` | `x,z[,radius]` inside that zone; radius defaults to 10 yalms |
| `M` | `area,id` — done when that mission is finished |
| `Q` | `area,id` — done when that quest is completed |
| `QA` | `area,id` — done when that quest is *accepted* |
| `KI` | key item id |
| `IT` | `item id[,count]` |
| `LV` | level |
| `JOB` | `job id,level` |
| `RANK` | nation rank |
| `SP` | spell id |
| `N` | note, shown under the step |
| `FIXED` | never auto-complete; always wait for the player |

`area` is a quest-log page name: `sandoria bastok windurst jeuno other outlands wotg
abyssea adoulin coalition`, and for missions also `zilart cop acp mkd asa adoulin rov`.

A step with **no** completion tag waits for the player to click Done — except `R` and `F`
steps, which complete when the player reaches the `POS`.

## Coordinates

Do not write coordinates you have not stood on. Stand where the step wants the player to
be, type

    /vg mark Talk to the gate guard

and Vanaguide appends a finished line to `<install>/addons/Vanaguide/marks.txt`:

    Talk to the gate guard|Z|230|POS|-142.6,118.9,10|N|Southern San d'Oria, y=-2.0|

Paste it into the guide and replace the note. FFXI's `X` is east/west, `Z` is north/south,
`Y` is height; Vanaguide only ever measures horizontal distance, so `Y` is recorded in the
note for context and otherwise ignored.

## Style

* One action per step. "Kill three orcs and come back" is two steps.
* Prefer a tag the server can answer over a manual step — that is the whole point.
* Say *where*, not just *what*: a step with `Z` gets a route; a step with `Z`+`POS` gets an
  arrow.
