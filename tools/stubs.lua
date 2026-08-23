-- Vanaguide :: tools/stubs.lua
-- Enough of Ashita's globals for the addon's logic to run outside the game.
-- Set WORLD before requiring the addon's modules; every stub reads from it.
--
-- Copyright (c) 2026 Bates LLC.  All rights reserved.

WORLD = {
    zone = 230,
    x = 0, z = 0, y = 0, yaw = 0,
    login = 2,
    main_job = 1, main_job_level = 5,
    job_levels = {},
    rank = 1,
    nation = 0,
    key_items = {},
    spells = {},
    items = {},          -- [item id] = count
    zone_names = {},
}

_G.print = function(...)
    local parts = {}
    for i = 1, select('#', ...) do parts[i] = tostring((select(i, ...))) end
    io.write(table.concat(parts, ' '), '\n')
end

function GetPlayerEntity()
    return {
        -- Ashita's struct, with the game's real axis order: X and Y are horizontal, Z is
        -- height. WORLD.z is the guide-space second horizontal number, so it goes in Y.
        Movement = { LocalPosition = { X = WORLD.x, Y = WORLD.z, Z = WORLD.y, Yaw = WORLD.yaw } },
        Heading = WORLD.yaw,
        Name = 'Tester',
    }
end

local player = {
    GetLoginStatus  = function() return WORLD.login end,
    GetMainJob      = function() return WORLD.main_job end,
    GetMainJobLevel = function() return WORLD.main_job_level end,
    GetJobLevel     = function(_, id) return WORLD.job_levels[id] or 0 end,
    GetRank         = function() return WORLD.rank end,
    GetNation       = function() return WORLD.nation end,
    HasKeyItem      = function(_, id) return WORLD.key_items[id] == true end,
    HasSpell        = function(_, id) return WORLD.spells[id] == true end,
}

local party = {
    GetMemberZone = function(_, i) return i == 0 and WORLD.zone or 0 end,
    GetMemberName = function() return 'Tester' end,
}

local inventory = {
    GetContainerCountMax = function(_, c) return c == 0 and 79 or 0 end,
    GetContainerItem = function(_, c, i)
        if c ~= 0 then return nil end
        local n = 0
        for id, count in pairs(WORLD.items) do
            n = n + 1
            if n == i then return { Id = id, Count = count } end
        end
        return nil
    end,
}

local resources = {
    GetString = function(_, tbl, id)
        if tbl == 'zones.names' then return WORLD.zone_names[id] end
        return nil
    end,
}

AshitaCore = {
    GetMemoryManager = function()
        return {
            GetPlayer = function() return player end,
            GetParty = function() return party end,
            GetInventory = function() return inventory end,
        }
    end,
    GetResourceManager = function() return resources end,
    GetInstallPath = function() return '/tmp/vanaguide-test' end,
}

addon = { name = 'Vanaguide', version = 'test', author = 'test' }
ashita = { events = { register = function() end }, memory = {} }
