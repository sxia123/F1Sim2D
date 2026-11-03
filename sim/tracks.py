"""Reference-map circuit geometry for the game calendar, widths and aero zones."""

from __future__ import annotations
import math
import copy
from functools import lru_cache
from sim.car_geometry import client_car_geometry
from sim.track_geometry import WORLD_UNITS_PER_M, GEOMETRY_REVISION, compile_centerline, build_pit_geometry, build_start_grid
from sim.track_environment import get_track_environment

# Official 2026 FIA Formula 1 Calendar including the 6 official 2026 Sprint Rounds:
# Shanghai (R2), Miami (R6), Montreal (R7), Silverstone (R11), Zandvoort (R14), Singapore (R18).
CALENDAR_2026 = [
    {"round": 1, "id": "australia", "name": "Australian Grand Prix", "circuit": "Albert Park Circuit", "city": "Melbourne", "country": "AUS", "length_m": 5278, "race_laps": 22, "sprint_laps": 0, "is_sprint": False, "track_width_m": 12.8, "rain_chance": 0.18, "base_temp_c": 24, "tire_abrasion": 0.95},
    {"round": 2, "id": "china", "name": "Chinese Grand Prix", "circuit": "Shanghai International Circuit", "city": "Shanghai", "country": "CHN", "length_m": 5451, "race_laps": 22, "sprint_laps": 8, "is_sprint": True, "track_width_m": 16.0, "rain_chance": 0.25, "base_temp_c": 21, "tire_abrasion": 1.12},
    {"round": 3, "id": "japan", "name": "Japanese Grand Prix", "circuit": "Suzuka International Racing Course", "city": "Suzuka", "country": "JPN", "length_m": 5807, "race_laps": 21, "sprint_laps": 0, "is_sprint": False, "track_width_m": 13.5, "rain_chance": 0.30, "base_temp_c": 19, "tire_abrasion": 1.18, "has_overpass": True},
    {"round": 4, "id": "bahrain", "name": "Bahrain Grand Prix", "circuit": "Bahrain International Circuit", "city": "Sakhir", "country": "BHR", "length_m": 5412, "race_laps": 22, "sprint_laps": 0, "is_sprint": False, "track_width_m": 15.5, "rain_chance": 0.03, "base_temp_c": 29, "tire_abrasion": 1.25},
    {"round": 5, "id": "saudi", "name": "Saudi Arabian Grand Prix", "circuit": "Jeddah Corniche Circuit", "city": "Jeddah", "country": "KSA", "length_m": 6174, "race_laps": 20, "sprint_laps": 0, "is_sprint": False, "track_width_m": 13.5, "rain_chance": 0.02, "base_temp_c": 30, "tire_abrasion": 0.90},
    {"round": 6, "id": "miami", "name": "Miami Grand Prix", "circuit": "Miami International Autodrome", "city": "Miami", "country": "USA", "length_m": 5412, "race_laps": 22, "sprint_laps": 8, "is_sprint": True, "track_width_m": 14.8, "rain_chance": 0.24, "base_temp_c": 31, "tire_abrasion": 1.00},
    {"round": 7, "id": "canada", "name": "Canadian Grand Prix", "circuit": "Circuit Gilles-Villeneuve", "city": "Montreal", "country": "CAN", "length_m": 4361, "race_laps": 26, "sprint_laps": 10, "is_sprint": True, "track_width_m": 12.2, "rain_chance": 0.34, "base_temp_c": 21, "tire_abrasion": 0.86},
    {"round": 8, "id": "monaco", "name": "Monaco Grand Prix", "circuit": "Circuit de Monaco", "city": "Monte Carlo", "country": "MON", "length_m": 3337, "race_laps": 28, "sprint_laps": 0, "is_sprint": False, "track_width_m": 10.5, "rain_chance": 0.20, "base_temp_c": 23, "tire_abrasion": 0.76},
    {"round": 9, "id": "barcelona", "name": "Barcelona-Catalunya Grand Prix", "circuit": "Circuit de Barcelona-Catalunya", "city": "Barcelona", "country": "ESP", "length_m": 4657, "race_laps": 24, "sprint_laps": 0, "is_sprint": False, "track_width_m": 13.8, "rain_chance": 0.14, "base_temp_c": 26, "tire_abrasion": 1.22},
    {"round": 10, "id": "austria", "name": "Austrian Grand Prix", "circuit": "Red Bull Ring", "city": "Spielberg", "country": "AUT", "length_m": 4326, "race_laps": 26, "sprint_laps": 0, "is_sprint": False, "track_width_m": 13.8, "rain_chance": 0.32, "base_temp_c": 22, "tire_abrasion": 0.98},
    {"round": 11, "id": "britain", "name": "British Grand Prix", "circuit": "Silverstone Circuit", "city": "Silverstone", "country": "GBR", "length_m": 5891, "race_laps": 21, "sprint_laps": 8, "is_sprint": True, "track_width_m": 15.2, "rain_chance": 0.38, "base_temp_c": 19, "tire_abrasion": 1.20},
    {"round": 12, "id": "belgium", "name": "Belgian Grand Prix", "circuit": "Circuit de Spa-Francorchamps", "city": "Spa", "country": "BEL", "length_m": 7004, "race_laps": 18, "sprint_laps": 0, "is_sprint": False, "track_width_m": 14.2, "rain_chance": 0.44, "base_temp_c": 18, "tire_abrasion": 1.15},
    {"round": 13, "id": "hungary", "name": "Hungarian Grand Prix", "circuit": "Hungaroring", "city": "Budapest", "country": "HUN", "length_m": 4381, "race_laps": 25, "sprint_laps": 0, "is_sprint": False, "track_width_m": 12.6, "rain_chance": 0.18, "base_temp_c": 29, "tire_abrasion": 1.05},
    {"round": 14, "id": "netherlands", "name": "Dutch Grand Prix", "circuit": "Circuit Zandvoort", "city": "Zandvoort", "country": "NED", "length_m": 4259, "race_laps": 26, "sprint_laps": 10, "is_sprint": True, "track_width_m": 11.6, "rain_chance": 0.33, "base_temp_c": 20, "tire_abrasion": 1.14},
    {"round": 15, "id": "italy", "name": "Italian Grand Prix", "circuit": "Autodromo Nazionale Monza", "city": "Monza", "country": "ITA", "length_m": 5793, "race_laps": 21, "sprint_laps": 0, "is_sprint": False, "track_width_m": 13.2, "rain_chance": 0.15, "base_temp_c": 26, "tire_abrasion": 0.88},
    {"round": 16, "id": "madrid", "name": "Spanish Grand Prix", "circuit": "Circuito de Madring", "city": "Madrid", "country": "ESP", "length_m": 5414, "race_laps": 22, "sprint_laps": 0, "is_sprint": False, "track_width_m": 13.4, "rain_chance": 0.10, "base_temp_c": 28, "tire_abrasion": 1.04},
    {"round": 17, "id": "azerbaijan", "name": "Azerbaijan Grand Prix", "circuit": "Baku City Circuit", "city": "Baku", "country": "AZE", "length_m": 6003, "race_laps": 20, "sprint_laps": 0, "is_sprint": False, "track_width_m": 13.0, "rain_chance": 0.08, "base_temp_c": 24, "tire_abrasion": 0.85},
    {"round": 18, "id": "singapore", "name": "Singapore Grand Prix", "circuit": "Marina Bay Street Circuit", "city": "Singapore", "country": "SGP", "length_m": 4927, "race_laps": 23, "sprint_laps": 9, "is_sprint": True, "track_width_m": 12.2, "rain_chance": 0.30, "base_temp_c": 30, "tire_abrasion": 0.96},
    {"round": 19, "id": "usa", "name": "United States Grand Prix", "circuit": "Circuit of the Americas", "city": "Austin", "country": "USA", "length_m": 5513, "race_laps": 21, "sprint_laps": 0, "is_sprint": False, "track_width_m": 16.0, "rain_chance": 0.16, "base_temp_c": 27, "tire_abrasion": 1.16},
    {"round": 20, "id": "mexico", "name": "Mexico City Grand Prix", "circuit": "Autodromo Hermanos Rodriguez", "city": "Mexico City", "country": "MEX", "length_m": 4304, "race_laps": 26, "sprint_laps": 0, "is_sprint": False, "track_width_m": 13.4, "rain_chance": 0.18, "base_temp_c": 23, "tire_abrasion": 0.92},
    {"round": 21, "id": "brazil", "name": "Sao Paulo Grand Prix", "circuit": "Autodromo Jose Carlos Pace", "city": "Interlagos", "country": "BRA", "length_m": 4309, "race_laps": 26, "sprint_laps": 0, "is_sprint": False, "track_width_m": 13.8, "rain_chance": 0.42, "base_temp_c": 24, "tire_abrasion": 1.06},
    {"round": 22, "id": "vegas", "name": "Las Vegas Grand Prix", "circuit": "Las Vegas Strip Circuit", "city": "Las Vegas", "country": "USA", "length_m": 6201, "race_laps": 20, "sprint_laps": 0, "is_sprint": False, "track_width_m": 15.0, "rain_chance": 0.04, "base_temp_c": 14, "tire_abrasion": 0.84},
    {"round": 23, "id": "qatar", "name": "Qatar Grand Prix", "circuit": "Lusail International Circuit", "city": "Lusail", "country": "QAT", "length_m": 5419, "race_laps": 22, "sprint_laps": 0, "is_sprint": False, "track_width_m": 15.0, "rain_chance": 0.02, "base_temp_c": 27, "tire_abrasion": 1.28},
    {"round": 24, "id": "abudhabi", "name": "Abu Dhabi Grand Prix", "circuit": "Yas Marina Circuit", "city": "Abu Dhabi", "country": "UAE", "length_m": 5281, "race_laps": 22, "sprint_laps": 0, "is_sprint": False, "track_width_m": 15.0, "rain_chance": 0.02, "base_temp_c": 26, "tire_abrasion": 1.00},
]

