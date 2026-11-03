# F1 2026 Perpetual 2D Championship & Team Principal Simulator

An always-running, realistic 2D Formula 1 World Championship and Team Principal career simulator built around the **2026 FIA Technical & Sporting Regulations** — zero external dependencies required (`Python 3` standard library backend + High-DPI 60fps HTML5 2D Canvas frontend).

---

## Table of Contents

- [Quick Start](#quick-start)
- [Key Features](#key-features)
  - [2026 On-Track Physics & Regulations](#2026-on-track-physics--regulations)
  - [Full Team Principal Mode](#full-team-principal-mode)
  - [Hall of Fame & Multi-Season Archive](#hall-of-fame--multi-season-archive)
  - [Broadcast Camera System & Controls](#broadcast-camera-system--controls)
  - [Engineered Smoothness & Architecture](#engineered-smoothness--architecture)
- [Calendars Through 2030 & Returning Circuits](#calendars-through-2030--returning-circuits)
- [Circuit Environments & Scenery](#circuit-environments--scenery)
- [Circuit Geometry & Pit Routes](#circuit-geometry--pit-routes)
- [Project Architecture](#project-architecture)
- [Running Tests](#running-tests)
- [License](#license)

---

## Quick Start

1. Start the simulation server:
   ```bash
   python server.py --host 127.0.0.1 --port 8080
   ```

2. Open **[http://127.0.0.1:8080](http://127.0.0.1:8080)** in any modern web browser.

The server immediately starts broadcasting live 20 Hz telemetry and physics. No Node.js, build steps, or pip packages are needed.

---

## Key Features

### 2026 On-Track Physics & Regulations

- **Active Aerodynamics (`STRAIGHT` X-Mode vs `CORNER` Z-Mode)**:
  All 22 cars flatten front and rear wing elements along designated straightaways (automatically inhibited in heavy rain or braking zones) and snap back to high-downforce Corner Mode at 4.5G braking markers.
- **2026 Overtake Mode (`OVT`)**:
  Replaces legacy DRS. Any chasing car within **1.000s** at the circuit's **OVT Detection Gate** gains `+0.5 MJ` extra harvest capacity and overrides the standard **290 km/h MGU-K electrical derating curve** up to **355+ km/h** on the subsequent lap.
- **Realistic Slipstream & Tow Dynamics**:
  Tow benefits require close trailing proximity directly behind an opponent with realistic wake falloff and dirty-air cornering penalties.
  Faster cars use available pace and closing speed to leave the tow, check both sides for traffic, and hold a passing lane until fully clear. Their actual speed advantage determines whether the straight-line pass succeeds.
- **Authentic Overtaking Maneuvers**:
  AI drivers execute contextual maneuvers matching track layout: late-braking divebombs into heavy braking hairpins, switchbacks on corner exits, dummy moves, and outside sweeps.
- **Multi-Compound Tyre Model & Deg**:
  Pirelli Soft, Medium, Hard, Intermediate, and Wet compounds with distinct thermal windows, degradation curves, and crossover points. Starting compounds can be manually selected during the pre-race Grid Walk.
- **Incidents, Damage & Safety Cars**:
  Wheel-to-wheel collisions, carbon fiber front-wing breakage (requiring `+6.2s` nosecone replacements), punctures, engine failures, yellow flag sectors, Virtual Safety Car (VSC), and full physical Safety Car (SC) pack bunching and restarts.
- **FIA Stewards & Penalty System**:
  Live `NOTED -> UNDER INVESTIGATION -> VERDICT` pipeline issuing `+5s` / `+10s` time penalties (served stationary in the pit box or added post-race), Drive-Through penalties, 4-strike Track Limits penalties, and Super Licence Penalty Points (`12 pts = automatic 1-Race Ban` with a reserve driver subbing in).
- **Situational Team Radio**:
  Dynamic contextual radio messages triggered by overtakes, safety cars, weather transitions, damage, pit windows, and race finishes. Each team and driver features distinct personalities and dialogue.

### Full Team Principal Mode

- **Take Command of Any of the 11 Teams**:
  McLaren, Ferrari, Mercedes, Red Bull, Aston Martin, Williams, Alpine, Racing Bulls, Haas, Audi, or Cadillac.
- **Factory R&D Upgrades**:
  Invest budget across 6 departments (`2026 Hybrid PU & MGU-K`, `Active Aero`, `Chassis`, `Suspension`, `Reliability`, and `Pit Crew Robotics`) while rival AI teams develop their machinery in parallel.
- **Driver Market & Rival Trades**:
  Negotiate driver swaps + cash packages with rival Team Principals, sign free agents, or promote rookies.
- **Finances & Sponsors**:
  Sign commercial partners with performance milestone bonuses, collect FIA Constructors' Championship prize money, manage driver salaries, and cover carbon-fibre crash repair invoices.
- **Live Pit Wall Console**:
  Issue tactical orders in real time: Pace Mode (`PUSH`, `BALANCED`, `CONSERVE`), ERS Mode (`OVERTAKE`, `BALANCED`, `HARVEST`), Team Orders, Box This Lap, and Tyre Selection. An autonomous AI Race Engineer manages strategy whenever you are away.

### Hall of Fame & Multi-Season Archive

The interactive **Hall of Fame** tab archives all completed seasons from 2026 through 2030+:
- **Season Selector**: Seamlessly inspect championship standings across 2026, 2027, 2028, 2029, and 2030.
- **Champions Banner**: Highlights the World Drivers' Champion, runner-up, and World Constructors' Champion with total points, wins, and podium counts.
- **Race-by-Race Summary**: Comprehensive calendar table showing the circuit, winner, pole-sitter, fastest lap, podium finishers, and total finishers for every Grand Prix and Sprint.
- **Expandable Classification Drawers**: Click **View Top 10 Classification** on any round to review the full finishing order, intervals, race times, points earned, and tyre compounds used.

### Broadcast Camera System & Controls

Choose between 5 broadcast camera modes via the top control bar:
- **CIRCUIT MAP**: Full overhead circuit overview with smooth track auto-centering.
- **LEADER**: Centers rigidly on the current race leader.
- **BATTLE CAM**: Automatically detects wheel-to-wheel battles across the field, framing both combatants at their midpoint with dynamic zoom and stability locking.
- **TEAM FEED**: Tracks your team's lead car.
- **ONBOARD / SELECTED**: Locks smoothly onto any selected driver on the grid.

**Interactive Navigation**:
- **Zoom**: Mouse wheel zooming from `0.4x` (wide landscape) to `6.5x` (tight cockpit view).
- **Pan**: Click and drag across the canvas to pan freely in manual camera mode.
- **Select Driver**: Click any car on track or click any row in the Timing Tower to focus telemetry and camera onto that driver.

### Engineered Smoothness & Architecture

- **Catmull-Rom Cubic Spline Interpolation**:
  Replaces straight-line chord interpolation with $C^1$-continuous Catmull-Rom cubic splines. Cars glide through curved corners with zero polygon kinks.
- **Direct Rock-Solid Camera Locking**:
  Eliminates spring-lag and velocity-lead shudder. When tracking a car, the vehicle remains centered while the circuit scrolls past with fluid sub-pixel continuity.
- **Tick-Based Phase-Locked Loop (PLL)**:
  Maintains a stable playback cushion decoupled from network delivery timing, adapting playback rate by $\pm 4\%$ max to guarantee continuous frame-to-frame flow.
- **High-Resolution 1ms Windows Timer**:
  Invokes `timeBeginPeriod(1)` on Windows, ensuring `time.sleep` executes with 1ms granularity.
- **Fixed-Timestep Physics Loop**:
  Simulation physics ticks at a deterministic `0.050s` (20 Hz), preventing step-time variance and eliminating speed-up/slow-down jitter.
- **Full-Circuit Scenery Pre-Caching**:
  Offscreen canvas rasterizes the entire circuit bounds once upon loading, using zero CPU/GPU overhead during racing.

---

## Calendars Through 2030 & Returning Circuits

The game includes **27 circuit maps**, adding classic venues: **Portimão, Istanbul Park, and Sepang**.
- Revised 2026 schedule, published 2027 order, and confirmed Barcelona/Spa rotation through 2030.
- Portugal is included through its confirmed 2028 deal.
- Existing careers preserve their current season's schedule and seamlessly adopt revisions at the subsequent season transition.
- Persistent championship state is saved to `data/championship_state.json`.

---

## Circuit Environments & Scenery

All 27 circuits feature offline geographic scenery:
- Mapped architectural buildings, grandstands, coastlines, lakes, woodland, landscaped grounds, fields, and parking areas.
- Regional vegetation and contextual ground details distinguish parkland, street venues, and desert tracks.
- Full object footprints clear race and pit-road segments using local road widths, with room for kerbs and aprons.
- A dedicated road mask protects the asphalt surface, including crossing points.

---

## Circuit Geometry & Pit Routes

Circuit layouts are defined in `sim/track_layouts.json`:
- Road ribbons maintain true shape without artificial separation.
- Track and pit widths use the same meter scale as the car geometry.
- Circuit-specific pit lane entries, exits, speed limits, and garage stalls with constructor liveries and logos.
- Yas Marina includes an authentic exit-road tunnel crossing.
- Launch grids feature authentic staggered slot pitch (nominal 16 m, adhering to FIA Article B5.1.2) tailored to fit short straights like Monaco and Las Vegas.

---

## Project Architecture

```
F1Sim2D/
├── server.py              # High-precision 20 Hz HTTP & SSE simulation server
├── sim/                   # Core simulation engine
│   ├── physics.py         # 2D vehicle dynamics, active aero, overtake mode, collisions
│   ├── championship.py    # Multi-season championship state machine & team principal logic
│   ├── tracks.py          # Circuit models, telemetry stations, DRS/OVT zones
│   ├── hall_of_fame.py    # Historical season archives and race classifications
│   ├── radio.py           # Context-sensitive team radio dispatcher
│   └── radio_messages.py  # Driver and race engineer dialogue database
├── public/                # Zero-dependency frontend
│   ├── index.html         # Broadcast layout & telemetry dashboard
│   ├── canvas.js          # High-DPI 60fps canvas renderer & camera system
│   ├── scenery.js         # Geographic scenery caching layer
│   ├── app.js             # SSE state management & DOM bindings
│   ├── styles.css         # F1 broadcast visual theme
│   └── logos.js           # Constructor livery SVG assets
├── data/                  # Persistent career saves and circuit assets
└── tests/                 # Unit and integration test suites
```

---

## Running Tests

Run the complete test suite using Python's standard library `unittest`:

```bash
python -m unittest discover tests
```

To run individual test modules:
```bash
python -m unittest tests/test_timing.py
python -m unittest tests/test_radio.py
python -m unittest tests/test_wheel_to_wheel.py
```

---

## License

This project is open-source software provided under the MIT License. Circuit layout references and trademarks belong to their respective rights holders.
