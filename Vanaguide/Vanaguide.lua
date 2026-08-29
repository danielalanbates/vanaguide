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
*   /vg route                  explain the route to the current step, leg by leg
*   /vg goto <zone>            route to any zone, guide or no guide; /vg goto off to stop
*   /vg nav                    whether a navigation grid is loaded for this zone
*   /vg line on | off          the line on the ground that shows the way
*   /vg line style solid|dots|both, /vg line width <px>, /vg line horizon <yalms>
*   /vg walk [auto|stop|status|speed <y/s>]   walk the character to the target (LOCAL WORLD ONLY)
*   /vg mark <name>            record where you are standing into marks.txt (guide authoring)
*   /vg dump graph             write the learned zone lines as a paste-ready seed block
*   /vg arrow flip             flip the arrow's rotation if it points the wrong way
*   /vg arrow nudge <degrees>  rotate the arrow by a fixed offset
*   /vg reset                  start the current guide again
*
* Copyright (c) 2026 Bates LLC.  All rights reserved.
* https://batesai.org  ·  help@batesai.org
--]]

addon.name    = 'Vanaguide';
addon.author  = 'Bates LLC';
addon.version = '0.2.0';
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
local Learned = require('core.learned');
local Verify = require('core.verify');
local Arrow  = require('ui.arrow');

-- Where the arrow sits by default, as a fraction of the screen, and how big it is.
-- Centred horizontally and low on the screen: Daniel asked for it directly under the macro
-- bar rather than up in the middle of the view, where it covered what he was walking into.
-- Measured from a real 2560x1600 frame, not guessed -- see docs/ARROW.md.
-- The arrow lives at the top, under the game's command bar. It used to sit at 0.86 -- down
-- among the chat log, the party list and the target bar, competing with all of them for the
-- one glance it exists to catch. Daniel asked for it moved on 2026-08-25.
local ARROW_X, ARROW_Y = 0.5, 0.12
local ARROW_Y_OLD = 0.86        -- the position being migrated away from; see apply_settings
local ARROW_SCALE = 0.6
local Window = require('ui.window');
local Line   = require('ui.line');
local Path   = require('routing.path');
local points = require('routing.zonepoints');
local Project = require('ui.project');
-- The navigation grid is optional: with no data/nav/<zone>.vgnav it answers "no" and the
-- line stays straight.  See docs/NAVMESH.md -- the grids are generated, never shipped.
local Nav    = require('routing.navgrid');
local Walk   = require('core.walk');

require('guides.init');

local default_settings = T{
    guide = '',
    progress = T{},          -- [guide name] = { index, checked, skipped }
    learned = T{},           -- zone lines this character has crossed
    arrow = T{ visible = true, calibration = 1, offset = 0, x = ARROW_X, y = ARROW_Y, scale = ARROW_SCALE },
    -- The line is on by default: it is the thing that makes the guide readable at a glance,
    -- and it turns itself off and says why if the device will not project (ui/line.lua).
    line = T{ visible = true, style = 'both', width = 4, horizon = 40 },
    window = T{ visible = true },
};

