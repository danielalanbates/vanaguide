-- Vanaguide :: routing/navgrid.lua
-- A path that goes around the wall.
--
-- routing/path.lua draws a straight line between two points, which is right about the
-- direction and silent about the cliff.  This is the other half: a grid of "can I stand
-- here", built by tools/gen_navgrid.py from the navigation meshes LandSandBoat already ships
-- to its own server operators, and an A* across it.
--
-- THE GRIDS ARE NOT IN THIS REPOSITORY and will not be.  They are derived from Square Enix's
-- map geometry by way of a GPL-3.0 project; the tool ships, the data does not.  With no file
-- for the zone you are in, everything here answers "no" immediately and the straight line
-- stands.  See docs/NAVMESH.md.
--
-- ## Why the search is stepped
--
-- This addon runs with LuaJIT's compiler off (Ashita 4.3 faults inside `lj_mcode_patch`
-- under Wine, see Vanaguide.lua), so an A* over eighty thousand cells is not something to do
-- between two frames.  It is done a few hundred expansions at a time from the present hook,
-- and until it finishes `provide()` says "not yet" and the line stays straight.  A path that
-- appears a third of a second late is not noticeable; a client that stutters every time the
-- guide changes its mind is.
--
-- Copyright (c) 2026 Bates LLC.  All rights reserved.

local U = require('core.util')

local N = {
    root = nil,          -- where to look for data/nav; the addon sets this from Ashita
    loaded = nil,        -- the zone whose grid is in memory
    grid = nil,
    missing = {},        -- zones already looked for and not found, so we look once
    -- Diagnostics for /vg status.
    state = 'idle',
    searched = 0,
    last_ms = 0,
    -- How much work per frame.  400 expansions is a couple of milliseconds interpreted and
    -- finishes a two-hundred-yalm path in well under a second.
    per_frame = 400,
    -- A cap, so an unreachable target cannot search a whole zone forever.  Eighty thousand
    -- cells is the biggest grid the generator will write.
    max_expansions = 90000,
}

-- ---------------------------------------------------------------------------------
-- reading the file

local function u16(s, i) return s:byte(i) + s:byte(i + 1) * 256 end

local function u32(s, i)
    return s:byte(i) + s:byte(i + 1) * 256 + s:byte(i + 2) * 65536 + s:byte(i + 3) * 16777216
end

local function i32(s, i)
    local v = u32(s, i)
    if v >= 2147483648 then v = v - 4294967296 end
    return v
end

--- Expand a run-length encoded array into a flat string, one `size`-byte entry per cell.
--- Flat rather than kept as runs on purpose: `string.byte` into a string is a constant-time
--- lookup, and a binary search through thirty thousand runs, forty times a path, is not.
local function expand(s, at, runs, size, count)
    local parts, n = {}, 0
    for _ = 1, runs do
        local len = u32(s, at)
        local chunk = s:sub(at + 4, at + 3 + size)
        at = at + 4 + size
        n = n + 1
        parts[n] = chunk:rep(len)
    end
    return table.concat(parts), at
end

