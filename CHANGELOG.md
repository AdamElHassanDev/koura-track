# Changelog

Every build that was installed in the game, newest first. "Driven" means the owner drove it and gave feedback; a build is never called working from file checks alone.

Smoothness figures come from `koura/survey.py`: the share of road length where the slope changes by more than 2 % (or 5 %) within 8 m. A race-track-smooth road has none.

## Koura combined preview · 2026-11-24 · in-game probe

- The private Stage 2 track `koura_combined` brings together the repaired Kousba–Tourza link, the Btouratij memorial and village centre, detailed frontages and walls, the civic bend, KNOTS, the first photo-matched Nakhle mosque model and the current shop and roof work.
- The 811 m surveyed Karting Mania surface replaces the earlier uniform-width loop. The preview includes one surveyed kerb and two divider runs. Venue scenery, paddock access and a timed lap remain open.
- CSP 0.2.11 passed 11 daylight and three night stops. All four wheels registered as `KART` at the three karting stops. Lights were visible on the Btouratij street and at the KNOTS entrance. The wider release gate remains open.

## Koura Btouratij civic bend review · 2026-11-24 · in-game probe

- The separate `koura_btouratij_civic` review includes the corrected entrance and mosque frontages, the municipality's photographed pointed sign and doors, the red tower across the bend, and the blue direction signs at the fork.
- The mosque approach now has the stone enclosure with open fencing and paved verge. Its lattice lamp lights the stone wall and road at 21:00. In the wider Btouratij core, 145 properties have reviewed roof shapes or sampled roof colours.
- Five daylight stops and one night stop passed in CSP 0.2.11. All 139 existing road meshes match the centre review.

## Koura Kousba-Tourza link review · 2026-11-24 · in-game probe

- The separate `koura_kousba_link_s2` review restores 101.6 m of Rue Al Arz east of the Kousba roundabout. The centre and both lanes have continuous collision across the former cut. The two invisible boundary crossings are gone.
- Three CSP 0.2.11 stops passed on the restored stretch and its joins. Median frame rate was 394 FPS. The grade survey matches Build 9 and the loop still climbs 417 m.
- This road-test build uses the existing Stage 2 storefront scenery. The newer entrance and mosque are in the Btouratij village centre review.

## Koura Btouratij village centre review · 2026-11-24 · in-game probe

- The separate `koura_btouratij_centre` review includes the corrected entrance and the mosque's limestone hall, arched windows, doors, low dome and green-capped minaret. From the Btouratij start, follow the village road beyond the memorial to the mosque.
- Five properties on each approach now have surveyed frontage work. The pass includes photographed façades, a stone-and-steel porch, open balcony arches, garden gates and rails, retaining walls, olive and conifer crowns, 562 m² of paving and a glazed corner house with physical steps.
- The unmarked village streets now match the footage along both approaches. A lattice lamp uphill lights the road, walls and garden gate at 21:00.
- CSP 0.2.11 passed eight daylight and two night stops, at 362 and 334 median FPS. All 139 existing road meshes match the entrance review. The wider village gate is open.

## Koura Btouratij corrected entrance · 2026-11-24 · in-game probe

- The separate `koura_btouratij_entrance` review contains the surveyed roadside memorial pad and railings, the sculpted salute and limestone relief, corrected road markings and the real asphalt shoulder opposite.
- The stone garden wall stays. The memorial-side house has a second photographed face and modelled balconies, and the pale arched villa has its other visible wing.
- Three CSP 0.2.11 stops passed at 11:00. Median frame rate was 350 FPS. All 139 existing Stage 1 road meshes match the earlier frontage review.

## Koura Btouratij frontage review · 2026-11-24 · in-game probe

