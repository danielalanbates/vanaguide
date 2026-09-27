-- Vanaguide :: core/story.lua
-- Quest and mission progress, read from the server rather than remembered by the addon.
--
-- FFXI sends the whole quest/mission log in packet 0x056.  Each 0x056 carries a *type*
-- word at 0x24 saying which log page it is, and either 32 bytes of flags at 0x04 (one bit
-- per quest, "current" and "completed" being separate pages) or, for the two special
-- types, the current mission number for each storyline.  That is the only way a client-side
-- addon can know what you have finished — there is no memory API for it — so a guide step
-- that says "this quest is done" is answering with the server's own bookkeeping.
--
-- Page ids and layout follow the same reading of the packet as AndreWesleyPS/ffxi-journal
-- (MIT), which is the clearest public description of 0x056, corrected against the code that
-- builds it in LandSandBoat (src/map/packets/s2c/0x056_*.cpp); the implementation here is
-- our own.  See docs/PACKETS.md.
--
-- Copyright (c) 2026 Bates LLC.  All rights reserved.

local S = {
    quest = { current = {}, completed = {} },
    mission = { current = {}, completed = {} },
    seen = false,
    -- Counters, so "no quest data" can be told apart from "the packet never arrived" without
    -- guessing. `/vg story` prints them.
    packets = 0,
    pages = {},
    unknown_pages = {},
}

-- log page id -> what it is
local PAGES = {
    [0x0050] = { 'quest', 'current',   'sandoria' },
    [0x0058] = { 'quest', 'current',   'bastok'   },
    [0x0060] = { 'quest', 'current',   'windurst' },
    [0x0068] = { 'quest', 'current',   'jeuno'    },
    [0x0070] = { 'quest', 'current',   'other'    },
    [0x0078] = { 'quest', 'current',   'outlands' },
    [0x0088] = { 'quest', 'current',   'wotg'     },
    [0x00E0] = { 'quest', 'current',   'abyssea'  },
    [0x00F0] = { 'quest', 'current',   'adoulin'  },
    [0x0100] = { 'quest', 'current',   'coalition'},
    [0x0090] = { 'quest', 'completed', 'sandoria' },
    [0x0098] = { 'quest', 'completed', 'bastok'   },
    [0x00A0] = { 'quest', 'completed', 'windurst' },
    [0x00A8] = { 'quest', 'completed', 'jeuno'    },
    [0x00B0] = { 'quest', 'completed', 'other'    },
    [0x00B8] = { 'quest', 'completed', 'outlands' },
    [0x00C8] = { 'quest', 'completed', 'wotg'     },
    [0x00E8] = { 'quest', 'completed', 'abyssea'  },
    [0x00F8] = { 'quest', 'completed', 'adoulin'  },
    [0x0108] = { 'quest', 'completed', 'coalition'},
    [0x0030] = { 'mission', 'completed', 'campaign'   },
    [0x0038] = { 'mission', 'completed', 'campaign_2' },
}

-- Which storyline sends what, as LandSandBoat builds it (src/map/packets/s2c/0x056_*.cpp,
-- sent by charutils::SendPartialMissionLog).  Two schemes:
--
--   * a *completed* bitset -- San d'Oria, Bastok, Windurst, Zilart (page 0x00D0) and ToAU,
--     WoTG (page 0x00D8).  CLuaBaseEntity::completeMission sets the bit and resets the
--     current number, so the bit is the lasting evidence.
--   * the *current mission number only* -- CoP, ACP, AMK, ASA, Seekers of Adoulin, RoV (page
--     0xFFFF).  The server stores no completed bit for CoP at all, and sends none for the
--     others; its own hasCompletedMission() for CoP is "id < current".  A mission is finished
--     when the mission script moves `current` on to the next one (npcUtil.completeMission
--     -> addMission(nextMission)).  `!completemission` alone resets current to 0, which is
--     "nothing done" to the server and to us alike.
--
-- TVR has neither: LandSandBoat's 0xFFFE page is a stub that always carries 0.

