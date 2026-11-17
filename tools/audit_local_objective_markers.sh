#!/bin/zsh
set -euo pipefail

command -v mariadb >/dev/null || { print -u2 -- 'mariadb client is required'; exit 2; }

print -r -- 'Read-only audit of local xidb via Unix socket; no game client or server packets are used.'

SPAWNS="$(mariadb --protocol=socket --batch --skip-column-names xidb <<'SQL'
WITH targets AS (
    SELECT 'Spook (item 940)' AS label, 190 AS zoneid, 'Spook' AS mob, 2.9 AS target_x, -99.3 AS target_z
    UNION ALL SELECT 'Orcish Fodder (item 16656)', 100, 'Orcish_Fodder', -366.1, 215.3
    UNION ALL SELECT 'Ding Bats (item 1112)', 190, 'Ding_Bats', -10, -89
    UNION ALL SELECT 'Amber Quadav (items 606-609)', 143, 'Amber_Quadav', 52, 60
), candidates AS (
    SELECT t.label, mg.name, msp.minLevel, msp.maxLevel,
           msp.pos_x, msp.pos_y, msp.pos_z,
           SQRT(POW(msp.pos_x - t.target_x, 2) + POW(msp.pos_z - t.target_z, 2)) AS distance,
           ROW_NUMBER() OVER (
               PARTITION BY t.label
               ORDER BY SQRT(POW(msp.pos_x - t.target_x, 2) + POW(msp.pos_z - t.target_z, 2))
           ) AS rn
    FROM targets t
    JOIN mob_groups mg ON mg.zoneid = t.zoneid AND mg.name = t.mob
    JOIN mob_spawn_points msp USING (groupid)
    WHERE msp.minLevel > 0
)
SELECT label, name, minLevel, maxLevel,
       ROUND(pos_x, 2), ROUND(pos_y, 2), ROUND(pos_z, 2), ROUND(distance, 2)
FROM candidates WHERE rn = 1 ORDER BY label;
SQL
)"

SPAWN_ROWS="$(print -r -- "$SPAWNS" | awk 'NF { count++ } END { print count+0 }')"
[[ "$SPAWN_ROWS" == 4 ]] || {
  print -u2 -- "expected four objective spawn groups, found $SPAWN_ROWS"; exit 1
}
if print -r -- "$SPAWNS" | awk -F '\t' '$8 > 1.0 { failed=1 } END { exit !failed }'; then
  print -u2 -- 'an objective marker is more than 1 yalms from its nearest concrete spawn row'
  print -r -- "$SPAWNS"
  exit 1
fi
print -r -- 'Nearest concrete spawn rows (marker distance in yalms):'
print -r -- "$SPAWNS"

