Read-only code reading, 2026-11-23, at the commits pinned in REFERENCES.md. Code is quoted verbatim with file:line. Nothing was executed. Verify line numbers against the checkout before editing.

I've read the code for all ten sections (A to J) and nothing was run. Below, file paths are relative to `<clones>/openlaps/`. Line numbers come from `cat -n` or `grep -n` at commit `d9e713c`.

**Read these first, because each one changes a spec you would otherwise copy:**

1. **`lane_mult` does not narrow roads.** It only changes where markings go (F2).
2. **The AC export deletes every collider in the `col` group**, not just the boundary wall: lamp posts, sign posts, tree trunks and pylons too (E2).
3. **Vegetation never sees OSM landuse**, so "olives in orchards" needs new code (C).
4. **A national orthophoto at 0.25 m/px for this bbox is about 4 GB in one array.** The XYZ source needs a lazy design (B5).
5. **`pipeline.run` can pin the origin, but there is no CLI flag**, and road heights do not match at seams between separate runs (D5).
6. **OSM way ids and area ids are dropped** before roads and buildings are built (F3, H2).
7. **Corrections to the earlier audit:**
   - `geo.py` has only 80 lines, so its `geo.py:351/376-392` references are wrong. The real ones are `geo.py:17-21` (`BBox.around`) and `geo.py:42-80` (`LocalProjection`).
   - Your bbox (34.29–34.38 N, 35.78–35.87 E) is about 8.3 km × 10.0 km, roughly 83 km², not 144 km².

---

## A. New region profile

### A1. The `Region` dataclass (openlaps/regions.py:20-71)
```python
@dataclass
class Region:
    code: str
    name: str
    country: str                    # nombre para ui_track.json (Content Manager lo usa para la bandera)
    # señalamiento horizontal
    center_mat: str = "raya_blanca"  # raya separadora de sentidos
    left_edge_mat: str = "raya_blanca"  # orilla izquierda en vías de un sentido
    line_w: float = 0.10            # ancho de raya en carretera convencional (m)
    line_w_fast: float = 0.15       # en autopista / autovía
    dash_rural: tuple = (3.5, 9.0)  # (pintado, sin pintar) en m
    dash_urban: tuple = (2.0, 5.5)
    curb_yellow_corners: bool = False
    # señalamiento vertical
    stop_text: str = "STOP"
    curve_sign: str = "triangle"    # "triangle" (Europa) o "diamond" (América)
    # edificios
    roof: str = "pitched"           # "flat" (azotea) o "pitched" (tejado a cuatro aguas)
    roof_colors: list = field(default_factory=lambda: [(168, 84, 58), (150, 74, 52), (182, 102, 70), (120, 112, 104)])
    tinaco: bool = False
    facade_colors: list = field(default_factory=lambda: [
        (236, 230, 216), (228, 214, 188), (214, 196, 160), (200, 176, 140), (240, 238, 232),
        (210, 190, 170), (186, 160, 128), (226, 220, 206)])
    levels_default: tuple = (2, 3, 4)   # niveles típicos (al azar) si OSM no dice nada
    asphalt_tone: float = 92.0      # gris medio del asfalto (0-255): México oscuro, España más claro
    pass_sight: tuple = (3.0, 30.0)  # visibilidad mínima para raya discontinua: a·v + b (m, v en km/h)
    delineator: str = "plain"       # "plain" (fantasma blanco) o "hito" (blanco con franja negra, Europa)
    delineator_gap: tuple = (25.0, 10.0)   # separación en recta y en curva (m)
    # vegetación: especies permitidas (las demás se cambian por la más parecida)
    species: tuple = ("encino", "pino", "arbusto", "tropical", "palma")
    # fuentes de datos
    ortho: str = ""                 # "" | "pnoa" | "geopf"
    dem: str = ""                   # "" | "mdt05"
    cadastre: str = ""              # "" | "catastro" (huellas y plantas reales de cada edificio)
    heights: str = ""               # "" | "overture" (alturas de edificios de Overture Maps)
    ortho_mpp: float = 0.25         # resolución a la que se pide la ortofoto (m/px)
    # calle y ciudad
    lane_mult: float = 1.0          # multiplicador del ancho de carril por defecto
    rural_sin_asfalto: bool = False  # fuera de poblado, un camino menor sin `surface` en OSM es de tierra
    sidewalk_w: float = 1.8         # ancho de banqueta (m)
    center_double: bool = False     # raya central doble continua donde no se puede rebasar (EE. UU.)
    parking_default: bool = False   # en ciudad, estacionamiento en ambos lados si OSM no dice nada
    speed_unit: str = "kmh"         # "kmh" | "mph": unidades de las señales de velocidad
    facade_style: str = ""          # estilo de fachada de casas ("" = según el techo: mx / eu; "us" = tablilla)
    roof_kind: str = "tiles"        # "tiles" (teja) | "shingles" (tela asfáltica)
    flat_from_floors: int = 0       # desde cuántas plantas la azotea es plana (0 = según roof)
    tower_floors: int = 0           # desde cuántas plantas la fachada es de torre de oficinas (0 = nunca)
    attribution: list = field(default_factory=list)
    # subregión (ver SUBREGIONES): "" en el perfil del país
    sub: str = ""
    sub_name: str = ""
    sub_name_en: str = ""
```

### A2. Instances and `REGIONS` (regions.py:74-85, 129-134)
```python
MX = Region(
    code="mx", name="México", country="Mexico",
    center_mat="raya_amarilla", left_edge_mat="raya_amarilla",   # NOM-034-SCT2
    line_w=0.15, line_w_fast=0.15, dash_rural=(5.0, 10.0), dash_urban=(3.0, 5.0),
    curb_yellow_corners=True, stop_text="ALTO", curve_sign="diamond",
    roof="flat", tinaco=True,
    facade_colors=[(196, 86, 52), (226, 170, 60), (40, 92, 160), (214, 52, 120), (236, 232, 222),
                   (110, 160, 90), (232, 140, 110), (180, 170, 150)],
    levels_default=(1, 1, 2, 2, 3),
    species=("encino", "pino", "arbusto", "tropical", "palma", "organo", "maguey"),
    rural_sin_asfalto=True,
)
...
EU = Region(code="eu", name="Europa (genérico)", country="", roof="pitched",
            species=("encino", "pino", "arbusto", "tropical"))

GENERIC = Region(code="generic", name="Genérico", country="")

REGIONS = {r.code: r for r in (MX, ES, FR, US, EU, GENERIC)}
```
ES (`regions.py:87-99`) is the only top-level profile that already includes `"olivo"`. `_FR_SUR` (`:198-203`) also has it.

### A3. `detect_sub`, `elegir`, `detect`, `set_active`, `map_species` (regions.py:265-346)
```python
def detect_sub(region, lat, lon):
    """Subregión de ese punto dentro del país `region`, o el propio perfil del país si no cae en ninguna."""
    for s in SUBREGIONES.get(region.code, []):
        for la0, la1, lo0, lo1 in _CAJAS.get(s.sub, ()):
            if la0 <= lat <= la1 and lo0 <= lon <= lo1:
                return s
    return region


def elegir(region, sub, lat, lon):
    r = detect(lat, lon) if region in (None, "", "auto") else REGIONS[SUBS[region].code if region in SUBS else region]
    if region in SUBS:
        return SUBS[region]
    if sub in (None, "", "auto"):
        return detect_sub(r, lat, lon)
    if sub in SUBS and SUBS[sub].code == r.code:
        return SUBS[sub]
    return r                     # "no", o una subregión de otro país: el perfil del país

_active = MX


def detect(lat, lon):
    """Perfil por coordenadas (cajas aproximadas; en fronteras manda la opción --region)."""
    if 14.4 <= lat <= 32.8 and -118.5 <= lon <= -86.6 and lat < _frontera_us_mx(lon):
        return MX
    if (24.3 <= lat <= 49.5 and -125.0 <= lon <= -66.8 and lat < _frontera(_FRONTERA_CA, lon)) or (51.0 <= lat <= 71.5 and -170.0 <= lon <= -129.0)             or (18.8 <= lat <= 22.4 and -160.5 <= lon <= -154.7):
        return US
    if (35.9 <= lat <= 43.9 and -9.6 <= lon <= 3.4) or (38.6 <= lat <= 40.1 and 1.1 <= lon <= 4.4) \
            or (27.5 <= lat <= 29.5 and -18.3 <= lon <= -13.3):
        return ES
    if 41.3 <= lat <= 51.2 and -5.3 <= lon <= 9.7:
        return FR
    if 34.0 <= lat <= 71.5 and -25.0 <= lon <= 45.0:
        return EU
    return GENERIC
...
def set_active(region):
    global _active
    _active = region if isinstance(region, Region) else (REGIONS.get(region) or SUBS[region])
    return _active
...
def map_species(kind):
    """Cambia una especie que no existe en la región por la más parecida."""
    sp = _active.species
    if kind in sp:
        return kind
    sub = {"organo": "arbusto", "maguey": "arbusto", "palma": "tropical", "tropical": "encino"}
    k = sub.get(kind, "encino")
    return k if k in sp else sp[0]
```

### A4. Allowed values, found by where each field is consumed

