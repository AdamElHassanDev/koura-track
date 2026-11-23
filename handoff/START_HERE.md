# Start here

Written 2026-11-23 after a research pass. Nothing has been built except one trial track.

## Goal

A free-roam Assetto Corsa map of the owner's home area in Koura, North Lebanon: Btouratij first, then Nakhle, Amioun, Kousba, Bishmizzine and the roads between them. The owner wants it as accurate and detailed as the data allows, and will supply dashcam video.

## What the research settled

1. **Three open-source generators already do most of this.** One of them, openlaps, builds a whole road network over an area and writes the track file in pure Python. It was run here on a 1 km square around Btouratij: 110 seconds, 76 MB track, 8.2 km of road, 40 junctions, 211 buildings. The output is in `poc/btouratij_poc/`. The owner loaded and drove it on 2026-11-23: it works, road detail was better than expected, and three problems were reported (cut-off street loops, a live-mode message that traps the car at the map edge, distances slightly off). Fixes are in work packages 2 and 12 and VERIFY checks 15 and 16.
2. **So the job is to fork and adapt openlaps, not to write a generator.** The other two projects supply the parts openlaps lacks: an in-game test probe, a track-file validator, and photo-to-facade code.
3. **The hard problems are scale and source data**, not the file format. openlaps is tuned for a few km². The named villages span about 70 km². Elevation is only available at 30 m.

4. **A drivable preview of the whole stage 2 network already exists** (`poc/koura_preview/`, built 2026-11-23 with quick patches). The owner wants it used as the starting base; `RUN.md` says how.

## Read in this order

| File | What it holds |
|---|---|
| `FINDINGS.md` | Measured facts: the area, the data sources, this machine, the trial build |
| `PLAN.md` | The three stages, design decisions, existing tools used, order of work, rules |
| `RUN.md` | How to run this with a coding agent: one work package per session, the exact prompt to paste, when to stop |
| `DETAIL-STANDARD.md` | The level of detail the owner expects, in their words, with the list of what "everything" means and which sources may be used |
| `WORK-PACKAGES.md` | Fourteen work packages with steps, gates, evidence and fallbacks |
| `VERIFY.md` | The checks every build must pass, with exact pass conditions |
| `inputs/recent_places.json` | New shops and changes the map sources are too old to show; the owner adds to it |
| `inputs/zone.json` | Editable stage extents, origin, spawn point and the loop route |
| `specs/` | Code quoted from the projects, with the exact changes to make |
| `AC-FORMAT.md` | Track-format rules and every documented crash cause |
| `DASHCAM.md` | Online videos of Btouratij already found, what the owner should record, and how each is used |
| `REFERENCES.md` | Repos with pinned commits, licences, docs |
| `audits/` | Full code-audit reports on the three reference projects |
| `PROGRESS.md` | Ledger. Update it after each work package |
| `evidence/` | Trial build log and images |

## Honest expectations

- **Stage 1, Btouratij and Nakhle (work packages 0 to 5):** about six sessions, one work package each. A Lebanon-styled, drivable map of about 3.6 by 4.1 km (10 km²), every small road included, with 0.5 m aerial ground texture.
- **Stage 2, the 25.6 km loop, its shortcut, the Tourza road, the Dabbousi Farms road and the Karting Mania kart track (work packages 6, 7 and 11):** depends on the performance work and on a part of openlaps its author has not tested in the game. Fallbacks are written into the plan.
- **Extreme detail in Btouratij and Nakhle (work package 12):** an item-by-item pass over every road and building in the green box. It is the longest package and its quality follows the footage available.
- **Detail outside the green box (work package 13):** the loop, the other roads and the village centres get a lighter version of the same pass: every road and building in the detailed ground checked against imagery and video, so that driving it looks like the real drive. The Karting Mania kart track is built as an exact copy and also as its own timed circuit.
- **Looking like the real place (work package 9):** depends on footage. Online driving and drone videos of Btouratij exist and are the first source. Without footage, buildings are right in footprint and wrong in appearance, and hills are right while camber and bumps are invented.
- **In-game checking by an agent** is unproven on this machine. Work package 1 finds out in 90 minutes; if it cannot be done, the owner drives each stage.

## Before the executing agent starts

The owner should, if possible:

1. Done 2026-11-23: the trial track was driven and loads.
2. Look at `evidence/loop_on_map.png` and say whether the Kousba road towards Tourza ends at the right turn-off, and whether the karting access road and the Dabbousi Farms road are the right ones. The loop, the shortcut, the stage 1 box and the two Nakhle loops are already confirmed by the owner.
3. Leave Steam running and logged in, and expect the game window to open by itself during work package 1.

None of these block the work. Defaults are in `PROGRESS.md`.

Git rules (owner-only commits, what never to commit, how the generator fork is published) are in the Git section of `RUN.md`.