NPC="$(mariadb --protocol=socket --batch --skip-column-names xidb <<'SQL'
SELECT name, (npcid >> 12)-4096, ROUND(pos_x,2), ROUND(pos_y,2), ROUND(pos_z,2)
FROM npc_list
WHERE (((npcid >> 12)-4096)=230 AND name='Ambrotien' AND ROUND(pos_x,2)=93.42 AND ROUND(pos_z,2)=-57.35)
   OR (((npcid >> 12)-4096)=241 AND name='Apururu' AND ROUND(pos_x,2)=-12.09 AND ROUND(pos_z,2)=15.94)
   OR (((npcid >> 12)-4096)=230 AND name='Balasiel' AND ROUND(pos_x,2)=-138.33 AND ROUND(pos_z,2)=65.76)
   OR (((npcid >> 12)-4096)=237 AND name='Cid' AND ROUND(pos_x,2)=-12.60 AND ROUND(pos_z,2)=2.43)
   OR (((npcid >> 12)-4096)=235 AND name='Cleades' AND ROUND(pos_x,2)=-361.90 AND ROUND(pos_z,2)=-169.13)
   OR (((npcid >> 12)-4096)=230 AND name='Endracion' AND ROUND(pos_x,2)=-112.82 AND ROUND(pos_z,2)=-37.19)
   OR (((npcid >> 12)-4096)=231 AND name='Arnau' AND ROUND(pos_x,2)=149.89 AND ROUND(pos_z,2)=141.87)
   OR (((npcid >> 12)-4096)=102 AND name='Augevinne' AND ROUND(pos_x,2)=-363.42 AND ROUND(pos_z,2)=267.72)
   OR (((npcid >> 12)-4096)=102 AND name='Deaufrain' AND ROUND(pos_x,2)=-307.02 AND ROUND(pos_z,2)=341.55)
   OR (((npcid >> 12)-4096)=102 AND name='Equesobillot' AND ROUND(pos_x,2)=-286.48 AND ROUND(pos_z,2)=287.82)
   OR (((npcid >> 12)-4096)=102 AND name='Galaihaurat' AND ROUND(pos_x,2)=-481.20 AND ROUND(pos_z,2)=220.55)
   OR (((npcid >> 12)-4096)=102 AND name='Laurisse' AND ROUND(pos_x,2)=-291.76 AND ROUND(pos_z,2)=141.19)
   OR (((npcid >> 12)-4096)=102 AND name='Narvecaint' AND ROUND(pos_x,2)=-261.94 AND ROUND(pos_z,2)=127.61)
   OR (((npcid >> 12)-4096)=193 AND name='Ruillont' AND ROUND(pos_x,2)=-69.85 AND ROUND(pos_z,2)=610.81)
   OR (((npcid >> 12)-4096)=102 AND name='Vicorpasse' AND ROUND(pos_x,2)=-344.96 AND ROUND(pos_z,2)=265.02)
   OR (((npcid >> 12)-4096)=102 AND name='Yaucevouchat' AND ROUND(pos_x,2)=-315.84 AND ROUND(pos_z,2)=184.48)
   OR (((npcid >> 12)-4096)=240 AND name='Hakkuru-Rinkuru' AND ROUND(pos_x,2)=-111.14 AND ROUND(pos_z,2)=102.06)
   OR (((npcid >> 12)-4096)=140 AND name='Hut_Door' AND ROUND(pos_x,2)=-165.36 AND ROUND(pos_z,2)=77.77)
   OR (((npcid >> 12)-4096)=240 AND name='Janshura-Rashura' AND ROUND(pos_x,2)=-230.63 AND ROUND(pos_z,2)=184.05)
   OR (((npcid >> 12)-4096)=116 AND name='Pore-Ohre' AND ROUND(pos_x,2)=262.27 AND ROUND(pos_z,2)=-459.61)
