-- Vanaguide :: guides/achievements.lua
-- One guide per RetroAchievements set, built at load time from data/achievements.lua, so the
-- achievement list doubles as a to-do list: every achievement is a step whose text is its
-- title and whose note is its description and points.
--
-- Where tools/gen_achievements.py matched an achievement to something this addon can check
-- (a quest, a mission, a level, a rank, an item) with enough confidence, the step carries that
-- completion tag and ticks itself off like any other.  A weaker match only lends the step a
-- place, so the arrow and the line can still take you there; the step waits for Done.  An
-- achievement nothing matched is a plain manual step.
--
-- RetroAchievements progress itself is earned on HorizonXI only.  On any other world the
-- window shows it (core/ra.lua reads the launcher's snapshot) but never uses it to complete a
-- step: a HorizonXI unlock says nothing about this character on this server.
--
-- These guides are registered after every other guide, so the numbering `/vg list`, saved
-- progress and tools/export_steps.lua rely on is unchanged for the guides before them.
--
-- Copyright (c) 2026 Bates LLC.  All rights reserved.

local G = require('core.guide')

local M = { PREFIX = 'RetroAchievements - ', COMPLETE_AT = 0.75 }

local JOB = { 'Warrior', 'Monk', 'White Mage', 'Black Mage', 'Red Mage', 'Thief', 'Paladin',
    'Dark Knight', 'Beastmaster', 'Bard', 'Ranger', 'Samurai', 'Ninja', 'Dragoon', 'Summoner',
    'Blue Mage', 'Corsair', 'Puppetmaster', 'Dancer', 'Scholar', 'Geomancer', 'Rune Fencer' }

--- Text that is safe inside a guide line: no tag separators, no line breaks.
local function clean(s)
    return (tostring(s or ''):gsub('|', '/'):gsub('[\r\n]+', ' '))
end

--- The completion tag for a confident mapping, or nil.
local function completion(m)
    if m.kind == 'quest' and m.area and m.id then return ('|Q|%s,%d|'):format(m.area, m.id) end
    if m.kind == 'mission' and m.area and m.id then return ('|M|%s,%d|'):format(m.area, m.id) end
    if m.kind == 'level' and m.level then return ('|LV|%d|'):format(m.level) end
    if m.kind == 'job' and m.job and m.level then return ('|JOB|%d,%d|'):format(m.job, m.level) end
    if m.kind == 'rank' and m.rank then return ('|RANK|%d|'):format(m.rank) end
    if m.kind == 'key_item' and m.ki then return ('|KI|%d|'):format(m.ki) end
    if m.kind == 'item' and m.item then return ('|IT|%d,%d|'):format(m.item, m.count or 1) end
    return nil
end

local VERB = { quest = 'C', mission = 'C', key_item = 'C', item = 'C', nm = 'K',
               level = 'L', job = 'L', rank = 'L' }

--- What a mapping points at, in words, for the note of a step that only borrows its place.
local function describe(m)
    if m.kind == 'job' then return ('%s level %d'):format(JOB[m.job] or ('job ' .. m.job), m.level) end
    if m.kind == 'level' then return ('level %d'):format(m.level) end
    if m.kind == 'rank' then return ('rank %d'):format(m.rank) end
    return m.name or m.kind
end

--- One guide line for one achievement.  `complete_at` is the confidence a mapping needs
--- before its condition is trusted to tick the step off.
function M.step_line(a, complete_at)
    complete_at = complete_at or M.COMPLETE_AT
    local m = a.map
    local sure = m ~= nil and (m.confidence or 0) >= complete_at and completion(m) ~= nil
    local verb = (m ~= nil and (sure or m.kind == 'nm')) and (VERB[m.kind] or 'C') or 'C'
    local line = { verb .. ' ' .. clean(a.title) }
    if sure then line[#line + 1] = completion(m) end
    if m ~= nil and m.zone ~= nil then
        line[#line + 1] = ('|Z|%d|'):format(m.zone)
        if m.x ~= nil and m.z ~= nil then
            line[#line + 1] = ('|POS|%.1f,%.1f,%d|'):format(m.x, m.z, m.kind == 'nm' and 20 or 8)
        end
    end
    line[#line + 1] = ('|RA|%d|'):format(a.id)

    local note = { clean(a.description) }
    note[#note + 1] = ('(%d %s)'):format(a.points or 0, (a.points == 1) and 'point' or 'points')
    if a.type == 'missable' then note[#note + 1] = 'Missable.' end
    if m ~= nil and not sure then
        note[#note + 1] = ('Possibly: %s - not checked automatically.'):format(clean(describe(m)))
    end
    line[#line + 1] = ('|N|%s|'):format(table.concat(note, ' '))
    return table.concat(line)
end

--- Register one guide per set in `A` (data/achievements.lua's table).  Returns the guides.
function M.build(A)
    local out = {}
    if type(A) ~= 'table' or type(A.sets) ~= 'table' then return out end
    local complete_at = A.complete_at or M.COMPLETE_AT
    for _, set in ipairs(A.sets) do
        local list = set.achievements or {}
        if #list > 0 then
            local steps, points = {}, 0
            for _, a in ipairs(list) do
                steps[#steps + 1] = M.step_line(a, complete_at)
                points = points + (a.points or 0)
            end
            out[#out + 1] = G.register({
                name = M.PREFIX .. clean(set.name or set.title or ('game ' .. tostring(set.game_id))),
                author = 'generated from RetroAchievements',
                desc = ('%d achievements, %d points. Progress is earned on HorizonXI and shown here when the launcher has fetched it.')
                    :format(#list, points),
                steps = table.concat(steps, '\n'),
            })
        end
    end
    return out
end

--- Is this guide one of these?
function M.is_achievement_guide(guide)
    return guide ~= nil and type(guide.name) == 'string'
        and guide.name:sub(1, #M.PREFIX) == M.PREFIX
end

-- The shipped data.  A file that fails to load (it is generated, and may not exist yet on a
-- checkout that never had a key) means no achievement guides, not a broken addon.
local ok, A = pcall(require, 'data.achievements')
M.guides = ok and M.build(A) or {}

return M
