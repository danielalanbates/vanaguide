-- Learned zone lines, dumped from play by /vg dump graph.
-- 171 crossings.  Paste the pairs into data/zonelines.lua Z.walk (they are already
-- de-duplicated and ordered); a seeded copy needs no per-character learning.
Z.learned_walk = {
    { 5, 18 }, { 5, 230 }, { 9, 24 }, { 9, 25 }, { 9, 178 }, { 9, 230 }, { 9, 274 }, { 11, 18 },
    { 11, 230 }, { 18, 24 }, { 18, 25 }, { 18, 50 }, { 18, 263 }, { 24, 29 }, { 24, 48 }, { 24, 245 },
    { 24, 263 }, { 24, 284 }, { 25, 26 }, { 25, 34 }, { 26, 29 }, { 26, 34 }, { 27, 32 }, { 29, 30 },
    { 29, 48 }, { 30, 48 }, { 32, 33 }, { 32, 52 }, { 32, 80 }, { 32, 81 }, { 32, 105 }, { 34, 48 },
    { 35, 50 }, { 48, 50 }, { 48, 54 }, { 48, 80 }, { 48, 230 }, { 50, 52 }, { 50, 53 }, { 50, 87 },
    { 52, 53 }, { 53, 54 }, { 53, 61 }, { 53, 64 }, { 54, 80 }, { 61, 80 }, { 64, 67 }, { 67, 68 },
    { 68, 72 }, { 68, 78 }, { 72, 78 }, { 78, 80 }, { 80, 84 }, { 80, 105 }, { 80, 231 }, { 81, 230 },
    { 84, 85 }, { 84, 87 }, { 84, 89 }, { 85, 89 }, { 87, 88 }, { 88, 94 }, { 89, 94 }, { 94, 98 },
    { 98, 100 }, { 98, 102 }, { 98, 105 }, { 98, 123 }, { 103, 104 }, { 104, 106 }, { 105, 108 }, { 105, 116 },
    { 105, 137 }, { 106, 107 }, { 106, 123 }, { 108, 109 }, { 108, 123 }, { 109, 112 }, { 112, 113 }, { 113, 114 },
    { 114, 117 }, { 116, 123 }, { 118, 121 }, { 121, 123 }, { 123, 126 }, { 123, 132 }, { 123, 136 }, { 123, 137 },
    { 126, 132 }, { 126, 136 }, { 132, 137 }, { 137, 145 }, { 137, 157 }, { 137, 159 }, { 137, 164 }, { 138, 156 },
    { 145, 164 }, { 156, 159 }, { 157, 164 }, { 159, 161 }, { 161, 168 }, { 161, 176 }, { 164, 167 }, { 164, 171 },
    { 167, 171 }, { 168, 176 }, { 171, 175 }, { 175, 178 }, { 176, 182 }, { 176, 184 }, { 176, 208 }, { 178, 218 },
    { 182, 184 }, { 184, 208 }, { 208, 230 }, { 208, 231 }, { 208, 239 }, { 218, 230 }, { 230, 234 }, { 230, 235 },
    { 230, 236 }, { 230, 241 }, { 231, 232 }, { 231, 235 }, { 231, 243 }, { 231, 274 }, { 232, 233 }, { 233, 234 },
    { 233, 236 }, { 234, 238 }, { 236, 237 }, { 236, 239 }, { 236, 240 }, { 237, 238 }, { 237, 239 }, { 239, 240 },
    { 240, 243 }, { 241, 242 }, { 241, 243 }, { 241, 245 }, { 241, 248 }, { 242, 243 }, { 245, 248 }, { 245, 274 },
    { 246, 247 }, { 246, 248 }, { 246, 249 }, { 247, 248 }, { 248, 252 }, { 249, 250 }, { 249, 251 }, { 249, 254 },
    { 249, 255 }, { 251, 252 }, { 252, 253 }, { 252, 256 }, { 253, 254 }, { 254, 255 }, { 255, 256 }, { 258, 262 },
    { 258, 263 }, { 262, 265 }, { 262, 266 }, { 263, 267 }, { 265, 266 }, { 266, 267 }, { 266, 274 }, { 267, 270 },
    { 267, 274 }, { 270, 277 }, { 277, 284 },
}

