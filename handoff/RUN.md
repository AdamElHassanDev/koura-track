# How to run this plan with a coding agent

Written for an agent that follows instructions literally. Follow it literally.

## Rules for every session

1. Work on **one work package per session**. Do not start a second one in the same session unless the first is fully done and `PROGRESS.md` is updated.
2. At the start of a session read, in this order: `AGENTS.md`, `handoff/START_HERE.md`, `handoff/BASE.md`, `handoff/PROGRESS.md`, `handoff/PLAN.md` sections 2 and 6, `handoff/DETAIL-STANDARD.md` (for packages 8, 9, 11, 12, 13 and 14), then the one work package you are doing in `handoff/WORK-PACKAGES.md`, then the parts of `handoff/specs/` that the package names. Do not read the whole `audits/` folder; open it only when a spec points there.
3. Do the steps in the order written. Do not redesign. If a step cannot be done as written, use the package's "If it fails" text. If that does not cover it, write what happened in `PROGRESS.md` under a heading `Blocked` and stop.
4. Never invent a coordinate, a road or a building. Every position comes from `inputs/zone.json`, the OSM snapshot, imagery, footage or an override file.
5. Never change `origin` in `inputs/zone.json`. Never edit the `polyline` lists by hand.
6. After every build run `koura/verify_static.py <stage>`. Paste its summary into `PROGRESS.md`. That script does not exist until WP0 is finished; until then run the interim checks in `BASE.md` section 3 and write "interim checks" beside the result. After every stage 2 build also run `koura/survey.py` and `koura/elevation.py` and compare with build 9 (`BASE.md` section 6).
7. Never write "works in game" unless the in-game probe ran in this session or the owner said they drove it. File checks are "static" only.
8. Commit at the end of the session with the work package number in the message.
9. End every session by updating `PROGRESS.md`: the ledger row, what was checked and how, anything left over, and the next package to do.
10. Do not ask the owner questions mid-session. Use the defaults in `PROGRESS.md` and list the question there.
11. The built map is for personal use and is never published. Do not upload outputs, imagery or renders made from imagery anywhere. The code and plan are public on GitHub (see the Git section).
12. For detail work you may use any tool and any online source (satellite and street imagery, videos, social media, shop listings). `DETAIL-STANDARD.md` lists them. Keep what you download out of git.
13. Road heights are reserved and absolute heights are never stored (`BASE.md` section 4). The machine and the game are shared with the owner (`BASE.md` section 5).

## Git

The project is a git repository on branch `main`. The owner publishes it on GitHub as a public repo. Rules:

1. **Commits show only the owner.** Never add `Co-Authored-By`, "Generated with", a session link, or any mention of Codex, Claude or another AI tool, in a commit message, a pull request or a file. Commit with exactly:
   `git -c user.name=AdamElHassanDev -c user.email=AdamElHassanDev@users.noreply.github.com commit -m "<message>"`
   Do not change the global git config.
2. **One commit per work package**, after `PROGRESS.md` is updated. Message: a plain sentence saying what changed, for example `WP8: road overrides for Btouratij`. Commit small fixes separately if they are unrelated.
3. **Push** with `git push origin main` once the remote exists (`git remote -v`). If there is no remote, do not create one and do not push: write "not pushed, no remote" in `PROGRESS.md` and carry on. Never force-push.
4. **The generator fork** lives in `openlaps/`, which is ignored by this repo and has its own git history on branch `koura`. After changing it: commit inside `openlaps/` with the same identity, then refresh the patch that this repo does track:
   `git -C openlaps diff d9e713c66c01417fb035c65b81d77093094742c6 HEAD > koura/openlaps_koura.patch`
   and commit that patch here. The patch is how the fork changes reach GitHub.
5. **Never commit** aerial imagery or anything rendered from it (not redistributable), built tracks (`*.kn5`, `out/`), caches, `recordings/`, `.venv/`, logs. `.gitignore` already covers these; if you add a new file of that kind, add it to `.gitignore` first. Run `git status --short` before every commit and read the list.
6. Do not rewrite history (`rebase`, `commit --amend` on pushed commits, `reset --hard`).

## State on 2026-11-24: a real base exists

`BASE.md` is the description of it. In short: the fork is in `openlaps/` on branch `koura`, the environment is in `.venv`, and `koura/build.py S1` / `koura/build.py S2` build the stages (always under `ulimit -v 22000000`). Do not re-clone and do not apply any patch. Only if `openlaps/` is missing (fresh checkout) run `koura/setup.sh`, which clones the pinned commit and applies `koura/openlaps_koura.patch`.

Treat what exists as a first version to bring up to each work package's gate.

History, do not execute: an earlier quick preview was made with `evidence/preview_patch.diff` and `evidence/build_preview.py`. Both are already folded into the fork and `koura/build.py`. Where a work package says "apply the preview patch" or "use `build_preview.py`", that step is done.

## Order

The order is the table in `BASE.md` section 8:

WP0 (finish), WP8, WP11, WP6, WP14, WP9, WP12, WP13, then WP2, WP3, WP4, WP5, WP7 (finish each), then WP10. WP1 only in a session where the owner says the game is free.

`PROGRESS.md` has a line `Next package:`. Do that one. When you finish it, change the line to the next in the order.

## The prompt to paste at the start of each session

```
You are continuing the Koura Assetto Corsa map project in this folder.
Read AGENTS.md and handoff/RUN.md and obey them exactly.
Then read handoff/BASE.md and handoff/PROGRESS.md and do the work package named on
the "Next package:" line of handoff/PROGRESS.md. Do only that one package.
Do not change road heights (handoff/BASE.md section 4).
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
| WP10 | remaining extras (speed bumps, night, traffic) | medium |
| WP11 | kart track | large |
| WP12 | item-by-item detail pass | very large; split over several sessions by checklist rows |
| WP13 | detail pass outside the green box | very large; split by route, 500 m sections |
| WP14 | ground, grass and trees inside the loop | large; depends on WP6 |

WP9, WP11, WP12, WP13 and WP14 need a model that can look at images. If the agent in use cannot open image files, say so in `PROGRESS.md` and do only the non-visual steps.
