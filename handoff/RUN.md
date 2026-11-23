# How to run this plan with a coding agent

Written for an agent that follows instructions literally. Follow it literally.

## Rules for every session

1. Work on **one work package per session**. Do not start a second one in the same session unless the first is fully done and `PROGRESS.md` is updated.
2. At the start of a session read, in this order: `AGENTS.md`, `handoff/START_HERE.md`, `handoff/PROGRESS.md`, `handoff/PLAN.md` sections 2 and 6, `handoff/DETAIL-STANDARD.md` (for packages 9, 11, 12 and 13), then the one work package you are doing in `handoff/WORK-PACKAGES.md`, then the parts of `handoff/specs/` that the package names. Do not read the whole `audits/` folder; open it only when a spec points there.
3. Do the steps in the order written. Do not redesign. If a step cannot be done as written, use the package's "If it fails" text. If that does not cover it, write what happened in `PROGRESS.md` under a heading `Blocked` and stop.
4. Never invent a coordinate, a road or a building. Every position comes from `inputs/zone.json`, the OSM snapshot, imagery, footage or an override file.
5. Never change `origin` in `inputs/zone.json`. Never edit the `polyline` lists by hand.
6. After every build run `koura/verify_static.py <stage>`. Paste its summary into `PROGRESS.md`.
7. Never write "works in game" unless the in-game probe ran in this session or the owner said they drove it. File checks are "static" only.
8. Commit at the end of the session with the work package number in the message.
9. End every session by updating `PROGRESS.md`: the ledger row, what was checked and how, anything left over, and the next package to do.
10. Do not ask the owner questions mid-session. Use the defaults in `PROGRESS.md` and list the question there.
11. Everything is for personal use and is never published. Do not upload outputs anywhere.
12. For detail work you may use any tool and any online source (satellite and street imagery, videos, social media, shop listings). `DETAIL-STANDARD.md` lists them. Keep what you download out of git.

## State on 2026-11-23: a real base already exists

Read the 2026-11-23 rows of `PROGRESS.md` first. The fork is already in `openlaps/` on branch `koura` with the base changes committed, the environment is in `.venv`, and `koura/build.py S1` / `koura/build.py S2` build the stages (always under `ulimit -v 21000000`). Do not re-clone or re-apply patches. If `openlaps/` is missing (fresh checkout), clone the pinned commit and apply `koura/openlaps_koura.patch`. Continue from the work packages, treating what exists as a first version to bring up to each gate. The section below describes the earlier quick preview and is kept for history.

## The preview is your starting base

The owner wants the preview build of 2026-11-23 used as the base to start from. It is in `poc/koura_preview/` (also installed in the game as `koura_preview`). How it was made:

- `evidence/preview_patch.diff`: the changes to openlaps (commit `d9e713c`). Apply it to the fork in WP0 with `git apply`, on branch `koura`, as the first commit.
- `evidence/build_preview.py` and `evidence/kart_pts.py`: the driver that reads `inputs/zone.json`, builds the stage 2 zone polygon, injects the rough kart track and sets the start points. Use it as the first version of `koura/build.py`.
- `evidence/preview_build.log`: the full log of a successful 21 minute build.

What the patch already does, so do not redo it from nothing, only bring it up to the work package's full standard and gate: free-roam zone polygon (`args.zona_fn`, part of WP5); edge wall and colliders kept in the game export (WP2 step 1, done the quick way: nothing is deleted; the rename to group `limite` is still to do); no live-mode script (WP2); multiple start points (WP2); flat roofs with tanks by overriding the `eu` profile (a stand-in for WP3); 1.5 m road-smoothing cells through the `KOURA_CELDA` environment variable (a stand-in for the WP6 memory fix).

What the preview does not have: the pinned origin from `zone.json` (it centres on its own bounding box, so its local coordinates differ from the plan's; switch to the pinned origin before any override file is written), the Lebanon profile, aerial imagery, performance work, OSM ids and overrides, any detail pass. Its kart track is a hand-placed rough loop, to be replaced by WP11.

## Order

WP0, WP2, WP3, WP4, WP5, WP1, WP6, WP8, WP9, WP12, WP7, WP11, WP13, WP10.

Stage 1 exists after WP5. Stage 1 at the owner's detail standard exists after WP12. Stage 2 (loop, shortcut, Tourza road, Dabbousi Farms road, kart track) exists after WP7 and WP11, and reaches the owner's "detailed" standard after WP13.

## The prompt to paste at the start of each session

```
You are continuing the Koura Assetto Corsa map project in this folder.
Read AGENTS.md and handoff/RUN.md and obey them exactly.
Then read handoff/PROGRESS.md and do the next work package that is not done,
following the order in handoff/RUN.md. Do only that one package.
Finish by running the package's gate, saving its evidence, updating
handoff/PROGRESS.md and committing. If you are blocked, record it under
"Blocked" in handoff/PROGRESS.md and stop.
```

## Size of each package, to plan usage

| Package | Kind of work | Relative size |
|---|---|---|
| WP0 | setup, downloads, baseline builds | small |
| WP1 | launching the game from a shell, probe app | medium, may fail; time-boxed |
| WP2 | code changes in the fork | medium |
| WP3 | code changes in the fork | medium |
| WP4 | new imagery reader | medium |
| WP5 | zone build, first stage 1 | medium |
| WP6 | performance changes | large |
| WP7 | stage 2 build and fixes | large |
| WP8 | override files | medium |
| WP9 | video download, frame review, new places | large, mostly looking at images |
| WP10 | stage 3 and extras | large, optional |
| WP11 | kart track | large |
| WP12 | item-by-item detail pass | very large; split over several sessions by checklist rows |
| WP13 | detail pass outside the green box | very large; split by route, 500 m sections |

WP9 and WP12 need a model that can look at images. If the agent in use cannot open image files, say so in `PROGRESS.md` and do only the non-visual steps.