--- Load the grid for a zone.  Returns the grid, or nil (and remembers, so a zone with no
--- file is looked for once and never again).
function N.load(zone)
    if zone == nil then return nil end
    if N.loaded == zone then return N.grid end
    if N.missing[zone] then return nil end
    local root = N.root
    if root == nil then
        local ok, path = pcall(function () return AshitaCore:GetInstallPath() end)
        if ok and path ~= nil and path ~= '' then
            root = ('%s\\addons\\Vanaguide'):format(path:gsub('[\\/]$', ''))
        end
    end
    if root == nil then N.missing[zone] = true; return nil end

    local sep = root:find('\\') and '\\' or '/'
    local path = ('%s%sdata%snav%s%d.vgnav'):format(root, sep, sep, sep, zone)
    local fh = io.open(path, 'rb')
    if fh == nil then N.missing[zone] = true; return nil end
    local s = fh:read('*a')
    fh:close()
    if s == nil or #s < 24 or s:sub(1, 4) ~= 'VGNV' then
        N.missing[zone] = true
        return nil
    end

    local g = {}
    g.version = s:byte(5)
    g.zone    = u16(s, 6)
    g.cell    = s:byte(8) / 10
    g.ox      = i32(s, 9) / 10
    g.oz      = i32(s, 13) / 10
    g.w       = u16(s, 17)
    g.h       = u16(s, 19)
    if (g.version ~= 1 and g.version ~= 2) or g.cell <= 0 or g.w == 0 or g.h == 0 then
        N.missing[zone] = true
        return nil
    end

    local at = 21
    local mask_runs = u32(s, at); at = at + 4
    g.mask, at = expand(s, at, mask_runs, 1, g.w * g.h)
    local h_runs = u32(s, at); at = at + 4
    g.height, at = expand(s, at, h_runs, 2, g.w * g.h)
    if #g.mask < g.w * g.h then N.missing[zone] = true; return nil end
    -- Version 2 carries a second floor: cells where a bridge, rampart or upper walk lies
    -- over the ground.  Without it (version 1) every cell has one floor.
    if g.version >= 2 and at + 4 <= #s then
        local m2 = u32(s, at); at = at + 4
        g.mask2, at = expand(s, at, m2, 1, g.w * g.h)
        local h2 = u32(s, at); at = at + 4
        g.height2 = expand(s, at, h2, 2, g.w * g.h)
        if #g.mask2 < g.w * g.h then g.mask2, g.height2 = nil, nil end
    end
    g.layers = (g.mask2 ~= nil) and 2 or 1
    -- A step between two cells: anything taller is a wall or a drop, not a floor.
    g.step = math.max(3, 1.5 * g.cell)

    N.loaded, N.grid = zone, g
    return g
end

-- ---------------------------------------------------------------------------------
-- the grid

-- A cell is (cx, cz) and a *floor* is (cx, cz, layer): layer 0 is the ground, layer 1 the
-- bridge or rampart over it where the file says there is one.  Nodes in the search are
-- (cz * w + cx) * 2 + layer, so a cell with two floors is two nodes that do not touch.
local function walkable(g, cx, cz, layer)
    if cx < 0 or cz < 0 or cx >= g.w or cz >= g.h then return false end
    if (layer or 0) == 0 then return g.mask:byte(cz * g.w + cx + 1) == 1 end
    return g.mask2 ~= nil and g.mask2:byte(cz * g.w + cx + 1) == 1
end

local function height_at(g, cx, cz, layer)
    local i = (cz * g.w + cx) * 2 + 1
    local arr = ((layer or 0) == 1) and g.height2 or g.height
    if arr == nil then return 0 end
    local lo, hi = arr:byte(i, i + 1)
    if lo == nil then return 0 end
    local v = lo + hi * 256
    if v >= 32768 then v = v - 65536 end
    return v / 4
end

--- Of the floors in a cell, the one nearest a height (nil = the ground).
local function floor_near(g, cx, cz, y)
    local best, best_d
    for layer = 0, g.layers - 1 do
        if walkable(g, cx, cz, layer) then
            if y == nil then return layer end
            local d = math.abs(height_at(g, cx, cz, layer) - y)
            if best_d == nil or d < best_d then best, best_d = layer, d end
        end
    end
    return best
end

--- Can you step from a floor at height `y` onto a floor in this cell?  Returns the layer.
local function step_onto(g, cx, cz, y)
    local best, best_d
    for layer = 0, g.layers - 1 do
        if walkable(g, cx, cz, layer) then
            local d = math.abs(height_at(g, cx, cz, layer) - y)
            if d <= g.step and (best_d == nil or d < best_d) then best, best_d = layer, d end
        end
    end
    return best
end

