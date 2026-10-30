#!/usr/bin/env python3
# Copyright (c) 2026 Daniel Bates / Bates LLC. All rights reserved.
import sys,re,subprocess
from pathlib import Path
from collections import defaultdict
from gen_loot import rows,num,lua_str
root=Path(sys.argv[1]);sql=root/'sql'
revision=subprocess.check_output(['git','-C',str(root),'rev-parse','HEAD'],text=True).strip()
pools={num(r[0]) for r in rows(sql/'mob_pools.sql','mob_pools') if num(r[14])&2}
groups={(num(r[0]),num(r[2])) for r in rows(sql/'mob_groups.sql','mob_groups') if num(r[1]) in pools}
zones={num(r[0]):r[4] for r in rows(sql/'zone_settings.sql','zone_settings')}
spawns=defaultdict(list)
for r in rows(sql/'mob_spawn_points.sql','mob_spawn_points'):
 z=(num(r[0])>>12)&4095
 if (num(r[4]),z) in groups: spawns[(r[3] or r[2].replace('_',' '),z,r[2])].append(r)
result=['-- Generated from public LSB spawn records/scripts; standard reference, not server validation.','-- Copyright (c) 2026 Daniel Bates / Bates LLC. All rights reserved.','return {']
for (name,z,internal),rs in sorted(spawns.items()):
 ids=sorted(num(r[0]) for r in rs); script=root/'scripts/zones'/zones.get(z,'unknown')/'mobs'/(internal+'.lua')
 text=script.read_text() if script.exists() else ''
 ph=[]
 for key,slot,offset in re.findall(r'\[ID\.mob\.([A-Z0-9_]+)(?:\[(\d+)\])?\s*-\s*(\d+)\]',text):
  if re.sub('[^A-Z0-9]+','_',internal.upper())==key:
   i=int(slot or 1)-1
   if i<len(ids): ph.append(ids[i]-int(offset))
 spawn='Lottery' if re.search(r'entity\.phList\s*=\s*\{\s*[^}]',text,re.S) else ''
 area='; '.join(f'X {r[7]}, Z {r[9]}' for r in rs[:8])
 fields={'name':name,'zone':z,'ids':', '.join(f'{i} (0x{i&4095:03X})' for i in ids),'spawn':spawn,'area':area,'ph':', '.join(f'{i} (0x{i&4095:03X})' for i in sorted(set(ph))),'scope':'Standard LSB reference','source':'https://github.com/LandSandBoat/server/blob/'+revision+'/scripts/zones/'+zones.get(z,'unknown')+'/mobs/'+internal+'.lua'}
 result.append(' { '+', '.join(k+' = '+(str(v) if isinstance(v,int) else lua_str(v)) for k,v in fields.items())+' },')
result.append('}\n');Path('Vanaguide/data/nm_details.lua').write_text('\n'.join(result));print(len(spawns),'NM records')