| Field | Consumer (file:line) | Allowed values |
|---|---|---|
| `roof` | buildings.py:352 (`R.roof == "pitched"`), textures.py:740 and buildings.py:375 (`"mx" if R.roof == "flat" else "eu"`) | `"pitched"`; anything else behaves as flat. Only `"flat"` is used. |
| `roof_kind` | textures.py:749 `shingles(...) if R.roof_kind == "shingles" else roof_tiles(...)` | `"shingles"`; anything else gives tiles (`"tiles"`) |
| `facade_style` | textures.py:740 `style = R.facade_style or ("mx" if R.roof == "flat" else "eu")`; :765 `facade_us(...) if style == "us" else facade(..., style=style)`; textures.py:249 `elif style == "eu"`; buildings.py:363 `== "us"`; textures.py:758 | `""` (derived from `roof`), `"mx"` (barred windows, the `facade()` default at textures.py:222), `"eu"` (shutters and frame), `"us"` (siding). An explicit `"eu"` with a flat roof is valid. |
| `curve_sign` | textures.py:548 `if active().curve_sign == "triangle"` | `"triangle"`; anything else gives a diamond |
| `delineator` | textures.py:707 → `delineator_tex(style)` at textures.py:130 `if style == "hito"` | `"hito"`, `"plain"` |
| `center_mat`, `left_edge_mat` | roads.py:2484, 2490 (material names) | Must be registered materials: `"raya_blanca"`, `"raya_amarilla"` (textures.py:701-702) |
| `speed_unit` | textures.py:526 `== "mph"` | `"kmh"`, `"mph"` |
| `stop_text` | textures.py:516 `d.text(..., active().stop_text, ..., font=_font(...))` | Any string. `_font` (textures.py:498-503) is `ImageFont.load_default(size=...)`, Pillow's default font, so Arabic glyphs and shaping will not render. Use Latin text ("STOP"). |
| `ortho` | pipeline.py:166, 170, 540-542 → `rasters.ortho(bbox, source)` → `ORTHO_WMS`/`ORTHO_ARCGIS` keys (rasters.py:391-402) | `""`, `"pnoa"`, `"geopf"`, `"naip"` |
| `dem` | pipeline.py:49, 54, 533-538 | `""`, `"mdt05"`, `"3dep"` (anything else falls to Copernicus) |
| `cadastre` | pipeline.py:179, vivo.py:764 | `""`, `"catastro"` |
| `heights` | pipeline.py:181, 551 | `""`, `"overture"` |
| `species` | vegetation.py `SPECIES` (`:19-22`) and textures.py:775 material loop | `"encino"`, `"tropical"`, `"pino"`, `"palma"`, `"organo"`, `"maguey"`, `"arbusto"`, `"olivo"`. `species[0]` is the final fallback in `map_species`. |
| `code` is compared directly | vegetation.py:27, 29 (`== "mx"` picks the Mexican rules, else EU), textures.py:729, 784, extras.py:54, roadside.py:45 | Any other code gets the EU branch everywhere |

Other notes:
- `lane_mult` (roads.py:828) only scales `e.lane_w`. See F2.
- `levels_default` is used at buildings.py:318-320.
- `tinaco` (rooftop black water tanks) is used at buildings.py:408.

### A5. Mixing flat and red-tile hipped roofs

The per-building logic is in `buildings.py:349-377`:
```python
        nave = not church and ((kind in NAVE_KINDS and h < 12.0) or (kind == "yes" and poly.area > 900 and h < 10.0))
        if nave:
            mat = f"nave_{int(r * len(textures.NAVE_COLORS)) % len(textures.NAVE_COLORS)}"
        pitched = R.roof == "pitched" and not church and not nave and kind not in ("retail", "supermarket",
                                                                                   "commercial") and poly.area < 1500
        floors = b.get("floors") or max(1, int(round((h - 0.6) / C.LEVEL_HEIGHT)))
        torre = bool(R.tower_floors) and floors >= R.tower_floors and not church
        if torre:
            mat = f"torre_{int(r * 4) % 4}"
            pitched = nave = False
        elif R.flat_from_floors and floors >= R.flat_from_floors and not church:
            pitched = False
            if R.facade_style == "us" and not nave:
                mat = f"ciudad_{int(r * 4) % 4}"
        tg = b["tags"]
        shape = tg.get("roof:shape")
        if shape == "flat":
            pitched = False
        elif shape in ("gabled", "hipped", "pyramidal", "half-hipped", "mansard", "gambrel") and not church:
            pitched = True
        fc = textures.parse_colour(tg.get("building:colour"))
        if fc and not church and not nave and not torre:
            mat = textures.facade_material(scene, fc, R.facade_style or ("mx" if R.roof == "flat" else "eu"))
        rc = textures.parse_colour(tg.get("roof:colour"))
        roof_mat = textures.roof_material(scene, rc, pitched) if rc else None
```
The roof is then built at :397-406:
```python
        tall = b.get("floors", 0) >= 3 or h >= 3 * C.LEVEL_HEIGHT + 0.3
        if pitched and _hip_roof(scene, poly, top + C.PARAPET,
                                 roof_mat or f"tejado_{int(_h((i, 'r')) * len(R.roof_colors)) % len(R.roof_colors)}",
                                 pitch=0.36 if tall else 0.58, max_inset=4.0 if tall else 7.0):
            continue
        # azotea
        verts, faces = triangulate_polygon(poly, 50.0)
        if len(faces):
            roofk = "rojo" if r > 0.62 else ("blanco" if r > 0.5 else "concreto")
```

Ways to get the mix today, without code changes:
- `roof="pitched"` with `flat_from_floors=3`: houses of 1–2 floors get red-tile hipped roofs, 3 or more get flat roofs. `levels_default` decides the share.
- OSM `roof:shape` always wins in both directions (lines 368-372).
- The `tejado_k` materials are always registered from `R.roof_colors` (textures.py:748), regardless of `roof`, so both kinds are always available.

For a random share (for example 30 % tiled), add a field such as `pitched_share: float = 0.0`. Right after line 353, add:
```python
if R.pitched_share and not church and not nave and poly.area < 1500 and floors < (R.flat_from_floors or 99):
    pitched = _h((i, "roofmix")) < R.pitched_share
```
Place it before the `roof:shape` override so OSM still wins. Note that `floors` is computed at :356, so the insertion has to go after :356, not :353.

Other caveats:
- The flat-roof colour (`rojo`/`blanco`/`concreto`) is hard-coded at :404. Expose it per profile if you need to.
- The parapet inner wall is skipped for pitched roofs (`:386-387`).

### A6. Registering `lb`

1. Create `LB = Region(code="lb", ...)`. Suggested values:
   - `country="Lebanon"`
   - `roof="flat"`, or `roof="pitched"` with `flat_from_floors=3`
   - `tinaco=True`
   - `facade_style="eu"` or `"mx"`
   - `species=("olivo", "pino", "encino", "arbusto", "cipres")`
   - `levels_default=(2, 2, 3, 3, 4)`
   - `stop_text="STOP"`, `curve_sign="triangle"`, `delineator="plain"`
2. Add it to `REGIONS` at `regions.py:134`.
3. In `detect()`, add a box before line 300, for example `if 33.0 <= lat <= 34.7 and 35.0 <= lon <= 36.7: return LB`.
4. **CLI:** `__main__.py:112` has no `choices=`, so any string reaches `regions.elegir`. An unknown code fails with `KeyError` at `regions.py:277` (`REGIONS[...]`) and `vivo.py:763` (`regions.REGIONS[gen_args.region]`). Update the help text: `"perfil regional: auto, mx, es, fr, us, eu, lb, generic"`.
5. **GUI:** add `<option value="lb" data-i18n="region.lb">` at `gui/web/index.html:121-123`, plus the i18n string in `gui/web/i18n.js`.
6. **Tests:** `tests/test_geo_regions.py:33-40` has no Lebanon point, so nothing breaks. Add `(34.33, 35.82, "lb")`. If you add subregions, `test_subregion_elegida_y_coste` (`:76-95`) requires exactly 8 `facade_colors` and an entry in `_CAJAS` for each one.

---

## B. Custom orthophoto source

### B1. `rasters.ortho` (openlaps/sources/rasters.py:391-453)
```python
ORTHO_WMS = {
    "pnoa": ("https://www.ign.es/wms-inspire/pnoa-ma", "OI.OrthoimageCoverage", 4096),
    "geopf": ("https://data.geopf.fr/wms-r", "HR.ORTHOIMAGERY.ORTHOPHOTOS", 4096),
}
ORTHO_ARCGIS = {
    "naip": ("https://imagery.nationalmap.gov/arcgis/rest/services/USGSNAIPPlus/ImageServer/exportImage", 4000),
}

def ortho(bbox, source, mpp=0.25, log=print):
    """Ortofoto RGB del área pedida a `mpp` metros por pixel (aprox.), por teselas WMS en EPSG:3857.
    Devuelve un Raster (3 bandas uint8) o None si el servicio no responde.
    """
    from PIL import Image
    import rasterio.transform
    from .cache import fetch
    arcgis = source in ORTHO_ARCGIS
    url, layer, maxpx = ORTHO_WMS[source] if not arcgis else (ORTHO_ARCGIS[source][0], None, ORTHO_ARCGIS[source][1])
    tr = Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True)
    x0, y0 = tr.transform(bbox.west, bbox.south)
    x1, y1 = tr.transform(bbox.east, bbox.north)
    k = 1.0 / math.cos(math.radians((bbox.south + bbox.north) / 2))   # escala de Mercator
    res = mpp * k
    W = int(math.ceil((x1 - x0) / res))
    H = int(math.ceil((y1 - y0) / res))
    step = min(2048, maxpx)
    out = np.zeros((3, H, W), np.uint8)

    def tesela(r0, c0):
        w, h = min(step, W - c0), min(step, H - r0)
        bx0, bx1 = x0 + c0 * res, x0 + (c0 + w) * res
        by1, by0 = y1 - r0 * res, y1 - (r0 + h) * res
        if arcgis:
            q = (f"{url}?bbox={bx0:.2f},{by0:.2f},{bx1:.2f},{by1:.2f}&bboxSR=3857&imageSR=3857&size={w},{h}"
                 f"&format=jpg&bandIds=0,1,2&compressionQuality=90&f=image")
        else:
            q = (f"{url}?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap&LAYERS={layer}&STYLES=&CRS=EPSG:3857"
                 f"&BBOX={bx0:.2f},{by0:.2f},{bx1:.2f},{by1:.2f}&WIDTH={w}&HEIGHT={h}&FORMAT=image/jpeg")
        try:
            path = fetch(q, ext=".jpg", log=log)
            img = Image.open(path).convert("RGB")
            if img.size != (w, h):
                raise ValueError(f"tamaño {img.size}")
            out[:, r0:r0 + h, c0:c0 + w] = np.asarray(img).transpose(2, 0, 1)
            return True
        except Exception as e:  # noqa: BLE001
            log(f"  aviso: tesela de ortofoto fallida ({e.__class__.__name__}: {e})")
            return False

    celdas = [(r0, c0) for r0 in range(0, H, step) for c0 in range(0, W, step)]
    with ThreadPoolExecutor(max_workers=4) as ex:
        n_ok = sum(ex.map(lambda rc: tesela(*rc), celdas))
    if n_ok == 0:
        return None
    log(f"  ortofoto {source}: {W}x{H} px (~{mpp:.2f} m/px)")
    return Raster(out, rasterio.transform.from_origin(x0, y1, res, res), "EPSG:3857")
```

