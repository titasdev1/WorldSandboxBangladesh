# Project A-Square — Competitive reference and presentation blueprint

**Purpose:** translate the user's named-game references into original A-Square systems. This is a design and acceptance specification, not a claim that the listed systems already exist. Do not copy game code, maps, characters, logos, music, UI artwork or other copyrighted assets.

**Reference date:** 13 November 2026.

## 1. Product identity: one game, multiple genuine experiences

A-Square is one Android game with a shared identity, profile, progression, content manager and world/map catalogue. It can contain several genuinely different game families, but a mode must not be advertised as playable until its own complete loop passes acceptance.

The project has two linked deliverables:
1. **The game:** a playable, mobile-first open-world action game with competitive and other mode families.
2. **The world:** Shariatpur first, then the remaining Dhaka Division and later the wider Bangladesh/world content pipeline.

Keep the one canonical Godot project and Android build. Keep the independently built map package pipeline. Do not create disconnected prototypes or competing APK projects.

## 2. What to learn from each reference

| Reference | Player-facing systems worth learning from | A-Square interpretation |
|---|---|---|
| Call of Duty: Mobile / Call of Duty | 3D operator-and-weapon lobby, loadouts, weapon inspection, tactical HUD, short match flow, MP and BR rule families, score/result presentation, limited-time events and seasonal progression | A real 3D A-Square lobby, a coherent operator/loadout system, compact responsive mobile controls, distinct MP/BR modes, honest match lifecycle and original seasonal content |
| VALORANT | 5v5 tactical round structure, distinct roles/agents, attacking vs defending, limited lives per round, ability economy, map-specific tactics, team composition, competitive progression and mastery | A future original Tactical Arena mode: defined roles and abilities, round economy, attack/defend objectives, map-specific cover/sightlines, team composition and role mastery |
| Arena of Valor / Mobile Legends: Bang Bang | 5v5 MOBA team roles, hero selection, three-lane map conventions, towers, minions, jungle objectives, item builds, team fights, minimap awareness, MVP/score breakdown and hero mastery | A separate original A-Square MOBA mode with its own arena, lane/minion/tower/jungle rules, hero/role roster, item economy, team objectives and post-match hero statistics |
| Grand Theft Auto / GTA VI | Open-world freedom, coherent districts, interiors, missions, environmental storytelling, traffic, pedestrians, police response, side activities, contextual interactions, dynamic audio and world density | The Deshi Sandbox pillar: local Bangladeshi street life, missions, transport bargaining, NPC routines, stores/economy, wanted/police, enterable buildings and map identity |
| Forza Horizon | Car collection and personalization, tuning, vehicle handling, cockpit/chase cameras, open-world driving, meets/convoys, races, drift/drag/time attack, seasonal atmosphere, leaderboards and shared activities | A genuine driving pillar: detailed original vehicles, physics, cockpit/chase cameras, vehicle ownership/tuning, meets, races and driving challenges |

**Important distinction:** GTA VI was officially scheduled for 19 November 2026 as of this reference date; it must be treated as an upcoming title at this checkpoint, not as a released game whose full player experience we have tested. Forza Horizon 6 official material is the basis for the automotive/open-world reference. VALORANT and AOV official descriptions inform their genre structures. See the source links at the end.

## 3. Mode architecture — separate rule systems, shared account and progression

### A. Deshi Open World / Deshi Sandbox
- Select installed district and saved session; spawn or continue.
- Free roam, real-world exploration, authored missions and dynamic activities.
- Bangladesh-specific traffic, pedestrians, rickshaw/CNG/bus/car/motorcycle, vendors, shops, fares, local economy, police/wanted, weather, time and building entry.
- Story contracts, delivery, rescue, racing, chase, investigation, business, exploration and combat missions.
- Save money, inventory, owned vehicles, mission progress, world state and player position.
- Offline civilian/traffic simulation uses local AI. Do not fake ambient AI when in the human-player-only online-world variant.

