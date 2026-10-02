-- Export the same quest and mission catalog the Ashita addon uses for the read-only Mac app.
-- Copyright (c) 2026 Daniel Bates / Bates LLC. All rights reserved.
local out = assert(arg[1], 'usage: luajit tools/export_companion.lua <output.json>')
package.path = 'Vanaguide/?.lua;Vanaguide/?/init.lua;' .. package.path
local quests = require('data.quests').quests
local missions = require('data.missions').missions
local zones = require('data.zone_names').name

local function quote(s)
    s = tostring(s or '')
    return '"' .. s:gsub('[%z\1-\31\\"]', function(c)
        if c == '\\' then return '\\\\' end
        if c == '"' then return '\\"' end
        if c == '\n' then return '\\n' end
        if c == '\r' then return '\\r' end
        if c == '\t' then return '\\t' end
        return string.format('\\u%04x', c:byte())
    end) .. '"'
end

local rows = {}
local function add(kind, catalog)
    for area, group in pairs(catalog) do
        for number, entry in pairs(group) do
            local fields = {
                '"id":' .. quote(kind .. ':' .. area .. ':' .. number),
                '"kind":' .. quote(kind),
                '"area":' .. quote(area),
                '"number":' .. tonumber(number),
                '"title":' .. quote(entry.name or entry.label or ''),
            }
            if entry.zone then
                fields[#fields + 1] = '"zone":' .. entry.zone
                fields[#fields + 1] = '"zoneName":' .. quote(zones[entry.zone] or 'Zone ' .. entry.zone)
            end
            if entry.npc then fields[#fields + 1] = '"npc":' .. quote(entry.npc) end
            for _, key in ipairs({ 'x', 'z', 'y', 'level' }) do
                if entry[key] then fields[#fields + 1] = quote(key) .. ':' .. entry[key] end
            end
            rows[#rows + 1] = '{' .. table.concat(fields, ',') .. '}'
        end
    end
end
add('quest', quests)
add('mission', missions)
table.sort(rows)
local f = assert(io.open(out, 'w'))
f:write('[\n', table.concat(rows, ',\n'), '\n]\n')
f:close()
print('exported ' .. #rows .. ' quests and missions to ' .. out)