ORDER BY name, (npcid >> 12)-4096;
SQL
)"
NPC_ROWS="$(print -r -- "$NPC" | awk 'NF { count++ } END { print count+0 }')"
[[ "$NPC_ROWS" == 20 ]] || {
  print -u2 -- "expected twenty exact local NPC spawn matches for authored guide arrows, found $NPC_ROWS"
  print -u2 -r -- "$NPC"
  exit 1
}
EXPECTED_NPC=$'Ambrotien\t230\t93.42\t1.00\t-57.35\n'
EXPECTED_NPC+=$'Apururu\t241\t-12.09\t-2.75\t15.94\n'
EXPECTED_NPC+=$'Arnau\t231\t149.89\t-0.60\t141.87\n'
EXPECTED_NPC+=$'Augevinne\t102\t-363.42\t39.71\t267.72\n'
EXPECTED_NPC+=$'Balasiel\t230\t-138.33\t-10.80\t65.76\n'
EXPECTED_NPC+=$'Cid\t237\t-12.60\t-10.99\t2.43\n'
EXPECTED_NPC+=$'Cleades\t235\t-361.90\t-10.02\t-169.13\n'
EXPECTED_NPC+=$'Deaufrain\t102\t-307.02\t27.69\t341.55\n'
EXPECTED_NPC+=$'Endracion\t230\t-112.82\t1.00\t-37.19\n'
EXPECTED_NPC+=$'Equesobillot\t102\t-286.48\t9.31\t287.82\n'
EXPECTED_NPC+=$'Galaihaurat\t102\t-481.20\t-7.03\t220.55\n'
EXPECTED_NPC+=$'Hakkuru-Rinkuru\t240\t-111.14\t-4.25\t102.06\n'
EXPECTED_NPC+=$'Hut_Door\t140\t-165.36\t-11.67\t77.77\n'
EXPECTED_NPC+=$'Janshura-Rashura\t240\t-230.63\t-8.40\t184.05\n'
EXPECTED_NPC+=$'Laurisse\t102\t-291.76\t28.28\t141.19\n'
EXPECTED_NPC+=$'Narvecaint\t102\t-261.94\t23.14\t127.61\n'
EXPECTED_NPC+=$'Pore-Ohre\t116\t262.27\t-17.25\t-459.61\n'
EXPECTED_NPC+=$'Ruillont\t193\t-69.85\t1.39\t610.81\n'
EXPECTED_NPC+=$'Vicorpasse\t102\t-344.96\t37.23\t265.02\n'
EXPECTED_NPC+=$'Yaucevouchat\t102\t-315.84\t40.04\t184.48'
[[ "$NPC" == "$EXPECTED_NPC" ]] || {
  print -u2 -- 'authored NPC target rows differ from the verified local LSB SQL coordinates:'
  print -u2 -r -- "$NPC"
  exit 1
}
print -r -- 'Verified guide NPC and battlefield targets against local npc_list (zone, x, y, z):'
print -r -- "$NPC"

DROPS="$(mariadb --protocol=socket --batch --skip-column-names xidb <<'SQL'
WITH expected AS (
    SELECT 'Spook' AS mob, 190 AS zoneid, 940 AS itemid
    UNION ALL SELECT 'Orcish_Fodder', 100, 16656
    UNION ALL SELECT 'Ding_Bats', 190, 1112
    UNION ALL SELECT 'Amber_Quadav', 143, 606
    UNION ALL SELECT 'Amber_Quadav', 143, 607
    UNION ALL SELECT 'Amber_Quadav', 143, 608
    UNION ALL SELECT 'Amber_Quadav', 143, 609
)
SELECT DISTINCT e.mob, e.zoneid, e.itemid, ROUND(md.itemRate / 10.0, 1)
FROM expected e
JOIN mob_groups mg ON mg.zoneid = e.zoneid AND mg.name = e.mob
JOIN mob_droplist md ON md.dropId = mg.dropid AND md.itemId = e.itemid
ORDER BY e.zoneid, e.mob, e.itemid;
SQL
)"

DROP_ROWS="$(print -r -- "$DROPS" | awk 'NF { count++ } END { print count+0 }')"
[[ "$DROP_ROWS" == 7 ]] || {
  print -u2 -- "expected seven objective drop entries, found $DROP_ROWS"; exit 1
}
EXPECTED_DROPS=$'Orcish_Fodder\t100\t16656\t15.0\n'
EXPECTED_DROPS+=$'Amber_Quadav\t143\t606\t25.0\n'
EXPECTED_DROPS+=$'Amber_Quadav\t143\t607\t25.0\n'
EXPECTED_DROPS+=$'Amber_Quadav\t143\t608\t25.0\n'
EXPECTED_DROPS+=$'Amber_Quadav\t143\t609\t25.0\n'
EXPECTED_DROPS+=$'Ding_Bats\t190\t1112\t10.0\n'
EXPECTED_DROPS+=$'Spook\t190\t940\t15.0'
[[ "$DROPS" == "$EXPECTED_DROPS" ]] || {
  print -u2 -- 'local mob/item drop rates differ from the verified guide data:'
  print -u2 -r -- "$DROPS"
  exit 1
}
print -r -- 'Expected objective drop rates (percent from itemRate):'
print -r -- "$DROPS"