**Signature:** `ortho(bbox: BBox, source: str, mpp: float = 0.25, log=print) -> Raster | None`

**What it returns:**
- A `Raster` whose `data` is `np.uint8` with shape `(3, H, W)`, bands first.
- `transform = Affine from_origin(west_merc, north_merc, res, res)`, in EPSG:3857 metres, north-up.
- `res = mpp / cos(lat_centre)`, so `mpp` means ground metres.
- `crs = "EPSG:3857"` as a string.

**Caching:**
- `ortho` is **not** wrapped in `@_cacheado`.
- Only each HTTP request is cached, through `cache.fetch` (sources/cache.py:25-48): SHA1 of the URL, stored under `~/.cache/openlaps` or `OPENLAPS_CACHE`.

**The `Raster` class** (rasters.py:61-86):
```python
class Raster:
    def __init__(self, data, transform, crs, nodata=None):
        self.data = data.astype(np.float32) if data.dtype != np.uint8 else data
        ...
    def sample(self, proj, x, y, order=1, mode="nearest"):
        ...
        lon, lat = _transformar(_transformer(proj.epsg, str(self.crs)), x.ravel() + proj.ox, y.ravel() + proj.oy)
        inv = ~self.transform
        col, row = inv * (lon, lat)
        coords = np.vstack([np.asarray(row) - 0.5, np.asarray(col) - 0.5])
        if self.data.ndim == 3:
            return np.stack([map_coordinates(b, coords, order=order, mode=mode, output=np.float32).reshape(x.shape)
                             for b in self.data], -1)
```
`sample()` returns float32 with shape `x.shape + (3,)`. Pixel centres are handled by the `-0.5` offset.

**Only `.sample()` is ever called on the orthophoto object:**
- terrain.py:618
- roads.py:2348 (`_island_meshes`)
- cobertura.py:330 (`panel`)

So a lazy object with the same `sample(proj, x, y, order=1, mode="nearest")` signature is a drop-in replacement.

### B2. How pipeline.py consumes it
```python
166    usar_orto = bool(R.ortho) and not args.sin_orto
170    f_orto = pool.submit(intento, "ortofoto", rasters.ortho, bbox.padded(60), R.ortho, mpp=R.ortho_mpp, log=log)         if usar_orto else None
171    f_s2 = pool.submit(intento, "Sentinel-2", rasters.sentinel2, bbox.padded(60), args.temporada, log=log)         if not args.sin_satelite and not usar_orto else None
...
198    orto = f_orto.result() if f_orto else None
199    s2 = f_s2.result() if f_s2 else None
200    if s2 is None and usar_orto and orto is None and not args.sin_satelite:
201        s2 = intento("Sentinel-2", rasters.sentinel2, bbox.padded(60), args.temporada, log=log)
202    mpp = args.mpp or (min(0.25, R.ortho_mpp) if orto is not None else 0.5)
```
- The variable is `orto`. It is passed to `roads.build_roads(..., ortho=orto, ...)` (:280-282), to `T.GroundPainter(..., s2=s2, ortho=orto)` (:340-341) and to `cob.panel(orto if orto is not None else s2, ...)` (:429).
- `intento` (:148-153) swallows exceptions. An unknown `source` raises `KeyError` inside `ortho()`, `intento` returns `None`, and the run silently falls back to Sentinel-2 (:200-201).
- If the corridor rule fires (tramo or circuito only, above 24 km²), `args.sin_orto` is forced on (:136-138).
- **`precargar` (pipeline.py:540-542) must mirror the call** for live mode: `tareas.append((rasters.ortho, (bbox.padded(60), R.ortho), {"mpp": R.ortho_mpp}))`.

### B3. How terrain bakes it (terrain.py:586-628, 407-454)
- `paint_tile(x0, y0, x1, y1, mpp, terrain)` builds a pixel grid of `W = round((x1-x0)/mpp)` by `H`, at pixel centres in local UTM metres.
- It paints the WorldCover colours, noise, and dirt patches.
- Then:
```python
        if self.ortho is not None:
            # ortofoto de 20-25 cm: es la base; el ruido solo aporta grano
            ph = self.ortho.sample(self.proj, PX, PY, order=1)
            ok = ph.sum(-1) > 15
            ph = ph * (0.94 + 0.12 * n2)[..., None]
            col = np.where(ok[..., None], ph * 0.94 + col * 0.06, col)
        elif self.s2 is not None:
            sat = self.s2.sample(self.proj, PX, PY, order=3)
            ok = sat.sum(-1) > 15
            sat = np.clip(sat * 1.05, 0, 255) * (0.88 + 0.24 * n2)[..., None]
            wsat = np.where(cls == C.WC_BUILT, 0.3, 0.78)[..., None]
            col = np.where(ok[..., None], sat * wsat + col * (1 - wsat), col)
```
After this come:
- rock blending on slopes above 32°;
- the RGBA mask for the multilayer shader;
- OSM areas, water, paths, road shoulders and building shadows drawn on top;
- `img.filter(ImageFilter.SMOOTH)`.

The orthophoto contract: any pixel with RGB sum of 15 or less counts as **missing** and falls back to the procedural colour. Return black (0, 0, 0) for missing tiles. Colour processing is ×0.94 brightness with ±6 % noise grain, blended 94 % photo and 6 % procedural.

### B4. The Sentinel-2 season window (rasters.py:244-246)
```python
    y = date.today().year
    ranges = ([(f"{y - 1}-11-01", f"{y}-04-30"), (f"{y - 2}-11-01", f"{y - 1}-04-30")] if season == "seca"
              else [(f"{y - 1}-07-01", f"{y - 1}-10-31"), (f"{y - 2}-07-01", f"{y - 2}-10-31")])
```
The season string has more consumers than the STAC window:
- the window itself (rasters.py:245);
- the STAC cache key (rasters.py:233-234): `["s2-stac", ..., season, ym]`;
- the raster cache key in `_cacheado` (rasters.py:114), which hashes `list(args)`, i.e. the season string;
- `GroundPainter.season = 0 if season == "seca" else 1` (terrain.py:574), which indexes `C.GROUND_COLORS` (config.py:123-135);
- `cobertura.py:184, 212`: intermittent streams are drawn dry when `season == "seca"`;
- `textures.register_all(scene, season, ...)` (textures.py:625) accepts it but never uses it.

To make it profile-dependent:
1. Add `s2_months: dict = field(default_factory=lambda: {"seca": ((11, 1), (4, 30)), "lluvias": ((7, 1), (10, 31))})` to `Region`. For `lb`, set dry to `((6, 1), (10, 15))` and wet to `((12, 1), (3, 31))`.
2. In `_s2_items`, import `regions.active()` and build `ranges` from it, handling a year wrap when the start month is after the end month.
3. Put `regions.active().code` (or the month tuple) into the STAC key at :233-234. Otherwise a cached `"seca"` query from the old window is reused for the current month.
4. For the `_cacheado` key, either pass the window as an extra argument or bump `version=` on `sentinel2` and `sentinel2_ndwi` (rasters.py:277, 316).

### B5. Adding an XYZ web-mercator source

**Size check:**
- `mpp = min(0.25, R.ortho_mpp)` (pipeline.py:202), so the baked texture is 0.25 m/px even if you fetch at 0.5.
- The orthophoto box is your bbox padded by 60 m, about 8.4 km × 10.1 km. As a single `(3, H, W)` uint8 array that is about **33,600 × 40,600 px, roughly 4.1 GB** at 0.25 m, or about 1 GB at 0.5 m.
- XYZ tile size: z18 is 0.597 m in Mercator, which is **0.493 m on the ground** at 34.3°N. z19 is about 0.25 m.

**Recommended function:**
```python
# rasters.py
ORTHO_XYZ = {"lb_xyz": ("https://<host>/{z}/{y}/{x}.jpg", 18)}   # url template, zoom

def ortho_xyz(bbox, source, mpp=0.5, log=print) -> "Raster | XYZRaster | None"
```
It must return an object with `.sample(proj, x, y, order=1, mode="nearest") -> float32 array of shape x.shape+(3,)`, where:
- `x` and `y` are in the **local projection** (metres from `proj.ox`, `proj.oy` in `EPSG:proj.epsg`);
- missing pixels are 0.

**Option 1, eager.** This only fits in memory at z18 or below, about 1 GB:
- Tile indices: `tx = floor((lon+180)/360·2^z)`, `ty = floor((1 − asinh(tan φ)/π)/2·2^z)`.
- Tile size in EPSG:3857 metres: `R = 2π·6378137/(256·2^z)`.
- Mosaic origin: `X0 = −20037508.3428 + tx_min·256·R`, `Y1 = 20037508.3428 − ty_min·256·R`.
- Return `Raster(mosaic_uint8_(3,H,W), rasterio.transform.from_origin(X0, Y1, R, R), "EPSG:3857")`.
- Fetch each tile with `cache.fetch(url, ext=".jpg")`, which handles caching and retries, and use a `ThreadPoolExecutor` as at :448.

**Option 2, lazy (needed at z19 for the full box).** Write `class XYZRaster` with the same `sample()` signature:
- Convert local x/y to EPSG:3857 with `_transformar(_transformer(proj.epsg, "EPSG:3857"), x+proj.ox, y+proj.oy)`.
- Compute the needed tile set from the min and max of those coordinates; `paint_tile` asks for 128 m at a time.
- Decode only those tiles, keeping an LRU dict of decoded tiles.
- Build a small local mosaic and call `map_coordinates`.

Note that `cobertura.panel` samples the whole rect at once (`self.PX`). Its resolution is about rect/1200 (cobertura.py:153), so it only needs low zoom; sample with a coarser fallback when the request covers more than N tiles.

**Where to register it:**
1. Extend `ortho()` at line 413 with an `if source in ORTHO_XYZ: return ortho_xyz(bbox, source, mpp, log)` branch. That way pipeline.py:170 and :542 need no change.
2. Set `LB.ortho = "lb_xyz"` and `LB.ortho_mpp = 0.5` (or 0.25).
3. Pass `--mpp 0.5` on the CLI, or change pipeline.py:202, to halve texture size: `min(0.25, R.ortho_mpp)` otherwise forces 0.25.
4. Add attribution to `LB.attribution`.

---

## C. Vegetation

