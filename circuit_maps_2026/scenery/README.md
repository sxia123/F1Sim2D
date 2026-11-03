# Circuit scenery sources

Portimão, Istanbul Park and Sepang were added on November 2, 2026 using the same
licenses and projection below. Portimão uses nine retained OSM map-API tiles;
Istanbul and Sepang use retained Overpass responses.

Copyright © OpenStreetMap contributors, licensed under the
[Open Database License (ODbL 1.0)](https://www.openstreetmap.org/copyright).

The original public map responses were downloaded on November 1, 2026 (US
Eastern time; response timestamps use UTC). The JSON responses retain their
database timestamps. The tiled `.xml` extracts retain original element versions
and timestamps. Sources: `https://overpass-api.de/api/interpreter`,
`https://maps.mail.ru/osm/tools/overpass/api/interpreter`, and
`https://api.openstreetmap.org/api/0.6/map`.

`sim/scenery_maps.json` is a derived geographic database under ODbL. Modifications:
north-up projection into the same metre-based reference frame as circuit layouts,
relation-ring assembly with inner holes, footprint classification and polygon
simplification. The runtime applies the circuit's uniform world scale, clips large
land-cover polygons to the view region and removes buildings intersecting race or
pit clearances. Directed coastlines close only at the scene boundary.

Land cover, coastlines, water and buildings are mapped features. Individual tree
canopies, ground tufts, spectator rows, roof details and yachts are illustrative.
Mapping can be incomplete, especially for temporary event facilities and active
construction at Madrid. This is an illustrated geographic environment, not a
survey or a representation of all race-weekend installations. No invented lake is
placed inside Interlagos; Miami's dry decorative marina is not treated as a sea.
Structures crossing above the roadway are omitted to keep cars visible.

Authoring (standard-library Python):

```powershell
python scratch/build_scenery_maps.py
# Optional downloads, cached once rather than requested by the game:
python scratch/build_scenery_maps.py --fetch
python scratch/fetch_scenery_tiles.py australia china vegas qatar
```

Runtime generation uses only the Python standard library and requires no network.
Rebuild the offline visual review with `python scratch/build_scenery_preview.py`.
Open `scratch/scenery_standalone.html` to inspect all circuits and a close view.

Jeddah has an additional 1,000 m map-extract margin, retained as
`saudi_margin1000_tile_*.xml`. Its mapped streets, pedestrian/cycle promenades
and marina piers are stored as `linear_features` in the derived database.
The Red Sea continues across the full camera width. Palm planting, berthed
yachts and floodlight halos are illustrative additions checked against race
and pit-road clearance; the coastline and local landmark footprints are mapped.
Rebuild this extract with:

```powershell
python scratch/fetch_scenery_tiles.py saudi --margin-m 1000
```