class CompiledTrack:
    """Uniformly sampled reference-map centerline and independent pit route."""

    NUM_STATIONS = 960

    def __init__(self, spec: dict):
        self.spec = spec
        self.round = spec["round"]
        self.id = spec["id"]
        self.name = spec["name"]
        self.circuit = spec["circuit"]
        self.city = spec["city"]
        self.country = spec["country"]
        self.length_m = float(spec["length_m"])
        self.race_laps = int(spec["race_laps"])
        self.sprint_laps = int(spec.get("sprint_laps", 0))
        self.is_sprint = bool(spec.get("is_sprint", False))
        self.track_width_m = float(spec.get("track_width_m", 14.0))
        # Use the same meter scale as the road geometry and car footprint.
        self.track_width_px = self.track_width_m * WORLD_UNITS_PER_M
        self.rain_chance = float(spec["rain_chance"])
        self.base_temp_c = float(spec["base_temp_c"])
        self.tire_abrasion = float(spec["tire_abrasion"])
        self.has_overpass = bool(spec.get("has_overpass", False))

        m = self.NUM_STATIONS
        total_canvas_len = compile_centerline(self)

        self.ds_m = self.length_m / m
        self.total_canvas_len = round(total_canvas_len, 2)
        self.px_per_m = total_canvas_len / self.length_m
        canvas_to_m = self.length_m / total_canvas_len

        for k in range(m):
            prev_s = self.stations[(k - 1) % m]
            next_s = self.stations[(k + 1) % m]
            dx = next_s["x"] - prev_s["x"]
            dy = next_s["y"] - prev_s["y"]
            mag = max(math.hypot(dx, dy), 1e-6)
            tx = dx / mag
            ty = dy / mag
            nx = -ty
            ny = tx
            self.stations[k]["tx"] = round(tx, 4)
            self.stations[k]["ty"] = round(ty, 4)
            self.stations[k]["nx"] = round(nx, 4)
            self.stations[k]["ny"] = round(ny, 4)

        self.pit_side = 1  # inferred from the reference pit route below

        raw_curv = []
        for k in range(m):
            s_prev = self.stations[(k - 3) % m]
            s_next = self.stations[(k + 3) % m]
            # Signed apex direction along normal (nx, ny)
            dtx = s_next["tx"] - s_prev["tx"]
            dty = s_next["ty"] - s_prev["ty"]
            apex_dot = dtx * self.stations[k]["nx"] + dty * self.stations[k]["ny"]
            self.stations[k]["inside_sign"] = 1 if apex_dot >= 0 else -1

            a1 = math.atan2(s_prev["ty"], s_prev["tx"])
            a2 = math.atan2(s_next["ty"], s_next["tx"])
            da = (a2 - a1 + math.pi) % (2 * math.pi) - math.pi
            kappa = abs(da) / (6.0 * self.ds_m)
            raw_curv.append(kappa / max(canvas_to_m / 2.8, 0.65))

        smooth_curv = []
        for k in range(m):
            val = (
                raw_curv[(k - 2) % m] * 0.14
                + raw_curv[(k - 1) % m] * 0.24
                + raw_curv[k] * 0.24
                + raw_curv[(k + 1) % m] * 0.24
                + raw_curv[(k + 2) % m] * 0.14
            )
            smooth_curv.append(val)

        max_k = max(smooth_curv) if smooth_curv else 0.02
        target_peak_k = 0.048 if self.id == "monaco" else (0.036 if self.id in ("italy", "saudi", "vegas") else 0.041)
        gamma = 0.72 if self.id in ("monaco", "singapore", "hungary") else 0.82
        for k in range(m):
            c_norm = (smooth_curv[k] / max(max_k, 1e-4)) ** gamma
            c_val = c_norm * target_peak_k
            self.stations[k]["curv"] = round(c_val, 5)
            self.stations[k]["sector"] = 1 if k < m // 3 else (2 if k < (2 * m) // 3 else 3)

        # Ignore small spline/control-point ripples when naming corners. Keep
        # the reference layout's turn count rather than inventing extra turns.
        candidates = [k for k in range(m) if
            self.stations[k]["curv"] >= self.stations[(k-1)%m]["curv"] and
            self.stations[k]["curv"] > self.stations[(k+1)%m]["curv"]]
        candidates.sort(key=lambda k:self.stations[k]["curv"], reverse=True)
        selected = []
        for k in candidates:
            if all(min((k-j)%m,(j-k)%m) >= 5 for j in selected):
                selected.append(k)
            if len(selected) == self.layout["corner_count"]:
                break
        markers = self.layout.get("corner_markers", [])
        if markers:
            selected = [int(round(c["fraction"]*m)) % m for c in markers]
        else:
            selected.sort()
        self.corners = [{"number":i+1,"station":k,"s_m":round(k*self.ds_m,1),
                         "x":self.stations[k]["x"],"y":self.stations[k]["y"],
                         "sector":self.stations[k]["sector"]}
                        for i,k in enumerate(selected)]

        low_thresh = 0.0044 if self.id not in ("monaco", "singapore") else 0.0034
        is_low = [self.stations[k]["curv"] < low_thresh for k in range(m)]
        straight_mode = [False] * m
        for start in range(m):
            if is_low[start] and not is_low[(start - 1) % m]:
                run = []
                idx = start
                while is_low[idx] and len(run) < m:
                    run.append(idx)
                    idx = (idx + 1) % m
                run_len_m = len(run) * self.ds_m
                if run_len_m >= 260.0 and len(run) > 8:
                    trim_start = 2
                    trim_end = max(3, int(90.0 / self.ds_m))
                    for sub_i in run[trim_start : max(trim_start, len(run) - trim_end)]:
                        straight_mode[sub_i] = True

        if not any(straight_mode):
            for sub_i in range(4, min(36, m // 8)):
                straight_mode[sub_i] = True

        for k in range(m):
            self.stations[k]["straight_mode"] = straight_mode[k]

        self.overpass_station: int | None = None
        if self.has_overpass:
            best_d = 999.0
            for i in range(20, m - 20):
                for j in range(i + 80, min(m, i + m - 80)):
                    d = math.hypot(self.stations[i]["x"] - self.stations[j]["x"], self.stations[i]["y"] - self.stations[j]["y"])
                    if d < best_d:
                        best_d = d
                        self.overpass_station = j

        # Multi-DRS Zones Generation from circuit straights
        drs_runs = []
        visited = [False] * m
        for i in range(m):
            if straight_mode[i] and not visited[i]:
                run = []
                curr = i
                while straight_mode[curr] and not visited[curr]:
                    visited[curr] = True
                    run.append(curr)
                    curr = (curr + 1) % m
                if len(run) * self.ds_m >= 130.0:
                    drs_runs.append(run)

        if not drs_runs:
            drs_runs = [[int(m * 0.05), int(m * 0.15)]]

        # Select up to top 3-4 major DRS straights
        drs_runs.sort(key=lambda r: len(r), reverse=True)
        selected_runs = drs_runs[:4]
        selected_runs.sort(key=lambda r: r[0])

        self.drs_zones: list[dict] = []
        for z_idx, r in enumerate(selected_runs):
            act_station = r[0]
            end_station = r[-1]
            det_station = (act_station - max(4, int(110.0 / self.ds_m))) % m
            self.drs_zones.append(
                {
                    "id": z_idx + 1,
                    "detection_station": det_station,
                    "detection_s_m": round(det_station * self.ds_m, 1),
                    "activation_station": act_station,
                    "activation_s_m": round(act_station * self.ds_m, 1),
                    "end_station": end_station,
                    "end_s_m": round(end_station * self.ds_m, 1),
                    "length_m": round(len(r) * self.ds_m, 1),
                }
            )

        self.detection_station = self.drs_zones[0]["detection_station"]
        self.detection_s_m = self.drs_zones[0]["detection_s_m"]
        build_pit_geometry(self)

        # Build ultra-smooth continuous geometric racing line (outside entry -> apex kerb -> exit kerb)
        if self.corners:
            n_c = len(self.corners)
            waypoints: list[tuple[float, float]] = []
            for i in range(n_c):
                c_cur = self.corners[i]
                c_prev = self.corners[(i - 1) % n_c]
                c_next = self.corners[(i + 1) % n_c]

                k_cur = c_cur["station"]
                ins_cur = self.stations[k_cur]["inside_sign"]

                d_prev = (k_cur - c_prev["station"]) % m
                d_next = (c_next["station"] - k_cur) % m

                # Apex is clipped tightly on the inside kerb
                waypoints.append((float(k_cur), 0.58 * ins_cur))

                # Wide outside setup on entry if coming off a straight
                if d_prev >= 18:
                    lead = min(d_prev * 0.35, 12.0)
                    k_entry = (k_cur - lead) % m
                    waypoints.append((float(k_entry), -0.60 * ins_cur))

                # Wide outside track-out on exit if heading onto a straight
                if d_next >= 18:
                    trail = min(d_next * 0.35, 12.0)
                    k_exit = (k_cur + trail) % m
                    waypoints.append((float(k_exit), -0.60 * ins_cur))

            waypoints.sort(key=lambda wp: wp[0])
            n_wp = len(waypoints)

            raw_line = [0.0] * m
            for k in range(m):
                target_s = float(k)
                idx = n_wp - 1
                for i in range(n_wp):
                    s_curr = waypoints[i][0]
                    s_nxt = waypoints[(i + 1) % n_wp][0]
                    if s_curr <= s_nxt:
                        if s_curr <= target_s < s_nxt:
                            idx = i
                            break
                    else:
                        if target_s >= s_curr or target_s < s_nxt:
                            idx = i
                            break

                w0 = waypoints[(idx - 1) % n_wp]
                w1 = waypoints[idx]
                w2 = waypoints[(idx + 1) % n_wp]
                w3 = waypoints[(idx + 2) % n_wp]

                span = (w2[0] - w1[0]) % m
                if span < 1e-4:
                    raw_line[k] = w1[1]
                    continue
                rel = (target_s - w1[0]) % m
                t = min(1.0, max(0.0, rel / span))

                h00 = (1.0 + 2.0 * t) * (1.0 - t) ** 2
                h10 = t * (1.0 - t) ** 2
                h01 = (t ** 2) * (3.0 - 2.0 * t)
                h11 = (t ** 2) * (t - 1.0)

                span_prev = max((w1[0] - w0[0]) % m, 1.0)
                span_next = max((w3[0] - w2[0]) % m, 1.0)
                m1 = 0.5 * (w2[1] - w0[1]) * (span / (span + span_prev)) * 2.0
                m2 = 0.5 * (w3[1] - w1[1]) * (span / (span + span_next)) * 2.0
                raw_line[k] = h00 * w1[1] + h10 * m1 + h01 * w2[1] + h11 * m2

            # 18-pass Laplacian smoothing for whisper-quiet C2 continuity
            cur_line = list(raw_line)
            for _ in range(18):
                nxt_line = list(cur_line)
                for k in range(m):
                    p = cur_line[(k - 1) % m]
                    c = cur_line[k]
                    n = cur_line[(k + 1) % m]
                    nxt_line[k] = 0.25 * p + 0.50 * c + 0.25 * n
                cur_line = nxt_line

            for k in range(m):
                self.stations[k]["racing_line_d"] = round(max(-0.66, min(0.66, cur_line[k])), 4)
        else:
            for k in range(m):
                self.stations[k]["racing_line_d"] = 0.0

        build_start_grid(self)

    def width_px_at(self,s_m:float) -> float:
        f=(s_m%self.length_m)/self.ds_m
        i=int(f)%self.NUM_STATIONS;t=f-int(f)
        return self.stations[i]['width_px']*(1-t)+self.stations[(i+1)%self.NUM_STATIONS]['width_px']*t

    def lateral_to_px(self, d: float, s_m:float|None=None) -> float:
        width=self.track_width_px if s_m is None else self.width_px_at(s_m)
        half_usable = width * 0.39
        abs_d = abs(d)
        if abs_d <= 1.0:
            return d * half_usable
        pit_center_px = width * 0.5 + 11.0
        sign = 1.0 if d >= 0.0 else -1.0
        return sign * (half_usable + (abs_d - 1.0) * (pit_center_px - half_usable))

    def sample_pit(self, s_m: float) -> dict:
        rel_s = (s_m - self.pit_entry_s) % self.length_m
        u = max(0.0, min(1.0, rel_s / max(self.pit_span_m, 1.0)))
        n_pit = len(self.pit_stations) - 1
        f = u * n_pit
        i0 = min(n_pit - 1, int(f))
        t = f - i0
        a = self.pit_stations[i0]
        b = self.pit_stations[i0 + 1]
        tx = a["tx"] + (b["tx"] - a["tx"]) * t
        ty = a["ty"] + (b["ty"] - a["ty"]) * t
        mag = max(math.hypot(tx, ty), 1e-6)
        return {
            "x": a["x"] + (b["x"] - a["x"]) * t,
            "y": a["y"] + (b["y"] - a["y"]) * t,
            "tx": tx / mag,
            "ty": ty / mag,
        }

    def sample(self, s_m: float) -> dict:
        s_wrapped = s_m % self.length_m
        f = (s_wrapped / self.length_m) * self.NUM_STATIONS
        i0 = int(f) % self.NUM_STATIONS
        i1 = (i0 + 1) % self.NUM_STATIONS
        t = f - int(f)
        a = self.stations[i0]
        b = self.stations[i1]
        return {
            "x": a["x"] + (b["x"] - a["x"]) * t,
            "y": a["y"] + (b["y"] - a["y"]) * t,
            "tx": a["tx"] + (b["tx"] - a["tx"]) * t,
            "ty": a["ty"] + (b["ty"] - a["ty"]) * t,
            "nx": a["nx"] + (b["nx"] - a["nx"]) * t,
            "ny": a["ny"] + (b["ny"] - a["ny"]) * t,
            "curv": a["curv"] + (b["curv"] - a["curv"]) * t,
            "straight_mode": a["straight_mode"],
            "inside_sign": a["inside_sign"],
            "racing_line_d": a.get("racing_line_d", 0.0) + (b.get("racing_line_d", 0.0) - a.get("racing_line_d", 0.0)) * t,
            "sector": a["sector"],
            "station": i0,
            "width_m":a['width_m']+(b['width_m']-a['width_m'])*t,
            "width_px":a['width_px']+(b['width_px']-a['width_px'])*t,
        }

    def nearest_corner(self, s_m: float) -> int:
        if not self.corners:
            return 1
        s_w = s_m % self.length_m
        best_num = 1
        best_dist = 1e9
        for c in self.corners:
            d = abs(c["s_m"] - s_w)
            d = min(d, self.length_m - d)
            if d < best_dist:
                best_dist = d
                best_num = c["number"]
        return best_num

    def to_client_payload(self) -> dict:
        return {
            "round": self.round,
            "id": self.id,
            "name": self.name,
            "circuit": self.circuit,
            "city": self.city,
            "country": self.country,
            "length_m": self.length_m,
            "race_laps": self.race_laps,
            "sprint_laps": self.sprint_laps,
            "is_sprint": self.is_sprint,
            "track_width_m": self.track_width_m,
            "track_width_px": self.track_width_px,
            "px_per_m": round(self.px_per_m, 4),
            "car_geometry":client_car_geometry(),
            "rain_chance": self.rain_chance,
            "base_temp_c": self.base_temp_c,
            "tire_abrasion": self.tire_abrasion,
            "pit_side": self.pit_side,
            "has_overpass": self.has_overpass,
            "overpass_station": self.overpass_station,
            "detection_station": self.detection_station,
            "detection_s_m": self.detection_s_m,
            "drs_zones": self.drs_zones,
            "pit_entry_s": self.pit_entry_s,
            "pit_box_s": self.pit_box_s,
            "pit_exit_s": self.pit_exit_s,
            "pit_exit_blend_s": self.pit_exit_blend_s,
            "pit_entry_blend_points": self.pit_entry_blend_line,
            "pit_blend_points": self.pit_blend_line,
            "racing_line_points": [
                [
                    round(self.stations[k]["x"] + self.stations[k]["nx"] * self.lateral_to_px(self.stations[k].get("racing_line_d", 0.0),k*self.ds_m), 1),
                    round(self.stations[k]["y"] + self.stations[k]["ny"] * self.lateral_to_px(self.stations[k].get("racing_line_d", 0.0),k*self.ds_m), 1),
                ]
                for k in range(self.NUM_STATIONS)
            ],
            "pit_points": [[round(p["x"], 2), round(p["y"], 2)] for p in self.pit_stations],
            "pit_width_px": self.pit_width_px,
            "pit_length_m": round(self.pit_length_m, 2),
            "pit_garages": self.pit_garages,
            "pit_speed_entry_u": self.pit_speed_entry_u,
            "pit_speed_exit_u": self.pit_speed_exit_u,
            "pit_tunnel_u": self.pit_tunnel_u,
            "bounds": self.bounds,
            "geometry_source": self.geometry_source,
            "geometry_revision":GEOMETRY_REVISION,
            "reference_year":self.layout.get('reference_year'),
            "width_note":self.layout.get('width_note'),
            "grid_boxes": self.grid_boxes,
            "start_line": self.start_line,
            "start_line_s": self.start_line_s,
            "grid_spacing_m": self.grid_spacing_m,
            "grid_pole_side": self.grid_pole_side,
            "corners": self.corners,
            "stations": self.stations,
            "environment": get_track_environment(self),
        }


# The original calendar remains a compatibility baseline for existing careers.
# COMPILED_TRACKS is the asset library, not the season's race order.
RETURNING_CIRCUITS = [
    {"round": 0, "id": "portugal", "name": "Portuguese Grand Prix", "circuit": "Autodromo Internacional do Algarve", "city": "Portimao", "country": "POR", "length_m": 4653, "race_laps": 24, "sprint_laps": 0, "is_sprint": False, "track_width_m": 14.0, "rain_chance": 0.16, "base_temp_c": 25, "tire_abrasion": 1.12},
    {"round": 0, "id": "turkey", "name": "Turkish Grand Prix", "circuit": "Istanbul Park", "city": "Istanbul", "country": "TUR", "length_m": 5338, "race_laps": 22, "sprint_laps": 0, "is_sprint": False, "track_width_m": 14.0, "rain_chance": 0.24, "base_temp_c": 21, "tire_abrasion": 1.22},
    {"round": 0, "id": "malaysia", "name": "Bahrain Grand Prix in Malaysia", "circuit": "Sepang International Circuit", "city": "Sepang", "country": "MAL", "length_m": 5543, "race_laps": 22, "sprint_laps": 0, "is_sprint": False, "track_width_m": 16.0, "rain_chance": 0.48, "base_temp_c": 31, "tire_abrasion": 1.20},
]
COMPILED_TRACKS: list[CompiledTrack] = [CompiledTrack(spec) for spec in CALENDAR_2026 + RETURNING_CIRCUITS]
TRACK_BY_ID = {t.id: t for t in COMPILED_TRACKS}
TRACK_BY_ROUND: dict[int, CompiledTrack] = {t.round: t for t in COMPILED_TRACKS if t.round}

ORDER_2026 = 'australia china japan miami canada monaco barcelona austria britain belgium hungary netherlands italy madrid azerbaijan malaysia singapore usa mexico brazil vegas qatar abudhabi'.split()
ORDER_2027 = 'bahrain saudi australia japan china miami canada monaco portugal britain austria belgium hungary italy madrid azerbaijan turkey singapore usa mexico brazil vegas qatar abudhabi'.split()
SPRINTS_2027 = set('bahrain australia japan canada monaco britain italy brazil qatar abudhabi'.split())

def calendar_status(year: int, legacy: bool = False) -> dict:
    if legacy:
        return {'status':'legacy', 'note':'Original 24-round schedule retained for this saved season. Calendar changes apply next season.', 'checked_on':'2026-11-02'}
    if year <= 2027:
        return {'status':'confirmed', 'note':f'Published {max(2026, year)} calendar; race lengths are shortened for the game.', 'checked_on':'2026-11-02'}
    return {'status':'projection', 'note':'Game schedule based on confirmed venue agreements, not a published full calendar. Order and Sprints follow 2027; Barcelona/Spa rotate. Portugal is included only through its confirmed 2028 deal. Later renewals and replacements remain unknown.', 'checked_on':'2026-11-02'}

@lru_cache(maxsize=12)
def get_season_tracks(year: int, legacy: bool = False) -> tuple[CompiledTrack, ...]:
    """Season-specific metadata sharing immutable, already compiled road geometry."""
    if legacy:
        order=[s['id'] for s in CALENDAR_2026]
    elif year <= 2026:
        order=ORDER_2026
    else:
        order=ORDER_2027[:]
        if year >= 2028:
            # Confirmed rotations through 2032; repeat the 2030 pattern later
            # as a game fallback, never as a newly confirmed real calendar.
            if year % 2 == 0:
                order[order.index('belgium')]='barcelona'
            if year > 2028:
                order.remove('portugal')
    tracks=[]
    for rnd, tid in enumerate(order, 1):
        track=copy.copy(TRACK_BY_ID[tid])
        spec={**track.spec, 'round':rnd}
        if not legacy and year >= 2027:
            spec['is_sprint']=tid in SPRINTS_2027
            spec['sprint_laps']=max(6,round(40000/track.length_m)) if spec['is_sprint'] else 0
        track.spec=spec
        for key in ('round','is_sprint','sprint_laps'):
            setattr(track,key,spec[key])
        tracks.append(track)
    return tuple(tracks)