-- 5 Uleguerand Range  <->  18 Promyvion - Dem
-- 5 Uleguerand Range  <->  230 Southern San d'Oria
-- 9 Pso'Xja  <->  24 Lufaise Meadows
-- 9 Pso'Xja  <->  25 Misareaux Coast
-- 9 Pso'Xja  <->  178 The Shrine of Ru'Avitau
-- 9 Pso'Xja  <->  230 Southern San d'Oria
-- 9 Pso'Xja  <->  274 Outer Ra'Kaznar
-- 11 Oldton Movalpolos  <->  18 Promyvion - Dem
-- 11 Oldton Movalpolos  <->  230 Southern San d'Oria
-- 18 Promyvion - Dem  <->  24 Lufaise Meadows
-- 18 Promyvion - Dem  <->  25 Misareaux Coast
-- 18 Promyvion - Dem  <->  50 Aht Urhgan Whitegate
-- 18 Promyvion - Dem  <->  263 Yorcia Weald
-- 24 Lufaise Meadows  <->  29 Riverne - Site #B01
-- 24 Lufaise Meadows  <->  48 Al Zahbi
-- 24 Lufaise Meadows  <->  245 Lower Jeuno
-- 24 Lufaise Meadows  <->  263 Yorcia Weald
-- 24 Lufaise Meadows  <->  284 Celennia Memorial Library
-- 25 Misareaux Coast  <->  26 Tavnazian Safehold
-- 25 Misareaux Coast  <->  34 Grand Palace of Hu'Xzoi
-- 26 Tavnazian Safehold  <->  29 Riverne - Site #B01
-- 26 Tavnazian Safehold  <->  34 Grand Palace of Hu'Xzoi
-- 27 Phomiuna Aqueducts  <->  32 Sealion's Den
-- 29 Riverne - Site #B01  <->  30 Riverne - Site #A01
-- 29 Riverne - Site #B01  <->  48 Al Zahbi
-- 30 Riverne - Site #A01  <->  48 Al Zahbi
-- 32 Sealion's Den  <->  33 Al'Taieu
-- 32 Sealion's Den  <->  52 Bhaflau Thickets
-- 32 Sealion's Den  <->  80 Southern San d'Oria [S]
-- 32 Sealion's Den  <->  81 East Ronfaure [S]
-- 32 Sealion's Den  <->  105 Batallia Downs
-- 34 Grand Palace of Hu'Xzoi  <->  48 Al Zahbi
-- 35 The Garden of Ru'Hmet  <->  50 Aht Urhgan Whitegate
-- 48 Al Zahbi  <->  50 Aht Urhgan Whitegate
-- 48 Al Zahbi  <->  54 Arrapago Reef
-- 48 Al Zahbi  <->  80 Southern San d'Oria [S]
-- 48 Al Zahbi  <->  230 Southern San d'Oria
-- 50 Aht Urhgan Whitegate  <->  52 Bhaflau Thickets
-- 50 Aht Urhgan Whitegate  <->  53 Nashmau
-- 50 Aht Urhgan Whitegate  <->  87 Bastok Markets [S]
-- 52 Bhaflau Thickets  <->  53 Nashmau
-- 53 Nashmau  <->  54 Arrapago Reef
-- 53 Nashmau  <->  61 Mount Zhayolm
-- 53 Nashmau  <->  64 Navukgo Execution Chamber
-- 54 Arrapago Reef  <->  80 Southern San d'Oria [S]
-- 61 Mount Zhayolm  <->  80 Southern San d'Oria [S]
-- 64 Navukgo Execution Chamber  <->  67 Jade Sepulcher
-- 67 Jade Sepulcher  <->  68 Aydeewa Subterrane
-- 68 Aydeewa Subterrane  <->  72 Alzadaal Undersea Ruins
-- 68 Aydeewa Subterrane  <->  78 Hazhalm Testing Grounds
-- 72 Alzadaal Undersea Ruins  <->  78 Hazhalm Testing Grounds
-- 78 Hazhalm Testing Grounds  <->  80 Southern San d'Oria [S]
-- 80 Southern San d'Oria [S]  <->  84 Batallia Downs [S]
-- 80 Southern San d'Oria [S]  <->  105 Batallia Downs
-- 80 Southern San d'Oria [S]  <->  231 Northern San d'Oria
-- 81 East Ronfaure [S]  <->  230 Southern San d'Oria
-- 84 Batallia Downs [S]  <->  85 La Vaule [S]
-- 84 Batallia Downs [S]  <->  87 Bastok Markets [S]
-- 84 Batallia Downs [S]  <->  89 Grauberg [S]
-- 85 La Vaule [S]  <->  89 Grauberg [S]
-- 87 Bastok Markets [S]  <->  88 North Gustaberg [S]
-- 88 North Gustaberg [S]  <->  94 Windurst Waters [S]
-- 89 Grauberg [S]  <->  94 Windurst Waters [S]
-- 94 Windurst Waters [S]  <->  98 Sauromugue Champaign [S]
-- 98 Sauromugue Champaign [S]  <->  100 West Ronfaure
-- 98 Sauromugue Champaign [S]  <->  102 La Theine Plateau
-- 98 Sauromugue Champaign [S]  <->  105 Batallia Downs
-- 98 Sauromugue Champaign [S]  <->  123 Yuhtunga Jungle
-- 103 Valkurm Dunes  <->  104 Jugner Forest
-- 104 Jugner Forest  <->  106 North Gustaberg
-- 105 Batallia Downs  <->  108 Konschtat Highlands
-- 105 Batallia Downs  <->  116 East Sarutabaruta
-- 105 Batallia Downs  <->  137 Xarcabard [S]
-- 106 North Gustaberg  <->  107 South Gustaberg
-- 106 North Gustaberg  <->  123 Yuhtunga Jungle
-- 108 Konschtat Highlands  <->  109 Pashhow Marshlands
-- 108 Konschtat Highlands  <->  123 Yuhtunga Jungle
-- 109 Pashhow Marshlands  <->  112 Xarcabard
-- 112 Xarcabard  <->  113 Cape Teriggan
-- 113 Cape Teriggan  <->  114 Eastern Altepa Desert
-- 114 Eastern Altepa Desert  <->  117 Tahrongi Canyon
-- 116 East Sarutabaruta  <->  123 Yuhtunga Jungle
-- 118 Buburimu Peninsula  <->  121 The Sanctuary of Zi'Tah
-- 121 The Sanctuary of Zi'Tah  <->  123 Yuhtunga Jungle
-- 123 Yuhtunga Jungle  <->  126 Qufim Island
-- 123 Yuhtunga Jungle  <->  132 Abyssea - La Theine
-- 123 Yuhtunga Jungle  <->  136 Beaucedine Glacier [S]
-- 123 Yuhtunga Jungle  <->  137 Xarcabard [S]
-- 126 Qufim Island  <->  132 Abyssea - La Theine
-- 126 Qufim Island  <->  136 Beaucedine Glacier [S]
-- 132 Abyssea - La Theine  <->  137 Xarcabard [S]
-- 137 Xarcabard [S]  <->  145 Giddeus
-- 137 Xarcabard [S]  <->  157 Middle Delkfutt's Tower
-- 137 Xarcabard [S]  <->  159 Temple of Uggalepih
-- 137 Xarcabard [S]  <->  164 Garlaige Citadel [S]
-- 138 Castle Zvahl Baileys [S]  <->  156 Throne Room [S]
-- 145 Giddeus  <->  164 Garlaige Citadel [S]
-- 156 Throne Room [S]  <->  159 Temple of Uggalepih
-- 157 Middle Delkfutt's Tower  <->  164 Garlaige Citadel [S]
-- 159 Temple of Uggalepih  <->  161 Castle Zvahl Baileys
-- 161 Castle Zvahl Baileys  <->  168 Chamber of Oracles
-- 161 Castle Zvahl Baileys  <->  176 Sea Serpent Grotto
-- 164 Garlaige Citadel [S]  <->  167 Bostaunieux Oubliette
-- 164 Garlaige Citadel [S]  <->  171 Crawlers' Nest [S]
-- 167 Bostaunieux Oubliette  <->  171 Crawlers' Nest [S]
-- 168 Chamber of Oracles  <->  176 Sea Serpent Grotto
-- 171 Crawlers' Nest [S]  <->  175 The Eldieme Necropolis [S]
-- 175 The Eldieme Necropolis [S]  <->  178 The Shrine of Ru'Avitau
-- 176 Sea Serpent Grotto  <->  182 Walk of Echoes
-- 176 Sea Serpent Grotto  <->  184 Lower Delkfutt's Tower
-- 176 Sea Serpent Grotto  <->  208 Quicksand Caves
-- 178 The Shrine of Ru'Avitau  <->  218 Abyssea - Altepa
-- 182 Walk of Echoes  <->  184 Lower Delkfutt's Tower
-- 184 Lower Delkfutt's Tower  <->  208 Quicksand Caves
-- 208 Quicksand Caves  <->  230 Southern San d'Oria
-- 208 Quicksand Caves  <->  231 Northern San d'Oria
-- 208 Quicksand Caves  <->  239 Windurst Walls
-- 218 Abyssea - Altepa  <->  230 Southern San d'Oria
-- 230 Southern San d'Oria  <->  234 Bastok Mines
-- 230 Southern San d'Oria  <->  235 Bastok Markets
-- 230 Southern San d'Oria  <->  236 Port Bastok
-- 230 Southern San d'Oria  <->  241 Windurst Woods
-- 231 Northern San d'Oria  <->  232 Port San d'Oria
-- 231 Northern San d'Oria  <->  235 Bastok Markets
-- 231 Northern San d'Oria  <->  243 Ru'Lude Gardens
-- 231 Northern San d'Oria  <->  274 Outer Ra'Kaznar
-- 232 Port San d'Oria  <->  233 Chateau d'Oraguille
-- 233 Chateau d'Oraguille  <->  234 Bastok Mines
-- 233 Chateau d'Oraguille  <->  236 Port Bastok
-- 234 Bastok Mines  <->  238 Windurst Waters
-- 236 Port Bastok  <->  237 Metalworks
-- 236 Port Bastok  <->  239 Windurst Walls
-- 236 Port Bastok  <->  240 Port Windurst
-- 237 Metalworks  <->  238 Windurst Waters
-- 237 Metalworks  <->  239 Windurst Walls
-- 239 Windurst Walls  <->  240 Port Windurst
-- 240 Port Windurst  <->  243 Ru'Lude Gardens
-- 241 Windurst Woods  <->  242 Heavens Tower
-- 241 Windurst Woods  <->  243 Ru'Lude Gardens
-- 241 Windurst Woods  <->  245 Lower Jeuno
-- 241 Windurst Woods  <->  248 Selbina
-- 242 Heavens Tower  <->  243 Ru'Lude Gardens
-- 245 Lower Jeuno  <->  248 Selbina
-- 245 Lower Jeuno  <->  274 Outer Ra'Kaznar
-- 246 Port Jeuno  <->  247 Rabao
-- 246 Port Jeuno  <->  248 Selbina
-- 246 Port Jeuno  <->  249 Mhaura
-- 247 Rabao  <->  248 Selbina
-- 248 Selbina  <->  252 Norg
-- 249 Mhaura  <->  250 Kazham
-- 249 Mhaura  <->  251 Hall of the Gods
-- 249 Mhaura  <->  254 Abyssea - Grauberg
-- 249 Mhaura  <->  255 Abyssea - Empyreal Paradox
-- 251 Hall of the Gods  <->  252 Norg
-- 252 Norg  <->  253 Abyssea - Uleguerand
-- 252 Norg  <->  256 Western Adoulin
-- 253 Abyssea - Uleguerand  <->  254 Abyssea - Grauberg
-- 254 Abyssea - Grauberg  <->  255 Abyssea - Empyreal Paradox
-- 255 Abyssea - Empyreal Paradox  <->  256 Western Adoulin
-- 258 Rala Waterways  <->  262 Foret de Hennetiel
-- 258 Rala Waterways  <->  263 Yorcia Weald
-- 262 Foret de Hennetiel  <->  265 Morimar Basalt Fields
-- 262 Foret de Hennetiel  <->  266 Marjami Ravine
-- 263 Yorcia Weald  <->  267 Kamihr Drifts
-- 265 Morimar Basalt Fields  <->  266 Marjami Ravine
-- 266 Marjami Ravine  <->  267 Kamihr Drifts
-- 266 Marjami Ravine  <->  274 Outer Ra'Kaznar
-- 267 Kamihr Drifts  <->  270 Cirdas Caverns
-- 267 Kamihr Drifts  <->  274 Outer Ra'Kaznar
-- 270 Cirdas Caverns  <->  277 Ra'Kaznar Turris
-- 277 Ra'Kaznar Turris  <->  284 Celennia Memorial Library
