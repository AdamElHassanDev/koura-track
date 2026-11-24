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

### Whole-map detail and night lighting

The owner confirmed on 2026-11-24 that the high-detail pass applies to the whole drivable map. Btouratij and Nakhle remain first in the work order. Give houses, businesses, names and signs, walls, vegetation and junction landmarks the same source-based treatment as each stretch is completed. Apply this to new drivable ground when it opens. Unseen detail belongs on the filming list.

The owner also requires working night lighting. Check street lamps, junctions, landmarks, and lit business signs where the source shows lighting. Verify the night build in Assetto Corsa from the driver's seat and record frame rate with the lights active. WP10 owns the night pass.

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

## Added by the owner on 2026-11-23, after driving the base

These points are as binding as the rest of this document. The owner's words are quoted.

### 1. Roads: smooth surface, real elevation

"Keep the smooth road surface, but get the most accurate elevation change possible. That is crucial to me." and "I care most about the bits and bumps."

- The surface must be race-track smooth: no slope change over 2 % within 8 m anywhere (`koura/survey.py` measures it). Camber stays.
- The hills must be as high and as steep as the real ones.
- **This point is not the detail agent's work.** Road heights are reserved (`BASE.md` section 4): they are being fitted to a phone recording of the real roads. The detail agent's duty here is not to make them worse: run `koura/survey.py` and `koura/elevation.py` after every stage 2 build and compare with build 9 (`BASE.md` section 6).

### 2. Real houses, not generic models

"Try to get images of the homes to put them in, or structure around them, so the road actually feels like or reminds you of when you drive on it in real life, so you know the direction better rather than it being just regular models."

- The aim is recognition: the owner should know where they are from the buildings alone.
- For every building that faces a route (level 1: every building in the box), find a photograph: street-level imagery, the owner's dashcam video, social media, business listings, real estate listings. Use it for the right number of floors, roof shape and colour, wall colour and material, balconies, the ground-floor shop front and its sign, the boundary wall and gate.
- Where a usable front-on photograph exists, rectify it and use it as the facade texture. Where it does not, model the shape and colours from what can be seen and from the aerial image.
- Landmarks (churches, schools, municipality, petrol stations, well-known shops and restaurants, the statue at the Btouratij junction) get an individual model. They are the navigation points; do them first on every stretch.
- Photographs are sources for a private build only. Never commit them or textures cut from them to the public repository (add the folder to `.gitignore` first).

### 3. No dead ground

"The dead parts of the map in the center where there is no terrain should be filled with grass and olive trees."

- Today stage 2 ground is the stage 1 box, a strip 250 m either side of each named route and a 450 m disc on six village centres (`inputs/zone.json`); the middle of the loop is empty. Fill it: every place the driver can see from any road must have ground, with grass and olive groves where the aerial image shows them. This is work package 14. The ground is background quality, but it must exist before the detail passes are judged.
- From any point on a route, turn the camera through a full circle. If the edge of the world or sky shows where land should be, it is not done.

### 4. Accurate vegetation and walls

"Vegetation and walls must also be accurate. The scenery needs to feel very real."

- Trees stand where the aerial image shows them, in rows where the groves are in rows, at the right density. Olive, pine, cypress, oak, citrus and palm are told apart. The base places trees from a canopy height model (20,326 olives, 7,371 pines, 5,469 oaks, 6,057 shrubs in stage 2), which gives approximate positions and guessed species. Compare with the image grove by grove and correct from the image.
- Stone terrace walls, garden walls, retaining walls beside the road, fences and gates are traced from the aerial image and street-level photographs, at the right height and material. A road cut into a hillside has its retaining wall; a road above a field has its drop and its low wall.
- Check each stretch against a photograph or a video frame of the same place, side by side, and keep the pair in `evidence/` (outside the public repository if it contains imagery).

### 5. Small details: roundabouts, statues, detailed buildings, walls

Added 2026-11-24. The owner asked for the focus to be on "a lot of small details like roundabouts, for example, statues, detailed buildings, etc., etc., and walls."

Small details are what make a place recognisable at driving speed. They are not an extra pass at the end: every stretch of road is finished with its small details before the next stretch is started. A stretch with generic boxes and no walls is not done, however many kilometres are covered.