local function to_cell(g, x, z)
    return math.floor((x - g.ox) / g.cell), math.floor((z - g.oz) / g.cell)
end

local function to_world(g, cx, cz)
    return g.ox + (cx + 0.5) * g.cell, g.oz + (cz + 0.5) * g.cell
end

--- The nearest walkable cell to one that is not, searched outwards in rings.  A player
--- standing on a ledge the mesh does not cover -- or a zone line whose recorded coordinate is
--- a yalm inside the wall -- is the normal case, not the exception.
--- Returns cx, cz, layer.  With a height, the floor nearest it: a player on the bridge
--- snaps to the bridge, not to the street underneath.
local function snap(g, cx, cz, y, radius)
    local l = floor_near(g, cx, cz, y)
    if l ~= nil then return cx, cz, l end
    for r = 1, (radius or 8) do
        for d = -r, r do
            for _, c in ipairs({ { cx + d, cz - r }, { cx + d, cz + r },
                                 { cx - r, cz + d }, { cx + r, cz + d } }) do
                l = floor_near(g, c[1], c[2], y)
                if l ~= nil then return c[1], c[2], l end
            end
        end
    end
    return nil
end

-- ---------------------------------------------------------------------------------
-- a binary heap, because a linear scan over an open set of thousands is the whole cost

local function heap_push(heap, f, node, index)
    local n = #heap + 1
    heap[n] = node
    index[node] = f
    while n > 1 do
        local parent = math.floor(n / 2)
        if index[heap[parent]] <= index[heap[n]] then break end
        heap[parent], heap[n] = heap[n], heap[parent]
        n = parent
    end
end

local function heap_pop(heap, index)
    local top = heap[1]
    local n = #heap
    heap[1] = heap[n]
    heap[n] = nil
    n = n - 1
    local i = 1
    while true do
        local l, r = i * 2, i * 2 + 1
        local best = i
        if l <= n and index[heap[l]] < index[heap[best]] then best = l end
        if r <= n and index[heap[r]] < index[heap[best]] then best = r end
        if best == i then break end
        heap[i], heap[best] = heap[best], heap[i]
        i = best
    end
    return top
end

-- ---------------------------------------------------------------------------------
-- the search

local search = nil

local DIRS = {
    { 1, 0, 1 }, { -1, 0, 1 }, { 0, 1, 1 }, { 0, -1, 1 },
    { 1, 1, 1.41421 }, { 1, -1, 1.41421 }, { -1, 1, 1.41421 }, { -1, -1, 1.41421 },
}

--- Start a search, or keep the one already running if it is for the same journey.
function N.request(zone, x1, z1, x2, z2, y1, y2)
    local g = N.load(zone)
    if g == nil then return false end
    if search ~= nil and search.zone == zone
        and math.abs(search.sx - x1) < g.cell and math.abs(search.sz - z1) < g.cell
        and math.abs(search.tx - x2) < g.cell and math.abs(search.tz - z2) < g.cell then
        return true
    end

    local ax, az = to_cell(g, x1, z1)
    local scx, scz, sl = snap(g, ax, az, y1)
    local bx, bz = to_cell(g, x2, z2)
    local tcx, tcz, tl = snap(g, bx, bz, y2)
    if scx == nil or tcx == nil then
        -- One end is nowhere the mesh knows about.  Say so once and let the straight line
        -- stand; this is a fact about the target, not a failure to try.
        search = { zone = zone, sx = x1, sz = z1, tx = x2, tz = z2, state = 'fail' }
        N.state = 'off the mesh'
        return true
    end

    local start = (scz * g.w + scx) * 2 + sl
    local goal  = (tcz * g.w + tcx) * 2 + tl
    search = {
        zone = zone, g = g, sx = x1, sz = z1, tx = x2, tz = z2,
        start = start, goal = goal, gx = tcx, gz = tcz,
        heap = {}, f = {}, gscore = { [start] = 0 }, came = {},
        closed = {}, expansions = 0, state = 'working',
    }
    heap_push(search.heap, 0, start, search.f)
    N.state = 'working'
    return true
