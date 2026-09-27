-- Vanaguide :: tools/test_achievements.lua
-- RetroAchievements: generating data/achievements.lua from the fixtures, the guides built from
-- it, how confident each mapping is, and reading the launcher's progress snapshot (present,
-- missing, stale, malformed).  Offline: the fixtures in tools/fixtures/ra are documented-shape
-- samples, not RetroAchievements data, and nothing here touches the network.
--
--   luajit tools/test_achievements.lua          (from the repository root; needs python3)
--
-- Copyright (c) 2026 Bates LLC.  All rights reserved.

package.path = 'Vanaguide/?.lua;Vanaguide/?/init.lua;' .. package.path
dofile('tools/stubs.lua')

local pass, fail = 0, 0
local function ok(cond, what)
    if cond then pass = pass + 1 else fail = fail + 1; print('FAIL: ' .. what) end
end
local function eq(a, b, what)
    if a == b then pass = pass + 1
    else fail = fail + 1; print(('FAIL: %s (got %s, want %s)'):format(what, tostring(a), tostring(b))) end
end

local function run(cmd)
    local r = os.execute(cmd)
    return r == 0 or r == true
end
local function slurp(path)
    local f = io.open(path, 'rb')
    if f == nil then return nil end
    local t = f:read('*a')
    f:close()
    return t
end
local function spit(path, text)
    local f = assert(io.open(path, 'wb'))
    f:write(text)
    f:close()
end