### C1. Species selection (vegetation.py:19-50)
```python
SPECIES = {  # altura media (m), ancho relativo
    "encino": (9.0, 0.95), "tropical": (11.0, 1.0), "pino": (17.0, 0.55), "palma": (10.0, 0.75),
    "organo": (4.5, 0.6), "maguey": (1.6, 1.3), "arbusto": (2.2, 1.2), "olivo": (4.2, 1.35),
}

def _choose(cls, elev, lat, r):
    from .regions import map_species, active
    k = _choose_mx(cls, elev, lat, r) if active().code == "mx" else _choose_eu(cls, elev, lat, r)
    # fuera de México las palmas solo en el sur (Andalucía, Levante, Canarias)
    if k == "palma" and active().code != "mx" and lat > 38.6:
        k = "encino"
    return map_species(k)

def _choose_eu(cls, elev, lat, r):
    if cls in (C.WC_TREE, C.WC_MANGROVE):
        if elev > 1400:
            return "pino" if r < 0.8 else "encino"
        return "pino" if r < 0.4 else ("encino" if r < 0.85 else "tropical")
    if cls == C.WC_SHRUB:
        return "arbusto" if r < 0.8 else "encino"
    if cls in (C.WC_GRASS, C.WC_CROP):
        # árboles sueltos en campos: olivos en el centro y sur, encinas más al norte
        if lat < 41.8:
            return "olivo" if r < 0.75 else "encino"
        return "encino" if r < 0.7 else "arbusto"
    if cls == C.WC_BUILT:
        return "tropical" if r < 0.55 else ("encino" if r < 0.85 else ("palma" if lat < 38.6 else "pino"))
    return "arbusto"
```

With the canopy layer, the common path is `_build_from_canopy` (vegetation.py:178-188):
```python
    for x, y, z, h, c in zip(X, Y, Z, Hc, cls):
        r = rng.random()
        if h <= 3.0:
            open_land = c in (C.WC_SHRUB, C.WC_GRASS, C.WC_BARE, C.WC_CROP)
            from .regions import map_species
            kind = map_species("maguey" if open_land and (proj.lat0 > 22 or z > 1700) and r < 0.4 else "arbusto")
        else:
            kind = _choose(C.WC_TREE if c in (C.WC_BUILT, C.WC_GRASS, C.WC_CROP, C.WC_SHRUB) and h > 6 else int(c), float(z), proj.lat0, r)
            if kind in ("maguey", "arbusto") and h > 5:
                kind = "encino" if z > 1000 else "tropical"
```
What this means for olives:
- `olivo` is only reached for canopy-height trees between 3 and 6 m on WorldCover GRASS or CROP, at 75 % odds.
- Trees of 3 m or less become shrubs.
- Trees above 6 m are reclassed as forest, giving pine, oak or "tropical".
- At lat 34.3 above 30 N, `"maguey"` becomes `arbusto` through `map_species` unless the profile lists `maguey`.

**`V.build` gets no OSM landuse.** Its signature is `build(scene, terrain, landcover, proj, exclude, osm_trees, density, road_pts, chm, log)`, called at pipeline.py:394-395. `orchard` and `farmland` appear only in pipeline.py:37-38 (`AREA_COLORS`, ground tint) and cobertura.py:95, where they map to class CULTIVO. Neither reaches vegetation.

### C2. Foliage definitions
- `foliage.py:22-28`, `LEAF`: `"encino"`, `"tropical"`, `"pino"`, `"arbusto"`, `"olivo"` → (RGB, variation). Olive is `(98, 108, 76), 0.15`.
- `foliage.py:221-227`, `LEAF_ASSETS`: `"encino"` LeafSet026, `"tropical"` LeafSet010, `"arbusto"` LeafSet026, `"olivo"` `("LeafSet026", (104, 112, 82), 0.018)`, `"pino"` PineNeedles001.
- Sprite generators: `broadleaf(kind)` at foliage.py:130 (crown params special-cased for `encino` and `olivo` at :141-143), `pine()` at :171 (conical tiers, `half = n*(0.04+0.36*f**0.9)`), and `photo_sprite(kind)` at :334, which uses `LEAF_ASSETS[kind]` (a `KeyError` for unknown species) and the `pine()` branch at :342.
- `textures.py:404-419`, `tree_sprite`: the photo path applies only to `kind in ("encino", "tropical", "arbusto", "pino", "olivo")` (:407). Other kinds use procedural branches.
- `textures.py:775`: materials are registered for `("encino", "tropical", "pino", "palma", "organo", "maguey", "arbusto", "olivo")` × `VEG_VARIANTS=3` (`:401`) as `veg_<kind>_<v>`.
- `vegetation.py:218`, `_emit`: `big = kind in ("encino", "tropical", "pino", "palma")` gives 3 planes instead of 2.
- `ext_config` (export_ac.py:316) picks up every `veg_*` material for the `ksTree` replacement automatically.

### C3. Changes needed
1. **The `lb` profile species** should include `"olivo"`, `"pino"`, `"encino"`, `"arbusto"`, plus a new `"cipres"`.
2. **Orchard placement:**
   - In pipeline.py, before :394, build `huertos = unary_union([pg for a in osm["areas"] if a["tags"].get("landuse") == "orchard" or a["tags"].get("trees") in ("olive_trees",) ...])`, plus `farmland` if you want it, using the same `proj.to_local` and `Polygon` pattern as :216-226.
   - Pass it as a new keyword `orchards=None` to `V.build`, which forwards it to `_build_from_canopy`.
   - In `_build_from_canopy`, before the species loop: `in_orch = shapely.contains_xy(orchards, X, Y)`. Inside the loop, `if in_orch[k] and h > 1.5: kind = "olivo"`, then skip the rest.
   - Also add a grid-planting pass inside orchards when the canopy model misses young trees: rows at about 7 × 7 m with height 3.5–5 m, added to `groups["olivo"]`.
   - Apply the same in `build()` (the no-canopy path).
3. **Mediterranean species elsewhere:** add a `_choose_lb(cls, elev, lat, r)` and dispatch on `active().code == "lb"` at vegetation.py:27. For example:
   - forest: pine 50 %, oak 30 %, cypress 20 %; above 1200 m, pine and cypress;
   - shrub: arbusto;
   - grass or crop: olive 60 %, otherwise oak or arbusto;
   - built: cypress, olive and pine (no "tropical").
   - Also change the `h > 6` override at :186, which otherwise turns tall olives into forest species.
4. **A new `"cipres"` touches:**
   - `vegetation.SPECIES`, e.g. `(12.0, 0.25)`;
   - `foliage.LEAF`;
   - `foliage.LEAF_ASSETS` (reuse `"PineNeedles001"` or `LeafSet026`);
   - a sprite generator (a narrow `pine()` variant: column shape, small `half`) and the `kind == "pino"` branch in `photo_sprite` (:342) and `tree_sprite` (textures.py:407 list and :419 fallback);
   - the `textures.py:775` registration tuple;
   - `_emit`'s `big` set (:218) if you want 3 planes;
   - optionally `map_species` substitutions (regions.py:344, e.g. `"cipres": "pino"`);
   - `vivo.respaldo` already falls back to `veg_arbusto_0` for unknown `veg_*`.
   - Bump `foliage.SPRITE_VERSION` (`:230`) if you change existing sprites, because they are cached on disk under `CACHE_DIR/sprites`.

---

## D. Large areas

### D1. Draw distance (lodOut)

From `mesh.py:18-25`:
```python
GROUP_LOD = {
    "vegetacion": 520, "vegetacion_lejos": 0, "senales": 600, "mobiliario": 650, "rayas": 0,
    "desgaste": 350, "bordes": 600, "topes": 400, "defensa": 900, "edificios": 2500,
    "edificios_det": 900, "col": 900, "portico": 800, "vallas": 600, "horizonte": 0, "barreras": 900, "isleta": 900, "tendido": 1800, "vallas_malla": 350,
}
# tamaño de celda del troceo espacial por grupo (m); el terreno ya viene en teselas
GROUP_CELL = {"horizonte": 2600.0, "terreno": 1e9, "vegetacion": 160.0}
```
The default `cell` is 200 m, from `meshes(self, cell=200.0)` at mesh.py:100.

How lod is computed (mesh.py:124-126, 187-195):
```python
                base = f"{group}_{material}_c{cx}_{cy}" + (f"x{niv}" if niv > 1 else "")
                nominal = gcell if gcell < 1e6 else 0.0
...
    lod = GROUP_LOD.get(group, 0)
    if lod and nominal:
        radio = float(np.linalg.norm(pos - (pos.min(0) + pos.max(0)) / 2, axis=1).max())
        lod += max(0.0, radio - nominal * 0.75)
    return {..., "lod": lod, "shadow": group not in NO_SHADOW}
```
It is written into the KN5 at export_ac.py:186: `b.write(struct.pack("<ff", 0.0, float(m["lod"])))`, which is lodIn = 0, lodOut = `m["lod"]`. A bounding sphere follows at :187-189.

**To give terrain a draw distance:**
- Add `"terreno": 1500` (for example) to `GROUP_LOD`.
- Because `GROUP_CELL["terreno"] = 1e9`, `nominal = 0` and there is no radius compensation. lodOut is measured from the tile centre, and 128 m tiles have a radius of about 90 m.
- The meshes from `faldones` (vivo) are also in group `terreno`.

**What covers the ground beyond lodOut:** nothing. `extras.horizon` drops every horizon cell inside the rect (extras.py:366-372, `inside = ...; cell_in = ...; keep = ~cell_in`), except inside a corridor `zona`. So culled tiles leave holes. To fix:
- keep the horizon cells inside the rect (they already follow the final terrain 1 m below it, extras.py:364-365), for example by skipping the `inside` removal behind a flag;
- or add a coarse LOD terrain group with `GROUP_LOD = 0`.

**Must test in game:** whether AC still collides with a physics mesh beyond its lodOut cannot be decided from the code. Terrain tiles carry physics, through the mesh-name prefix `1GRASS_` etc. (export_glb.py:29-30). A safe variant is a separate invisible physics copy with lodOut 0, at the cost of more meshes.

`agregar_biblioteca` (export_ac.py:249-260) adds one tiny mesh per material, **including every `terreno_*`**, which doubles the terrain mesh count.

