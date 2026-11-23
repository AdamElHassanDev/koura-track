# Footage: online videos, dashcam and phone recordings

## Videos that already exist (found 2026-11-23)

These are the first footage source, ahead of any new recording. Download for private reference only. Resolution and dates are from the video metadata; contents are from the titles and have **not** been watched yet.

Channel "Saed Alhassan سائد الحسن": https://www.youtube.com/channel/UChxVh0hYni3ZT2jFHrOs2dg

| Video | Length | Quality | Date | Title (translated) | Likely use |
|---|---|---|---|---|---|
| https://www.youtube.com/watch?v=8gIn9XWJ_4Y | 17:01 | 1080p30 | 2020-06 | A tour of the streets of my beloved village Btouratij | Street-level drive. Road widths, surfaces, walls, facades |
| https://www.youtube.com/watch?v=WVUXxnztroQ | 3:05 | check | check | Btouratije village in orbit of 400 meters from the mosque minaret | Drone orbit. Best candidate for 3D reconstruction |
| https://www.youtube.com/watch?v=fMbNxqZE8fc | 5:38 | 1080p30 | 2018-02 | Fly over Btouratij, the crowned mountain house | Drone. Building heights, roofs |
| https://www.youtube.com/watch?v=-O9THHEDtp0 | 5:15 | 1080p24 | 2016-05 | Fly over Btouratij (earlier version) | Drone. Older state of the village |
| https://www.youtube.com/watch?v=EXy2zH-Dft8 | 7:37 | 1080p30 | 2022-08 | My village that I miss and love, Btouratij | Drone or mixed |
| https://www.youtube.com/watch?v=9adWYleZwac | 4:27 | 1080p30 | 2023-03 | My village Btouratij that I love | Drone or mixed. Most recent |
| https://www.youtube.com/watch?v=EFjMn8Lvcls | 3:05 | check | check | Btouratij, a love story that never ends | Unknown |
| https://www.youtube.com/watch?v=Sdcchuxx3Qo | 4:13 | check | check | Btouratij, a love story | Unknown |

Channel "Biking Tripoli & Beyond" (bicycle point-of-view rides, 4K):

| Video | Length | Quality | Date | Title (translated) | Likely use |
|---|---|---|---|---|---|
| https://www.youtube.com/watch?v=_MhRX5NSwLU | 9:41 | 2160p30 | 2026-05 | Btouratij to Barsa: fast descents and calm village paths | Recent 4K road view north of Btouratij |
| https://www.youtube.com/watch?v=BkyebTBsanY | 34:42 | 2160p30 | 2026-07 | Exploring inside Dahr el Ain, away from the main road | Roads north of stage 1 |
| https://www.youtube.com/watch?v=79ZHXKlZ8Mk | 46:44 | 2160p30 | 2026-07 | From the Koura hills to the Qalamoun sea via Balamand | Wider Koura roads |

Also: https://www.youtube.com/watch?v=yEVqb3CR6_I ("Btouratij", 2:43, channel Ragheb Elhassan), contents unknown.

Search again before starting work package 9: the same search (`yt-dlp "ytsearch20:بتوراتيج"` and the village names in Arabic for Nakhle, Amioun, Kousba, Bishmizzine) will find footage for the stage 2 villages.

Limits of online video: no GPS, so each drive has to be located on the map from landmarks; older videos show the village as it was; drone videos edited with cuts, music-video pacing or zooms will not reconstruct in 3D, though they are still good for counting floors and reading roofs.

## New recordings by the owner: what each one changes

| Recording | What it fixes | How reliable |
|---|---|---|
| Phone GPS track with altitude, one per drive | Road elevation profile. Replaces the 30 m model along driven roads | Good for slopes and crests. Not good enough for camber or bumps |
| Forward dashcam video | Road width, lane count, surface, markings, speed bumps, walls, poles, signs, where buildings start | Good, but by review: a person or agent reads frames and fills an overrides file |
| Sideways phone video from the passenger window | Building facades as textures | Good for flat walls seen square-on. One wall at a time |
| Still photos of landmarks, walked around | Church, square, shop fronts, the owner's own street | Best quality. Needed for anything modelled by hand |

Forward dashcam video alone does **not** give a 3D model of the street. Automatic reconstruction from driving video is weak on asphalt (too little texture) and none of the reference projects handle video. Treat it as an experiment after the rest works.

## New shops and changes

The aerial imagery is from 2024-01. Anything that opened since (Knots and others) only reaches the map through footage or the owner's list in `inputs/recent_places.json`. When recording, drive past each new place slowly once in each direction, and take one square-on phone photo of the shopfront with location turned on.

## How to record

**Every drive**
- Start a GPS logger on the phone before moving and save a GPX file (1 point per second or faster, altitude on). A phone with a barometer gives a much steadier altitude; note the phone model.
- Say the date and road name aloud at the start so video and track can be paired.
- Drive at 30 to 40 km/h. Daylight, sun high or overcast. Clean windscreen.
- Drive each road in both directions.

**Forward camera**
- Fixed mount, centred, horizon level. 1080p at 60 frames per second, or 4K at 30.
- Note the camera's height above the road and the car's width. Those two numbers let widths be measured from frames.

**Sideways facade passes**
- Phone held at right angles to the street, landscape, widest lens, from the passenger side. One pass per side of the street.
- Slow enough that each building stays in frame for two seconds.

**Landmarks**
- 20 to 40 overlapping photos walking around the building, plus one square-on photo of each wall.

## Where to start

A GPS track of every drive is the one thing online video cannot supply; record that first, even without video. Then record what the online videos do not cover: the road to Nakhle, and the loop roads to Amioun, Kousba and Bishmizzine.

## Where files go

```
recordings/
  2026-MM-DD_<road-name>/
    track.gpx
    forward.mp4
    left.mp4  right.mp4
    notes.txt        camera height, car width, phone model, anything odd
  landmarks/<name>/*.jpg
```

## How each is used (work package 9)

1. **GPS to elevation.** Match each track to OSM roads, filter altitude along the road, replace the model's profile on those roads, blend at the ends.
2. **Frames to overrides.** Extract one frame every 10 m of travel using the GPS track for position. Review frames per road and fill `koura/overrides/roads.json` (width, lanes, surface, markings, bumps, roadside walls) and `koura/overrides/buildings.json` (floors, roof type, colour).
3. **Facades.** For a chosen wall, pick the four wall corners in a frame, straighten with a homography, and store the result as that wall's texture. road-to-assetto's `photo_projection.py` refuses fits with more than 3 px error; keep that strictness.
4. **Road texture.** Use frames to choose and tint tiling asphalt and concrete materials. Do not project video onto the road.
