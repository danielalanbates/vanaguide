--[[
* Vanaguide -- a guided-walkthrough addon for FINAL FANTASY XI (Ashita v4).
*
* Shows the next thing to do, ticks it off when the server says you have done it, and
* points an arrow at where to go, routing across zones when "there" is a continent away.
*
* Commands:
*   /vanaguide, /vg            show or hide the guide window
*   /vg guides                 pick a guide
*   /vg next | back | skip     move through the current guide
*   /vg route                  explain the route to the current step
*   /vg mark <name>            record where you are standing into marks.txt (guide authoring)
*   /vg arrow flip             flip the arrow's rotation if it points the wrong way
*   /vg arrow nudge <degrees>  rotate the arrow by a fixed offset
*   /vg reset                  start the current guide again
*
* Copyright (c) 2026 Bates LLC.  All rights reserved.
* https://batesai.org  ·  help@batesai.org
--]]

addon.name    = 'Vanaguide';
addon.author  = 'Bates LLC';
addon.version = '0.1.0';
addon.desc    = 'Step-by-step quest and mission guides with a routing arrow.';
addon.link    = 'https://batesai.org';

require('common');

-- LuaJIT's mcode patcher faults inside Ashita 4.3's Addons.dll on this project's Wine
-- build; every addon here turns the JIT off for the same reason.  See
-- HorizonXI-on-Mac docs/ADDONS.md.
if (jit ~= nil and jit.off ~= nil) then jit.off(true, true); end

-- Ashita puts the addon's own folder on package.path, but say it explicitly: a path that
-- silently lacks it turns every require below into a confusing "module not found".
do
    local ok, root = pcall(function () return AshitaCore:GetInstallPath(); end);
    if (ok and root ~= nil and root ~= '') then
        root = root:gsub('[\\/]$', '');
        package.path = ('%s\\addons\\Vanaguide\\?.lua;%s'):format(root, package.path);
    end
end

local settings = require('settings');

local U      = require('core.util');
local story  = require('core.story');
local G      = require('core.guide');
local C      = require('core.conditions');
local P      = require('core.progress');
local graph  = require('routing.zonegraph');
local R      = require('routing.router');
local L      = require('core.lookup');
local Verify = require('core.verify');
local Arrow  = require('ui.arrow');
local Window = require('ui.window');

require('guides.init');

local default_settings = T{
    guide = '',
    progress = T{},          -- [guide name] = { index, checked, skipped }
    learned = T{},           -- zone lines this character has crossed
    arrow = T{ visible = true, calibration = 1, offset = 0, x = 0.5, y = 0.28 },
    window = T{ visible = true },
};

local vg = {
    settings = settings.load(default_settings),
    last_zone = nil,
    last_advance = 0,
    results = {},
    was_logged_in = false,
    d3d8 = nil,
};

local function save_progress()
    if (P.guide == nil) then return; end
    vg.settings.guide = P.guide.name;
    vg.settings.progress[P.guide.name] = P.save_state();
    vg.settings.learned = graph.save_learned();
    settings.save();
end

local function load_guide(name)
    local guide = G.get(name);
    if (guide == nil) then
        U.print('no guide named "' .. tostring(name) .. '"');
        return false;
    end
    P.set_guide(guide, vg.settings.progress[name]);
    save_progress();
    U.print(('loaded "%s" (%d steps, on step %d)'):format(guide.name, P.count(), P.index));
    return true;
end

local function apply_settings(s)
    if (s ~= nil) then vg.settings = s; end
    graph.load_learned(vg.settings.learned);
    Arrow.calibration = vg.settings.arrow.calibration or 1;
    Arrow.offset = vg.settings.arrow.offset or 0;
    Arrow.move(vg.settings.arrow.x or 0.5, vg.settings.arrow.y or 0.28);
    Window.open[1] = vg.settings.window.visible ~= false;
    if (vg.settings.guide ~= nil and vg.settings.guide ~= '') then
        load_guide(vg.settings.guide);
    end
