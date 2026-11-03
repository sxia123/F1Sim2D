# 2026 F1 circuit maps and pit lanes

**November 2, 2026 update:** [New-map gallery and calendars through 2030](future/index.html).
Portimão, Istanbul Park and Sepang are now playable, bringing the asset library
to 27 circuits. [Confirmed changes, sources and projection limits](future/README.md).
The sections below describe the original 24-map rebuild and source archive.

## Updated game geometry

Open **[accuracy_review.html](accuracy_review.html)** for the rebuilt game maps,
official circuit/pit references, starting-grid previews and width-source notes.
The original downloaded gallery below remains available as a source archive.

All 24 game layouts now use geographic centerlines and independent geographic
pit roads, checked against FIA drawings. Aspect ratios are preserved. Start and
control lines are separate reference landmarks. The grid uses 8 m between
consecutive staggered slots and 16 m within each column; start lines are never
moved or grids compressed to fit an inaccurate drawing.

The added `fia_reference/` PDFs cover all 24 game circuits: 18 from 2026 and six
2025 baselines. `fia_reference_manifest.json` records exact sources and years.
The FIA licensed-circuit registers supply pole sides and reference widths;
explicitly labelled pit drawings provide additional pole-side checks.

Fourteen circuits use local satellite-derived width variation from TUMFTM,
matched only to unchanged roadway and bounded by the FIA reference width.
Circuits without useful local widths use the FIA reference value. Madrid's width
and pole side remain assumptions pending better published data. These are
reference-matched maps, not survey-precision models. Pit speed markers, garage
allocations, kerbs and aero/OVT zones retain simulation approximations.

`geographic/`, `osm/` and `width_reference/` retain source data and licenses.
`geometry_audit.json` records final per-track dimensions and remaining limits.
The authoring entry point is `scratch/build_geographic_layouts.py`; it requires
NumPy, SciPy, Pillow and the retained reference-registration files. The game
runtime still uses only the Python standard library. Attribution is also in
`sim/track_layouts.LICENSE.md`.

## Original map archive

Open **index.html** to browse all 25 circuit reference sets offline.

- `svg/`: downloaded, unmodified scalable circuit diagrams. For Australia, Miami, Montreal and Zandvoort these are supplementary outlines; use the FIA files for the pit lane.
- `fia_pdf/`: six official circuit-map and pit-lane documents for Australia, Miami, Montreal, Zandvoort, Yas Marina and Sepang.
- `png/`: white-background SVG previews and rendered FIA circuit/pit-lane pages.
- `manifest.json`: per-circuit file paths, source links, scope, source dates, licenses and SVG checksums.
- `source_metadata.json`: the original Wikimedia image metadata response.
- `contact_sheet.png`: one overview per circuit.

## Calendar and editions

Coverage is the union of the originally announced 24-round calendar used by this project and the current 23-venue calendar checked on October 31, 2026: 25 different circuits. Sepang is included; Sakhir and Jeddah are retained as original-calendar extras. File numbering follows the original project calendar, not the revised race round numbers.