- Installed as the separate Stage 1 track `koura_btouratij_review`. From the Btouratij start, continue past the memorial toward the photographed shrine, palm gardens, arched villa and flat-roof carport.
- The first reviewed stretch includes six paved areas, photographed façade and wall materials, the pierced villa fence and gate, and 16 surveyed trees. The Oliva forecourt has its photographed paver finish.
- Five surveyed lattice poles carry six working lamp heads. Four CSP 0.2.11 probe stops passed at 11:00 and 21:00, with median frame rates of 349 and 334 FPS on the reference machine.
- All 139 Stage 1 road primitives match the previous build. The wider village detail and release checks are still open.

## Koura storefront and footage candidate · 2026-11-24 · in-game probe

- Installed as a separate private review track, `koura_wp9_s2`. Start in Btouratij to see the photographed bilingual direction sign, the workshop façades and gates, and the surveyed memorial island and railing.
- Nosh Café, Winner Force Kousba and Spinneys The Hub have sourced signs. Spinneys has a new traced footprint and glazing.
- All seven CSP 0.2.11 test stops passed. All 455 road meshes match the earlier Stage 2 export byte for byte.
- Build 9 remains the regular preview. The full release checks, timed kart layout and night lighting are open.

## Build 9 · 2026-11-24 · driven
- **Real heights restored.** Build 8 had flattened the hills. The road now follows the height model: on the main loop it climbs 417 m against 458 m in the raw model (which also counts roofs and trees), and differs from it by 0.7 m on average.
- Bridges are built as ordinary road, which removes the band of ground across the road at the Aaba bridge. Bridge side walls are gone for now.
- Smoothness slightly lower as the price: main highways 0.9 % of length over 2 % (was 0.4 %), none over 5 %.
- New tool: `koura/elevation.py` compares every route with the height model.
- Owner after driving: "definitely feels a lot better". Long straight climbs, for example Aaba to Kfar Hazir, still feel flat; the road there matches the height model, so this waits for the phone recording.

## Build 8 · 2026-11-23 · driven
- Bare ground patches inside junctions paved (78 across the map), including the two in the middle of the highway at the Aaba junction.
- Smoothness as build 7.

## Build 7 · 2026-11-23
- Hairpins and sharp forks: the two legs stay level only where they overlap and ease out gradually. Before, they left pits of 2 to 3 m.
- Worst slope jump on the map: 45 % down to 13.7 %.
- Main highways over 2 %: 0.4 % of length. Over 5 %: none.

## Build 6 · 2026-11-23
- Network smoothing run a second time after the fork merge step.

## Build 5 · 2026-11-23
- **Road grades smoothed over the whole network in one pass.** A road now keeps its own line through every side street instead of being pulled up or down at each junction.
- Aaba highway stretch: worst slope jump 15.8 % down to about 7 %.

## Build 4 · 2026-11-23 · driven
- Pavements and kerbs removed: the paved strips at junctions looked like parking strips and the kerbs damaged the car.
- Small holes inside roads paved.
- Owner: "Better, but still the bumps on the highway are very strong", worst at junctions; the Aaba highway junction "horrible".

## Build 3 · 2026-11-23 · driven
- **Karting Mania rebuilt** as one purpose-made surface traced from aerial imagery (832 m racing line, 8 m wide), replacing ordinary streets.
- Drivable surface ironed with local plane fits. Share of the main loop over 0.5 g of vertical kick at 100 km/h: 2.1 % down to 0.4 %.
- New tool `koura/ride.py`.
- Owner: road "a lot better", junctions and kerbs bad, the dip from the video still there.

## Build 2 · 2026-11-23 · driven
- Aerial imagery on the ground at 0.5 m.
- Lebanon profile: flat roofs with water tanks, stone-coloured walls, olives as the main tree.
- Trees placed from canopy height data.
- Owner: hills close but some too gentle; sharp bumps and sudden dips.

## Build 1 (preview) · 2026-11-23 · driven
- First build of the whole area: 27.5 km², 198 km of road, 6,110 buildings, 11 start points, a rough kart track.
- Edge of the map: invisible wall instead of the generator's live-mode message.

## Trial · 2026-11-23 · driven
- 1 km square of Btouratij to prove the approach.
- Owner: "Excellent start. More detail than I anticipated road-wise."
