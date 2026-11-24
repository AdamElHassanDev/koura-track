# Roadmap

Status of each work package from [`handoff/WORK-PACKAGES.md`](handoff/WORK-PACKAGES.md). The detailed ledger, with evidence for every claim, is [`handoff/PROGRESS.md`](handoff/PROGRESS.md).

| | Meaning |
|---|---|
| ✅ | done and checked |
| 🟡 | partly done |
| ⬜ | not started |

## Foundation

| | Work package | State |
|---|---|---|
| ✅ | WP0 Setup and baseline | Stock trial rebuilt at three resolutions, Build 9 measured, static verifier implemented and S3 map data cached. |
| ✅ | WP1 Game launch and probe | Trial passed the automated game probe on Proton with CSP 0.2.11. |
| 🟡 | WP2 Export fixes for free roam | Edge wall, no live-mode script, start points done. |
| 🟡 | WP3 Lebanon profile | First version in use. |
| 🟡 | WP4 Aerial imagery reader | Working, zoom 18. |
| 🟡 | WP5 Zone build and stage 1 | Stage 1 builds in 3 minutes. |
| ⬜ | WP6 Performance | Frame rate not measured. Memory handled with a cap and a coarser merge grid. |
| 🟡 | WP7 Stage 2: the loop | Whole network builds in 20 minutes and is installed. |

## Road quality (the owner's first concern)

| | Item | State |
|---|---|---|
| ✅ | Measuring tools | `ride.py`, `grade.py`, `survey.py`, `elevation.py` |
| 🟡 | Smooth grades | Main highways: 0.9 % of length over a 2 % slope jump in 8 m, none over 5 %. Target: none over 2 %. |
| 🟡 | Junction surfaces | Bare patches paved. Remaining jumps of 7 to 8 % at some junction patches. |
| ⬜ | Junction shapes | Still generic; to be corrected junction by junction from imagery. |
| 🟡 | Real heights | Road follows the 30 m height model to 0.7 m on the loop (build 9). Next: fit to a phone recording of the real roads. |

## Detail

| | Work package | State |
|---|---|---|
| ⬜ | WP8 Map-data ids and override files | Missing buildings: about 1 roof in 10 in central Btouratij. |
| ⬜ | WP9 Footage and recent places | Knots, Clutch N' Carb and others listed in `handoff/inputs/recent_places.json`. |
| 🟡 | WP11 Karting Mania | Surface and shape done. Tyre walls, kerbs, concrete colour, pit building, timing and real slope not done. |
| ⬜ | WP12 Btouratij and Nakhle fine detail | |
| ⬜ | WP13 Detail outside the stage 1 box | |
| ⬜ | WP14 Ground inside the loop | The middle of the loop is empty today. Fill with ground, grass and olive groves. |
| ⬜ | WP10 Speed bumps, night lighting, traffic | |
