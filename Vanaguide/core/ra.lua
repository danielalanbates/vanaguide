-- Vanaguide :: core/ra.lua
-- RetroAchievements progress, read from the snapshot the launcher writes:
--
--   <Ashita install>/config/addons/Vanaguide/retroachievements.json
--   { "source": "RetroAchievements", "user": "<name>", "fetched_at": <unix seconds>,
--     "games": [ { "game_id": 28275, "title": "...", "earned": N, "total": M,
--                  "achievements": { "<id>": { "earned_at": "<iso or null>",
--                                              "earned_hardcore_at": "<iso or null>" } } } ] }
--
-- This addon never talks to the network.  The launcher (Swift, off the game's thread) fetches
-- and writes the file; this module only reads it, on load and then at most once a minute, and
-- only parses it when its bytes have changed.  A read or parse failure is caught and reported,
-- never thrown into the frame.
--
-- A missing, stale or malformed file means "no progress data" -- never "not earned".  An
-- achievement the snapshot does not list is unknown, not unearned.  And whatever the file
-- says, it is shown, never used to complete a step: RetroAchievements are earned on
-- HorizonXI, and a HorizonXI unlock says nothing about this character on this world.
--
-- Copyright (c) 2026 Bates LLC.  All rights reserved.

local J = require('core.json')

local R = {
    path = nil,             -- set by R.default_path() or by a test
    interval = 60,          -- seconds between polls of the file
    fresh_for = 86400,      -- older than this: earned still shows, 'not earned' becomes unknown
                            -- (the companion app uses the same rule)
    max_bytes = 4 * 1024 * 1024,
    -- state
    status = 'missing',     -- 'ok' | 'missing' | 'stale' | 'malformed'
    reason = 'not read yet',
    user = nil,
    fetched_at = nil,
    games = {},             -- [game_id] = { title, earned, total }
    by_id = {},             -- [achievement id] = { earned_at, earned_hardcore_at, game_id }
    last_poll = nil,
    last_text = nil,
    reads = 0,
    parses = 0,
}

--- The snapshot's place in an Ashita install.
function R.default_path()
    local ok, root = pcall(function() return AshitaCore:GetInstallPath() end)
    if not ok or root == nil or root == '' then return nil end
    root = root:gsub('[\\/]$', '')
    local sep = root:find('\\', 1, true) and '\\' or '/'
    return table.concat({ root, 'config', 'addons', 'Vanaguide', 'retroachievements.json' }, sep)
end

local function clear(status, reason)
    R.status, R.reason = status, reason
    R.user, R.fetched_at = nil, nil
    R.games, R.by_id = {}, {}
end

local function iso_or_nil(v)
    if type(v) == 'string' and v:match('^%d%d%d%d%-%d%d%-%d%d') then return v end
    return nil
end

--- Take a decoded snapshot, or return false and why it cannot be used.
local function accept(doc, now)
    if not J.is_object(doc) then return false, 'not a JSON object' end
    if doc.source ~= 'RetroAchievements' then return false, 'source is not RetroAchievements' end
    if type(doc.games) ~= 'table' or J.is_object(doc.games) then return false, 'no games list' end
    local fetched = tonumber(doc.fetched_at)
    if fetched == nil then return false, 'no fetched_at' end

    local games, by_id = {}, {}
    for _, g in ipairs(doc.games) do
        local gid = type(g) == 'table' and tonumber(g.game_id) or nil
        if gid == nil then return false, 'a game without a game_id' end
        local list = g.achievements
        if list ~= nil and type(list) ~= 'table' then return false, 'achievements is not an object' end
        games[gid] = { title = tostring(g.title or ''), earned = tonumber(g.earned) or 0,
                       total = tonumber(g.total) or 0 }
        for key, rec in pairs(list or {}) do
            local id = tonumber(key)
            if id ~= nil and type(rec) == 'table' then
                by_id[id] = { earned_at = iso_or_nil(rec.earned_at),
                              earned_hardcore_at = iso_or_nil(rec.earned_hardcore_at), game_id = gid }
            end
        end
    end

    R.user, R.fetched_at, R.games, R.by_id = doc.user and tostring(doc.user) or nil, fetched, games, by_id
    local age = now - fetched
    -- Stale: an unlock never goes away, so earned achievements still show; only "not earned"
    -- stops being claimed, because it may have been earned since.
    if age > R.fresh_for then
        R.status, R.reason = 'stale', ('fetched %s ago'):format(R.age_text(age))
        return true
    end
    if age < -86400 then
        R.status, R.reason = 'stale', 'fetched_at is in the future; check the clock'
        return true
    end
    R.status, R.reason = 'ok', nil
    return true
end

--- Take a snapshot's text.  Exposed so tests (and a future in-process writer) can feed it.
function R.load_text(text, now)
    now = now or os.time()
    R.parses = R.parses + 1
    local doc, err = J.decode(text)
    if doc == nil then clear('malformed', err or 'not JSON'); return R.status end
    local ok, why = accept(doc, now)
    if not ok then clear('malformed', why) end
    return R.status
end

--- Read the file now.  Never throws.  Returns the status.
function R.refresh(now)
    now = now or os.time()
    R.last_poll = now
    local path = R.path or R.default_path()
    if path == nil then clear('missing', 'no install path'); R.last_text = nil; return R.status end
    local ok, text = pcall(function()
        local f = io.open(path, 'rb')
        if f == nil then return nil end
        local t = f:read(R.max_bytes + 1)
        f:close()
        return t
    end)
    R.reads = R.reads + 1
    if not ok then clear('missing', 'could not read the file'); R.last_text = nil; return R.status end
    if text == nil or text == '' then
        clear('missing', 'no snapshot yet (the launcher writes it)')
        R.last_text = nil
        return R.status
    end
    if #text > R.max_bytes then clear('malformed', 'file too large'); R.last_text = nil; return R.status end
    if text == R.last_text and R.status ~= 'missing' then
        -- Same bytes: nothing to parse, but the age still moves on (and the clock can move
        -- back), so re-take it only when fresh-or-stale would now come out differently.
        if R.fetched_at ~= nil then
            local age = now - R.fetched_at
            local stale = age > R.fresh_for or age < -86400
            if stale ~= (R.status == 'stale') then return R.load_text(text, now) end
        end
        return R.status
    end
    R.last_text = text
    local okp, status = pcall(R.load_text, text, now)
    if not okp then clear('malformed', 'could not parse: ' .. tostring(status)) end
    return R.status
end

--- Call every frame: reads at most once per `interval` seconds.
function R.tick(now)
    now = now or os.time()
    if R.last_poll ~= nil and now - R.last_poll < R.interval then return false end
    R.refresh(now)
    return true
end

--- 'earned' | 'not_earned' | 'unknown', and the record when there is one.
function R.state(id)
    if R.status ~= 'ok' and R.status ~= 'stale' then return 'unknown', nil end
    local rec = R.by_id[tonumber(id) or -1]
    if rec == nil then return 'unknown', nil end
    if rec.earned_at ~= nil or rec.earned_hardcore_at ~= nil then return 'earned', rec end
    if R.status == 'stale' then return 'unknown', rec end
    return 'not_earned', rec
end

function R.earned(id) return (R.state(id)) == 'earned' end

-- The trophy mark.  ASCII on purpose: the fonts this draws with have no trophy glyph, and
-- FFXI's prints garbage for anything outside ASCII.
R.MARK = '[Earned]'

--- One line for the guide window about an achievement step, and its colour.  The window puts
--- R.MARK in front of an earned step's text as well.
function R.describe(id)
    local state, rec = R.state(id)
    if state == 'earned' then
        local hard = rec.earned_hardcore_at
        local when = (hard or rec.earned_at):sub(1, 10)
        return ('Earned on HorizonXI %s%s'):format(when, hard and ' (hardcore)' or ''),
               { 0.4, 1.0, 0.4, 1.0 }
    end
    if state == 'not_earned' then
        return 'Not yet earned on HorizonXI', { 0.7, 0.7, 0.7, 1.0 }
    end
    if R.status == 'ok' then
        return 'Not in the RetroAchievements snapshot', { 0.7, 0.7, 0.7, 1.0 }
    end
    if R.status == 'stale' then
        return 'Progress unknown: RetroAchievements snapshot ' .. tostring(R.reason), { 0.7, 0.7, 0.7, 1.0 }
    end
    return 'No RetroAchievements progress data', { 0.7, 0.7, 0.7, 1.0 }
end

--- Lines for `/vg ra`.
function R.summary(now)
    now = now or os.time()
    local out = {}
    out[#out + 1] = ('RetroAchievements: %s%s'):format(R.status, R.reason and (' - ' .. R.reason) or '')
    if R.user ~= nil then
        out[#out + 1] = ('  user %s, fetched %s ago'):format(R.user,
            R.fetched_at and R.age_text(now - R.fetched_at) or '?')
    end
    local ids = {}
    for gid in pairs(R.games) do ids[#ids + 1] = gid end
    table.sort(ids)
    for _, gid in ipairs(ids) do
        local g = R.games[gid]
        out[#out + 1] = ('  %d %s: %d/%d earned'):format(gid, g.title, g.earned, g.total)
    end
    out[#out + 1] = '  file: ' .. tostring(R.path or R.default_path() or '?')
    return out
end

function R.age_text(s)
    if s < 0 then return '0s' end
    if s < 120 then return ('%ds'):format(s) end
    if s < 7200 then return ('%dm'):format(math.floor(s / 60)) end
    if s < 172800 then return ('%dh'):format(math.floor(s / 3600)) end
    return ('%dd'):format(math.floor(s / 86400))
end

return R
