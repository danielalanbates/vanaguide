-- Vanaguide :: tools/export_steps.lua
-- Every step of every guide, one JSON object per line, in the numbering /vg list uses.
--   luajit tools/export_steps.lua > steps.jsonl       (from the repository root)
-- Copyright (c) 2026 Bates LLC.  All rights reserved.
package.path = 'Vanaguide/?.lua;Vanaguide/?/init.lua;' .. package.path
dofile('tools/stubs.lua')
local G = require('core.guide')
require('guides.init')
local Q = require('data.quests')
local okm, MI = pcall(require, 'data.missions')

local function esc(s)
    return (tostring(s):gsub('\\', '\\\\'):gsub('"', '\\"'):gsub('\n', ' '):gsub('[%c]', ' '))
end
local function val(v)
    if v == nil then return 'null' end
    if type(v) == 'number' then return tostring(v) end
    if type(v) == 'boolean' then return v and 'true' or 'false' end
    return '"' .. esc(v) .. '"'
end
local function obj(t)
    local keys = {}
    for k in pairs(t) do keys[#keys + 1] = k end
    table.sort(keys)
    local parts = {}
    for _, k in ipairs(keys) do parts[#parts + 1] = '"' .. k .. '":' .. val(t[k]) end
    return '{' .. table.concat(parts, ',') .. '}'
end

for gi, guide in ipairs(G.list()) do
    for si, s in ipairs(guide.steps or {}) do
        local key = s.quest or s.quest_accept or s.mission or s.mission_accept
        local db = nil
        if key and (s.quest or s.quest_accept) and Q.quests and Q.quests[key.area] then db = Q.quests[key.area][key.id] end
        if key and (s.mission or s.mission_accept) and okm and MI.get then db = MI.get(key.area, key.id) end
        local note = s.note or ''
        local npc = G.npc_of(s, db)
        local row = {
            guide = gi, guide_name = guide.name, step = si, steps = #guide.steps,
            kind = s.kind, text = s.text, zone = s.zone,
            x = s.pos and s.pos.x, z = s.pos and s.pos.z, r = s.pos and s.pos.r,
            cond = (s.quest and 'Q') or (s.quest_accept and 'QA') or (s.mission and 'M') or (s.mission_accept and 'MA') or (s.key_item and 'KI')
                or (s.item and 'IT') or (s.level and 'LV') or (s.job and 'JOB') or (s.rank and 'RANK')
                or (s.spell and 'SP') or 'manual',
            area = key and key.area, id = key and key.id,
            ki = s.key_item, item = s.item and s.item.id, item_n = s.item and s.item.count,
            ra = s.ra, level = s.level, job = s.job and s.job.id, job_lv = s.job and s.job.level, rank = s.rank, spell = s.spell,
            npc = npc, note = note, db_zone = db and db.zone, db_x = db and db.x, db_y = db and db.y, db_z = db and db.z,
        }
        print(obj(row))
    end
end