Calendar sources: [announced calendar](https://www.formula1.com/en/latest/article/formula-1-reveals-calendar-for-2026-season.YctbMZWqBvrgyddrnauo8), [current calendar](https://www.formula1.com/en/racing/2026).

Yas Marina uses the **2025 official FIA map and pit-lane drawing**, a previous-season baseline ahead of the 2026 event. Wikimedia diagrams have different original publication years; their source filenames are preserved in the manifest. They are visual layout references, not guaranteed 2026 race-control overlays. Historical DRS/sector labels on some diagrams should not be used as 2026 regulations data.

Barcelona uses the 14-turn layout without the final chicane. Madrid uses the 2026 Madring diagram. SVG pit-lane branches may be thin, gray, blue or unlabelled: zoom in around the start/finish straight. For the six FIA documents, the dedicated pit-lane page is also provided as a PNG and linked in the gallery.

## Sources and attribution

SVG originals are unmodified. PNG previews are rendered from those originals with a white background. FIA PDFs are unmodified; their circuit-map and pit-lane pages are also rendered as PNGs. Each source retains its own license and copyright notice.

| Circuit | Author / credit | License | Source |
| --- | --- | --- | --- |
| Albert Park Circuit | ごひょううべこ | CC BY-SA 4.0 | [Source](https://commons.wikimedia.org/wiki/File:2022_F1_CourseLayout_Australia.svg) |
| Shanghai International Circuit | Will Pittenger | CC BY-SA 3.0 | [Source](https://commons.wikimedia.org/wiki/File:Shanghai_International_Racing_Circuit_track_map.svg) |
| Suzuka Circuit | Will Pittenger | CC BY-SA 3.0 | [Source](https://commons.wikimedia.org/wiki/File:Suzuka_circuit_map--2005.svg) |
| Bahrain International Circuit | Will Pittenger | CC BY-SA 3.0 | [Source](https://commons.wikimedia.org/wiki/File:Bahrain_International_Circuit--Grand_Prix_Layout.svg) |
| Jeddah Corniche Circuit | GabrielStella | CC BY-SA 3.0 | [Source](https://commons.wikimedia.org/wiki/File:Jeddah_Street_Circuit_2021.svg) |
| Miami International Autodrome | ごひょううべこ | CC BY-SA 4.0 | [Source](https://commons.wikimedia.org/wiki/File:2022_F1_CourseLayout_Miami.svg) |
| Circuit Gilles Villeneuve | ごひょううべこ | CC BY-SA 4.0 | [Source](https://commons.wikimedia.org/wiki/File:2022_F1_CourseLayout_Canada.svg) |
| Circuit de Monaco | Will Pittenger | CC BY-SA 3.0 | [Source](https://commons.wikimedia.org/wiki/File:Monte_Carlo_Formula_1_track_map.svg) |
| Circuit de Barcelona-Catalunya | Formula1 Circuit Catalunya.svg: Will Pittenger derivative work: HorsePunchKid, Cs-wolves, Sentoan, Gpmat | CC BY-SA 3.0 | [Source](https://commons.wikimedia.org/wiki/File:Circuit_de_Catalunya_moto_2021.svg) |
| Red Bull Ring | I, User:HumanBodyPiloter5, created this SVG map as a derivative work based on the satellite image of the Spielberg circuit released by w:en:Planet Labs under CC-BY-SA 4.0 in 2018 | CC BY-SA 4.0 | [Source](https://commons.wikimedia.org/wiki/File:Spielberg_bare_map_numbers_contextless_2021_corner_names.svg) |
| Silverstone Circuit | AlexJ | CC0 | [Source](https://commons.wikimedia.org/wiki/File:Circuit_Silverstone_2011.svg) |
| Circuit de Spa-Francorchamps | Will Pittenger | CC BY-SA 3.0 | [Source](https://commons.wikimedia.org/wiki/File:Spa-Francorchamps_of_Belgium.svg) |
| Hungaroring | PhilipTheLeftist | CC0 | [Source](https://commons.wikimedia.org/wiki/File:Hungaroring2026.svg) |
| Circuit Zandvoort | ごひょううべこ | CC BY-SA 4.0 | [Source](https://commons.wikimedia.org/wiki/File:2022_F1_CourseLayout_Netherlands.svg) |
| Monza Circuit | Will Pittenger | CC BY-SA 3.0 | [Source](https://commons.wikimedia.org/wiki/File:Monza_track_map.svg) |
| Madring | GabrielStella, Cherkash | CC BY-SA 3.0 | [Source](https://commons.wikimedia.org/wiki/File:Madring_(2026).svg) |
| Baku City Circuit | HumanBodyPiloter5 | CC0 | [Source](https://commons.wikimedia.org/wiki/File:Baku_Formula_One_circuit_map.svg) |
| Marina Bay Street Circuit | Cherkash | CC BY-SA 4.0 | [Source](https://commons.wikimedia.org/wiki/File:Marina_Bay_circuit_2023.svg) |
| Circuit of the Americas | Gustavo GirardelliOwn work This W3C-unspecified vector image was created with Inkscape . | CC BY-SA 2.0 | [Source](https://commons.wikimedia.org/wiki/File:Austin_circuit.svg) |
| Autódromo Hermanos Rodríguez | Pitlane02 | CC BY-SA 3.0 | [Source](https://commons.wikimedia.org/wiki/File:Aut%C3%B3dromo_Hermanos_Rodr%C3%ADguez_2015.svg) |
| Interlagos Circuit | Will Pittenger | CC BY-SA 3.0 | [Source](https://commons.wikimedia.org/wiki/File:Aut%C3%B3dromo_Jos%C3%A9_Carlos_Pace_(AKA_Interlagos)_track_map.svg) |
| Las Vegas Strip Circuit | Valentin JJ. | CC BY-SA 4.0 | [Source](https://commons.wikimedia.org/wiki/File:2023_Las_Vegas_street_circuit.svg) |
| Lusail International Circuit | Losail.svg: Will Pittenger derivative work: Gpmat | CC BY-SA 3.0 | [Source](https://commons.wikimedia.org/wiki/File:Lusail_International_Circuit_2023.svg) |
| Yas Marina Circuit | FIA / Formula One World Championship Limited | All rights reserved (FIA reference) | [Source](https://www.fia.com/system/files/decision-document/2025_abu_dhabi_grand_prix_-_event_notes_-_circuit_map_pit_lane_drawing_emergency_exits_map_quarantine_zone_and_red_zones.pdf) |
| Sepang International Circuit | FIA / Formula One World Championship Limited | All rights reserved (FIA reference) | [Source](https://www.fia.com/system/files/decision-document/2026_bahrain_grand_prix_in_malaysia_-_competition_notes_-_circuit_map_pit_lane_drawing_emergency_exits_map_and_red_zone.pdf) |