--- Page 0x00D0: completed missions of mission logs 0..3, 64 bits each.
---
--- LandSandBoat MissionComplete::Nations packs log n into Data[n*2], Data[n*2+1] -- bytes
--- n*8 .. n*8+7 of the 32 at 0x04 (0x056_mission_other.cpp).  So the page carries all three
--- nations and Zilart side by side; reading the whole 32 bytes as the player's own nation
--- only happened to work for San d'Oria (measured in-game 2026-08-22 on a San d'Oria
--- character: bit 0 for mission 0, bits 0,1 after mission 1).  A Bastok character's mission
--- 2 is bit 66 of the page, not bit 2.
local NATIONS_COMPLETED_PAGE = 0x00D0
local NATIONS_SLICES = { { 'sandoria', 0 }, { 'bastok', 8 }, { 'windurst', 16 }, { 'zilart', 24 } }

--- Page 0x00D8: completed ToAU missions in bytes 0..7, WoTG in bytes 8..15
--- (MissionComplete::ToAU_WoTG in 0x056_mission_other.cpp).
local TOAU_WOTG_COMPLETED_PAGE = 0x00D8
local TOAU_WOTG_SLICES = { { 'toau', 0 }, { 'wotg', 8 } }

--- Page 0x0080: Aht Urhgan quests *in progress*, but LandSandBoat overwrites Data[4..7] with
--- the current Assault, ToAU, WoTG and Campaign mission numbers (QuestOffer::AhtUrghan).
--- So only bytes 0..15 are quest flags, and ToAU / WoTG current missions sit at 0x18 / 0x1C.
local AHTURHGAN_CURRENT_PAGE = 0x0080

--- Page 0x00C0: Aht Urhgan quests *completed* in bytes 0..15; bytes 16..31 are completed
--- Assault missions OR'd in (QuestComplete::AhtUrghan), not quests.
local AHTURHGAN_COMPLETED_PAGE = 0x00C0

--- 0xFFFF sends Seekers of Adoulin as `current*2 + 0x6E` and RoV as `current + 0x6C`, or 0
--- when the player declined the expansion (GP_SERV_COMMAND_MISSION::MISSION).  Read raw,
--- a character who has not started either looked 110 / 108 missions in.
local SOA_BASE, SOA_SCALE = 0x6E, 2
local ROV_BASE = 0x6C

local NATION_AREA = { [0] = 'sandoria', [1] = 'bastok', [2] = 'windurst' }

local function u32(data, off)
    if data == nil or #data < off + 4 then return nil end
    local b1, b2, b3, b4 = data:byte(off + 1, off + 4)
    return b1 + b2 * 0x100 + b3 * 0x10000 + b4 * 0x1000000
end

local function i32(data, off)
    local v = u32(data, off)
    if v == nil then return nil end
    if v >= 0x80000000 then return v - 0x100000000 end
    return v
end

--- Undo the offset 0xFFFF puts on a storyline's current number.  nil when the raw value is
--- below the offset (0 = expansion declined), so it reads as "nothing started".
local function unoffset(raw, base, scale)
    if raw == nil or raw < base then return nil end
    return math.floor((raw - base) / (scale or 1))
end

--- `count` bytes of flags -> set of ids that are set.  Bit n of byte b is quest id b*8+n.
local function flags(data, off, count)
    local set = {}
    for b = 0, count - 1 do
        local byte = data:byte(off + b + 1)
        if byte == nil then break end
        for bit = 0, 7 do
            if math.floor(byte / 2 ^ bit) % 2 == 1 then set[b * 8 + bit] = true end
        end
    end
    return set
end

