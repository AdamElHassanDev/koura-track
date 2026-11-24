# Koura free-roam map for Assetto Corsa

Start with `handoff/START_HERE.md`. It links everything else. `handoff/BASE.md` describes what exists today and the order of work. `handoff/RUN.md` says how to work: one work package per session.

Rules that hold for the whole project:

- Personal use only. The built map is never published, so aerial imagery that cannot be redistributed is allowed as a build-time source. The repository itself is public (https://github.com/AdamElHassanDev/koura-track): never commit imagery, renders made from it, or built tracks.
- Target: Assetto Corsa on this Fedora desktop, run through Steam Proton with Custom Shaders Patch 0.2.11.
- No Blender, ksEditor or Wine on the build path. The track file is written in pure Python.
- Never claim a build works in game from file checks alone. Either the in-game probe ran, or the owner drove it and said so. Record which in `handoff/PROGRESS.md`.
- Update `handoff/PROGRESS.md` after every work package.
- The owner's first priority is extreme detail in Btouratij and Nakhle (the stage 1 box): every small road, every house, roadside details. See work package 12.
- New shops and buildings that the 2024 imagery does not show are tracked in `handoff/inputs/recent_places.json`.
- Outside the stage 1 box the map must still be detailed, to the "Detailed" column of the table in work package 13. Only stage 3 ground is background quality.
- Karting Mania must be an exact copy of the real track and work as a real timed circuit (work package 11, steps 10 and 11).
- The standard outside stage 1 is "it looks like the real drive", for the whole detailed ground, not only the strip beside the route.
- `handoff/DETAIL-STANDARD.md` is the owner's quality bar. Any tool and any online source may be used for detail work.
- Git: commits show only the owner (`AdamElHassanDev`), with no AI attribution of any kind. See the Git section of `handoff/RUN.md`.
- Keep the public pages current: add a `CHANGELOG.md` entry for every build the owner receives, and tick `ROADMAP.md` when a work package passes its gate.
- Owner's additions of 2026-11-23 (in `handoff/DETAIL-STANDARD.md`): smooth roads with real elevation, recognisable houses from photographs, no dead ground inside the loop, accurate vegetation and walls.
- Road heights are reserved (`handoff/BASE.md` section 4): do not change how road heights or road smoothing are computed until `handoff/PROGRESS.md` has a row "Road-height reserve lifted". Plan-view road changes and everything beside the road are open.
- Never store an absolute height. Every added object is placed by latitude and longitude and takes its height from the terrain at build time; heights above ground are fine.
- The owner drives the map while work goes on (`handoff/BASE.md` section 5): one large build at a time, stop builds by process id only, never install while the game is running, never start the game unless the owner says it is free, `recordings/owner/` is read only.