### D2. Per-tile material (terrain.py:441-459)
```python
                name = f"terreno_{ti:03d}"
                tex = f"{name}.png"
                img = painter.paint_tile(x0, y0, x1, y1, mpp, self)
                self.tiles.append((x0, y0, x1, y1, img))
                scene.textures[tex] = png(img)
                scene.images[tex] = img
                scene.images[f"{name}_mask.png"] = painter.last_mask
                rep = tile_m / 2.0   # una repetición del detalle cada 2 m
                scene.material(name, tex, kind="multilayer", specular=0.0, ambient=0.4, diffuse=0.36, spec_exp=5.0,
                               extra={"mask": f"{name}_mask.png",
                                      "details": ["det_pasto.png", "det_tierra.png", "det_roca.png", "det_hojarasca.png"],
                                      "detail_nm": "det_nm.png", "mult": rep,
                                      "props": {"magicMult": 1.0, "fresnelC": 0.0, "fresnelEXP": 4.0, "fresnelMaxLevel": 0.0,
                                                "detailNMMult": [0.0, 1.0, rep, 0, 0, 0, 0, 0, 0, 0]}})
                for fis, sel in fisica_del_suelo(pos, faces, cobertura):
                    ...
                    scene.add("terreno", name, pos[usados], uv[usados], remap[sel], normals=nrm[usados], phys=fis)
```
- UVs run 0–1 across each tile (`uv = [(GX-x0)/(x1-x0), (y1-GY)/(y1-y0)]`, :430).
- Each tile stores a PIL image plus PNG bytes plus a mask.
- `ext_config` lists every `terreno_*` in `GRASS_FX`, `ROUGH_MATERIALS` and `MATERIAL_ADJUSTMENT_2` (export_ac.py:311, 320-330).

**To share materials (texture atlas):**
1. Group tiles into K×K blocks, for example 4×4 tiles of 128 m = 512 m.
2. Paint one atlas image per block, either `paint_tile` over the whole block or pasting the tiles.
3. Name the material after the block: `terreno_b{bx}_{by}`.
4. Set UVs to `(GX - bx0)/(bx1-bx0)` and `(by1 - GY)/(by1-by0)`.
5. Set `rep = block_m / 2` (or keep the detail at 2 m with `mult = block_m/2`).
6. Store `self.tiles` per block for `mosaic()`.
7. Keep `scene.add("terreno", block_mat, ...)` per tile so meshes stay tile-sized for culling.

Texture size stays bounded: 512 m at 0.5 m/px is 1024², at 0.25 m/px it is 2048². `vivo.renombrar_terreno` (vivo.py:478-497) keys on the `terreno_` prefix, so keep that prefix.

### D3. The `pedazo` parameter and `semilla_ac`
- **Signature:** `run(args, log=print, proj=None, scene=None, osm_data=None, pedazo=None, cat_data=None, extension=None)` (pipeline.py:110).
- **Type:** `pedazo` is a `(xmin, ymin, xmax, ymax)` tuple of floats, in local metres relative to the fixed origin of `proj`.

When `pedazo` is set:
- no corridor (:132);
- no `_place_free` (:317);
- `terr.solo = pedazo` (:346-347), which **keeps only the terrain tiles whose centre is inside the box** (terrain.py:424-426);
- no `BR.boundary` (:356-357);
- no horizon (:184);
- an early return at :407-410: `return {"scene": scene, "proj": proj, "net": net, "terr": terr}`, a `dict` with no export.

Without `pedazo`, `run` returns the `.glb` path as a `str` (:473).

`run` itself does no exact cropping or stitching. That happens in `vivo._escena` (vivo.py:108-139):
- the projection is `LocalProjection.marco(lat0, lon0, core ± MARGEN)`;
- `recortar(scene, core, excluir)` (:184-271) splits triangles exactly on the core edges with `partir`. Small parts (under 40 m) go whole to the piece containing their centre. Dummies are cleared.
- `coser(scene, core, vecinos)` (:407-475) runs only if `carpeta` is given. It reads neighbour `.olv` files and blends heights within 10 m, up to 0.8 m.
- `faldones()` adds a 1 m skirt.
- `renombrar_terreno(scene, i, j)` renames `terreno_NNN` to `tv_i_j_NNN`.

**The seed builder** is `semilla_ac(vivo, nombre, carpeta_ac, url, radio=1, log=print, r_carga=430.0, r_soltar=640.0, t_foco=0.5)` (vivo.py:1304). Core loop at :1342-1369:
```python
    for i in range(ci - radio, ci + radio + 1):
        for j in range(cj - radio, cj + radio + 1):
            x0, y0, x1, y1 = nucleo(i, j)
            rect = rect_pedazo(i, j)
            vivo.osm.asegurar(rect, espera=900)
            for _ in range(4):
                els, ext, faltan = vivo.osm.del_pedazo(i, j)
                if not faltan:
                    break
                vivo.osm.asegurar(ext, espera=600)
            partes = None
            ...
            sc, terr = _escena(i, j, els, partes, ext=ext)
            for k, v in sc.materials.items():
                scene.materials.setdefault(k, v)
            for k, v in sc.textures.items():
                scene.textures.setdefault(k, v)
            for k, v in sc.images.items():
                scene.images.setdefault(k, v)
            for k, piezas in sc.pieces.items():
                scene.pieces[k].extend(piezas)
            if (i, j) == (ci, cj):
                terr_salida = terr
            horneados.append(f"{i}_{j}")
```
It then calls `export_ac.agregar_biblioteca`, places a simple start grid along `vivo.salida`, builds `info` with `"es_semilla_vivo": True`, and calls `export_ac.write_track(scene, salida, nombre, info, [], None)`. That means no `map_lines` and **no traffic**, because there is no `info["trafico"]`.

**Can it bake an N × M block into one KN5 with a shared origin? Not as-is:**
- It needs a live `Vivo` instance: process pools, background threads, the HTTP OSM tile fetcher, and `vivo.salida` set by `_buscar_salida`.
- It always bakes a square of `2·radio+1` pieces around the start.
- It calls `_escena` without `carpeta`, so `coser` never runs between baked pieces; only skirts hide seams.
- There is no merged road network, so no traffic and no minimap.

**Recommended:** lift vivo.py:1333-1369 into a standalone `bake_block(args, lat0, lon0, i_range, j_range, osm_elements_fn, carpeta)`:
1. Call `_iniciar(vars(args), lat0, lon0)` once.
2. For each piece in raster order, call `_escena(i, j, els, ext=ext, carpeta=carpeta)` and write `p_i_j.olv` (via `escribir_olv`) so later pieces stitch to earlier ones.
3. Merge into one `Scene`, then call `write_track`.

Note that live pieces use `--tesela 64` and `--sin-horizonte` (vivo.py:1659).

**`--excluir X0,Y0,X1,Y1`** (vivo.py:1643-1644, 751, 822-827, 184-203) is a local-metre box, relative to `--centro`, that is already baked into a KN5:
- pieces fully inside it are never generated (`_cubierto`, used at :1062);
- pieces overlapping it are cut along its edges by `recortar`.