end

local function octile(g, ax, az, bx, bz)
    local dx, dz = math.abs(ax - bx), math.abs(az - bz)
    local lo, hi = dx, dz
    if lo > hi then lo, hi = hi, lo end
    return (hi - lo + 1.41421 * lo) * g.cell
end

--- Advance the current search.  Call it once a frame; it does `budget` expansions and stops.
function N.step(budget)
    if search == nil or search.state ~= 'working' then return search and search.state or 'idle' end
    local g = search.g
    local heap, f, gscore, came, closed = search.heap, search.f, search.gscore, search.came, search.closed
    local goal, gx, gz = search.goal, search.gx, search.gz
    local w = g.w
    budget = budget or N.per_frame

    for _ = 1, budget do
        if #heap == 0 then
            search.state = 'fail'
            N.state = 'no route'
            return 'fail'
        end
        local node = heap_pop(heap, f)
        if node == goal then
            search.state = 'done'
            N.state = 'done'
            N.searched = search.expansions
            return 'done'
        end
        if not closed[node] then
            closed[node] = true
            search.expansions = search.expansions + 1
            if search.expansions > N.max_expansions then
                search.state = 'fail'
                N.state = 'gave up'
                return 'fail'
            end
            local layer = node % 2
            local cell = (node - layer) / 2
            local cz = math.floor(cell / w)
            local cx = cell - cz * w
            local y = height_at(g, cx, cz, layer)
            local base = gscore[node]
            for i = 1, 8 do
                local d = DIRS[i]
                local nx, nz = cx + d[1], cz + d[2]
                -- The floor next door you can actually step onto from this height: on a
                -- bridge that is the bridge, and the street under it is a different node.
                local nl = step_onto(g, nx, nz, y)
                if nl ~= nil then
                    -- No cutting corners: a diagonal is only a step if both of the squares
                    -- beside it are open, or the path clips the corner of a building and the
                    -- line drawn from it goes through a wall.
                    local okd = true
                    if d[1] ~= 0 and d[2] ~= 0 then
                        okd = step_onto(g, cx + d[1], cz, y) ~= nil
                          and step_onto(g, cx, cz + d[2], y) ~= nil
                    end
                    if okd then
                        local nnode = (nz * w + nx) * 2 + nl
                        local ng = base + d[3] * g.cell
                        if gscore[nnode] == nil or ng < gscore[nnode] then
                            gscore[nnode] = ng
                            came[nnode] = node
                            heap_push(heap, ng + octile(g, nx, nz, gx, gz), nnode, f)
                        end
                    end
                end
            end
        end
    end
    return 'working'
end

--- Is there a clear run of walkable cells between two of them?  Bresenham, used to throw
--- away the staircase A* produces and keep only the corners.
local function line_of_sight(g, x0, z0, x1, z1, y)
    local dx, dz = math.abs(x1 - x0), math.abs(z1 - z0)
    local sx = (x0 < x1) and 1 or -1
    local sz = (z0 < z1) and 1 or -1
    local err = dx - dz
    while true do
        -- Follow the floor: each cell must have a surface within a step of the last one,
        -- so a sight line cannot hop from the bridge to the street below it.
        local l = step_onto(g, x0, z0, y)
        if l == nil then return false end
        y = height_at(g, x0, z0, l)
        if x0 == x1 and z0 == z1 then return true end
        local e2 = err * 2
        if e2 > -dz then err = err - dz; x0 = x0 + sx end
        if e2 < dx then err = err + dx; z0 = z0 + sz end
    end
end