--- Feed one incoming packet.  Anything that is not 0x056 is ignored cheaply.
function S.on_packet(id, data, size)
    if id ~= 0x056 or data == nil or (size or #data) < 40 then return end
    S.packets = S.packets + 1
    local page = u32(data, 0x24)
    if page == nil then return end
    S.pages[page] = (S.pages[page] or 0) + 1

    local p = PAGES[page]
    if p ~= nil then
        S[p[1]][p[2]][p[3]] = flags(data, 0x04, 32)
        S.seen = true
        return
    end

    if page == NATIONS_COMPLETED_PAGE or page == TOAU_WOTG_COMPLETED_PAGE then
        local slices = page == NATIONS_COMPLETED_PAGE and NATIONS_SLICES or TOAU_WOTG_SLICES
        for _, s in ipairs(slices) do
            S.mission.completed[s[1]] = flags(data, 0x04 + s[2], 8)
        end
        S.seen = true
        return
    end

    if page == AHTURHGAN_CURRENT_PAGE then
        S.quest.current.ahturhgan = flags(data, 0x04, 16)
        S.mission.current.toau = i32(data, 0x18)
        S.mission.current.wotg = i32(data, 0x1C)
        S.seen = true
        return
    end

    if page == AHTURHGAN_COMPLETED_PAGE then
        S.quest.completed.ahturhgan = flags(data, 0x04, 16)
        S.seen = true
        return
    end

    -- 0xFFFF: the current mission number of the storylines that are not on another page.
    if page == 0xFFFF then
        local nation = i32(data, 0x04)
        S.nation = nation
        local cur = S.mission.current
        cur.nation  = i32(data, 0x08)
        cur.zilart  = i32(data, 0x0C)
        cur.cop     = i32(data, 0x10)
        -- uint16 bitfield at 0x18: ACP bits 0-3, AMK bits 4-7, ASA bits 8-11.
        local acp_amk = data:byte(0x18 + 1)
        if acp_amk ~= nil then
            cur.acp = acp_amk % 16
            cur.amk = math.floor(acp_amk / 16)
        end
        local asa = data:byte(0x19 + 1)
        if asa ~= nil then cur.asa = asa % 16 end
        cur.adoulin = unoffset(i32(data, 0x1C), SOA_BASE, SOA_SCALE)
        cur.rov     = unoffset(i32(data, 0x20), ROV_BASE)
        local area = NATION_AREA[nation]
        if area ~= nil then cur[area] = cur.nation end
        S.seen = true
        return
    end

    -- 0xFFFE is The Voracious Resurgence (GP_SERV_COMMAND_MISSION::TVR), not Aht Urhgan:
    -- LandSandBoat always sends 0 there, so there is nothing to read yet.
    if page == 0xFFFE then return end

    S.unknown_pages[page] = (S.unknown_pages[page] or 0) + 1
    -- Keep the bits as well as the count. A page id means nothing on its own; a page
    -- whose bit 0 turns on exactly when you finish mission 0 identifies itself.
    S.unknown_sets = S.unknown_sets or {}
    S.unknown_sets[page] = flags(data, 0x04, 32)
end

--- Has this quest been completed?  `area` is a log page name ('jeuno', 'sandoria', ...).
function S.quest_done(area, id)
    local set = S.quest.completed[area]
    return set ~= nil and set[id] == true
end

--- Is this quest accepted and not yet turned in?
function S.quest_active(area, id)
    local set = S.quest.current[area]
    return set ~= nil and set[id] == true
end

--- 65535 is "no mission active in this storyline" -- LandSandBoat's `xi.mission.id.*.NONE`,
--- and what a fresh character reports for every line.  Read as a number it is larger than
--- every real mission id, so a naive `current > id` marks the entire game finished: measured
--- in-game on a brand-new character, which walked a 24-step guide straight to "complete".
--- (Logs 3 and up use 0 for "none" instead -- lua_base_entity.cpp completeMission -- which
--- `current > id` already reads as nothing done.)
local NO_MISSION = 65535

--- Is this mission finished?  Storylines are linear, so "the current mission is past it" is
--- the completion test -- the only one there is for CoP, ACP, AMK, ASA, Adoulin and RoV,
--- exactly as the server's own hasCompletedMission() does it for CoP.  The nation lines,
--- Zilart, ToAU and WoTG also have a completed bitset, which is what survives once the
--- current number has been reset.
function S.mission_done(area, id)
    local cur = S.mission.current[area]
    if cur ~= nil and cur < NO_MISSION and cur > id then return true end
    local set = S.mission.completed[area]
    return set ~= nil and set[id] == true
end

function S.mission_current(area)
    local cur = S.mission.current[area]
    if cur == NO_MISSION then return nil end
    return cur
end

--- Is this mission active, or has it already been completed?
function S.mission_active(area, id)
    return S.mission_current(area) == id or S.mission_done(area, id)
end

--- Forget everything.  Called on zone-out to a new character / logout, because the flags
--- belong to whoever is logged in, and a stale set would silently mark steps done.
function S.reset()
    S.quest = { current = {}, completed = {} }
    S.mission = { current = {}, completed = {} }
    S.nation = nil
    S.seen = false
    S.packets = 0
    S.pages = {}
    S.unknown_pages = {}
end

return S
