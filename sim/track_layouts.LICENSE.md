# Circuit geometry sources

`track_layouts.json` combines the following separately attributed data sources:

- Geographic GP centerlines: Tomislav Bacinger, f1-circuits, MIT. Original data
  and license: `circuit_maps_2026/geographic/`.
- Geographic pit roads: OpenStreetMap contributors, ODbL 1.0. Original query
  responses and attribution: `circuit_maps_2026/osm/`.
- Local width variations: TUMFTM racetrack-database, LGPL-3.0. Original CSVs,
  README, and full license: `circuit_maps_2026/width_reference/`.
- FIA circuit and pit drawings: FIA / Formula One World Championship Limited.
  Original PDFs and source URLs: `circuit_maps_2026/fia_reference_manifest.json`.

Modifications: geographic projection to metres, uniform lap-length calibration,
resampling, small digitizing-noise smoothing, FIA start/control and turn landmark
transfer, pit-road selection, and spatial width matching. Width estimates below
the FIA licensed reference width are suppressed; sections with no useful width
data use the reference width. Detailed boundaries are not surveyed data.

The authoring code and all source files are retained for review and rebuilding.
The third-party data licenses above remain applicable to their derived portions.

Returning circuits added November 2, 2026: Portimão, Istanbul Park and Sepang.
Their source years, OSM way selections and mapping limits are recorded in
`circuit_maps_2026/future/README.md`, `future/geometry_audit.json` and
`future/manifest.json`. They use the same MIT centerline and ODbL pit-road
licenses above. New widths are nominal simulation estimates; 2021 FIA drawings
for Portugal and Türkiye are historical baselines, not 2027 race overlays.