local vg = {
    settings = settings.load(default_settings),
    last_zone = nil,
    last_advance = 0,
    results = {},
    was_logged_in = false,
    last_index = nil,
    -- A destination the player asked for by name, which outranks the guide's own step while
    -- it is set.  Wanting to get somewhere is not always the same as wanting to do the next
    -- thing in a walkthrough, and every guide program has this.
    goto_step = nil,
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
    -- Zone lines are account-wide (core/learned.lua): merge the shared file with anything
    -- this character learned before the graph became shared, adopt the union, and write it
    -- back once so the per-character copy is migrated.  A character now starts with every
    -- road any character on this install has already walked, not a blank map.
    local shared = Learned.load();
    local merged = Learned.merge(shared, vg.settings.learned);
    graph.load_learned(merged);
    vg.settings.learned = graph.save_learned();
    local grew = false;
    for k in pairs(vg.settings.learned) do if not shared[k] then grew = true; break; end end
    if (grew) then Learned.save(vg.settings.learned); end
    Arrow.calibration = vg.settings.arrow.calibration or 1;
    Arrow.offset = vg.settings.arrow.offset or 0;
    -- A saved position wins over the default, which would have left every existing install
    -- sitting at the old spot for ever. Anyone still on the old default is moved once; a
    -- position somebody actually chose is left alone, because it will not be exactly 0.86.
    if (vg.settings.arrow.y == ARROW_Y_OLD) then
        vg.settings.arrow.y = ARROW_Y;
    end
    Arrow.move(vg.settings.arrow.x or ARROW_X, vg.settings.arrow.y or ARROW_Y);
    Arrow.scale = vg.settings.arrow.scale or ARROW_SCALE;
    Arrow.locked = vg.settings.arrow.locked ~= false;
    if (vg.settings.line == nil) then vg.settings.line = T{ visible = true, style = 'both', width = 4 }; end
    Line.enabled = vg.settings.line.visible ~= false;
    Line.style   = vg.settings.line.style or 'both';
    Line.width   = vg.settings.line.width or 4;
    Line.horizon = vg.settings.line.horizon or 40;
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
    -- The height goes in POS as the fourth number, not only in the note: the line on the
    -- ground needs it, and a note is prose.
    local line = ('%s|Z|%d|POS|%.1f,%.1f,10,%.1f|N|%s|')
        :format(name or 'mark', zone, x, z, y or 0, U.zone_name(zone));
    local path = ('%s\\addons\\Vanaguide\\marks.txt'):format(AshitaCore:GetInstallPath():gsub('[\\/]$', ''));
    -- Binary mode on purpose. Lua on Windows opens files in text mode and rewrites every
    -- \n as \r\n, and marks.txt is meant to be read on the Mac side; a sibling project lost
    -- whole multi-line bursts to exactly that (VanaVoice, 2026-08-22).
    local f = io.open(path, 'ab');
    if (f ~= nil) then f:write(line, '\n'); f:close(); end
    U.print(line);
end

ashita.events.register('load', 'vg_load', function ()
    Nav.install(Path);
    apply_settings(nil);
    U.print(('v%s loaded. /vg for the window, /vg guides to pick one.'):format(addon.version));
end);

ashita.events.register('unload', 'vg_unload', function ()
    save_progress();
    settings.save();
end);

-- The event the server currently has open on this client.
--
-- Talking to an NPC does not end when the NPC has spoken: the client is left holding an
-- event, waiting for the player to press Enter. Nothing scripted can press Enter, so the
-- second `/vg talk` in a row did nothing at all and looked exactly like the first one having
-- failed -- see docs/DRIVING_THE_CLIENT.md, which is where that cost a day.
--
-- The way out is to end the event the way the client does: outgoing packet 0x05B. That needs
-- the ids the server sent when it opened the event, so they are kept here.
--   0x032  UniqueNo(0x04) ActIndex(0x08) EventNum(0x0A)  -- a plain event
--   0x034  same three fields in the same places          -- an event with numeric parameters
-- Declared here, above the packet handler, and not beside the chat tap further down.
-- Lua closes over the local that exists at the point the closure is written: with the table
-- declared later, `chatlog` inside the packet handler resolved to the *global* of that name,
-- which is nil, and the addon unloaded itself on the first packet with
-- "attempt to index global 'chatlog' (a nil value)".
local chatlog = { path = nil, all_in = false };

local event = { open = false, unique = 0, index = 0, num = 0, auto = false, pending = false,
                release = 2, release_pending = false, server = false, kick = nil, await_ack = nil };

local function u16(data, off) return data:byte(off + 1) + data:byte(off + 2) * 256; end
local function u32(data, off)
    return u16(data, off) + u16(data, off + 2) * 65536;
end

ashita.events.register('packet_in', 'vg_packet_in', function (e)
    story.on_packet(e.id, e.data, e.size);

    if (chatlog.all_in and chatlog.path ~= nil) then
        local f = io.open(chatlog.path, 'ab');
        if (f ~= nil) then
            local h = {};
            for i = 1, math.min(24, e.size) do h[i] = ('%02X'):format(e.data:byte(i)); end
            f:write(('[in ] id=0x%03X size=%d %s\n'):format(e.id, e.size, table.concat(h, ' ')));
            f:close();
        end
    end

    if ((e.id == 0x032 or e.id == 0x034) and e.size >= 0x10) then
        if (chatlog.path ~= nil) then
            local f = io.open(chatlog.path, 'ab');
            if (f ~= nil) then
                local h = {};
                for i = 1, math.min(32, e.size) do h[i] = ('%02X'):format(e.data:byte(i)); end
                f:write(('[in ] id=0x%03X size=%d %s\n'):format(e.id, e.size, table.concat(h, ' ')));
                f:close();
            end
        end
        event.open   = true;
        event.unique = u32(e.data, 0x04);
        -- 0x034 (an event with numeric parameters) is NOT laid out like 0x032: eight int32
        -- parameters sit between UniqueNo and ActIndex, so its ids are 32 bytes further on
        -- (LandSandBoat 0x034_eventnum.h). Read as a 0x032 it gave "event 0 on index 0" and
        -- the server answered the 0x05B with "Event ID mismatch 523 != 0" -- Rosel, 2026-08-28.
        local shift = (e.id == 0x034) and 32 or 0;
        event.index  = u16(e.data, 0x08 + shift);
        -- 0x0C, not 0x0A. LandSandBoat's struct lists EventNum immediately after ActIndex, but
        -- on the wire 0x0A carries something else and the event id is two bytes further on.
        -- Measured 2026-08-25 from a real packet, talking to Ambrotien:
        --
        --   32 0A DD 00 | 62 60 0E 01 | 62 00 | E6 00 | E9 07 00 00 | E6 00 00 00
        --                  UniqueNo     ActIndex  230    0x07E9=2025
        --
        -- and the server had already said which of those two it wanted, by rejecting the
        -- other one: "Invalid GP_CLI_COMMAND_EVENTEND packet: Event ID mismatch 2025 != 230".
        event.num    = u16(e.data, 0x0C + shift);
        -- Unattended mode. The client latches on an event and waits for Enter, and on this
        -- build no synthetic key reaches it -- Ashita's WNDPROC hook never sees a posted
        -- WM_KEYDOWN at all (`/winecursor` reports "real key events 0" straight after one).
        -- So do not let the client open the event: block the packet that starts it and end
        -- the event server-side instead. The NPC's words are NOT in this packet -- they
        -- arrive separately as ordinary chat -- so nothing is lost from the narration, which
        -- is the whole reason this works.
        --
        -- Off by default: a person playing wants their cutscenes.
        if (event.auto) then
            e.blocked = true;
            event.pending = true;
        end
    elseif (e.id == 0x052) then
        -- EVENTUCOFF: the server acknowledging the end of an event.
        event.open = false;
        if (event.await_ack ~= nil and not e.injected) then
            event.await_ack = nil;
            event.release_pending = true;
        end
    end
end);

--- Injected packets do not leave the client on their own. Measured 2026-08-28 against the
--- local LandSandBoat world with its packet debug on: an injected 0x05B sat in the client's
--- outgoing queue for eight seconds and was parsed by the server in the same bundle as the
--- next chat line typed -- and two injected 0x01A talks were parsed together, both at the
--- moment a `!checkquest` went out. The client bundles queued packets when IT has something
--- to send; standing still with a dialogue open, it has nothing. So after every injection,
--- give it something: a chat command the world will not mind. `/vg kick <command>` sets it
--- (`!where` on a world where you are a GM); unset, nothing is sent and injections wait.
local function kick()
    if (event.kick ~= nil and event.kick ~= '') then
        AshitaCore:GetChatManager():QueueCommand(-1, event.kick);
    end
end

--- Send 0x05B to end (mode 0) or update (mode 1) the open event.
--- `option` is the menu choice; 0 is "just carry on", which is what advancing dialogue is.
local function event_end(mode, option)
    if (not event.open) then return false, 'no event is open'; end
    local u, i, n, o = event.unique, event.index, event.num, option or 0;
    local pkt = { 0, 0, 0, 0 };
    local function put16(v) pkt[#pkt+1] = bit.band(v, 0xFF); pkt[#pkt+1] = bit.band(bit.rshift(v, 8), 0xFF); end
    local function put32(v) put16(bit.band(v, 0xFFFF)); put16(bit.band(bit.rshift(v, 16), 0xFFFF)); end
    put32(u);            -- 0x04 UniqueNo
    put32(o);            -- 0x08 EndPara: the option chosen
    put16(i);            -- 0x0C ActIndex
    put16(mode);         -- 0x0E Mode: 0 = End, 1 = UpdatePending
    put16(n);            -- 0x10 EventNum
    put16(n);            -- 0x12 EventPara: the server reads THIS as the event id it is ending
    AshitaCore:GetPacketManager():AddOutgoingPacket(0x05B, pkt);
    kick();
    -- The 0x05B ends the event on the SERVER. The client is still holding its dialogue box
    -- open, waiting for Enter, and the server does not tell it otherwise: what comes back is
    -- a 0x052 in mode 1 (EventRecvPending), which is bookkeeping, not a release. A real
    -- release -- what `player:release()` sends -- is a 0x052 in mode 2 (CancelEvent) or
    -- mode 0 (Standard). The client acts on packets, not on who sent them, so hand it one.
    -- ...but not yet. The client answers a release with a 0x05B of its own (EndPara
    -- 0x40000000, "cancelled"), and if that is bundled ahead of ours the server finishes
    -- the event with the cancel and the quest is not begun -- seen 2026-08-28, two 0x05Bs
    -- in one bundle, "Not in an event" for the second. So wait for the server's answer to
    -- OUR 0x05B (a 0x052 that is not ours) before handing the client its release; after two
    -- seconds without one, release anyway.
    if (mode == 0 and event.release ~= nil) then event.await_ack = os.clock() + 2; end
    return true, ('event %d on index %d: %s, option %d')
        :format(n, i, mode == 0 and 'end' or 'update', o);
end

--- Inject an incoming 0x052 (EVENTUCOFF) so the client lets go of the event it is in.
--- mode 0 = Standard, 1 = EventRecvPending, 2 = CancelEvent, 3 = CancelInput.
local function event_release(mode)
    local m = mode or event.release or 2;
    -- The Mode field is a uint32 and, for CancelEvent, the server packs the event id into
    -- it: `Mode | (eventId << 8)` (LandSandBoat, 0x052_eventucoff.cpp). A release without
    -- the id is ignored by the client -- measured 2026-08-28: after one, the next event's
    -- text never rendered; after a real `!release` (bytes `02 77 02 00` for event 631) it
    -- did. So the injected one carries the id of the event it is closing.
    local n = (m == 2) and event.num or 0;
    local pkt = { 0, 0, 0, 0, bit.band(m, 0xFF), bit.band(n, 0xFF), bit.band(bit.rshift(n, 8), 0xFF), 0 };
    AshitaCore:GetPacketManager():AddIncomingPacket(0x052, pkt);
    return ('release: injected 0x052 mode %d, event %d'):format(m, n);
end

-- Everything the game says, copied to a file.
--
-- A script driving the client through cmd.txt is deaf: `/vg tee` mirrors Vanaguide's own
-- prints, but Ashita's core replies -- "addon not found", a Lua error from a freshly written
-- addon, the server's answer to a GM command -- go to chat and nowhere else, so a command
-- that failed looked exactly like a command that worked. That cost most of a morning.
--
-- The tap is off unless asked for (`/vg chatlog on`), appends, and strips FFXI's colour and
-- auto-translate bytes so the file is readable text rather than a field of question marks.

local function chat_strip(text)
    if (text == nil) then return ''; end
    return (text:gsub('[\30\31].', '')          -- colour prefixes: marker + one byte
                :gsub('\239[\39\41].', '')     -- auto-translate brackets
                :gsub('[%z\1-\8\11\12\14-\29]', ''));
end

-- Outgoing packet ids, to the same file. `/vg talk` builds a 0x01A and hands it to Ashita;
-- until this existed there was no way to tell "the packet was sent and the server ignored it"
-- from "the packet never left", and those two need completely different fixes.
ashita.events.register('packet_out', 'vg_packet_out', function (e)
    if (chatlog.path == nil) then return; end
    local f = io.open(chatlog.path, 'ab');
    if (f == nil) then return; end
    local head = {};
    for i = 1, math.min(16, e.size) do head[i] = ('%02X'):format(e.data:byte(i)); end
    f:write(('[out] id=0x%03X size=%d injected=%s %s\n')
        :format(e.id, e.size, tostring(e.injected), table.concat(head, ' ')));
    f:close();
end);

ashita.events.register('text_in', 'vg_text_in', function (e)
    if (chatlog.path == nil) then return; end
    local line = chat_strip(e.message_modified ~= '' and e.message_modified or e.message);
    if (line:match('^%s*$')) then return; end
    local f = io.open(chatlog.path, 'ab');
    if (f ~= nil) then f:write(('[%d] %s\n'):format(e.mode or -1, line)); f:close(); end
end);

--- Turn the chat tap on or off. Exposed to the command handler below.
local function chatlog_set(name)
    if (name == nil or name:lower() == 'off') then
        chatlog.path = nil;
        return 'chatlog off';
    end
    local base = AshitaCore:GetInstallPath():gsub('[\\/]$', '');
    chatlog.path = ('%s\\addons\\Vanaguide\\%s'):format(base, name);
    return 'chatlog -> ' .. name;
end

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

    -- `/vg target`: the current step's destination, machine-readably, for a script driving
    -- the client (tools/guided_run.sh). One line: zone, x/y/z, the NPC, the quest key.
    if (sub == 'target') then
        local step = P.step();
        if (step == nil) then U.print('target: no step'); return; end
        local key = step.quest or step.quest_accept or step.mission;
        local q = nil;
        if (step.quest or step.quest_accept) then
            local ok, Qd = pcall(require, 'data.quests');
            if (ok and Qd.quests and Qd.quests[key.area]) then q = Qd.quests[key.area][key.id]; end
        end
        local npc = (q and q.npc) or (step.note or ''):match('Ask ([^.]+)%.') or (step.note or ''):match('Starts with ([^.]+)%.') or '';
        U.print(('target: step=%d zone=%s x=%s y=%s z=%s npc=%s key=%s,%s name=%s')
            :format(P.index, tostring(step.zone or (q and q.zone) or ''),
                    q and q.x or (step.pos and step.pos.x) or '', q and q.y or '',
                    q and q.z or (step.pos and step.pos.z) or '', npc,
                    key and key.area or '', key and key.id or '', step.text or ''));
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
        U.print(Line.status());
        U.print(Nav.status());
        U.print(Walk.status());
        U.print(('exits known out of this zone: %d'):format(points.count(U.zone())));
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
    -- `/vg chatlog chat.txt` starts copying every incoming chat line to that file;
    -- `/vg chatlog off` stops. See the tap above for why this exists.
    if (sub == 'chatlog') then
        U.print(chatlog_set((#args > 2) and args[3] or 'off'));
        return;
    end

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

    -- `/vg dump graph` writes the learned crossings as a paste-ready block for
    -- data/zonelines.lua, so a playthrough's map can be promoted into the shipped seed and a
    -- fresh install starts with roads instead of a blank graph (docs/PATHWAYS.md #2).
    if (sub == 'dump' and #args > 2 and args[3]:lower() == 'graph') then
        local set = graph.save_learned() or {};
        local n = #Learned.pairs_list(set);
        if (n == 0) then
            U.print('dump: nothing learned yet -- walk some zone lines first.');
            return;
        end
        local path = Learned.dump(set, function (id) return U.zone_name(id); end);
        if (path == nil) then
            U.print('dump: could not write the file (is the game folder writable?).');
        else
            U.print(('dump: %d learned crossing%s written to %s'):format(n, n == 1 and '' or 's', path));
            U.print('paste the Z.learned_walk pairs into data/zonelines.lua Z.walk to ship them.');
        end
        return;
    end

    -- What the zone graph has learned from play, and whether it is learning at all. The
    -- graph records every crossing (docs/ROUTING.md) and until now nothing could read the
    -- result back, so "zone-line learning works" was an untested claim in the docs.
    if (sub == 'graph') then
        -- `/vg graph <a> <b>` answers about one pair. The count on its own cannot tell you
        -- whether a crossing was recorded, because Z.learn refuses to record a pair it
        -- already knows -- so warping between two zones the sweep has visited a hundred
        -- times leaves the total unchanged and looks exactly like learning being broken.
        if (#args > 3) then
            local a, b = tonumber(args[3]), tonumber(args[4]);
            -- The graph stores crossings keyed "from:to" with a colon, both directions.
            -- This query used to build "from-to" with a dash and so always reported "no".
            local set = graph.save_learned() or {};
            local yes = set[('%d:%d'):format(a, b)] or set[('%d:%d'):format(b, a)];
            U.print(('graph: %d-%d learned = %s'):format(a, b, yes and 'yes' or 'no'));
            return;
        end
        -- `/vg graph suspect` lists the hand-written pairs the server's own zone line table
        -- contradicts. They still route, at three times the cost, so a way round wins when
        -- there is one -- see docs/ROUTING.md.
        if (#args > 2 and args[3]:lower() == 'suspect') then
            local sus = graph.suspect or {};
            U.print(('%d seed pairs the server table contradicts:'):format(#sus));
            for _, pair in ipairs(sus) do
                U.print(('  %s <-> %s'):format(U.zone_name(pair[1]), U.zone_name(pair[2])));
            end
            return;
        end
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
        local here = U.zone();
        local x, z = U.position();
        local legs, cost = graph.route(here, step.zone);
        if (legs == nil) then
            U.print(('no route from %s to %s'):format(U.zone_name(here), U.zone_name(step.zone)));
            return;
        end
        U.print(('%s -> %s: %d legs, about %dm')
            :format(U.zone_name(here), U.zone_name(step.zone), #legs, math.floor((cost or 0) / 60 + 0.5)));
        -- One line per leg, and each says whether the router can point at it. A leg with no
        -- recorded coordinate still gets you there; it just cannot aim the arrow, and saying
        -- so is the difference between a gap and a bug.
        for _, leg in ipairs(R.itinerary(legs, here, x, z)) do
            U.print(('  %d. %s%s'):format(leg.n, leg.text, leg.known and '' or '   [no coordinate]'));
        end
        return;
    end

    -- The line on the ground.
    if (sub == 'nav') then
        local what = (#args > 2) and args[3]:lower() or '';
        if (what == 'off') then
            Path.provider = nil;
            Path.forget();
            U.print('navmesh paths off; the line is straight again');
            return;
        elseif (what == 'on' or what == 'reload') then
            Nav.reset();
            Nav.install(Path);
            Path.forget();
        end
        U.print(Nav.status());
        if (Nav.grid == nil) then
            U.print('tools/gen_navgrid.py builds them from a LandSandBoat checkout you have;');
            U.print('they are not shipped -- see docs/NAVMESH.md.');
        end
        return;
    end

    -- Route to any zone, with or without a guide loaded.
    if (sub == 'goto' or sub == 'go') then
        local rest = (#args > 2) and table.concat({ unpack(args, 3) }, ' ') or '';
        if (rest == '' or rest:lower() == 'off' or rest:lower() == 'stop') then
            vg.goto_step = nil;
            Window.destination = nil;
            Path.forget();
            U.print('not going anywhere in particular');
            return;
        end
        local id = tonumber(rest) or U.zone_id(rest);
        if (id == nil) then
            U.print(('no zone called "%s"'):format(rest));
            return;
        end
        vg.goto_step = { kind = 'run', text = ('Go to %s'):format(U.zone_name(id)), zone = id };
        Window.destination = vg.goto_step;
        Path.forget();
        local w = C.world(); w.yaw = U.heading();
        local rec = R.recommend(vg.goto_step, w);
        U.print(('going to %s: %s'):format(U.zone_name(id), rec.text or '?'));
        local summary = R.summary(rec);
        if (summary ~= nil) then U.print('  ' .. summary); end
        return;
    end

    -- Walk the character to the current target.  Local world only: writing the player's
    -- position is a bannable offence anywhere that is not our own server.
    -- Measurement aid for docs/WALK.md: drive the client's own auto-follow by hand.
    --   /vg af <index>        follow that entity (what /follow does), by memory
    --   /vg af d <x> <z> [y]  set the follow delta directly and auto-run
    --   /vg af off
    --   /vg af                print the raw struct
    if (sub == 'af') then
        local f = AshitaCore:GetMemoryManager():GetAutoFollow();
        local a = (args[3] or ''):lower();
        if (a == 'off') then
            f:SetIsAutoRunning(0); f:SetFollowTargetIndex(0); f:SetFollowTargetServerId(0);
            f:SetFollowDeltaX(0); f:SetFollowDeltaY(0); f:SetFollowDeltaZ(0);
        elseif (a == 'd') then
            f:SetFollowTargetIndex(0); f:SetFollowTargetServerId(0);
            f:SetFollowDeltaX(tonumber(args[4]) or 0); f:SetFollowDeltaY(tonumber(args[5]) or 0);
            f:SetFollowDeltaZ(tonumber(args[6]) or 0); f:SetFollowDeltaW(tonumber(args[7]) or 0);
            f:SetIsAutoRunning(1);
        elseif (tonumber(a) ~= nil) then
            local idx = tonumber(a);
            local sid = AshitaCore:GetMemoryManager():GetEntity():GetServerId(idx);
            f:SetFollowTargetIndex(idx); f:SetFollowTargetServerId(sid);
            f:SetTargetIndex(idx); f:SetTargetServerId(sid);
            f:SetIsAutoRunning(1);
        end
        U.print(('af: target=%d/%d follow=%d/%d delta=(%.2f, %.2f, %.2f, %.2f) run=%d fp=%d lock=%d/%d'):format(
            f:GetTargetIndex(), f:GetTargetServerId(), f:GetFollowTargetIndex(), f:GetFollowTargetServerId(),
            f:GetFollowDeltaX(), f:GetFollowDeltaY(), f:GetFollowDeltaZ(), f:GetFollowDeltaW(),
            f:GetIsAutoRunning(), f:GetIsFirstPersonCamera(), f:GetIsCameraLocked(), f:GetIsCameraLockedOn()));
        return;
    end

    if (sub == 'walk') then
        local what = (#args > 2) and args[3]:lower() or '';
        if (what == 'stop' or what == 'off') then
            Walk.stop('stopped');
            U.print(Walk.status());
            return;
        end
        if (what == 'status') then U.print(Walk.status()); return; end
        if (what == 'mode' and #args > 3) then
            Walk.mode = args[4]:lower();
            U.print('walk mode ' .. Walk.mode);
            return;
        end
        if (what == 'tick' and #args > 3) then
            Walk.tick = math.max(0.1, math.min(2, tonumber(args[4]) or 0.25));
            U.print(('walk tick %.2f s'):format(Walk.tick));
            return;
        end
        if (what == 'speed' and #args > 3) then
            Walk.speed = math.max(0.5, math.min(20, tonumber(args[4]) or 5));
            U.print(('walk speed %.1f yalms/s'):format(Walk.speed));
            return;
        end
        if (what == 'allow') then
            vg.walk_allowed = true;
            U.print('walk: allowed on this world');
            return;
        end
        if (not vg.walk_allowed) then
            U.print('walk: only on the local world. /vg walk allow  says this is it (never on a hosted server).');
            return;
        end
        local step = vg.goto_step or P.step();
        if (step == nil) then U.print('walk: no step'); return; end
        local w = C.world(); w.yaw = U.heading();
        local rec = R.recommend(step, w);
        if (rec.target == nil) then U.print('walk: the step has no place to walk to (' .. tostring(rec.text) .. ')'); return; end
        local label = (rec.mode == 'travel') and U.zone_name(rec.leg and rec.leg.to) or step.text;
        Walk.start(rec.target, label);
        vg.walk_auto = (what == 'auto');
        -- Auto-walking ends every event it runs into: a city gate is a gatekeeper event whose
        -- finish is what moves the character through the door.  Restored when the walk ends.
        if (vg.walk_auto) then vg.walk_event_auto_was = event.auto; event.auto = true; end
        U.print(Walk.status());
        return;
    end

    if (sub == 'line' or sub == 'path') then
        local what = (#args > 2) and args[3]:lower() or '';
        if (what == 'probe') then
            local w = C.world(); w.yaw = U.heading();
            Line.probe(w, function (s) U.print(s); end);
            return;
        end
        if (what == '') then
            what = Line.enabled and 'off' or 'on';       -- bare /vg line toggles
        end
        local said = Line.set(what, (#args > 3) and args[4]:lower() or nil);
        if (said == nil) then
            U.print('/vg line on | off | style solid|dots|both | width <px> | horizon <yalms>');
            U.print(Line.status());
            return;
        end
        vg.settings.line.visible = Line.enabled;
        vg.settings.line.style = Line.style;
        vg.settings.line.width = Line.width;
        vg.settings.line.horizon = Line.horizon;
        settings.save();
        U.print(said);
        U.print(Line.status());
        return;
    end

    -- Talk to an NPC: the one thing a guide could describe but never do.  Every other
    -- command here reads the world; this one acts on it, and it is what turns the guide from
    -- a list into a run -- the step says "Ask Ambrotien", and this asks him.
    --
    --   /vg talk              the NPC the current step names
    --   /vg talk Ambrotien    by name, or any unique part of one
    --
    -- FFXI has no "interact" command.  Talking is outgoing packet 0x01A -- the action packet
    -- -- with category 0, which is the same thing the client sends when a player presses
    -- Enter on a targeted NPC.  Ashita's AddOutgoingPacket takes the whole packet including
    -- its four-byte header, so the payload starts at index 5 (offset 0x04):
    --
    --   0x04  uint32  the target's SERVER id (not its entity index -- using the index here
    --                 is silently ignored by the server, which looks exactly like the NPC
    --                 refusing to talk)
    --   0x08  uint16  the target's entity index
    --   0x0A  uint16  the action id, 0 = Talk (interact with an NPC)
    --   0x0C  16 bytes  the action union -- unused for Talk, but it must be THERE
    --
    -- The whole packet is 28 bytes, and that is not negotiable. A 16-byte one is dropped by
    -- the server before any handler sees it, with no reply and nothing on screen:
    --
    --   [map][warn] Bad packet size for GP_CLI_COMMAND_ACTION (0x01a) from Test:
    --                got 16, expected [28, 28]
    --
    -- which is indistinguishable, from inside the client, from injection being broken. It
    -- cost this project a day (docs/DRIVING_THE_CLIENT.md). The size comes from
    -- GP_CLI_COMMAND_ACTION in LandSandBoat's src/map/packets/c2s/0x01a_action.h: four bytes
    -- of header, UniqueNo, ActIndex, ActionID, then a 16-byte union big enough for the
    -- largest action (a spell cast, which carries a target position).
    --
    -- The server answers with the event, and the event's text arrives as ordinary chat --
    -- which is what VanaVoice reads aloud.  So this is also how an unattended run proves the
    -- narrator: talk, and something should speak.
    if (sub == 'talk') then
        local want = (#args > 2) and table.concat({ unpack(args, 3) }, ' ') or nil;
        if (want == nil) then
            local step = P.step();
            want = step and step.npc or nil;
            if (want == nil and step ~= nil and step.note ~= nil) then
                -- The generated guides put the name in the note as "Ask <npc>." / "Starts
                -- with <npc>." -- the only place it survives for a generated step.
                want = step.note:match('Ask ([^.]+)%.') or step.note:match('Starts with ([^.]+)%.');
            end
        end
        if (want == nil or want == '') then
            U.print('/vg talk <npc>   (this step names nobody to talk to)');
            return;
        end

        local px, pz = U.position();
        if (px == nil) then U.print('talk: not in the world'); return; end

        local needle = want:lower();
        local best;
        for _, e in ipairs(Verify.nearby(px, pz)) do
            if (e.name:lower():find(needle, 1, true) ~= nil) then best = e; break; end
        end
        if (best == nil) then
            U.print(('talk: no "%s" loaded here (nearest is %s)'):format(
                want, (Verify.nearby(px, pz)[1] or { name = 'nothing' }).name));
            return;
        end

        -- Out of range reads as silence, not as an error, so say the distance either way.
        local ents = AshitaCore:GetMemoryManager():GetEntity();
        local sid = ents:GetServerId(best.index);
        local pkt = { 0, 0, 0, 0,                                       -- 0x00 header
            bit.band(sid, 0xFF), bit.band(bit.rshift(sid, 8), 0xFF),    -- 0x04 UniqueNo
            bit.band(bit.rshift(sid, 16), 0xFF), bit.band(bit.rshift(sid, 24), 0xFF),
            bit.band(best.index, 0xFF), bit.band(bit.rshift(best.index, 8), 0xFF), -- 0x08 ActIndex
            0, 0 };                                                     -- 0x0A ActionID 0 = Talk
        for _ = 1, 16 do pkt[#pkt + 1] = 0; end                          -- 0x0C the action union
        AshitaCore:GetPacketManager():AddOutgoingPacket(0x01A, pkt);
        kick();
        U.print(('talk -> %s (index %d, server id %d) at %.1f yalms'):format(
            best.name, best.index, sid, best.dist or -1));
        return;
    end

    -- `/vg advance [option]` is the scripted Enter. It closes the event the NPC opened, so
    -- the next `/vg talk` is heard instead of being swallowed. `/vg pick <n>` answers a menu.
    -- `/vg auto on` makes every NPC event end itself, so an unattended run can walk a whole
    -- guide without a keyboard. `/vg auto off` gives cutscenes back to the player.
    -- `/vg packets on` logs every incoming packet id into the chat log. Very noisy; it is
    -- how the event packet's real layout gets found when a struct and the wire disagree.
    if (sub == 'packets') then
        chatlog.all_in = (args[3] or 'on'):lower() == 'on';
        U.print('packet log ' .. (chatlog.all_in and 'on' or 'off'));
        return;
    end

    if (sub == 'auto') then
        event.auto = (args[3] or 'on'):lower() == 'on';
        U.print('auto-advance ' .. (event.auto and 'on' or 'off'));
        return;
    end

    -- `/vg release [mode]` injects the client-side release on its own; `/vg release auto <mode|off>`
    -- sets which one `/vg advance` sends after the 0x05B (default 2 = CancelEvent).
    -- `/vg send <id> <hex bytes...>` hands a raw outgoing packet to Ashita. For experiments
    -- only: the header's size/sequence are whatever you typed, so type the whole packet.
    if (sub == 'send') then
        local id = tonumber(args[3] or '');
        if (id == nil) then U.print('send: /vg send <id> <hex bytes...>'); return; end
        local pkt = {};
        for i = 4, #args do pkt[#pkt+1] = tonumber(args[i], 16) or 0; end
        AshitaCore:GetPacketManager():AddOutgoingPacket(id, pkt);
        kick();
        U.print(('send: 0x%03X, %d bytes'):format(id, #pkt));
        return;
    end

    if (sub == 'kick') then
        event.kick = (#args > 2) and table.concat({ unpack(args, 3) }, ' ') or nil;
        if (event.kick ~= nil and event.kick:lower() == 'off') then event.kick = nil; end
        U.print('kick after injection: ' .. tostring(event.kick));
        return;
    end

    if (sub == 'release') then
        local a = (args[3] or ''):lower();
        if (a == 'auto') then
            local v = (args[4] or ''):lower();
            if (v == 'off') then event.release = nil; else event.release = tonumber(v) or 2; end
            U.print('release after advance: ' .. tostring(event.release));
            return;
        end
        U.print(event_release(tonumber(a)));
        return;
    end

    if (sub == 'advance' or sub == 'pick') then
        local mode   = (sub == 'pick') and 1 or 0;
        local option = tonumber(args[3] or '0') or 0;
        if (event.server and event.open and mode == 0) then
            -- The scripted Enter, done on the SERVER. Measured 2026-08-28 on the local
            -- LandSandBoat world: an injected 0x05B reaches the server (it warns "Not in an
            -- event" when sent idle) but while an event is open it is swallowed without a
            -- trace -- no EVENTUCOFF back, quest still AVAILABLE. What does work is running
            -- the event's finish handler through the GM `!exec` and then `!release`, which
            -- ends the event server-side AND sends the client the CancelEvent it needs to
            -- let go of the dialogue box. Needs GM level 4+ on a world you own; it is never
            -- sent anywhere else (`/vg advance server off`).
            local n = event.num;
            AshitaCore:GetChatManager():QueueCommand(-1,
                ('!exec InteractionGlobal.onEventFinish(player, %d, %d, player:getEventTarget())'):format(n, option));
            AshitaCore:GetChatManager():QueueCommand(-1, '!release');
            event.open = false;
            U.print(('advance: event %d finished on the server, option %d, released'):format(n, option));
            return;
        end
        local ok, why = event_end(mode, option);
        U.print(ok and ('advance: ' .. why) or ('advance: ' .. why));
        return;
    end

    -- `/vg advance server on|off`: use the GM-side finish above instead of the 0x05B.
    if (sub == 'server') then
        event.server = (args[3] or 'on'):lower() == 'on';
        U.print('advance on the server: ' .. (event.server and 'on' or 'off'));
        return;
    end

    if (sub == 'mark') then
        mark(#args > 2 and table.concat({ unpack(args, 3) }, ' ') or nil);
        return;
    end

    if (sub == 'arrow') then
        local what = (#args > 2) and args[3]:lower() or '';

        -- `/vg arrow unlock`, drag it with the mouse, `/vg arrow lock` to fix it there.
        --
        -- HXUI's pattern (addons/HXUI/expbar.lua): the element is an ImGui window and locking
        -- only adds ImGuiWindowFlags_NoMove. Dragging then runs on ImGui's io, which is the
        -- one mouse path that works under wine on this build -- the WNDPROC 'mouse' event the
        -- primitives-based panels use is dead here, which is exactly why HXUI's bars can be
        -- dragged and `timers`/`tparty` cannot. ImGui writes the position into
        -- config/imgui.ini by itself, so nothing about it is stored on this side.
        if (what == 'lock' or what == 'unlock') then
            Arrow.locked = (what == 'lock');
            vg.settings.arrow.locked = Arrow.locked;
            settings.save();
            U.print(Arrow.locked and 'arrow locked'
                    or 'arrow unlocked -- drag it with the mouse, then /vg arrow lock');
            return;
        end

        if (what == 'why' and Arrow.last_error ~= nil) then
            U.print('arrow draw error: ' .. Arrow.last_error);
            return;
        end
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
                U.print('/vg arrow move <across%> <down%>   e.g. /vg arrow move 50 12');
                return;
            end
            local rx, ry = Arrow.move(px / 100, py / 100);
            vg.settings.arrow.x, vg.settings.arrow.y = rx, ry;
        elseif (what == 'size' and #args > 3) then
            -- 1.0 is the arrow's original size; the default is deliberately smaller.
            local k = tonumber(args[4]);
            if (k == nil or k <= 0) then
                U.print('/vg arrow size <n>   1.0 is the original size, 0.6 is the default');
                return;
            end
            Arrow.scale = math.max(0.2, math.min(3, k));
            vg.settings.arrow.scale = Arrow.scale;
        elseif (what == 'reset') then
            local rx, ry = Arrow.move(ARROW_X, ARROW_Y);
            vg.settings.arrow.x, vg.settings.arrow.y = rx, ry;
            Arrow.scale = ARROW_SCALE;
            vg.settings.arrow.scale = ARROW_SCALE;
        end
        settings.save();
        U.print(('arrow: %s, at %.0f%% across and %.0f%% down, calibration %d, offset %.0f degrees')
            :format(vg.settings.arrow.visible and 'on' or 'off',
                    (vg.settings.arrow.x or ARROW_X) * 100, (vg.settings.arrow.y or ARROW_Y) * 100,
                    Arrow.calibration, math.deg(Arrow.offset)));
        U.print('/vg arrow move <across%> <down%> | reset | flip | nudge <deg> | on | off');
        return;
    end

    U.print('commands: guides, load <n>, next, back, skip, reset, route, goto <zone>, mark,');
    U.print('          arrow, line, nav, dump graph');
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
    -- The 0x05B cannot be sent from inside the packet handler: Ashita is mid-dispatch and the
    -- outgoing queue is not reentrant. One frame later is soon enough.
    if (event.pending) then
        event.pending = false;
        event_end(0, 0);
    end
    if (event.await_ack ~= nil and os.clock() > event.await_ack) then
        event.await_ack = nil;
        event.release_pending = true;
        U.print('release: no answer to the 0x05B in 2 s; releasing anyway');
    end
    if (event.release_pending) then
        event.release_pending = false;
        U.print(event_release());
    end
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
            Learned.save(vg.settings.learned);   -- shared across every character
            settings.save();
        end
        vg.last_zone = w.zone;
        -- A path belongs to the zone it was found in, and so does the grid it was found on.
        Path.forget();
    end

    -- A few hundred cells of pathfinding, and no more. The JIT is off in this addon, so a
    -- whole A* between two frames is a visible stutter; spread over a third of a second it
    -- is nothing, and the straight line is drawn in the meantime.
    Nav.step();

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
        Project.set_viewport(vp.Width, vp.Height);
    end

    Window.draw(w, function (name) load_guide(name); end);

    if (P.guide ~= nil or vg.goto_step ~= nil) then
        -- A destination asked for by name outranks the guide's own step: the player said
        -- where they want to be, and the guide can wait until they are there.
        local step = vg.goto_step or P.step();
        if (step ~= nil) then
            -- A new step is a new destination: the cached path belongs to the old one, and
            -- keeping it draws a confident line to somewhere the guide has stopped asking for.
            if (P.index ~= vg.last_index) then
                vg.last_index = P.index;
                Path.forget();
            end

            local rec = R.recommend(step, w);

            -- Arrived: a goto is a one-shot errand, and leaving it set would keep pointing at
            -- the door the player has just walked through.
            if (vg.goto_step ~= nil and step == vg.goto_step
                and rec.mode == 'here' and w.zone == vg.goto_step.zone) then
                U.print(('arrived in %s'):format(U.zone_name(vg.goto_step.zone)));
                vg.goto_step = nil;
                Window.destination = nil;
                Path.forget();
            end

            -- Walking: re-aim at the current target every frame (a step that completes, or
            -- a zone crossed, moves it) and take one run-speed step along the line.
            if (Walk.active and rec.target ~= nil) then
                if (not vg.walk_back and (Walk.target.x ~= rec.target.x or Walk.target.z ~= rec.target.z)) then
                    Walk.target = { x = rec.target.x, z = rec.target.z, y = rec.target.y };
                end
                if (Walk.update(w)) then
                    if (vg.walk_back) then
                        vg.walk_back = false;
                        Walk.start(rec.target, 'back to the crossing');
                        vg.walk_wait.since = os.time();
                        return;
                    end
                    U.print(('walk: arrived (%s)'):format(step.text or ''));
                    if (vg.walk_auto and rec.mode == 'travel') then
                        -- A zone line or a gate: the crossing happens on its own once we
                        -- stand on it (the gate's event is auto-ended).  Wait here, quietly,
                        -- and resume when the zone or the target changes.
                        vg.walk_wait = { zone = w.zone, x = rec.target.x, z = rec.target.z, since = os.time() };
                    end
                end
            elseif (vg.walk_auto and vg.walk_wait ~= nil and rec.target ~= nil) then
                local ww = vg.walk_wait;
                if (w.zone ~= ww.zone or rec.target.x ~= ww.x or rec.target.z ~= ww.z) then
                    vg.walk_wait = nil;
                    Walk.start(rec.target, (rec.mode == 'travel') and U.zone_name(rec.leg and rec.leg.to) or step.text);
                elseif (os.time() - ww.since > 8 and (ww.retries or 0) < 2) then
                    -- A gate only fires when you *enter* its area, and a gate that turned us
                    -- away (rank, mission) will not fire again while we stand in it.  Step
                    -- back a dozen yalms and walk in again; twice, then give up.
                    ww.retries = (ww.retries or 0) + 1;
                    ww.since = os.time() + 6;
                    local dx, dz = w.x - ww.x, w.z - ww.z;
                    local d = math.sqrt(dx * dx + dz * dz);
                    if (d < 0.5) then dx, dz, d = math.cos(w.yaw or 0), -math.sin(w.yaw or 0), 1; end
                    ww.back = { x = ww.x + dx / d * 12, z = ww.z + dz / d * 12, y = w.y };
                    U.print(('walk: the crossing did not open; stepping back to try again (%d)'):format(ww.retries));
                    Walk.start(ww.back, 'stepping back');
                    vg.walk_back = true;
                elseif (os.time() - ww.since > 20) then
                    vg.walk_wait = nil; vg.walk_auto = false;
                    U.print('walk: stood at the crossing for 20 s and nothing happened; stopping');
                end
            elseif (Walk.active and rec.target == nil) then
                Walk.stop('the step has no place');
                U.print('walk: stopped, the step has no place to walk to');
            end
            if (not Walk.active and vg.walk_auto and vg.walk_wait == nil) then
                vg.walk_auto = false;
                if (vg.walk_event_auto_was ~= nil) then event.auto = vg.walk_event_auto_was; vg.walk_event_auto_was = nil; end
            end

            -- The line first, so the arrow is drawn on top of it rather than under it.
            if (rec.target ~= nil) then
                local label = (rec.mode == 'travel') and U.zone_name(rec.leg and rec.leg.to)
                                                     or step.text;
                Line.draw(w, rec.target, label);
            end

            if (vg.settings.arrow.visible ~= false) then
                if (rec.bearing ~= nil) then
                    -- Travel legs have a bearing now: the arrow points at the doorway out of
                    -- this zone for the whole walk, instead of sitting at zero and saying the
                    -- same five words from one end of the road to the other.
                    local sub_text = step.text;
                    if (rec.mode == 'travel') then
                        sub_text = U.zone_name(rec.destination);
                    end
                    Arrow.draw(rec.bearing, rec.distance,
                        ('%.0f yalms'):format(rec.distance or 0), sub_text);
                elseif (rec.mode == 'travel') then
                    Arrow.draw(0, nil, rec.text, U.zone_name(rec.destination));
                end
            end
        end
    end
end);