end

settings.register('settings', 'settings_update', apply_settings);

--- Guide authoring helper: write where the player is standing to a file the guide format
--- can be pasted from.  Coordinates in guides should come from somebody actually standing
--- there, which is the whole reason this exists.
local function mark(name)
    local x, z, y = U.position();
    local zone = U.zone();
    if (x == nil or zone == nil) then U.print('not in the world'); return; end
    local line = ('%s|Z|%d|POS|%.1f,%.1f,10|N|%s, y=%.1f|')
        :format(name or 'mark', zone, x, z, U.zone_name(zone), y or 0);
    local path = ('%s\\addons\\Vanaguide\\marks.txt'):format(AshitaCore:GetInstallPath():gsub('[\\/]$', ''));
    -- Binary mode on purpose. Lua on Windows opens files in text mode and rewrites every
    -- \n as \r\n, and marks.txt is meant to be read on the Mac side; a sibling project lost
    -- whole multi-line bursts to exactly that (VanaVoice, 2026-08-22).
    local f = io.open(path, 'ab');
    if (f ~= nil) then f:write(line, '\n'); f:close(); end
    U.print(line);
end

ashita.events.register('load', 'vg_load', function ()
    apply_settings(nil);
    U.print(('v%s loaded. /vg for the window, /vg guides to pick one.'):format(addon.version));
end);

ashita.events.register('unload', 'vg_unload', function ()
    save_progress();
    settings.save();
end);

ashita.events.register('packet_in', 'vg_packet_in', function (e)
    story.on_packet(e.id, e.data, e.size);
end);