local FIXTURES = 'tools/fixtures/ra'
local GAMES = '--game-id 28275 --game-id 28317 --game-id 28303'
local tmp = {}
local function tmpfile() local p = os.tmpname(); tmp[#tmp + 1] = p; return p end

-- ---- generation from fixtures ------------------------------------------------------------
local out1, out2 = tmpfile(), tmpfile()
ok(run(('python3 tools/gen_achievements.py --fixture %s %s --out %s 2>/dev/null'):format(FIXTURES, GAMES, out1)),
   'gen_achievements.py runs from fixtures')
ok(run(('python3 tools/gen_achievements.py --fixture %s %s --out %s 2>/dev/null'):format(FIXTURES, GAMES, out2)),
   'and runs again')
local text1 = slurp(out1)
ok(text1 ~= nil and #text1 > 0, 'it wrote a file')
eq(text1, slurp(out2), 'the output is deterministic: two runs, identical bytes')
ok(text1:find('Copyright (c) 2026 Bates LLC. All rights reserved.', 1, true) ~= nil, 'the file carries the header')
ok(text1:find('NOT RetroAchievements data', 1, true) ~= nil, 'a fixture build says so in its header')

local A = assert(loadstring(text1))()
eq(#A.sets, 3, 'three sets from three fixtures')
eq(A.sets[1].game_id, 28275, 'sets keep the order given: base game first')
eq(A.sets[2].game_id, 28317, 'then Zilart')
eq(A.sets[3].game_id, 28303, 'then the Hero of Nations subset')
eq(A.sets[3].name, 'Hero of Nations', 'a subset is named by its subset title')
eq(A.sets[3].set_id, 9299, 'and carries its known set id')
eq(A.sets[2].parent_id, 28275, 'a subset records its parent game')
eq(#A.sets[1].achievements, 11, 'every base achievement is listed')
eq(A.sets[1].achievements[1].id, 900101, 'achievements are in display order')
eq(A.sets[1].points, 116, 'set points are the sum')

local a = A.get(900102)
eq(a.title, 'Squire No More', 'title')
eq(a.points, 10, 'points')
eq(a.type, 'progression', 'type')
eq(a.badge, '500102', 'badge name')
eq(a.game_id, 28275, 'game id per achievement')
eq(A.get(900104).type, nil, 'a null type stays nil')
eq(A.get(900107).type, 'missable', 'missable type')
eq(A.get(900111).description, 'A title with a pipe - and a deja vu', 'text is folded to what the fonts can draw')
eq(A.get(900106).description, "Set foot in Ru'Aun Gardens", 'typographic apostrophes become plain ones')

-- ---- mapping confidence --------------------------------------------------------------------
local m = A.get(900102).map
ok(m ~= nil and m.kind == 'quest' and m.area == 'sandoria' and m.id == 29, "a quoted quest name maps to that quest (A Knight's Test)")
eq(m.confidence, 0.9, 'with high confidence')
eq(m.method, 'quoted-name', 'by the quoted-name rule')
eq(m.zone, 230, 'and carries where the quest starts')
m = A.get(900103).map
ok(m.kind == 'mission' and m.area == 'sandoria' and m.id == 2, "San d'Oria Mission 1-3 maps by its number")
eq(m.method, 'nation-mission-number', 'by the nation-mission rule')
m = A.get(900302).map
ok(m.kind == 'mission' and m.area == 'bastok' and m.id == 9,
   'a multi-part mission (Bastok 2-3) completes on its last id, whichever route was taken')
eq(m.zone, 236, 'but points at where its first part starts')
m = A.get(900104).map
ok(m.kind == 'job' and m.job == 7 and m.level == 30, 'level 30 as a Paladin maps to JOB 7,30')
m = A.get(900101).map
ok(m.kind == 'level' and m.level == 10, 'reach level 10 maps to LV 10')
m = A.get(900108).map
ok(m.kind == 'rank' and m.rank == 3, 'reach rank 3 maps to RANK 3')
m = A.get(900105).map
ok(m.kind == 'nm' and m.zone == 75 and m.x ~= nil, 'a named notorious monster maps to its spawn')
ok(m.confidence >= A.complete_at, 'confidently')
m = A.get(900106).map
ok(m.kind == 'zone' and m.zone == 130, 'a zone named in the text is a place')
ok(m.confidence < A.complete_at, 'but only a hint')
m = A.get(900109).map
ok(m ~= nil and m.confidence < A.complete_at and m.method:find('rival'),
   'two different quoted targets are a rival pair: kept as a place, never a condition')
eq(A.get(900110).map, nil, 'a monster name spread across zones, with nothing else to go on, is left unmapped')
eq(A.get(900107).map, nil, 'a description that names nothing stays unmapped')
eq(A.get(900203).map, nil, 'so does one that only describes a place in words')
m = A.get(900202).map
ok(m.kind == 'mission' and m.area == 'zilart' and m.id == 26, 'an achievement titled with a mission name maps to it')

-- ---- no key: a clean refusal, nothing written ---------------------------------------------
do
    local out = tmpfile()
    os.remove(out)
    local cmd = ('env -u RETROACHIEVEMENTS_API_KEY RETROACHIEVEMENTS_KEYCHAIN_SERVICE=vanaguide-test-no-such-item '
        .. 'python3 tools/gen_achievements.py --out %s > %s.err 2>&1'):format(out, out)
    ok(not run(cmd), 'without a key the generator fails')
    local err = slurp(out .. '.err') or ''
    ok(err:find('no web API key', 1, true) ~= nil, 'and says the key is missing: ' .. err)
    eq(slurp(out), nil, 'and writes nothing')
    os.remove(out .. '.err')
end

-- ---- hand overrides win -------------------------------------------------------------------
do
    local ov, out = tmpfile(), tmpfile()
    spit(ov, '{"_comment": "test", "900107": {"kind": "key_item", "ki": 123, "name": "Test Key"}}')
    ok(run(('python3 tools/gen_achievements.py --fixture %s --game-id 28275 --overrides %s --out %s 2>/dev/null')
        :format(FIXTURES, ov, out)), 'generation with an overrides file')
    local B = assert(loadstring(slurp(out)))()
    local mo = B.get(900107).map
    ok(mo ~= nil and mo.kind == 'key_item' and mo.ki == 123, 'an override maps an achievement nothing else could')
    ok(mo and mo.confidence == 1.0 and mo.method == 'override', 'with full confidence, labelled as an override')
    eq(require('guides.achievements').step_line(B.get(900107), B.complete_at),
       'C Behind the Curtain|KI|123||RA|900107||N|Witness a secret that few adventurers ever see (25 points) Missable.|',
       'and its step waits on the key item')
end

-- ---- the shipped placeholder -----------------------------------------------------------
do
    local shipped = require('data.achievements')
    eq(type(shipped.sets), 'table', 'the shipped data file loads')
    local RAG = require('guides.achievements')
    eq(#RAG.guides, #shipped.sets, 'one shipped guide per shipped set (none until a key has been used)')
end

-- ---- the guide builder ---------------------------------------------------------------------
local G = require('core.guide')
local C = require('core.conditions')
local P = require('core.progress')
local RAG = require('guides.achievements')
require('guides.init')
local before = {}
for i, g in ipairs(G.list()) do before[i] = g.name end
local built = RAG.build(A)
eq(#built, 3, 'one guide per set')
local list = G.list()
eq(#list, #before + 3, 'appended to the list')
for i, name in ipairs(before) do
    if list[i].name ~= name then fail = fail + 1; print('FAIL: guide numbering moved at ' .. i) break end
end
pass = pass + 1
eq(list[#before + 1].name, 'RetroAchievements - Final Fantasy XI', 'the base set guide comes first after the others')
eq(list[#before + 3].name, 'RetroAchievements - Hero of Nations', 'subset guides are named by the subset')
ok(RAG.is_achievement_guide(list[#before + 1]), 'is_achievement_guide knows its own')
ok(not RAG.is_achievement_guide(list[1]), 'and nobody else')

local base = G.get('RetroAchievements - Final Fantasy XI')
eq(#base.errors, 0, 'the base guide parses cleanly')
eq(#base.steps, 11, 'one step per achievement')
for _, g in ipairs(built) do
    eq(#g.errors, 0, g.name .. ' parses cleanly')
    for _, s in ipairs(g.steps) do ok(s.ra ~= nil, g.name .. ' step ' .. s.index .. ' carries its achievement id') end
end
local function step_of(id)
    for _, g in ipairs(built) do
        for _, s in ipairs(g.steps) do if s.ra == id then return s end end
    end
end
local s = step_of(900102)
eq(s.text, 'Squire No More', 'step text is the title')
ok(s.note:find('Complete the quest', 1, true) and s.note:find('(10 points)', 1, true), 'note is description + points')
ok(s.quest ~= nil and s.quest.area == 'sandoria' and s.quest.id == 29, 'a confident quest mapping gets its Q tag')
ok(s.zone == 230 and s.pos ~= nil, 'and a place for the arrow and the line')
s = step_of(900103)
ok(s.mission ~= nil and s.mission.id == 2, 'a confident mission mapping gets its M tag')
s = step_of(900104)
ok(s.job ~= nil and s.job.id == 7 and s.job.level == 30 and s.kind == 'level', 'job mapping: JOB tag, level verb')
s = step_of(900108)
eq(s.rank, 3, 'rank mapping: RANK tag')
s = step_of(900105)
ok(s.kind == 'kill' and s.zone == 75 and s.pos.r == 20, 'a monster step is a kill with a wide marker')
ok(not C.is_automatic(s), 'which the player ticks off')
s = step_of(900106)
ok(s.zone == 130 and not C.is_automatic(s), 'a hint gives a zone but no condition')
ok(s.note:find('Possibly: Ru', 1, true) ~= nil, 'and says it is a guess')
s = step_of(900109)
ok(s.quest == nil and s.mission == nil and s.zone == 230, 'a rival mapping gives a place but no condition')
s = step_of(900107)
ok(s.zone == nil and not C.is_automatic(s) and s.kind == 'complete', 'an unmapped achievement is a manual step')
ok(s.note:find('Missable.', 1, true) ~= nil, 'missable achievements say so')
s = step_of(900111)
eq(s.text, 'Pipe / Dream', 'a pipe in a title cannot break the guide line')
eq(step_of(900110).zone, nil, 'an unmapped monster step has no place')

-- The step line itself, exactly.
eq(RAG.step_line(A.get(900101), A.complete_at), 'L First Steps|LV|10||RA|900101||N|Reach level 10 (5 points)|',
   'the line for a level achievement')
eq(RAG.step_line({ id = 1, title = 'T', description = 'D', points = 1 }), 'C T|RA|1||N|D (1 point)|',
   'the line for an unmapped achievement')
eq(RAG.build({ sets = { { game_id = 1, title = 'Empty', achievements = {} } } })[1], nil, 'an empty set makes no guide')
eq(#RAG.build(nil), 0, 'no data makes no guides')

-- Conditions: a confident mapping ticks itself off; the level step completes at level 10.
do
    WORLD.main_job_level = 9
    ok(not C.done(step_of(900101), C.world()), 'level 9 has not reached level 10')
    WORLD.main_job_level = 10
    ok(C.done(step_of(900101), C.world()), 'level 10 has')
    WORLD.job_levels[7] = 30
    ok(C.done(step_of(900104), C.world()), 'Paladin 30 completes the job achievement step')
end

-- ---- the snapshot reader -------------------------------------------------------------------
local J = require('core.json')
do
    local v = J.decode('{"a":[1,2.5,-3e2,true,false,null],"s":"q\\"\\u00e9\\ud83c\\udfc6\\n","o":{}}')
    ok(v ~= nil, 'json: decodes')
    eq(v.a[2], 2.5, 'json: numbers')
    eq(v.a[3], -300, 'json: exponents')
    eq(v.a[4], true, 'json: booleans')
    eq(v.a[6], nil, 'json: null is nil')
    eq(v.s, 'q"\195\169\240\159\143\134\n', 'json: escapes, \\u and surrogate pairs')
    eq(next(v.o), nil, 'json: empty object')
    ok(J.decode('{"a":') == nil, 'json: truncated text is an error, not a throw')
    ok(J.decode('[1,2] x') == nil, 'json: trailing text is an error')
    ok(J.decode(('['):rep(100)) == nil, 'json: absurd nesting is an error')
    ok(J.decode(nil) == nil, 'json: nil is an error')
end

local RA = require('core.ra')
local NOW = 1790000000
local snap = tmpfile()
ok(run(('python3 tools/retroachievements.py FixtureUser --fixture %s %s --now %d --out %s'):format(
    FIXTURES, GAMES, NOW, snap)), 'retroachievements.py writes a snapshot from fixtures')
local doc = J.decode(slurp(snap) or '')
ok(doc ~= nil and doc.source == 'RetroAchievements' and doc.user == 'FixtureUser' and doc.fetched_at == NOW,
   'the snapshot has the contract header')
ok(doc and doc.games[1].game_id == 28275 and doc.games[1].earned == 2 and doc.games[1].total == 11,
   'and per-game counts')
ok(doc and doc.games[1].achievements['900101'].earned_hardcore_at == '2026-09-01T12:00:00Z',
   'dates are ISO 8601 UTC')
ok(doc and doc.games[1].achievements['900103'] ~= nil and doc.games[1].achievements['900103'].earned_at == nil,
   'unearned achievements are listed with null dates')

-- missing
RA.path = snap .. '.does-not-exist'
eq(RA.refresh(NOW), 'missing', 'no file: missing')
eq((RA.state(900101)), 'unknown', 'missing is unknown, never "not earned"')
ok(not RA.earned(900101), 'and not earned either')
eq((RA.describe(900101)), 'No RetroAchievements progress data', 'the window says there is no data')

-- present
RA.path = snap
eq(RA.refresh(NOW + 60), 'ok', 'a fresh snapshot is ok')
eq((RA.state(900101)), 'earned', 'an achievement with dates is earned')
eq((RA.describe(900101)), 'Earned on HorizonXI 2026-09-01 (hardcore)', 'hardcore date shown')
eq((RA.describe(900102)), 'Earned on HorizonXI 2026-09-03', 'softcore date shown')
eq((RA.state(900103)), 'not_earned', 'null dates: not earned')
eq((RA.state(900301)), 'earned', 'subset progress is read too')
eq((RA.state(12345)), 'unknown', 'an id the snapshot does not list is unknown')
ok(RA.summary(NOW + 60)[2]:find('FixtureUser', 1, true) ~= nil, '/vg ra names the user')

-- the timer, and not re-parsing unchanged bytes
do
    local reads, parses = RA.reads, RA.parses
    ok(not RA.tick(NOW + 61), 'the timer does not read again within the interval')
    eq(RA.reads, reads, 'no read happened')
    ok(RA.tick(NOW + 60 + RA.interval), 'it reads once the interval has passed')
    eq(RA.reads, reads + 1, 'one read')
    eq(RA.parses, parses, 'unchanged bytes are not parsed again')
end

-- stale
eq(RA.refresh(NOW + RA.max_age + 3600), 'stale', 'an old snapshot goes stale on its own')
eq((RA.state(900101)), 'unknown', 'stale is unknown, never "not earned"')
ok((RA.describe(900101)):find('stale', 1, true) ~= nil, 'the window says it is stale')
eq(RA.refresh(NOW), 'ok', 'and ok again when it is fresh')

-- malformed, in several ways, each of which must read as no data
local bad = tmpfile()
RA.path = bad
local cases = {
    { '', 'missing', 'an empty file' },
    { '{"source":"RetroAchievements","games":[', 'malformed', 'a truncated file' },
    { '{"source":"Other","fetched_at":1,"games":[]}', 'malformed', 'another source' },
    { '{"source":"RetroAchievements","fetched_at":1,"games":{}}', 'malformed', 'games that is not a list' },
    { '{"source":"RetroAchievements","games":[]}', 'malformed', 'no fetched_at' },
    { '{"source":"RetroAchievements","fetched_at":' .. NOW .. ',"games":[{"title":"x"}]}', 'malformed', 'a game with no id' },
    { '{"source":"RetroAchievements","fetched_at":' .. NOW .. ',"games":[{"game_id":1,"achievements":7}]}', 'malformed', 'achievements that is not an object' },
    { '{"source":"RetroAchievements","fetched_at":' .. (NOW + 3 * 86400) .. ',"games":[]}', 'stale', 'a snapshot from the future' },
    { '[1,2,3]', 'malformed', 'a list instead of an object' },
    { 'not json at all', 'malformed', 'not JSON' },
}
for _, c in ipairs(cases) do
    spit(bad, c[1])
    eq(RA.refresh(NOW), c[2], c[3] .. ' -> ' .. c[2])
    eq((RA.state(900101)), 'unknown', c[3] .. ' reads as no data')
end
spit(bad, '{"source":"RetroAchievements","fetched_at":' .. NOW
    .. ',"games":[{"game_id":28275,"achievements":{"900107":{"earned_at":"2026-09-10 01:02:03","earned_hardcore_at":null}}}]}')
eq(RA.refresh(NOW), 'ok', 'a minimal hand-written snapshot is fine')
eq((RA.describe(900107)), 'Earned on HorizonXI 2026-09-10', "RetroAchievements' own date format is accepted too")
RA.path = snap
RA.refresh(NOW)

-- ---- the window --------------------------------------------------------------------------
do
    local shown = {}
    _G.imgui = {
        Begin = function() return true end, End = function() end,
        Text = function(t) shown[#shown + 1] = t end,
        TextWrapped = function(t) shown[#shown + 1] = t end,
        TextColored = function(_, t) shown[#shown + 1] = t end,
        PushTextWrapPos = function() end, PopTextWrapPos = function() end,
        Separator = function() end, SameLine = function() end,
        Button = function() return false end,
        SetNextWindowSize = function() end, SetNextWindowPos = function() end,
    }
    _G.ImGuiCond_FirstUseEver, _G.ImGuiCond_Always = 4, 1
    local Win = require('ui.window')
    Win.open[1] = true
    Win.set_viewport(1280, 720)
    WORLD.main_job_level = 1
    P.set_guide(base)
    local function has(needle)
        for _, t in ipairs(shown) do if t:find(needle, 1, true) then return true end end
        return false
    end
    Win.draw(C.world(), nil)
    ok(has('[Earned] Level: First Steps'), 'an earned step is marked in the window')
    ok(has('Earned on HorizonXI 2026-09-01 (hardcore)'), 'with the date it was earned')
    ok(has('[Earned] Do Squire No More'), 'earned steps are marked in the upcoming list too')

    P.index = 3        -- Save the Children: not earned in the fixture snapshot
    shown = {}
    Win.draw(C.world(), nil)
    ok(has('Do: Save the Children') and not has('[Earned] Do: Save'), 'an unearned step has no mark')
    ok(has('Not yet earned on HorizonXI'), 'and says so')

    -- Earned on HorizonXI never completes a step here: the quest behind 900102 is not done.
    P.index = 2
    ok(RA.earned(900102) and not C.done(P.step(), C.world()), 'an earned achievement does not complete its step')

    RA.path = snap .. '.gone'
    RA.refresh(NOW)
    P.index = 1
    shown = {}
    Win.draw(C.world(), nil)
    ok(not has('[Earned]'), 'with no data nothing is marked earned')
    ok(has('No RetroAchievements progress data'), 'and the window says there is no data')
    _G.imgui = nil
end

-- ---- export numbering ----------------------------------------------------------------------
do
    local first = G.list()[#before + 1]
    eq(first.steps[1].ra, 900101, 'the first achievement guide starts after every existing guide')
end

for _, p in ipairs(tmp) do os.remove(p) end
print(('\n%d passed, %d failed'):format(pass, fail))
os.exit(fail == 0 and 0 or 1)