### B. Online Open World
- Actual session creation, real player roster, joining/leaving, synchronized player transforms and actions, reconnect and server authority.
- Ambient shopkeeper/pedestrian simulation follows the user's requested mode rules; do not silently add bots to a human-only online-world session.
- No fake player count, ping, matchmaking status or online badge.

### C. Competitive Shooter family
- **MP Casual:** small-team rounds or score-limit matches, selectable installed maps, real spawn logic, team scores and match result.
- **MP Ranked:** rating/rank, region eligibility, real queue, team balance, map rotation/vote, disconnect/reconnect and server-validated score.
- **BR Casual/Ranked:** deployment, loot, inventory, safe-zone phases, combat, revive/spectate, elimination, win/loss and progression. Ranked adds real rating, region and matchmaking rules.
- **Tactical Arena (future):** distinct 5v5 round-based tactical rules; attack/defend, role/ability economy, map objectives and competitive result. Not a reskin of CODM MP.

### D. MOBA family
- Hero selection and (when supported) ban/pick, role assignment and team lineup.
- Three-lane arena with base, towers, minions, jungle camps and map objectives.
- Hero skills, cooldowns, level progression, gold/XP, item shop, team fights and respawn rules.
- Minimap, ally/enemy information with fair visibility rules, pings and team communication.
- Victory/defeat, MVP, individual hero statistics, mastery and rewards.
- This is a distinct mode with a real map and combat rules, not a card in the lobby or a shooter map with different icons.

### E. Racing / Driving family
- Separate time trial, circuit/sprint race, drift, drag, checkpoint, pursuit and convoy/meets activities.
- Real vehicle handling and collision, steering, throttle, braking, suspension, wheel rotation, lights, damage and cockpit/chase cameras.
- Garage with owned vehicles, upgrades/tuning, paint/liveries, saved setups and transparent performance values.
- AI opponents offline; actual network synchronization/anti-cheat for online races.
- Rewards, best times, leaderboards and events.

### F. PvE / special experiences
- Zombies/co-op survival: enemy director, waves/objectives, revive, ammo/resource loop, fail/victory and rewards.
- Limited-time modes: data-driven rules, supported maps, loadout restrictions, event progression, schedule and reward definitions.
- Do not expose a mode as playable until its mode-specific test passes.

## 4. Shared player journey and hierarchy

1. **Cold launch:** brief original identity animation; do not block the player with a long static screen.
2. **Profile:** local guest/offline entry must work; online login only reports success after a real provider/session handshake.
3. **Content manager:** measured map/asset download, byte progress, storage check, resumable parts, hashes, version and activation state.
4. **3D lobby:** actual rigged player/operator, current outfit and weapon, animated idle/inspection, scene lighting and a real 3D environment. The lobby is not a generated poster.
5. **Navigation:** profile/level/rank/currency/notices; prominent Play; Loadout/Characters/Vehicles; Modes; Events/Season; Achievements; Social/Clan; Settings; Store/Battle Pass where implemented. Every visible control opens a real screen or is clearly marked unavailable.
6. **Mode setup:** region/map rules, offline/online selection where supported, squad/team, loadout/hero/vehicle selection and queue state.
7. **Matchmaking/pre-match:** actual roster/readiness/timer, map vote where applicable, and streaming progress based on real work.
8. **Match introduction:** animated roster/team reveal, character/vehicle/arena camera or short cinematic transition; never claim a rendered trailer is gameplay.
9. **In-match:** mode-specific HUD, minimap, objectives, status, ability/ammo/vehicle values and accessibility controls.
10. **Post-match:** victory/defeat, team scoreboard, MVP, stats, mission/event progress, earned rewards, rank changes and return to the same lobby/profile state.

## 5. High-resolution images and videos are part of the game — used correctly

Do not discard generated stills or cinematic video. High-quality authored media can materially improve:
- studio/project identity and boot sequence;
- login/profile welcome and season intro;
- event/season/Battle Pass banners and character reveal;
- lobby background loops, promotional panels and mode cards;
- matchmaking interstitials, map/arena loading, team introductions and vehicle showcases;
- victory/defeat, MVP, achievements, unlocks and reward reveals;
- tutorial explainers and patch/event announcements.