**Roundabouts and junctions**

- Every roundabout is built as a roundabout: the real diameter, a raised centre island with its real content (planting, stone edging, a statue, a monument, a fountain, a sign, a flagpole), the real number of arms, splitter islands on the arms where they exist, and the real kerb line.
- The base draws junctions as wide flat patches with nothing in them. Replace each one on a named route with its real outline from the aerial image: islands, painted areas, widened corners, bus bays, parking in front of shops.
- First on the list: the Btouratij junction with the statue. The owner named it. Then every roundabout and island junction on the loop, then the rest.
- This is plan-view work and is open to the detail agent. The heights of the road surface stay reserved (`BASE.md` section 4): an island or a statue sits on the road height that the build gives it.
- Kerbs: the owner had pavement kerbs removed because they damaged the car. Island and roundabout kerbs are allowed where they are real, at most 8 cm high with a sloped face, so that a car that clips one is not damaged. Never put a vertical kerb beside a driving line.

**Statues, monuments and one-off objects**

- Every statue, monument, shrine, cross, memorial, fountain, village entrance sign and arch that can be seen from a route is placed, at its real position and its real size.
- Each one is modelled individually from photographs. A recognisable simple shape with the right proportions and colour is acceptable; an empty place or a generic stand-in is not.
- Find them from the owner's video, street-level imagery, the online videos in `DASHCAM.md`, municipality and church social media pages, and map place photos. List each one in `koura/overrides/landmarks.json` with position, source and state (`todo`, `shape`, `textured`).
- Give each a collider if a car could hit it.

**Detailed buildings**

- A building facing a route is more than a box: the right number of floors and floor height, balconies where they exist, the roof (flat with tank and stair house, or tiled, with the real pitch), the ground floor as it is (shop front with its sign and shutters, garage, open pillars, entrance steps), external stairs, and the wall material and colour.
- Shops, restaurants, petrol stations, pharmacies, banks and bakeries carry their real name on a sign in the real colours. Signs are how the owner knows where they are.
- Churches, mosques, schools, the municipality and other public buildings get an individual model: bell tower, dome, minaret, arches, courtyard wall and gate.
- Unfinished buildings (bare concrete frames, columns with reinforcing bars on the roof) are common in the area and are modelled as unfinished.
- Order of work on every stretch: landmarks first, then buildings on the outside of bends and at junctions (they are in view longest), then the rest.

**Walls**

- Every wall that borders a route is built: garden walls, stone terrace walls in the groves, retaining walls in cuttings, concrete block walls, low walls with railings on top, gates and gate pillars, crash barriers, and the side walls of bridges (missing in the base).
- Each wall has its real height to the nearest 25 cm, its real material (dry stone, cut limestone, plastered, bare block, concrete) and its real line from the aerial image. Openings for driveways and gates are where they really are.
- Walls beside the road have colliders. A wall the car can drive through is a defect.
- Away from the routes, terrace walls in the groves are placed from the aerial image wherever they can be seen from a route.
- Walls are stored as lines with a height above ground and a material in `koura/overrides/walls.json`, never with an absolute height. Walls that touch the road edge are marked `recheck after heights`.

**Other small things, same rule**

Speed bumps, street lamps, electricity poles and their wires, transformers, water tanks, road signs and village name signs, shop awnings, billboards, bus shelters, bins, parked cars where cars are always parked, petrol pump canopies, olive presses, football pitches and their fences.

**How it is checked**

- Each route is divided into 250 m sections (50 m in the stage 1 cores). Each section has a row in the checklist with one column per group above: junctions, one-off objects, buildings, walls, other. A section is done when no column says `todo`.
- For every section keep one pair: a video frame or photograph, and the render from the same position. Keep the pairs out of git.
- Count and report in `PROGRESS.md` after each session: roundabouts and island junctions done of the total, one-off objects done of the total, buildings with a real facade of those facing routes, metres of wall built.

## Where the information comes from

Use anything. The built map is for the owner's personal use and is never published (only the code and plan are public), so sources that cannot be redistributed are allowed. Keep every downloaded item under `recordings/online/` or `koura/overrides/facades/`, never in git.

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
