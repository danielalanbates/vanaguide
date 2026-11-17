-- Vanaguide :: core/progress.lua
-- Which step you are on, and the record of what you have finished — per character, because
-- two characters on one account are two different playthroughs.
--
-- Copyright (c) 2026 Bates LLC.  All rights reserved.

local C = require('core.conditions')

local P = {
    guide = nil,        -- the active guide table
    index = 1,          -- 1-based step index
    skipped = {},       -- [step index] = true
    checked = {},       -- [step index] = true, ticked by hand
}

local function fingerprint(guide)
    local hash = 5381
    local function atom(value) return tostring(value or '') end
    for _, step in ipairs(guide.steps or {}) do
        local text = table.concat({
            atom(step.kind), atom(step.text), atom(step.zone),
            atom(step.pos and step.pos.x), atom(step.pos and step.pos.z), atom(step.pos and step.pos.r),
            atom(step.mission and step.mission.area), atom(step.mission and step.mission.id),
            atom(step.quest and step.quest.area), atom(step.quest and step.quest.id),
            atom(step.quest_accept and step.quest_accept.area), atom(step.quest_accept and step.quest_accept.id),
            atom(step.key_item), atom(step.item and step.item.id), atom(step.item and step.item.count),
            atom(step.level), atom(step.job and step.job.id), atom(step.job and step.job.level),
            atom(step.rank), atom(step.spell), atom(step.fixed),
        }, '\31') .. '\n'
        for i = 1, #text do
            hash = (hash * 33 + text:byte(i)) % 2147483647
        end
    end
    return ('%d:%d'):format(#(guide.steps or {}), hash)
end

local function saved_marks(marks, count)
    local clean = {}
    if type(marks) ~= 'table' then return clean end
    for index, marked in pairs(marks) do
        if type(index) == 'number' and index >= 1 and index <= count
            and index == math.floor(index) and marked == true then
            clean[index] = true
        end
    end
    return clean
end

--- Start (or resume) a guide.  Resuming keeps whatever was already recorded for it.
function P.set_guide(guide, saved)
    P.guide = guide
    local signature = guide and fingerprint(guide) or nil
    local count = guide and #guide.steps or 0
    local compatible = type(saved) == 'table' and signature ~= nil
        and saved.fingerprint == signature
    local saved_index = compatible and tonumber(saved.index) or 1
    if saved_index == nil or saved_index ~= saved_index then saved_index = 1 end
    P.index = compatible and math.max(1, math.min(math.floor(saved_index), count + 1)) or 1
    P.skipped = compatible and saved_marks(saved.skipped, count) or {}
    P.checked = compatible and saved_marks(saved.checked, count) or {}
    P.fingerprint = signature
    return P.guide
end

function P.step(i)
    if P.guide == nil then return nil end
    return P.guide.steps[i or P.index]
end

function P.count()
    if P.guide == nil then return 0 end
    return #P.guide.steps
end

local function satisfied(i, w)
    if P.checked[i] or P.skipped[i] then return true end
    local step = P.guide.steps[i]
    if step == nil then return true end
    if step.fixed and not P.checked[i] then return false end
    return C.done(step, w)
end

--- Move the cursor past everything that is already true.  Returns the number of steps
--- crossed, so the caller can announce "3 steps completed" rather than silently jumping.
function P.advance(w)
    if P.guide == nil then return 0 end
    w = w or C.world()
    local moved = 0
    while P.index <= #P.guide.steps and satisfied(P.index, w) do
        P.index = P.index + 1
        moved = moved + 1
    end
    return moved
end

--- The next few steps that still need doing, for the guide window.
function P.upcoming(n, w)
    local out = {}
    if P.guide == nil then return out end
    w = w or C.world()
    local i = P.index
    while i <= #P.guide.steps and #out < (n or 6) do
        if not satisfied(i, w) then out[#out + 1] = P.guide.steps[i] end
        i = i + 1
    end
    return out
end

function P.check(i)  P.checked[i or P.index] = true end
function P.uncheck(i) P.checked[i or P.index] = nil end
function P.skip(i)   P.skipped[i or P.index] = true end

--- Step back to the last thing that is not finished, undoing a hand tick if that is what
--- put the cursor where it is.
function P.back()
    if P.guide == nil then return end
    local i = P.index - 1
    while i >= 1 do
        if P.checked[i] then P.checked[i] = nil; P.index = i; return end
        if P.skipped[i] then P.skipped[i] = nil; P.index = i; return end
        i = i - 1
    end
    P.index = math.max(1, P.index - 1)
end

function P.complete()
    return P.guide ~= nil and P.index > #P.guide.steps
end

function P.save_state()
    return { index = P.index, skipped = P.skipped, checked = P.checked,
             fingerprint = P.fingerprint }
end

return P
