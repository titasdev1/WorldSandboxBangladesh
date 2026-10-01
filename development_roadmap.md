# World Sandbox: Bangladesh — Autonomous Development Roadmap

Single canonical Godot project. Every workflow/build must operate on this same repository state.

## Verified state
- Godot 4.4.1
- Android target
- Latest verified Android workflow: run 24
- Current focus: third-person camera, mobile foundation, persistence

## Milestones
- [x] 001 Project foundation / Android CI
- [~] 002 Player controller
- [~] 003 Third-person camera + touch camera
- [~] 004 Procedural Bangladesh-inspired city
- [~] 005 NPC behavior
- [~] 006 Traffic
- [~] 007 Local transport
- [~] 008 Rickshaw/CNG fare negotiation
- [~] 009 Economy
- [~] 010 Mission framework
- [~] 011 Police/wanted
- [~] 012 Combat
- [ ] 013 Vehicle entry/exit and ownership
- [~] 014 World simulation
- [~] 015 Mobile UI
- [ ] 016 Audio
- [~] 017 Save/load foundation
- [ ] 018 Performance/streaming/LOD
- [ ] 019 Game modes
- [ ] 020 Polish
- [ ] 021 QA
- [ ] 022 Release/final archive

## Loop
Inspect → implement highest-priority unfinished system → Android build → inspect logs → fix failures → checkpoint verified state → continue.

Do not create disconnected projects or nested ZIPs.

## Final
Create exactly one FINAL_GAME_PROJECT.zip from the latest complete canonical project directory. It must contain actual source/assets/configuration and legally redistributable dependencies, not previous ZIP files or filler data.
