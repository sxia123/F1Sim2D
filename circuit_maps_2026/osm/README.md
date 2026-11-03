# Geographic pit-road references

Portimão, Istanbul Park and Sepang were added on November 2, 2026. Their selected
pit ways are in `../future/geometry_audit.json`; support/karting/alternate pit
roads were excluded. Existing source responses remain unchanged.

Copyright OpenStreetMap contributors. Downloaded through the Overpass API on
2026-11-01. Original query responses are retained here; their `osm3s` metadata
records the database timestamp. Data is available under the Open Database
License: https://www.openstreetmap.org/copyright

The selected way IDs are recorded in `../geometry_audit.json` and in each baked
layout. Some circuits have separate support or karting pit lanes; these were
excluded explicitly. The Albert Park pit road is a service road outside race
weekends. Shanghai's pit road is an unnamed raceway.

Shanghai's F1 entry includes connector **107371147** from the T15–T16 approach,
followed by garage/exit road **107371138**. The latter's first node is an infield
junction; snapping that junction directly to the nearest GP station incorrectly
creates an entry from the back straight. The corrected selection is checked
against the retained 2026 FIA circuit and pit-lane drawings. Rebuild only this
pit route with `scratch/fix_shanghai_pit_entry.py`.