The GUI uses it to extend a baked track with live mode (gui/app.py:515 passes the track's `rect`). For alignment, `--centro` must equal the baked track's `lat0, lon0` (written to `openlaps_geo.json`).

### D4. Corridor logic

pipeline.py:132-139:
```python
    corredor = ancho_corredor(args, area_km2) if pedazo is None else 0.0
    if corredor:
        log(f"  tramo largo: solo se genera un corredor de {corredor:.0f} m a cada lado de la ruta "
            "(el resto de la zona queda como relieve lejano)")
        if area_km2 > CORREDOR_DESDE_KM2:
            args.sin_orto = args.sin_dosel = True
            log("  (zona grande: sin ortofoto ni altura de dosel)")
```
pipeline.py:263-272:
```python
    if corredor:
        ruta0, _, _ = roads.route(net, puntos_ruta(args, proj), closed=args.modo == "circuito")
        zona = LineString(ruta0[:, :2]).buffer(corredor, quad_segs=4).intersection(sbox(*rect))
        net.acotar(zona)
        osm = solo_en_zona(osm, proj, zona.buffer(30.0))
        antes = len(blds)
        blds = [b for b in blds if b["poly"].intersects(zona)]
        cob.quieta = [g for g in cob.quieta if g.intersects(zona)]
        cob.corriente = [g for g in cob.corriente if g.intersects(zona)]
```
pipeline.py:476-488:
```python
CORREDOR_DESDE_KM2 = 24.0     # un tramo o circuito en una zona mayor que esto se genera como corredor
CORREDOR_ANCHO = 220.0        # m a cada lado de la ruta

def ancho_corredor(args, area_km2):
    if getattr(args, "modo", "libre") not in ("tramo", "circuito") or not getattr(args, "ruta", None):
        return 0.0
    v = str(getattr(args, "corredor", "auto") or "auto")
    if v == "auto":
        return CORREDOR_ANCHO if area_km2 > CORREDOR_DESDE_KM2 else 0.0
    return max(60.0, float(v)) if float(v) > 0 else 0.0
```
`zona` then limits:
- road runs (`acotar` → `_runs`, roads.py:1262-1284);
- terrain tiles (`terr.zona`, terrain.py:427-429);
- the boundary wall shape (`BR.boundary(..., zona)`);
- vegetation (an exclusion at :382-383);
- the horizon fill (extras.py:368-372).

**The gate is line 483:** `--modo libre` always gets 0, even with `--ruta`. A test pins this: tests/test_rally.py:77.

**Side-road fences** live only in `_place_stage` (pipeline.py:782-807), which runs only for tramo and circuito (:305-309). The corridor code does not close anything.

**Free-roam corridor along a multi-waypoint route without closed side roads:** yes, with a one-line change.
- Change :483 to `if not getattr(args, "ruta", None): return 0.0`, so libre is allowed when `--ruta` is given, and update test_rally.py:77.
- Then `roads.route` builds the multi-waypoint path, which already accepts N waypoints (roads.py:3271-3303).
- Libre then calls `_place_free`, which only uses edges with runs inside `zona` (its `net.ranges` are `zona`-limited). No fences are added.
- Side roads are cut where they leave the corridor, ending at the corridor edge, where the invisible wall would be if kept (see E).
- Above 24 km², :136-138 also disables the orthophoto and canopy layers. Decouple that if you supply XYZ imagery.

### D5. Shared origin and projection

geo.py:42-66:
```python
class LocalProjection:
    """UTM de la zona que toca, recentrada en el centro del área."""
    def __init__(self, bbox: BBox):
        lat0, lon0 = bbox.center
        zone = int((lon0 + 180) // 6) + 1
        epsg = (32600 if lat0 >= 0 else 32700) + zone
        ...
        ox, oy = self._fwd.transform(lon0, lat0)
        self.ox, self.oy = ox, oy
        ...
    @classmethod
    def marco(cls, lat0, lon0, rect):
        """Proyección con el origen fijo en (lat0, lon0) y límites `rect` = (xmin, ymin, xmax, ymax) en metros.
        La usa el modo en vivo: todos los pedazos comparten el mismo origen, así encajan sin moverlos."""
        p = cls(BBox.around(lat0, lon0, 10.0))
        p.xmin, p.ymin, p.xmax, p.ymax = (float(v) for v in rect)
        return p
```
- Local coordinates are UTM (Koura is zone 36, EPSG:32636) minus the UTM of `(lat0, lon0)`.
- AC axes: x = east − x0, y = height, z = −(north − y0) (export_ac.py:339-351).
- Two CLI runs with different `--bbox` get **different origins** (each bbox centre), so they do not line up.
- **There is no CLI option to pin the origin.** The only way is programmatic: `run(args, proj=LocalProjection.marco(lat0, lon0, (xmin, ymin, xmax, ymax)))`. With `pedazo=None` this produces a full normal export; `bbox = proj.bbox()` at :116-117.
- XY then lines up exactly. Choose `rect` edges as multiples of `--res` and `--tesela`, because the mesh grid is `np.linspace(p.xmin, p.xmax, nx)` (terrain.py:84-87) and tiles start at `xmin`. The 10 m working grid is already aligned to multiples of 10 (terrain.py:36-42).
- **Z at seams will not match.** Road profiles are median and gaussian smoothed along whole chains (roads.py:983-997), and junction heights and the second-pass road surface (`armonizar_calzadas`) depend on what is in each run. Live mode needs `coser` for exactly this reason.
- Each separate run also gets its own boundary wall, its own `_place_free` spawn and a duplicate road strip at the edges.

---

## E. Free roam

### E1. `_place_free` (pipeline.py:810-847)
```python
def _place_free(scene, net, log=print):
    best, score = None, -1e18
    for e in net.edges:
        if e.tunnel or e.bridge:  # una salida bajo tierra hace que AC deje el coche en la calle de encima
            continue
        for a, b in net.ranges(e):
            if b - a <= 40:
                continue
            m = e.at(np.array([(a + b) / 2]), 0.0)[0]
            centro = math.hypot(m[0], m[1])          # el origen local es el centro de la zona
            sc = min(b - a, 150.0) * (1 + e.prio) - centro * 0.35
            if sc > score:
                best, score = (e, a, b), sc
    if best is None:
        for e in net.edges:
            for a, b in net.ranges(e):
                if b - a > score:
                    best, score = (e, a, b), b - a
    if best is None:
        log("  aviso: no hay calles dentro del área para poner salidas")
        return
    e, a, b = best
    sv = np.arange(a + 2, b - 2, 1.0)
    poly = e.at(sv, 0.0)
    hw = np.full(len(poly), e.hw)
    i_line = len(poly) - 1 if len(poly) < 120 else 110
    _place_grid(scene, poly, hw, i_line, count=12, prefix="AC_START")
    _place_grid(scene, poly, hw, i_line, count=8, prefix="AC_PIT")
    t, n = _frame(poly, i_line)
    p = poly[i_line].copy()
    p[2] += 0.3
    scene.dummy("AC_HOTLAP_START_0", p, t)
    for side, nm in ((1, "AC_TIME_0_L"), (-1, "AC_TIME_0_R")):
        scene.dummy(nm, poly[i_line] + np.r_[n * side * (e.hw + 1), 0.5], t)
    log(f"  salidas en {e.tags.get('name', e.cls)} ({b - a:.0f} m)")
```
`_place_grid` (:744-754) puts cars 8 + 7k m behind the line, alternating ±0.45·hw. To pin the spawn, add an optional `(x, y)` target and score by distance to it instead of `centro`.

### E2. Boundary wall and its removal for AC
The wall is built at pipeline.py:356-357 (`if pedazo is None: BR.boundary(scene, terr, rect, zona)`). barriers.py:114-139:
```python
def boundary(scene, terrain, rect, zona=None, height=6.0, step=4.0):
    """Muro invisible (solo colisión) en el borde del área generada (o del corredor `zona` de un tramo largo)."""
    if zona is not None:
        ...
                scene.add("col", "invisible", p, uv, f, phys="WALL")
        return
    ...
        z = terrain.height(x, y) - 2.0
        pts = np.column_stack([x, y, z])
        p, uv, f = wall_strip(pts, height + 2.0, both=True)
        scene.add("col", "invisible", p, uv, f, phys="WALL")
```
The removal is at pipeline.py:439-442:
```python
    if args.ac:
        # el muro invisible de borde queda en el .glb, pero en AC estorbaría si el usuario activa el modo en vivo
        for k in [k for k in scene.pieces if k[0] == "col"]:
            del scene.pieces[k]
```
**This also deletes every other collider in the `col` group:**
- street-lamp posts (extras.py:148);
- sign posts (extras.py:175);
- tree trunks (`trunk_colliders`, extras.py:299);
- pylon bases (roadside.py:390).

So in the AC export, lamps, signs, trunks and pylons have no collision, which contradicts docs/assetto-corsa.md:46-47.

**Fix:**
1. In barriers.py:123 and :139, change the group to a new `"limite"`: `scene.add("limite", "invisible", p, uv, f, phys="WALL")`.
2. In mesh.py, add `"limite": 0` to `GROUP_LOD` (lodOut 0 means always drawn) and `"limite"` to `NO_SHADOW`.
3. Change pipeline.py:441 to `k[0] == "limite"` only when you want the wall removed (for example behind a new `--sin-muro` flag). Otherwise delete nothing.

The wall uses the `invisible` material (textures.py, `kind="invisible"`: blended, fully transparent, no shadow at export_ac.py:176). Its physics comes from the `1WALL_` name prefix.

### E3. ui_track.json text (export_ac.py:424-435, and pipeline.py:453-454)
```python
                "description": f"Generada con openlaps a partir de datos abiertos. {area_km2:.2f} km².",
                "tags": [t for t in (R.code, R.sub, "openlaps", args.modo) if t], ...
```
```python
    tags = list(info.get("tags", [])) + ([T.ETIQUETA] if trafico else [])
    desc = info["description"]
    if trafico:
        desc += (f" Tráfico: modo Traffic de CSP con unos {T.coches_recomendados(trafico)} coches "
                 "(con los 1000 de partida el área se atasca).")
    ui = {"name": info["name"], "description": f"{desc} {CREDIT}", "tags": tags,
          "geotags": [f"{info['lat']:.5f}", f"{info['lon']:.5f}"], "country": regions.active().country,
          "city": info.get("city", ""), "length": str(int(info.get("length", 0))), "width": str(info.get("width", "")),
          "pitboxes": str(info.get("pitboxes", 8)), "run": info.get("run", "A-B"),
          "author": "openlaps", "version": __version__, "url": URL}
```
Notes for translating to English:
- `CREDIT` is in `openlaps/__init__.py:6` and is already mostly language-neutral.
- `info["name"]` comes from `--titulo`.
- `run` is `"free roam"` in libre mode (pipeline.py:304).
- `tags` include `"libre"` (the Spanish mode name); map it to English at pipeline.py:454.
- Keep `T.ETIQUETA = "traffic-planner-ready"`: CSP's Traffic mode requires it (trafico.py:48).
- `city` is never set; add `info["city"] = "Koura"`.
- `ATRIBUCIONES.txt` text is `pipeline.ATTRIBUTION` (pipeline.py:24-34, Spanish).

---

## F. Width and lanes

### F1. `ROAD_CLASS` (config.py:38-62)
```python
# ancho de carril (m), carriles por defecto si es doble sentido, acotamiento (m),
# velocidad de proyecto (km/h), sigma del suavizado vertical (m), prioridad
ROAD_CLASS = {
    #               carril  carriles  acot  vel  sigma prio
    "motorway":      (3.50,  2,       2.50, 110, 45.0, 10),
    "trunk":         (3.50,  2,       2.00,  90, 35.0, 9),
    "primary":       (3.50,  2,       1.50,  80, 28.0, 8),
    "secondary":     (3.25,  2,       1.00,  70, 22.0, 7),
    "tertiary":      (3.00,  2,       0.50,  60, 16.0, 6),
    "unclassified":  (2.90,  2,       0.25,  50, 13.0, 5),
    "road":          (2.90,  2,       0.00,  40, 12.0, 4),
    "residential":   (3.25,  2,       0.00,  40, 10.0, 4),
    "living_street": (2.75,  2,       0.00,  20, 8.0,  3),
    "service":       (3.00,  1,       0.00,  30, 8.0,  2),
    "track":         (3.20,  1,       0.00,  30, 9.0,  1),
    "pedestrian":    (3.00,  2,       0.00,  20, 6.0,  0),
    "path":          (2.60,  1,       0.00,  20, 5.0,  0),
    "bridleway":     (2.60,  1,       0.00,  20, 5.0,  0),
    "motorway_link": (3.75,  1,       1.50,  60, 25.0, 8),
    "trunk_link":    (3.75,  1,       1.00,  50, 20.0, 7),
    "primary_link":  (3.50,  1,       0.50,  50, 16.0, 6),
    "secondary_link":(3.50,  1,       0.50,  40, 14.0, 5),
    "tertiary_link": (3.25,  1,       0.25,  40, 12.0, 4),
}
```

### F2. The width function `RoadNetwork._attrs` (roads.py:819-851)
```python
    def _attrs(self, e, deducida=None):
        t = e.tags
        lane_w, def_lanes, shoulder, speed, sigma, prio = C.ROAD_CLASS.get(e.cls, C.ROAD_CLASS["road"])
        e.oneway = t.get("oneway") in ("yes", "1", "true", "-1") or t.get("junction") == "roundabout" \
            or e.cls in ("motorway", "motorway_link")
        lanes = _num(t.get("lanes"))
        if lanes is None:
            lanes = def_lanes if not e.oneway else (2 if e.cls in ("motorway", "trunk") else 1)
        lanes = int(max(1, min(lanes, 8)))
        e.lanes, e.lane_w, e.shoulder = lanes, lane_w * regions.active().lane_mult, shoulder
        e.speed = _velocidad(t.get("maxspeed")) or speed
        e.sigma, e.prio = sigma, prio
        surf = t.get("surface") if t.get("surface") in C.SURFACE_MAP else deducida
        ...
        width = _num(t.get("width"))
        carriage = lanes * lane_w
        if e.cls in C.PAVED_PATHS:
            e.oneway = False
            carriage = 6.0
        if e.oneway and lanes == 1 and e.cls in ("residential", "unclassified", "tertiary", "living_street"):
            carriage = lane_w * 1.7   # calle de un sentido con cochera / estacionamiento
        e.hw = (width if width and 2.5 < width < 40 else carriage) / 2.0
```
**`lane_mult` does not change road width.** :845 and :850 use the raw table `lane_w`, not `e.lane_w`. `e.lane_w`, which includes `lane_mult`, is read only at:
- roads.py:2485 (marking offsets: `carriage = e.lanes * e.lane_w; edge_o = min(carriage / 2.0, e.hw - 0.2)`);
- extras.py:85 (dead code under `if False:`).

To make `lane_mult` narrow roads, change :845 and :850 to use `e.lane_w`.

`_geometry` (roads.py:912-920) later adds the shoulder when the road is not urban and has no `width` tag, plus parking/2.

### F3. Per-way overrides
There is no mechanism today. **The graph does not keep OSM way ids:**
- `osm.parse` keeps `w["id"]` (sources/osm.py:276);
- `RoadNetwork._build_graph` splits ways into `raw.append((cur, w["tags"]))` (roads.py:551, 554), dropping the id;
- `Edge.id` is a sequential index (`Edge(id=i, ...)` at :558, renumbered in `_merge_deg2` at :879-880);
- `_merge_deg2` (:853-881) fuses consecutive edges with equal `key_attrs()` (cls, hw, mat, phys, bridge, tunnel, layer, oneway), so one edge can span several OSM ways.
- `e.tags` is the same dict object as `w["tags"]`, shared by reference.

**Best hook, the cheapest and safest:** patch tags right after OSM parsing, at pipeline.py:193 (`osm = f_osm.result()`):
```python
for w in osm["ways"]:
    o = overrides.get(w["id"])          # {way_id: {"width": 5.5, "surface": "asphalt", "lanes": 1, ...}}
    if o: w["tags"] = {**w["tags"], **{k: str(v) for k, v in o.items()}}
```
This flows through `_superficies` (surface inference) and `_attrs` (width, lanes, surface, physics). Widths outside 2.5–40 m are ignored by `_attrs`. Apply the same in `red_de_calles` (pipeline.py:64) and in vivo (`OSM.parse` at vivo.py:121) for live mode.

If you need ids on edges (for example for G):
- change `raw` to a 3-tuple `(cur, w["tags"], w["id"])` at roads.py:551 and :554;
- update the unpacking at :557, in `_superficies` (`for i, (nodes, t) in enumerate(raw)` at :749 and :774, and `raw[i][0]`, `raw[i][1]` at :777-792);
- add `way_ids: list` to `Edge` and concatenate it in `_merge_deg2` (:870).

---

## G. Elevation overrides

`_elevation` (roads.py:980-1051) is where the DEM is sampled:
```python
    def _elevation(self):
        prof = {}
        for chain in self._chains():
            pts, owners = [], []
            for e, fwd in chain:
                P = e.P if fwd else e.P[::-1]
                start = 1 if pts else 0
                pts.append(P[start:, :2])
                owners.append((e, fwd, start, len(P)))
            P = np.vstack(pts)
            z = self.dem_z(P[:, 0], P[:, 1])
            s = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(P, axis=0), axis=1))])
            sig_m = max(e.sigma for e, _ in chain)
            k = max(3, int(round(18.0 / DS)) | 1)
            if len(z) > k:
                z = median_filter(z, size=k, mode="nearest")
            zs = gaussian_filter1d(z, sig_m / DS, mode="nearest") if len(z) > 3 else z
            ...
                prof[e.id] = seg if fwd else seg[::-1]
        acc = {}
        for e in self.edges:
            w = 0.05 if (e.bridge or e.tunnel) else 3.0 ** e.prio
            for nid, val in ((e.a, prof[e.id][0]), (e.b, prof[e.id][-1])):
                ...
        self.node_z = {n: v[0] / v[1] for n, v in acc.items()}
        ...
            else:
                zs = prof[e.id]
                L = e.s[-1]
                D = max(min(12.0, L * 0.5), min(60.0, L * 0.5))
                wa = 0.5 * (1 + np.cos(np.pi * np.clip(e.s / D, 0, 1)))
                wb = 0.5 * (1 + np.cos(np.pi * np.clip((L - e.s) / D, 0, 1)))
                e.Z = _acuerdos_verticales(e.s, zs + (za - zs[0]) * wa + (zb - zs[-1]) * wb, e.speed)
```
`_acuerdos_verticales(s, z, v_kmh, desvio=2.0, iters=400)` (roads.py:410-435) smooths only where vertical curvature exceeds `1/(0.18·v²)` and clamps to within ±2 m of its input (`z = np.clip(z, z0 - desvio, z0 + desvio)`). `self.dem_z` is `terr.z`, a bicubic read of the 10 m DSM-to-DTM grid (terrain.py:73-79), passed at pipeline.py:258.

**Best hook:** right after roads.py:991, `z = self.dem_z(P[:, 0], P[:, 1])`.
1. Add `gpx_z=None` to `RoadNetwork.__init__`, as a callable `(x, y) -> (z, mask)`, or a list of `(Nx3 local xyz polyline)`.
2. At :991, for each chain point within about 6 m of the GPX polyline (cKDTree on GPX points densified to 1 m), replace `z` with the GPX height interpolated by nearest arc position.
3. To restrict this to given OSM way ids, the edges need way ids (F3). Then build a per-point mask from `owners`: points `P[start:]` belong to `e`, so `mask[pos:pos+n] = bool(set(e.way_ids) & ids)`.

What still happens downstream:
- the 18 m median filter, then a gaussian with sigma 5–45 m (`config.ROAD_CLASS[...][4]`). Reduce `sig_m` for GPX-covered chains to keep detail;
- node blending (a cosine bell over 12–60 m toward the weighted node height);
- `_acuerdos_verticales` with its ±2 m clamp;
- later, `armonizar_calzadas` (roads.py:1464) and terrain carving to the road.

**State the GPX vertical datum.** The DEM is Copernicus EGM2008 orthometric height. GPX `<ele>` is often WGS84 ellipsoidal; the geoid near Koura is roughly +20 to +25 m, which needs verifying. Also smooth the GPX noise first.

---

## H. Building overrides

### H1. Height decision (buildings.py:295-320)
```python
def height_of(b, urban_dense):
    t = b["tags"]
    hh = _num(t.get("height"))
    if hh:
        return max(2.6, hh)
    lv = _num(t.get("building:levels"))
    if lv:
        return lv * C.LEVEL_HEIGHT + 0.3
    if b.get("height"):
        return max(2.6, float(b["height"]))
    kind = t.get("building", "yes")
    area = b["poly"].area
    r = _h(b["poly"].centroid.wkt)
    if kind in ("church", "cathedral", "chapel"):
        return 12.0 + 6 * r
    if kind in ("industrial", "warehouse", "retail", "supermarket", "commercial", "factory", "manufacture", "hangar"):
        return 6.0 + 3 * r
    if kind in ("barn", "farm_auxiliary", "cowshed", "stable"):
        return 4.5 + 2 * r
    if kind in ("shed", "garage", "hut", "kiosk"):
        return 2.6
    if area > 600:
        return 7.0 + 4 * r
    opts = active().levels_default
    lv = opts[min(len(opts) - 1, int(r * len(opts)))]
    return lv * C.LEVEL_HEIGHT + 0.3
```
- OSM `height` and `building:levels` tags beat `b["height"]` (Microsoft or Overture).
- Writing an override only into `b["height"]` loses to OSM tags. Write it into `b["tags"]["height"]`, or set `b["floors"]` too, because floors drive `flat_from_floors` and tower logic at buildings.py:356.

### H2. The footprint data structure
`B.collect` (buildings.py:32-89) returns a list of dicts:
- `{"poly": shapely Polygon in local metres, "tags": dict, "height": float|None, "src": "osm"|"ms"|"catastro"|"overture", ["floors": int]}`;
- OSM entries come from :63, Microsoft from :81 (`tags={"building": "yes"}`).

**There is no OSM id:** `osm.parse` drops it for areas (sources/osm.py:292 `{"tags": tags, "outer": coords, "inners": []}` and :302). Microsoft footprints carry only `{"outer", "height"}` (sources/msbuildings.py:101-102).

**Best hook:**
1. Add `"id": el["id"]` (with `"type"`) at osm.py:292 and :302.
2. Propagate it at buildings.py:63: `out.append({..., "osm_id": a.get("id")})`.
3. Apply overrides at the end of `collect`, before `return out` at :89, or in pipeline.py right after :213 (`blds = B.collect(...)`):
   - by `osm_id`, set or merge tags (`height`, `building:levels`, `roof:shape`, `roof:colour`, `building:colour`) or replace `poly`;
   - for Microsoft or any source without an id, use an `STRtree` of `b["poly"]` and match override centroids (lat/lon → `proj.to_local`) with `tree.query(Point, predicate="intersects")` or nearest within about 3 m.
4. Optionally support adding footprints: append new dicts with `"src": "manual"`.

`drop_on_roads` (:262-288) copies dicts with `dict(b)`, so keys survive. Note that OSM cache files hold the parsed-from-raw JSON, so parse changes take effect on cached data too, because `parse` runs on the raw elements.

### H3. Facade materials and UVs
Walls are built in `build()` at buildings.py:379-385:
```python
        for ring in [poly.exterior] + list(poly.interiors):
            pts = np.asarray(ring.coords)[:, :2]
            bot = np.column_stack([pts, np.full(len(pts), base)])
            p, uv, f = wall_strip(bot, top + C.PARAPET - base, u_scale=4.0, v_scale=-3.0, both=False)
            # alinear la textura con el nivel del piso
            uv[:, 1] = (ground - p[:, 2]) / 3.0
            scene.add("edificios", mat, p, uv, f, phys="WALL")
```
`wall_strip` is at roads.py:1375-1389:
```python
def wall_strip(points_bottom, height, u_scale=4.0, v_scale=3.0, both=True):
    pb = np.asarray(points_bottom, float)
    n = len(pb)
    pt = pb.copy()
    pt[:, 2] += height
    pos = np.vstack([pt, pb])
    d = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(pb[:, :2], axis=0), axis=1))])
    uv = np.vstack([np.column_stack([d / u_scale, np.zeros(n)]),
                    np.column_stack([d / u_scale, np.full(n, height / v_scale)])])
    ...
```
- U is the distance along the ring divided by 4 m, so one texture is 4 m wide, one window bay.
- V is `(ground − z)/3`, so one texture is 3 m tall, one floor, aligned to the ground floor.
- The texture repeats.
- The material is chosen once per building: `fachada_{k}{"", "_d", "_l"}`, `iglesia`, `nave_k`, `torre_k`, `ciudad_k`, or `textures.facade_material(scene, rgb, style)` for `building:colour` (textures.py:838-851, quantized names `fachada_cRRGGBB`).
- The `fachada_*` textures are 512 px procedural images generated at textures.py:764-771.

**A per-wall facade texture is possible, but not today:** each whole ring gets one material in one `wall_strip` call.

To do it:
1. Iterate the ring's segments, or runs of segments.
2. Call `wall_strip(bot[k:k+2], ...)` per segment, with `uv[:,1] = (ground - p[:,2])/3.0`, then `scene.add("edificios", seg_mat, ...)`.
3. Register a custom material per photo texture: `scene.textures[name+".png"] = png(img)`, `scene.images[...] = img`, `scene.material(name, tex, normal=...)`. Follow `facade_material` as the pattern.
4. For a photo that spans the whole wall rather than tiling, compute `u = d / wall_length` and `v = (top - z) / wall_height` instead of the 4 m × 3 m tiling.

Also add the material name to `ext_config`'s `fac` filter (export_ac.py:315 matches prefixes `fachada_`, `iglesia`, `azotea_`), so use a `fachada_` prefix.

In live mode, `vivo.respaldo` (vivo.py:500-509) maps unknown materials to `fachada_0`. Custom textures only survive in baked KN5s.

---

## I. tools/ and tests

### I1. Scripts

| Script | Purpose |
|---|---|
| `tools/cobertura.py` | Land-cover and water diagnostic panel for an area without generating a track (`--centro/--tam/--nombre/--temporada`); writes `salida/<nombre>_cobertura.jpg/.json` |
| `tools/comparar_fotos.py` | Compares real street photos (from referencias.py) with renders of a `.glb` from the same pose; IoU and skyline metrics, panels, `index.html` |
| `tools/comparar_ruta.py` | Driver-view contact sheet along a `.glb` route (`--cada`, `--referencia`) |
| `tools/costuras.py` | Measures gaps, overlaps and steps between neighbouring live-mode `.olv` pieces (`<folder> [--lado 256] [--max 40]`) |
| `tools/defectos.py` | Finds steep slivers on flat surfaces and sharp grade breaks in a `.glb` (`--vistas`, `--n`) |
| `tools/escalones.py` | Finds overlaps (3–60 cm), seams (over 5 cm) and holes in drivable surfaces of `.glb` files (`--min/--max/--n`) |
| `tools/instalar_vivo_lua.py` | Reinstalls `openlaps/vivo_ac.lua` into existing seed tracks. The default AC path is the Windows Steam folder. |
| `tools/kn5_check.py` | Reads a whole `.kn5` and verifies its structure byte by byte; also imported by tests |
| `tools/kn5_inspect.py` | Inspects a large `.kn5` without loading vertex blocks (details below) |
| `tools/probar_ac.ps1` | Windows PowerShell: links the track, edits race.ini, launches `acs.exe`, waits and prints log errors |
| `tools/referencias.py` | Downloads open street-level photos with pose (Panoramax, Mapillary, Wikimedia Commons) |
| `tools/render.py` | CPU software renderer for `.glb` (`--cam`, `--mira`, `--ancho`, `--salida-coche`) |
| `tools/rendimiento_ac.py` | Estimates AC draw calls and visible triangles from a `.kn5` |
| `tools/trafico_check.py` | Checks `data/traffic.json` as CSP would join it (`--png`, `--zona x0,z0,x1,z1`) |

**`kn5_inspect.py`:** `python tools/kn5_inspect.py pista.kn5 [--texturas carpeta] [--json salida.json] [--muestras N]` (arguments at :39-42).
- Prints the version, the texture list (name, MB, format), materials (shader, blend/at/depth, properties, samplers), the first 80 dummies with matrices, and per-group mesh counts, vertices and triangles.
- Prints physics meshes (name, v, mat, vis, cast, lod, bs). `--muestras` adds sample vertices for road meshes.
- `--texturas` dumps textures to a folder.
- `--json` writes `{"textures", "materials", "dummies", "meshes"}`; each mesh has `name, v, t, mat, vis, rend, cast, lod[in,out], bs[cx,cy,cz,r]`.

**`probar_ac.ps1`:** parameters `-Pista` (required), `-Coche abarth500`, `-Skin ""`, `-AC $env:OPENLAPS_AC`, `-Espera 120`.
1. Junctions `salida\assetto_corsa\<Pista>` into `content\tracks`.
2. Kills `acs` and `AssettoCorsa.exe`.
3. Backs up race.ini once to `race.ini.antes_openlaps`.
4. Rewrites these race.ini keys (lines 49-51):
   - `TRACK=<Pista>`, `CONFIG_TRACK=` (empty)
   - `MODEL=<Coche>` (the first one after `[RACE]`)
   - `SKIN=<Skin>`, `SPAWN_SET=START`, `CARS=1`
5. Writes `steam_appid.txt` with 244210 if missing.
6. Starts `acs.exe` and waits for `goToSpawnPosition START` in `Documents\Assetto Corsa\logs\log.txt`.
7. Prints log lines matching the track, `ERROR` or `CRASH`.

It is Windows-only.

**`rendimiento_ac.py`:** `python tools/rendimiento_ac.py pista.kn5 [more.kn5 ...] [--grupos]`.
- Runs `kn5_inspect.py --json` in a subprocess.
- Samples up to 160 road-mesh centres at 1.2 m height, 8 headings, 95° horizontal FOV, and respects each mesh's lodOut.
- Prints mesh, triangle, material and texture counts (MB), visible draw calls (median and p95), visible triangles, and shadow casters within 380 m. `--grupos` adds a per-group breakdown.

**`referencias.py`:** `--centro lat,lon | --bbox s,w,n,e`, `--tam 800`, `--nombre` (required), `--fuentes panoramax,mapillary,commons`, `--max 60`, `--sep 12`, `--margen 40`, `--salida referencias`.
- Mapillary needs `MAPILLARY_TOKEN`.
- Output goes to `referencias/<nombre>/`: images, `referencias.json` (position, heading, FOV, flat or 360, author, licence) and `hoja.jpg`.

### I2. Tests
- `tests/`: conftest.py (`tiny_scene` fixture; adds `tools/` to `sys.path`), test_catastro, test_cobertura, test_eeuu, test_formats (DDS, glTF, `.ai`, KN5), test_geo_regions, test_google3d, test_gui (one test skips on non-Windows, :279), test_rally (corridor and pace notes), test_rendimiento, test_terraceria, test_trafico, test_trafico_vivo, test_vivo. That is 2,331 lines in total.
- **How to run:**
  ```
  python -m pip install -e ".[dev]"
  python -m pytest -q
  ruff check openlaps tools tests
  ```
  `[tool.pytest.ini_options] testpaths = ["tests"]` is set in pyproject.toml:60-61. CI (.github/workflows/ci.yml) runs on ubuntu and windows with Python 3.11 and 3.12.
- **Network:** CONTRIBUTING.md:28 says "Tests run offline". Network calls are monkeypatched, for example test_vivo.py:218-248 replaces `post_form` and `download_api`.
- **Runtime:** no hints in the repo. Expect the first run to be slower because numba-compiled functions (`cache=True`) build their caches.

---

## J. traffic.json

- **Consumer:** CSP's Traffic Planner tool (by x4fab, public domain) and CSP's **"Traffic" game mode**. They read `data/traffic.json` (lanes as 3D polylines with roles, and intersections as polygons). This is described in the `openlaps/trafico.py:1-27` docstring.
- **Requirements:**
  - the track tag `traffic-planner-ready` (`trafico.py:48 ETIQUETA`, added at export_ac.py:424);
  - `surfaces.ini` gets `ALLOW_NEW_MODE_SCRIPTS=1` when traffic exists (export_ac.py:363 → `surfaces_ini(nuevos_modos=bool(trafico))`, :244-245).
- **Written** by export_ac.py:364-370 unless `--sin-trafico`. The description gets the recommended car count (`:426-428`, `coches_recomendados` at about 150 m of lane per car).
- **docs/assetto-corsa.md has no traffic section.** It only covers install, Quick Drive Practice, `probar_ac.ps1`, a checklist and logs.

**What the user does in game:**
- In Content Manager, pick the CSP **Traffic** mode. The GUI does the equivalent by writing `__CM_CUSTOM_MODE=traffic` under `[RACE]` and `NAME=Traffic` in `[SESSION_0]` of race.ini (gui/assetto.py:196-203, `_modo`).
- Lower the car count from the default 1000, which jams the area, per the description text.

**Alternative path:**
- Every exported track also carries `extension/vivo.lua` (export_ac.py:373-377).
- Its `trCargar` (vivo_ac.lua:609-650) runs the CSP traffic simulation itself, from a copy in `<track>/extension/trafico`. The copy is made by `trafico_vivo.instalar_simulacion(track, ac)` (trafico_vivo.py:140+), which copies from `extension/lua/tools/csp-traffic-tool` in the AC install (`HERRAMIENTA`, :27).
- That copy step only happens through the GUI (gui/app.py:541, 632) or a vivo seed install (vivo.py:1522). A plain CLI export plus a manual copy will not have it.
- If Traffic mode is active, the script defers to it (`if ac.load('newmode.traffic.active')`, vivo_ac.lua:611-613).
- The in-game settings are `ac.storage({trafico=true, coches=120, cochesPista=0, velocidad=100})` (vivo_ac.lua:598).