**Production rule:**
- Use original or properly licensed generated stills/video as finite, optimized media assets. Use them for presentation, not as an imitation of an interactive map or live match.
- Keep playable avatars, weapons, cars, NPCs, buildings, maps, menu controls, UI values and match state as real game-engine content.
- Create short clips at appropriate aspect ratios/resolutions, encode with Android-supported formats, stream or preload only the next needed clip, cache by version, release decoder memory after use, allow skip/mute, provide reduced-motion/static fallback and no-network fallback.
- Keep text, names, scores, timers, ranks and button controls in Godot UI so they remain legible, localized, dynamic and accessible; do not bake critical UI text into AI video.
- Generated video may distort logos, text, vehicle geometry, continuity and motion; inspect every clip frame-by-frame before use. Never use it as evidence of gameplay functionality.
- Avoid playing a large 4K clip on every transition on a mid-range phone. Measure decode time, memory, battery and file size; offer low-bandwidth and reduced-motion options.
- High-resolution master footage may be retained as production source, but Android receives optimized, scene-specific variants.

## 6. Production sequencing

1. Stabilize the existing Android boot, player controls, camera, interaction, save and small playable world.
2. Replace the weak character placeholder with a visually reviewed, rigged, textured character and correctly bound animations; fix sprint/jump/crouch/cloth deformation and test on the target device.
3. Build one complete Deshi Sandbox vertical slice in a small dense area: doors, interiors, NPCs, one working local vehicle, shops, traffic, one mission chain and save/reload.
4. Build one genuinely complete casual shooter match loop with real bots, hit detection, weapon handling, spawn, scoring and results.
5. Build the 3D lobby, navigation, loadout, matchmaking/pre-match, map loading, victory/defeat, MVP and achievement presentation shell around real player/profile/match state.
6. Expand ranked/BR/Zombies only after their separate rules and server/offline behavior are real.
7. Add the racing pillar with at least one authored car, proper driving physics and one polished event; then scale the fleet/garage.
8. Add the MOBA as a distinct game mode only when a full lane/minion/tower/jungle/hero/item loop can be delivered and supported on Android.
9. Advance Shariatpur's real-world quality gate independently; do not call 60 tile records a finished district. Preserve geography, facade evidence, floor evidence, Bangla identity, unique interiors and navigable connections.
10. Implement real online services incrementally: two-client test, casual matchmaking, reconnect/disconnect and session authority before ranked/BR/large open-world scale.

## 7. Acceptance rules

A feature is accepted only when all relevant layers exist:
- source implementation;
- actual assets/data;
- integration in the canonical game;
- automated tests appropriate to the system;
- rendered output and behavior reviewed;
- Android build/integrity checked;
- physical-device touch, visual, stability and performance QA where required.

Do not calculate a single game completion percentage. Track independently: playable core, mode loops, character/animation quality, vehicles, UI/presentation, map geometry, facade identity, floor evidence, Android packaging and device QA.

## 8. Reference links

- Call of Duty: Mobile: https://www.callofduty.com/mobile
- CODM Season 10 official update: https://www.callofduty.com/blog/2026/11/call-of-duty-mobile-season-10-seventh-anniversary
- VALORANT: https://playvalorant.com/
- VALORANT agent mastery help: https://support-valorant.riotgames.com/
- Arena of Valor: https://www.arenaofvalor.com/
- Forza Horizon 6 official FAQ: https://support.forza.net/hc/en-us/articles/forza-horizon-6-faq
- Forza Horizon official site: https://forza.net/
- Grand Theft Auto VI official site: https://www.rockstargames.com/VI
- Project master plan: `DREAM_GAME_MASTER_PLAN.md`
- Acceptance matrix: `DREAM_GAME_ACCEPTANCE_MATRIX.md`