--- The finished path, as world points, or nil while the search is still running.
--- Second return is true when the caller should ask again.
function N.provide(zone, x1, z1, y1, x2, z2, y2)
    if not N.request(zone, x1, z1, x2, z2, y1, y2) then return nil, false end
    if search.state == 'working' then return nil, true end
    if search.state ~= 'done' then return nil, false end
    if search.points ~= nil then return search.points, false end

    local g = search.g
    local cells, node = {}, search.goal
    local guard = 0
    while node ~= nil do
        table.insert(cells, 1, node)
        node = search.came[node]
        guard = guard + 1
        if guard > 200000 then return nil, false end
    end

    -- Keep a cell only when the line from the last kept one to the *next* one is blocked.
    -- Eighty staircase steps become five corners, and the drawn line stops looking like a
    -- flight of stairs laid on the ground.
    local function unpack_node(n)
        local layer = n % 2
        local c = (n - layer) / 2
        local cz = math.floor(c / g.w)
        return c - cz * g.w, cz, layer
    end
    local kept = { cells[1] }
    local anchor = 1
    for i = 3, #cells do
        local ax, az, al = unpack_node(cells[anchor])
        local bx, bz = unpack_node(cells[i])
        if not line_of_sight(g, ax, az, bx, bz, height_at(g, ax, az, al)) then
            kept[#kept + 1] = cells[i - 1]
            anchor = i - 1
        end
    end
    kept[#kept + 1] = cells[#cells]

    -- Corners alone are not enough.  A straight run of two hundred yalms across La Theine
    -- crosses three hills, and a line drawn from corner to corner interpolates its height
    -- between the ends and buries itself in the first one.  Sample the grid along the way.
    local stride = math.max(1, math.floor(6 / g.cell))
    local points = {}
    local function emit(cx, cz, layer)
        local wx, wz = to_world(g, cx, cz)
        points[#points + 1] = { x = wx, z = wz, y = height_at(g, cx, cz, layer) }
    end
    for i = 1, #kept do
        local cx, cz, layer = unpack_node(kept[i])
        if i > 1 then
            local px, pz, pl = unpack_node(kept[i - 1])
            -- Between two corners the floor is followed cell by cell, so a sample on a
            -- bridge takes the bridge's height and not the street's.
            local y = height_at(g, px, pz, pl)
            local steps = math.max(math.abs(cx - px), math.abs(cz - pz))
            local k = stride
            while k < steps do
                local t = k / steps
                local sx = math.floor(px + (cx - px) * t + 0.5)
                local sz = math.floor(pz + (cz - pz) * t + 0.5)
                local l = step_onto(g, sx, sz, y) or floor_near(g, sx, sz, y)
                if l ~= nil then
                    y = height_at(g, sx, sz, l)
                    emit(sx, sz, l)
                end
                k = k + stride
            end
        end
        emit(cx, cz, layer)
    end
    -- The ends are the real ones, not the middle of whatever cell they landed in.
    points[1] = { x = x1, z = z1, y = y1 or points[1].y }
    points[#points] = { x = x2, z = z2, y = y2 or points[#points].y }
    search.points = points
    return points, false
end

--- Install as routing/path.lua's provider.  Kept separate so the module can be required and
--- tested without changing how anything draws.
function N.install(Path)
    Path.provider = function (zone, x1, z1, y1, x2, z2, y2)
        return N.provide(zone, x1, z1, y1, x2, z2, y2)
    end
end

function N.status()
    if N.grid == nil then
        return 'navmesh: none loaded (see docs/NAVMESH.md)'
    end
    return ('navmesh: zone %d, %dx%d at %.0f yalms, %d floor%s, %s (%d cells searched)')
        :format(N.grid.zone, N.grid.w, N.grid.h, N.grid.cell, N.grid.layers,
                N.grid.layers == 1 and '' or 's', N.state, N.searched)
end

--- Forget everything.  The tests move between zones faster than a player can.
function N.reset()
    N.loaded, N.grid, search = nil, nil, nil
    N.missing = {}
    N.state = 'idle'
end

return N
