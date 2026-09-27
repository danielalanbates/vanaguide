-- Vanaguide :: core/json.lua
-- A small JSON decoder: enough for the files the launcher writes for this addon to read.
-- Plain Lua 5.1, no C modules, so it behaves the same in the client and in the harness.
--
--   local J = require('core.json')
--   local value, err = J.decode(text)      -- value, or nil and a message; never throws
--
-- JSON null becomes nil (so a null field reads as absent), and J.null is not used.
-- Objects become tables with string keys; arrays become 1-based sequences.  An empty object
-- and an empty array would both be {}, so objects carry a marker: J.is_object(t).
--
-- Copyright (c) 2026 Bates LLC.  All rights reserved.

local J = {}

local MAX_DEPTH = 32
local OBJECT = {}

--- Was this table a JSON object (rather than an array)?
function J.is_object(t) return type(t) == 'table' and getmetatable(t) == OBJECT end

local ESCAPES = { ['"'] = '"', ['\\'] = '\\', ['/'] = '/', b = '\b', f = '\f', n = '\n', r = '\r', t = '\t' }

local function utf8(cp)
    if cp < 0x80 then return string.char(cp) end
    if cp < 0x800 then
        return string.char(0xC0 + math.floor(cp / 0x40), 0x80 + cp % 0x40)
    end
    if cp < 0x10000 then
        return string.char(0xE0 + math.floor(cp / 0x1000), 0x80 + math.floor(cp / 0x40) % 0x40, 0x80 + cp % 0x40)
    end
    return string.char(0xF0 + math.floor(cp / 0x40000), 0x80 + math.floor(cp / 0x1000) % 0x40,
                       0x80 + math.floor(cp / 0x40) % 0x40, 0x80 + cp % 0x40)
end

local decode_value

local function fail(pos, what) error({ pos = pos, what = what }, 0) end

local function skip(s, i)
    local _, e = s:find('^[ \t\r\n]*', i)
    return e + 1
end

local function decode_string(s, i)
    -- i is on the opening quote
    local out, j = {}, i + 1
    while true do
        local a, b = s:find('^[^"\\]+', j)
        if a ~= nil then out[#out + 1] = s:sub(a, b); j = b + 1 end
        local c = s:sub(j, j)
        if c == '"' then return table.concat(out), j + 1 end
        if c == '' then fail(j, 'unterminated string') end
        -- a backslash
        local e = s:sub(j + 1, j + 1)
        if e == 'u' then
            local hex = s:sub(j + 2, j + 5)
            if not hex:match('^%x%x%x%x$') then fail(j, 'bad \\u escape') end
            local cp = tonumber(hex, 16)
            j = j + 6
            if cp >= 0xD800 and cp <= 0xDBFF and s:sub(j, j + 1) == '\\u' then
                local lo = tonumber(s:sub(j + 2, j + 5), 16)
                if lo ~= nil and lo >= 0xDC00 and lo <= 0xDFFF then
                    cp = 0x10000 + (cp - 0xD800) * 0x400 + (lo - 0xDC00)
                    j = j + 6
                end
            end
            out[#out + 1] = utf8(cp)
        elseif ESCAPES[e] ~= nil then
            out[#out + 1] = ESCAPES[e]
            j = j + 2
        else
            fail(j, 'bad escape')
        end
    end
end

local function decode_array(s, i, depth)
    local out, n = {}, 0
    i = skip(s, i + 1)
    if s:sub(i, i) == ']' then return out, i + 1 end
    while true do
        local v
        v, i = decode_value(s, i, depth + 1)
        n = n + 1
        out[n] = v
        i = skip(s, i)
        local c = s:sub(i, i)
        if c == ']' then return out, i + 1 end
        if c ~= ',' then fail(i, "expected ',' or ']'") end
        i = skip(s, i + 1)
    end
end

local function decode_object(s, i, depth)
    local out = setmetatable({}, OBJECT)
    i = skip(s, i + 1)
    if s:sub(i, i) == '}' then return out, i + 1 end
    while true do
        if s:sub(i, i) ~= '"' then fail(i, 'expected a key') end
        local key
        key, i = decode_string(s, i)
        i = skip(s, i)
        if s:sub(i, i) ~= ':' then fail(i, "expected ':'") end
        local v
        v, i = decode_value(s, skip(s, i + 1), depth + 1)
        out[key] = v
        i = skip(s, i)
        local c = s:sub(i, i)
        if c == '}' then return out, i + 1 end
        if c ~= ',' then fail(i, "expected ',' or '}'") end
        i = skip(s, i + 1)
    end
end

decode_value = function(s, i, depth)
    if depth > MAX_DEPTH then fail(i, 'nested too deeply') end
    i = skip(s, i)
    local c = s:sub(i, i)
    if c == '{' then return decode_object(s, i, depth) end
    if c == '[' then return decode_array(s, i, depth) end
    if c == '"' then return decode_string(s, i) end
    if s:sub(i, i + 3) == 'true' then return true, i + 4 end
    if s:sub(i, i + 4) == 'false' then return false, i + 5 end
    if s:sub(i, i + 3) == 'null' then return nil, i + 4 end
    local num = s:match('^-?%d+%.?%d*[eE]?[-+]?%d*', i)
    if num ~= nil and num ~= '' and num ~= '-' then
        local v = tonumber(num)
        if v == nil then fail(i, 'bad number') end
        return v, i + #num
    end
    fail(i, 'unexpected ' .. (c == '' and 'end of text' or ("'" .. c .. "'")))
end

--- Decode a JSON text.  Returns the value, or nil and a message.  Never throws.
function J.decode(text)
    if type(text) ~= 'string' then return nil, 'not text' end
    local ok, value, i = pcall(decode_value, text, 1, 0)
    if not ok then
        local e = value
        if type(e) == 'table' then return nil, ('%s at byte %d'):format(e.what, e.pos) end
        return nil, tostring(e)
    end
    if skip(text, i) <= #text then return nil, ('trailing text at byte %d'):format(skip(text, i)) end
    return value
end

return J
