# The level of detail the owner wants

Read this before work packages 9, 11, 12 and 13. It explains, in the owner's own terms, what "done" looks like. When a work package and this file disagree, this file wins on quality and the work package wins on method.

## What the owner said

- "It is critical to me that in the detailed zone, the green one, especially in Btouratij, the houses and roads and small details are extremely detailed."
- "Even things like statues, for example. Anything, to be very detailed."
- "The rest of the road to be lifelike. It doesn't need to be extremely accurate, but still needs to be very, very accurate."
- "Not just along the route. Try to get it similar, like detailed, very similar, like I'm driving on it."
- "Karting Mania should be copy paste exact as it is in real life. Everything like a real track."
- "New shops like Knots opened. Make sure things like this are added, since not all visuals are up to date."

The owner lives in Btouratij and knows every corner of it. They will notice a missing statue, a wall on the wrong side, a house with the wrong number of floors. Outside the village they know the roads as a daily driver: the shape of each bend, what stands at each junction, which shops and landmarks they pass.

## The three levels

**Level 1, extreme: Btouratij and Nakhle (the stage 1 box, strongest in the village cores).** A person from the village must recognise every street and every house. Nothing generic is acceptable where evidence exists.

**Level 2, lifelike: every other road and village in the detailed ground** (the loop, the Bishmizzine to Amioun shortcut, the Tourza road, the karting access road, the Dabbousi Farms road, Aaba, Bishmizzine, Kfar Hazir, Amioun, Kousba, Bsarma). Driving it must feel like the real drive: the right things in the right places at the right size and colour. A building may have a generic front if no photo exists, but it must be there, the right shape, height, roof and colour.

**Level 3, exact copy: Karting Mania.** A replica, built and checked item by item (work package 11).

## Level 1 in practice: what "everything" means

For every street in Btouratij and Nakhle, go along it in the footage and write down every object that a person could point at. Each one is either built at its real place or listed as "seen, could not place". The list below is the minimum; add whatever else the footage shows.

Buildings
- Every house: outline, number of floors, open ground floor on pillars or closed, roof (flat, red tile, mixed), roof items (water tanks, solar heaters and panels, satellite dishes, stair housing, pergolas), wall colour and material (stone, plaster, bare block), balconies and their railings, external stairs, garages and their doors, unfinished floors with bare columns and rebar.
- Real fronts from photos wherever a photo exists.
- Shops: shopfront, awning, sign with the real name, things kept outside (crates, fridges, chairs).
- Religious buildings: mosques with minaret, dome and crescent; churches with bell tower and cross; shrines.
- Public buildings: municipality, school, clinic, hall, with flags, signs and yards.
- Half-built and abandoned buildings as they are.

Monuments and small landmarks
- Statues, busts, memorials, plaques, martyrs' pictures and banners, religious statues and roadside shrines, fountains, wells, old olive presses, decorative arches at village entrances, village name signs, flagpoles, clock or bell structures.
- For each: find photos from two or more sides, estimate height from a person or car in the picture, and build it as its own small model. A plain block is not acceptable for a statue; build the recognisable shape, even if simple, and put the real photo on it where that helps.

Roads
- Every street, lane, alley wide enough for a car, and driveway. Real width at each point, including where it narrows between walls.
- Surface per stretch: fresh asphalt, old patched asphalt, concrete, dirt. Potholes and broken edges where footage shows them clearly.
- Edges: kerb, wall, open verge, drop, ditch, drainage channel.
- Speed bumps, manhole covers and grates where seen, painted lines only where they really exist.
- Slopes and cambers as well as the elevation data and footage allow.

Along the road
- Boundary walls and fences with the right material and height, gates, pillars, house numbers where readable.
- Electricity and telephone poles and the wires between them, transformers, street lamps at their real positions, generator sheds.
- Road signs, mirrors at blind corners, direction signs, advertising boards, political and religious banners that are long-standing.
- Bins and skips, water tanks at ground level, benches, bus shelters, planters.
- Parked cars only where a spot always has one in every video (optional).

Green
- Each tree seen from above at its place and size: olive groves in their rows, pines, cypresses, fig, citrus, palms in gardens.
- Garden hedges, vines on pergolas, terraces with stone walls on slopes, empty plots with scrub.

Open places
- Squares, parking areas, football pitches and courts with their markings and fences, playgrounds, cemeteries with their walls.

## Level 2 in practice

For every road in the detailed ground outside stage 1, in 500 m sections:
- road shape, width, surface, edges and junction layout right;
- every building present with the right outline, height, roof and colour;
- every landmark and every shop with a sign present and named: petrol stations with their brand and canopy, car dealers (Clutch N' Carb on the shortcut), restaurants, bakeries, supermarkets, pharmacies, banks, churches, mosques, schools, the hospital near Aaba, monuments and statues at junctions and roundabouts;
- walls, guard rails, lamps, big signs and billboards where they are;
- groves, tree lines and single large trees where they are;
- the view from the driver's seat compared with video of the same spot, the five biggest differences fixed, repeat.

Generic is allowed here only for: house fronts with no photo, small roadside clutter, poles between seen positions.

## Where the information comes from

Use anything. The map is for the owner's personal use and is never published, so sources that cannot be redistributed are allowed. Keep every downloaded item under `recordings/online/` or `koura/overrides/facades/`, never in git.

- Aerial and satellite: Esri World Imagery (zoom 18 and 19), Google Earth and Google Maps satellite and 3D views, Bing, Apple Maps. Compare dates and prefer the newest.
- Street level: Google Street View and user photo spheres if any exist for these roads, Mapillary, KartaView, photos attached to map listings.
- Video: the Saed Alhassan channel (street tour and drone videos of Btouratij), any other YouTube, Facebook, Instagram or TikTok video of driving, cycling, walking or drone flights in these villages; wedding and festival videos often show streets and squares.
- Photos: image search for each village name in English, French and Arabic; municipality and parish pages; real-estate listings (they show house fronts and interiors of plots); news articles.
- Shops and businesses: their own pages and map listings for the sign, the front and the opening date. Add new ones to `inputs/recent_places.json`.
- The owner: they will record roads on request. Keep a filming list in `PROGRESS.md`.

Use any tool that helps: a browser, downloaders, image search, photogrammetry on drone video, a 3D editor for individual landmark models. The only fixed rule is that the track itself is still built by the Python pipeline and its override files, so every addition is repeatable.

## How to record what you find

- One row per object in the checklists (`s1_roads.csv`, `s1_buildings.csv`, `s1_details.json`, and the `s2_` files), with the source (file name or link and frame time) and a status.
- Never leave something out silently. If it was seen and not built, it is listed with the reason.
- Never invent. If nothing shows a place, mark it `no_evidence`, build the plausible default, and put it on the owner's filming list.

## The test

Level 1: pick any 20 m of any street in Btouratij or Nakhle that appears in a video. Put the video frame next to a render from the same position. A villager should say "that is the spot" without being told where it is, and should not be able to name a missing object.

Level 2: pick any 500 m section. The render sheet next to the video frames must match in road shape, in what stands on each side, and in every landmark and signed shop.

Level 3: the Karting Mania checklist has no open rows and the outline matches the aerial image within 0.5 m.
