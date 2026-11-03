# F1 2026 Perpetual 2D Championship & Team Principal Simulator

An always-running, realistic 2D Formula 1 World Championship and Team Principal career simulator built around the **2026 FIA Technical & Sporting Regulations** — zero external dependencies required (`Python 3` standard library backend + High-DPI 60fps HTML5 2D Canvas frontend).

## Quick Start

```powershell
python server.py --port 8080
```

Then open **http://127.0.0.1:8080** in any browser.

## Calendars through 2030 and returning circuits

The game includes 27 circuit maps, adding **Portimão, Istanbul Park and Sepang**.
See the [new-map gallery](circuit_maps_2026/future/index.html) and
[calendar research with sources](circuit_maps_2026/future/README.md).
Season calendars now follow the revised 2026 schedule, the published 2027 order,
and the confirmed Barcelona/Spa rotation through 2030. The game labels 2028 and
later schedules as projections; Portugal is included through its confirmed 2028
deal. Existing careers keep their current season's original schedule and adopt
the changes at the next season. Restart the server and refresh after updating.

## Circuit environments

All 27 circuits use offline geographic scenery: mapped buildings, grandstands,
coastlines, lakes, woodland, landscaped grounds, fields and parking. Regional
vegetation and small ground details fill the surroundings while keeping forests,
city circuits and desert venues distinct. Sources and mapping limits are recorded
in `circuit_maps_2026/scenery/README.md`.

Full object footprints clear every race and pit-road segment using local road
widths, with room for kerbs and pit aprons. A separate scenery mask protects the
road surface, including crossings, and all scenery renders below the cars.
The camera caches scenery between frames; environmental objects do not participate
in race physics. Restart the server and refresh the browser after updating scenery.

## Circuit geometry

The game loads `sim/track_layouts.json`, traced from the downloaded maps in
`circuit_maps_2026/`. Roads retain their shape when the camera fits the circuit;
nearby straights are no longer pushed apart to accommodate inflated asphalt.
Track and pit widths use the same meter scale as the car footprint. Full-circuit
view uses small team-color markers; the follow cameras show the detailed cars.

Pit routes have circuit-specific entry/exit points and shortcuts. Garage markers
and simulated team stops share coordinates, and pit distance is accounted for
when advancing cars through a shortcut. Yas Marina includes an exit-road tunnel
crossing using the downloaded 2025 FIA reference.

The downloaded diagrams are visual references, not surveyed road boundaries.
Widths remain the project's nominal circuit-width estimates, with an 8 m pit
fast-lane/apron model. Separate pit schematics were digitized by hand. Baku,
Austin and Yas Marina retain the existing GPS centerlines where the downloaded
artwork does not supply a usable continuous centerline. Source details and
licenses remain in `circuit_maps_2026/README.md`; derived diagram geometry retains
the corresponding source license. Season-specific calendars select from the
27-circuit library; retired and rotating venues retain their map assets.

After changing geometry, restart `server.py` and refresh the browser. Run the
geometry and complete pit-visit checks with:

```powershell
python -m unittest discover -s tests -v
```

The launch grid has its own start-line position, separate from the timing/finish
line where needed to fit the reference drawing's start straight. Cars, painted
slots and qualifying order share this grid during grid walk and the lights
sequence. The nominal staggered slot pitch is 16 m, following [FIA Article
B5.1.2](https://www.fia.com/system/files/documents/fia_2026_f1_regulations_-_section_b_sporting_-_iss_06_-_2026-04-28.pdf).
Pitch is reduced on the short schematic straights at Monaco, Spa and Las Vegas
so rear slots stay on the start straight. Pole defaults to the outside approach
to Turn 1; circuit specifications can override the side.

- **Always-Running Persistent Server**: The simulation ticks continuously at 20 Hz on the Python server even when all browser tabs are closed, automatically advancing through `Weekend Buildup -> Qualifying -> Starting Grid -> Grand Prix -> Podium -> Next Round -> Off-Season -> Next Season (2026, 2027, 2028...)` and persisting career state to `data/championship_state.json`.
- **Smart Auto-Strategist**: Your AI Race Engineer manages pit windows, mandatory dry tyre compounds, and wet-weather tyre crossovers whenever you are away, while allowing instant manual overrides from the **Pit Wall Console** at any moment.

## Key Features

### 2026 On-Track Physics & Regulations
- **Active Aerodynamics (`STRAIGHT` X-Mode vs `CORNER` Z-Mode)**: All 22 cars flatten front and rear wing elements on designated straights (automatically restricted in heavy rain or braking zones) and snap back to high-downforce Corner Mode at 4.5G braking markers.
- **2026 Overtake Mode (`OVT`)**: Replaces legacy DRS. Any chasing car within **1.000s** at the circuit's **OVT Detection Gate** earns `+0.5 MJ` extra harvest capacity and overrides the standard **290 km/h MGU-K electrical derating curve** all the way up to **355+ km/h** on the following lap.
- **Multi-Lane 2D Wheel-to-Wheel Racing**: Slipstream tow, dirty-air cornering wake, defensive inside-line covering, late-braking lunges, carbon brake glow, floor sparks, lockup smoke, and wet-weather spray.
- **Crashes, Mechanical DNFs & Safety Cars**: Wheel-to-wheel collisions, front-wing endplate damage (requiring `+6.2s` nosecone replacement), spins, sector **Yellow Flags**, **Virtual Safety Car (VSC)** cheap pit windows, and full physical **Safety Car (SC)** pack bunching & restarts.
- **FIA Stewards & Penalty System**: Live `NOTED -> UNDER INVESTIGATION -> VERDICT` pipeline issuing `+5s` / `+10s` time penalties (served stationary in the pit box before mechanics touch the car, or added post-race), Drive-Through penalties, 4-strike Track Limits penalties, Pit Lane speeding/unsafe release penalties, mandatory 2-dry-compound enforcement, and **Super Licence Penalty Points** (`12 pts = automatic 1-Race Ban` with a Reserve Driver subbing in!).

### Full Team Principal Mode
- **Take Command of Any of the 11 Teams**: McLaren, Ferrari, Mercedes, Red Bull, Aston Martin, Williams, Alpine, Racing Bulls, Haas, Audi, or Cadillac.
- **Factory R&D Upgrades**: Invest across 6 departments (`2026 Hybrid PU & MGU-K`, `Active Aero`, `Chassis`, `Suspension`, `Reliability`, and `Pit Crew Robotics`) while rival AI teams develop their cars in parallel.
- **Driver Market, Rival Trades & Buyouts**: Negotiate direct driver swaps + cash packages with rival Team Principals or buy out contracts to sign Free Agents and F2 Academy rookies.
- **Finances, Sponsors & Crash Bills**: Sign commercial partners with finishing-target bonuses, collect FIA Constructors' Championship prize pools, pay driver salaries, and cover carbon-fibre crash repair invoices.