ashita.events.register('command', 'vg_command', function (e)
    local args = e.command:args();
    if (#args == 0 or not args[1]:any('/vanaguide', '/vg')) then return; end
    e.blocked = true;

    local sub = (#args > 1) and args[2]:lower() or '';

    if (sub == '') then
        Window.toggle();
        vg.settings.window.visible = Window.open[1];
        settings.save();
        return;
    end

    -- Guides are listed with a number, and `/vg load 7` takes it.  Typing
    -- "San d'Oria — every quest" into the FFXI chat box is not a thing anyone will do,
    -- and on this Mac port the window's buttons cannot be clicked at all (see
    -- HorizonXI-on-Mac docs/MOUSE.md), so the numbers are the real interface.
    if (sub == 'guides' or sub == 'list') then
        Window.picker[1] = true;
        for i, g in ipairs(G.list()) do
            U.print(('  %2d. %s  (%d steps%s)')
                :format(i, g.name, #g.steps, g.levels and (', levels ' .. g.levels) or ''));
        end
        U.print('load one with /vg load <number>');
        return;
    end

    if (sub == 'load' and #args > 2) then
        local wanted = table.concat({ unpack(args, 3) }, ' ');
        local n = tonumber(wanted);
        if (n ~= nil) then
            local list = G.list();
            if (list[n] == nil) then
                U.print(('there is no guide %d; /vg guides lists them'):format(n));
            else
                load_guide(list[n].name);
            end
        else
            load_guide(wanted);
        end
        return;
    end

    if (sub == 'next' or sub == 'done') then P.check(); P.advance(); save_progress(); return; end
    if (sub == 'skip') then P.skip(); P.advance(); save_progress(); return; end
    if (sub == 'back') then P.back(); save_progress(); return; end
    if (sub == 'reset') then
        if (P.guide ~= nil) then
            vg.settings.progress[P.guide.name] = nil;
            P.set_guide(P.guide, nil);
            save_progress();
            U.print('progress reset');
        end
        return;
    end

    -- Lookups.  Each prints a numbered list and remembers it, so `/vg track 2` can turn any
    -- line of it into the active step -- same arrow, same router, no second navigation path.
    if (sub == 'find' and #args > 2) then
        local text = table.concat({ unpack(args, 3) }, ' ');
        vg.results = {};
        for _, item in ipairs(L.find_item(text)) do
            for _, src in ipairs(item.sources) do
                vg.results[#vg.results + 1] = {
                    title = item.name, text = ('%s: %s'):format(item.name, src.text),
                    zone = src.zone, x = src.x, z = src.z,
                    note = ('level %d %s%s'):format(item.level, item.slot,
                        item.rare and ' (rare)' or (item.ex and ' (ex)' or '')),
                };
                if (#vg.results >= 15) then break; end
            end
            if (#vg.results >= 15) then break; end
        end
        if (#vg.results == 0) then
            U.print(('nothing called "%s" that anything drops or sells'):format(text));
        else
            for i, r in ipairs(vg.results) do U.print(('  %2d. %s'):format(i, r.text)); end
            U.print('/vg track <number> to point the arrow at one');
        end
        return;
    end

    if (sub == 'gear') then
        local slot = (#args > 2) and args[3]:lower() or 'body';
        local job, level = U.main_job();
        vg.results = {};
        for _, item in ipairs(L.gear_for(slot, level, job)) do
            local src = item.sources[1];
            vg.results[#vg.results + 1] = {
                title = item.name, text = ('%s (lvl %d) - %s'):format(item.name, item.level, src.text),
                zone = src.zone, x = src.x, z = src.z,
            };
        end
        if (#vg.results == 0) then
            U.print(('no %s gear with a source at level %d for this job'):format(slot, level or 0));
        else
            U.print(('%s, for your level and job:'):format(slot));
            for i, r in ipairs(vg.results) do U.print(('  %2d. %s'):format(i, r.text)); end
            U.print('/vg track <number>');
        end
        return;
    end

    if (sub == 'nm') then
        local where = (#args > 2) and table.concat({ unpack(args, 3) }, ' ') or nil;
        vg.results = {};
        for _, n in ipairs(L.nms(where)) do
            local place = n.x and ('%s (%.0f, %.0f)'):format(U.zone_name(n.zone), n.x, n.z)
                or ('%s (spot unknown)'):format(U.zone_name(n.zone));
            vg.results[#vg.results + 1] = {
                title = n.name, text = ('%s, level %d-%d, %s'):format(n.name, n.lo, n.hi, place),
                zone = n.zone, x = n.x, z = n.z,
                note = (#n.loot > 0) and ('%d things drop from it'):format(#n.loot) or nil,
            };
            if (#vg.results >= 20) then break; end
        end
        if (#vg.results == 0) then
            U.print(where and ('no notorious monster called "' .. where .. '"')
                or 'no notorious monsters recorded in this zone');
        else
            for i, r in ipairs(vg.results) do U.print(('  %2d. %s'):format(i, r.text)); end
            U.print('/vg track <number>');
        end
        return;
    end

    if (sub == 'track' and #args > 2) then
        local n = tonumber(args[3]);
        local r = n and vg.results and vg.results[n];
        if (r == nil) then U.print('no such result; run /vg find, /vg gear or /vg nm first'); return; end
        L.track(P, r);
        save_progress();
        U.print('tracking: ' .. r.text);
        return;
    end

    -- What the addon can actually see. The first thing to ask when nothing is drawing.
    if (sub == 'status') then
        local x, z, y = U.position();
        U.print(('login=%s zone=%s (%s) pos=%s,%s,%s yaw=%s')
            :format(tostring(U.logged_in()), tostring(U.zone()), U.zone_name(U.zone()),
                    x and ('%.1f'):format(x) or '?', z and ('%.1f'):format(z) or '?',
                    y and ('%.1f'):format(y) or '?',
                    U.heading() and ('%.2f'):format(U.heading()) or '?'));
        local step = P.step();
        if (step ~= nil) then
            local w = C.world(); w.yaw = U.heading();
            local rec = R.recommend(step, w);
            U.print(('step="%s" mode=%s dist=%s bearing=%s deg  %s')
                :format(step.text, rec.mode,
                        rec.distance and ('%.1f'):format(rec.distance) or '-',
                        rec.bearing and ('%.0f'):format(math.deg(rec.bearing)) or '-',
                        rec.text or ''));
        end
        U.print(('window=%s arrow=%s guide=%s step=%d/%d imgui=%s')
            :format(tostring(Window.open[1]), tostring(vg.settings.arrow.visible ~= false),
                    P.guide and P.guide.name or 'none', P.index, P.count(),
                    tostring((pcall(require, 'imgui')))));
        return;
    end

    -- What the server has actually told us about this character's log. This is the only
    -- source for quest and mission completion (docs/PACKETS.md), so if it is empty, every
    -- `Q` and `M` step in every guide is waiting on nothing.
    if (sub == 'story') then
        local areas, flags = 0, 0;
        for area, set in pairs(story.quest.completed) do
            areas = areas + 1;
            for _ in pairs(set) do flags = flags + 1; end
        end
        local missions = {};
        for area, id in pairs(story.mission.current) do
            missions[#missions + 1] = ('%s=%s'):format(area, tostring(id));
        end
        table.sort(missions);
        local pages, unknown = 0, {};
        for _ in pairs(story.pages) do pages = pages + 1; end
        for page in pairs(story.unknown_pages) do unknown[#unknown + 1] = ('0x%04X'):format(page); end
        U.print(('story: 0x056 packets=%d  distinct pages=%d  unknown pages=%s')
            :format(story.packets, pages, next(unknown) and table.concat(unknown, ',') or 'none'));
        for page, set in pairs(story.unknown_sets or {}) do
            local bits = {};
            for id in pairs(set) do bits[#bits + 1] = id; end
            table.sort(bits);
            U.print(('story: page 0x%04X has bits: %s'):format(page,
                next(bits) and table.concat(bits, ',') or '(none set)'));
        end
        U.print(('story: seen=%s  quest areas=%d  completed quests=%d  nation=%s')
            :format(tostring(story.seen), areas, flags, tostring(story.nation)));
        U.print('current missions: ' .. (next(missions) and table.concat(missions, ' ') or '(none)'));
        return;
    end

    -- Stand on a quest's coordinates and check the NPC is really there. Writes a CSV row to
    -- addons/Vanaguide/verify.csv as well as printing, because a full sweep is hundreds of
    -- these and they are read by a script.  See docs/QUEST_VERIFICATION.md.
    -- `/vg verify <area> <id>` for a quest, `/vg verify m <area> <id>` for a mission.
    if (sub == 'verify' and #args > 4 and args[3]:lower() == 'm') then
        local r = Verify.entry('mission', args[4]:lower(), tonumber(args[5]) or -1);
        Verify.log('verify.csv', Verify.row(r));
        U.print(('verify mission %s %s: %s — %s'):format(r.area, tostring(r.id),
            r.ok and 'ok' or 'MISS', r.why));
        return;
    end
    if (sub == 'verify' and #args > 3) then
        local r = Verify.entry('quest', args[3]:lower(), tonumber(args[4]) or -1);
        Verify.log('verify.csv', Verify.row(r));
        U.print(('verify %s %s: %s — %s'):format(r.area, tostring(r.id),
            r.ok and 'ok' or 'MISS', r.why));
        return;
    end

    -- What is loaded around me right now: the raw material the check above works from.
    if (sub == 'nearby') then
        local x, z = U.position();
        local list = Verify.nearby(x, z);
        U.print(('%d entities loaded here'):format(#list));
        for i = 1, math.min(8, #list) do
            U.print(('  %-24s %5.1f yalms'):format(list[i].name, list[i].dist or -1));
        end
        return;
    end

    -- Copy everything printed to a file as well as to chat. A script driving the client
    -- through cmd.txt has no way to read the game's chat log, so without this the only
    -- commands it can check are the ones that happen to write a file of their own.
    --   /vg tee answers.txt   -> addons/Vanaguide/answers.txt
    --   /vg tee off
    if (sub == 'tee') then
        local name = (#args > 2) and args[3] or 'off';
        if (name:lower() == 'off') then
            U.tee = nil;
            U.print('tee off');
        else
            local base = AshitaCore:GetInstallPath():gsub('[\\/]$', '');
            U.tee = ('%s\\addons\\Vanaguide\\%s'):format(base, name);
            U.print('tee -> ' .. name);
        end
        return;
    end

    -- What the zone graph has learned from play, and whether it is learning at all. The
    -- graph records every crossing (docs/ROUTING.md) and until now nothing could read the
    -- result back, so "zone-line learning works" was an untested claim in the docs.
    if (sub == 'graph') then
        local learned, seed = {}, 0;
        for key in pairs(graph.save_learned() or {}) do learned[#learned + 1] = key; end
        for _ in pairs(graph.adj or {}) do seed = seed + 1; end
        table.sort(learned);
        U.print(('graph: %d zones with edges, %d learned crossings'):format(seed, #learned));
        for i = 1, math.min(20, #learned) do U.print('  learned ' .. learned[i]); end
        return;
    end

    if (sub == 'route') then
        local step = P.step();
        if (step == nil or step.zone == nil) then U.print('the current step has no place'); return; end
        local legs = graph.route(U.zone(), step.zone);
        U.print(R.describe(legs));
        return;
    end

    if (sub == 'mark') then
        mark(#args > 2 and table.concat({ unpack(args, 3) }, ' ') or nil);
        return;
    end

    if (sub == 'arrow') then
        local what = (#args > 2) and args[3]:lower() or '';
        if (what == 'flip') then
            Arrow.calibration = -Arrow.calibration;
            vg.settings.arrow.calibration = Arrow.calibration;
        elseif (what == 'nudge' and #args > 3) then
            local deg = tonumber(args[4]) or 0;
            Arrow.offset = Arrow.offset + math.rad(deg);
            vg.settings.arrow.offset = Arrow.offset;
        elseif (what == 'on' or what == 'off') then
            vg.settings.arrow.visible = (what == 'on');
        elseif (what == 'move' or what == 'pos') then
            -- Dragging is not available: this client gives Ashita no mouse button messages at
            -- all (HorizonXI-on-Mac docs/MOUSE.md), so the arrow is moved by saying where it
            -- goes. Percentages of the screen, so it survives a resolution change.
            local px = tonumber(args[4]);
            local py = tonumber(args[5]);
            if (px == nil or py == nil) then
                U.print('/vg arrow move <across%> <down%>   e.g. /vg arrow move 50 28');
                return;
            end
            local rx, ry = Arrow.move(px / 100, py / 100);
            vg.settings.arrow.x, vg.settings.arrow.y = rx, ry;
        elseif (what == 'reset') then
            local rx, ry = Arrow.move(0.5, 0.28);
            vg.settings.arrow.x, vg.settings.arrow.y = rx, ry;
        end
        settings.save();
        U.print(('arrow: %s, at %.0f%% across and %.0f%% down, calibration %d, offset %.0f degrees')
            :format(vg.settings.arrow.visible and 'on' or 'off',
                    (vg.settings.arrow.x or 0.5) * 100, (vg.settings.arrow.y or 0.28) * 100,
                    Arrow.calibration, math.deg(Arrow.offset)));
        U.print('/vg arrow move <across%> <down%> | reset | flip | nudge <deg> | on | off');
        return;
    end

    U.print('commands: guides, load <n>, next, back, skip, reset, route, mark, arrow');
    U.print('lookups:  find <item>, gear <slot>, nm [name], track <n>');
end);

--- A file the shell can write to run commands in the game.
---
--- Driving this client from outside is otherwise a keyboard-simulation problem, and a fragile
--- one: Return opens the chat line only when nothing is targeted, so a stray target turns
--- every scripted command into "Target out of range". Ashita's own idea -- the same trick
--- `mousediag` used -- is a file poll. Write one command per line into
--- `<install>\addons\Vanaguide\cmd.txt`; each is run once and the file is emptied.
---
--- It executes only what a player could type. It is here for verification and for people
--- driving a client they own; it sends nothing to the server on its own.
local function pump_commands()
    local path = ('%s\\addons\\Vanaguide\\cmd.txt')
        :format(AshitaCore:GetInstallPath():gsub('[\\/]$', ''));
    local f = io.open(path, 'r');
    if (f == nil) then return; end
    local lines = {};
    for line in f:lines() do
        line = line:gsub('^%s+', ''):gsub('%s+$', '');
        if (line ~= '') then lines[#lines + 1] = line; end
    end
    f:close();
    if (#lines == 0) then return; end
    -- Emptied before running: a command that reloads this addon would otherwise re-read the
    -- same file after the reload and run everything again, forever.
    local w = io.open(path, 'w');
    if (w ~= nil) then w:close(); end
    for _, line in ipairs(lines) do
        AshitaCore:GetChatManager():QueueCommand(-1, line);
    end
end

ashita.events.register('d3d_present', 'vg_present', function ()
    pump_commands();
    -- Gate on being in a zone, not on GetLoginStatus(). Measured in-game 2026-08-22: the
    -- status word is not 2 on this client while standing in Southern San d'Oria, so gating on
    -- it drew nothing at all -- the commands worked and the window never appeared.
    if (U.zone() == nil) then
        -- Back at the character select.  The quest flags belong to whoever was logged in,
        -- and keeping them would silently mark the next character's steps done.
        if (vg.was_logged_in) then
            story.reset();
            vg.was_logged_in = false;
            vg.last_zone = nil;
        end
        return;
    end
    vg.was_logged_in = true;

    local w = C.world();
    w.yaw = U.heading();

    -- Learn the zone line we just crossed.  This is what fills in the travel graph.
    if (w.zone ~= nil and w.zone ~= vg.last_zone) then
        if (vg.last_zone ~= nil and graph.learn(vg.last_zone, w.zone)) then
            vg.settings.learned = graph.save_learned();
            settings.save();
        end
        vg.last_zone = w.zone;
    end

    -- Advancing walks the whole remaining guide in the worst case; once a second is plenty.
    local now = os.time();
    if (now ~= vg.last_advance) then
        vg.last_advance = now;
        if (P.advance(w) > 0) then save_progress(); end
    end

    -- The viewport, before anything is drawn: the window sizes itself against the screen, so
    -- it has to know the screen even when there is no guide loaded and no arrow to place.
    -- (The local test world runs at 640x480; a window sized for 1920 covers half of it.)
    local ok, vp = pcall(function ()
        if (vg.d3d8 == nil) then vg.d3d8 = require('d3d8'); end
        local res, v = vg.d3d8.get_device():GetViewport();
        if (res == 0) then return v; end
        return nil;
    end);
    if (ok and vp ~= nil) then
        Arrow.set_viewport(vp.Width, vp.Height);
        Window.set_viewport(vp.Width, vp.Height);
    end

    Window.draw(w, function (name) load_guide(name); end);

    if (vg.settings.arrow.visible ~= false and P.guide ~= nil) then
        local step = P.step();
        if (step ~= nil) then
            local rec = R.recommend(step, w);
            if (rec.mode == 'here' and rec.bearing ~= nil) then
                Arrow.draw(rec.bearing, rec.distance,
                    ('%.0f yalms'):format(rec.distance or 0), step.text);
            elseif (rec.mode == 'travel') then
                Arrow.draw(0, nil, rec.text, U.zone_name(rec.destination));
            end
        end
    end
end);
