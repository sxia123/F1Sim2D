# F1 calendar changes through 2030

Checked **November 2, 2026** against Formula 1 and FIA announcements. The game now
contains **27 playable circuit assets**, including three new maps: Portimão,
Istanbul Park and Sepang. Open [the map gallery](index.html) for game previews,
pit-road views, source overlays and the season-by-season circuit lists.

## Confirmed changes

| Season | Arrivals / returns | Departures / rotation |
| --- | --- | --- |
| 2026 | Madrid debuts. Sepang hosts the Bahrain GP in Malaysia as a one-off relocation. | Imola is absent. Sakhir and Jeddah are absent from the revised 2026 calendar. |
| 2027 | Portimão and Istanbul Park return. Sakhir and Jeddah return on the published calendar. | Zandvoort leaves after its final 2026 race. Barcelona rotates out; Sepang has no recurring agreement established by these sources. |
| 2028 | Barcelona returns; Portimão's two-year agreement covers this season. | Spa sits out under its rotation agreement. |
| 2029 | Spa returns under its agreement. | Barcelona sits out. Portugal's status beyond 2028 is unconfirmed, rather than a confirmed departure. |
| 2030 | Barcelona returns under its agreement. Istanbul Park's agreement continues through 2031. | Spa sits out. No complete 2030 race schedule is claimed here. |

Madrid already had a playable map in this project. Zandvoort, Spa and Barcelona
remain in the asset library even when absent from a season.

## Confirmed calendars versus game projections

The 2026 schedule uses the current 23-race calendar. The 2027 schedule uses the
published 24-race order and ten Sprint venues. Existing race lengths remain
shortened for gameplay.

Full 2028–30 schedules and Sprint assignments are not published in the sources
used here. The game carries forward the 2027 order and Sprint choices, applies
the confirmed Barcelona/Spa rotation, and includes Portugal only through its
confirmed 2028 agreement. This produces 24 races in 2028 and 23 known-venue races
in 2029–30; the missing future slot is not filled with an invented replacement.
Other retained venues are a game continuity assumption, not a guarantee that
every contract lasts through 2030. The calendar panel labels these schedules as
projections. Beyond 2030 the same rules continue as a game fallback.

Qiddiya is a planned successor to Jeddah, with 2028 discussed as a target. A
construction target is not an approved F1 calendar. This update retains Jeddah
until a firm switch can be verified. Thailand is a bid, not an established race
in these sources. Rwanda has a newly announced deal for the **early 2030s**,
without a specific inaugural season; it is not assigned to 2030. None of these
unfixed events receives fabricated race geometry or a guaranteed season slot.

## Sources

- [Current official 2026 calendar](https://www.formula1.com/en/racing/2026)
- [Published 2027 calendar](https://www.formula1.com/en/racing/2027)
- [2027 announcement and ten Sprint venues, September 16, 2026](https://www.formula1.com/en/latest/article/formula1-reveals-calendar-for-2027-season-with-10-sprint-events.5J8ePLyjRuMyWEIDNUKgY4)
- [Portugal: 2027 and 2028, December 16, 2025](https://www.formula1.com/en/latest/article/formula-1-to-return-portugal-in-2027-and-2028.6kRRgAnvEoGiOkJMkzp1Cr)
- [Türkiye: 2027–31, April 24, 2026](https://www.formula1.com/en/latest/article/formula-1-returns-turkeys-istanbul-park-from-2027-as-part-of-new-five-year-agreement.1I7OZGeDPoC6Vysv3iqadY.1I7OZGeDPoC6Vysv3iqadY)
- [Barcelona/Spa rotation, February 16, 2026](https://www.formula1.com/en/latest/article/f1-announces-multi-year-extension-with-the-circuit-de-barcelona-catalunya-to.34PBcnuzB9vYVzFIwdEgf4)
- [Sepang relocation, July 26, 2026](https://www.formula1.com/en/latest/article/formula-1-and-fia-confirm-malaysia-will-join-2026-calendar-as-host-venue-for-bahrain-grand-prix.6lL7vjFEM2VVynRHvg1TCf)
- [Qiddiya timing remains uncertain, circuit contract overview](https://www.skysports.com/f1/news/12538/13535466/f1-track-contracts-how-long-does-each-circuit-have-a-deal-for-on-future-formula-1-calendars)
- [Thailand: ongoing talks](https://www.skysports.com/f1/news/13328101/formula-1-chief-stefano-domenicali-reveals-thailand-visit-as-talks-over-possible-bangkok-race-continue)
- [Rwanda: early 2030s announcement, October 13, 2026](https://www.formula1.com/en/latest/article/formula-1-returns-to-africa-with-10-year-agreement-to-race-in-rwanda.13xs9VMK7cGFiBd2IplyES.13xs9VMK7cGFiBd2IplyES)

## Map sources and limits

The three new maps preserve the aspect ratios of the retained Tomislav Bacinger
geographic centerlines (MIT). Pit roads come from OpenStreetMap contributors
(ODbL 1.0), downloaded November 2, 2026; selected way IDs are in
`geometry_audit.json` and each baked layout. Scenery uses separately retained
OSM footprints and land cover. The game requires no network or additional
runtime packages.

Portimão and Istanbul Park use **2021 FIA drawings as historical baselines**;
future 2027 start/control landmarks and event facilities are not yet verified.
Sepang uses the retained 2026 FIA drawing. FIA / Formula One World Championship
Limited retain copyright in those drawings. New map widths are nominal constant
estimates (14 m at Portimão and Istanbul, 16 m at Sepang), not surveyed boundary
measurements. Garage allocations, aero/OVT zones and pit speed markers remain
simulation placements. Turkey's pole side is a baseline assumption.

Rebuild geometry with `python scratch/build_future_layouts.py` using the same
authoring dependencies as the existing geographic pipeline. Existing layouts
are left intact. `python scratch/build_track_layouts.py` rebuilds both groups.
Regenerate the previews with `scratch/preview_future_maps.py`,
`scratch/check_map_renderer.cjs` and `scratch/publish_future_review.py`.

## Existing careers

Saves written before this update retain the original 24-round order for their
current season. They switch to the new season-specific rules on the next season
rollover. Fresh 2026 and 2028 careers use their corresponding updated schedule.
The existing career file is not rewritten by the map build or tests. Restart the
game server and refresh the browser to load the update.
