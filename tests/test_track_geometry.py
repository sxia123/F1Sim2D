"""Geometry integration checks against the baked reference-map routes."""
import math
import random
import unittest

from sim.data import clone_initial_roster
from sim.physics import RaceSession, enforce_2d_car_separation, _sat_obb_penetration
from sim.tracks import COMPILED_TRACKS
from sim.track_geometry import LAYOUTS, WORLD_UNITS_PER_M


class TrackGeometryTests(unittest.TestCase):
    def test_reference_routes_and_width_scale(self):
        self.assertEqual({t.id for t in COMPILED_TRACKS}, set(LAYOUTS))
        for t in COMPILED_TRACKS:
            with self.subTest(track=t.id):
                self.assertAlmostEqual(t.track_width_px/t.track_width_m, WORLD_UNITS_PER_M)
                self.assertAlmostEqual(t.px_per_m, WORLD_UNITS_PER_M)
                for p in t.stations+t.pit_stations:
                    self.assertTrue(all(math.isfinite(v) for v in p.values()))
                self.assertGreater(t.pit_span_m, 0)
                self.assertLess(t.pit_span_m, t.length_m*.5)
                self.assertEqual(len(t.pit_garages),11)
                for g in t.pit_garages:
                    self.assertLess((g['s_m']-t.pit_entry_s)%t.length_m,t.pit_span_m)
                self.assertEqual(t.to_client_payload()['pit_garages'],t.pit_garages)

    def test_pit_joins_share_racing_coordinates(self):
        for t in COMPILED_TRACKS:
            with self.subTest(track=t.id):
                a=t.sample(t.pit_entry_s);b=t.sample_pit(t.pit_entry_s)
                self.assertLess(math.hypot(a['x']-b['x'],a['y']-b['y']),.01)
                a=t.sample(t.pit_exit_s);b=t.sample_pit(t.pit_exit_s)
                offset=t.lateral_to_px(.76*t.pit_side,t.pit_exit_s)
                self.assertLess(math.hypot(a['x']+a['nx']*offset-b['x'],a['y']+a['ny']*offset-b['y']),.01)

    def test_complete_pit_visits_on_every_circuit(self):
        teams,drivers=clone_initial_roster()
        teams={t['id']:t for t in teams}
        driver=next(d for d in drivers if d.get('team_id'))
        for t in COMPILED_TRACKS:
            with self.subTest(track=t.id):
                random.seed(7)
                race=RaceSession(t,teams,[driver],0,.1,driver['team_id'])
                race.flag_state='GREEN';race.lights_out=True
                c=race.cars[0]
                c.s=t.pit_entry_s-1;c.total_dist=c.s;c.v=30
                c.box_this_lap=True;c.auto_strategy=False;c.d=.42*t.pit_side
                race._update_xy(c)
                before=(c.x,c.y)
                race._step_car(c,None,c,False,.05,lambda *_:None)
                race._update_xy(c)
                self.assertTrue(c.in_pits)
                self.assertLess(math.dist(before,(c.x,c.y)),15)
                max_jump=0
                for _ in range(5000):
                    if not c.in_pits:break
                    before=(c.x,c.y)
                    race._step_pit_lane(c,False,.05,lambda *_:None)
                    race._update_xy(c)
                    max_jump=max(max_jump,math.dist(before,(c.x,c.y)))
                    race.race_clock+=.05
                self.assertFalse(c.in_pits,'Pit visit did not complete')
                self.assertEqual(c.pit_stops,1)
                self.assertTrue(c.pit_blend_active)
                self.assertLess(max_jump,20,'Discontinuous pit movement')
                self.assertAlmostEqual(c.d,.76*t.pit_side)

    def test_shanghai_pit_split_is_after_turn_15_and_not_on_the_back_straight(self):
        t=next(t for t in COMPILED_TRACKS if t.id=='china')
        turns={c['number']:c['fraction'] for c in t.layout['corner_markers']}
        self.assertGreater(t.pit_entry_s/t.length_m,turns[15])
        self.assertLess(t.pit_entry_s/t.length_m,turns[16])
        self.assertIn('107371147',t.layout['pit_reference'])
        back_straight=t.stations[int(.65*t.NUM_STATIONS):int(.875*t.NUM_STATIONS)]
        distance=min(math.hypot(p['x']-s['x'],p['y']-s['y'])
                     for p in t.pit_stations[:90] for s in back_straight)
        self.assertGreater(distance,t.track_width_px,'Pit entry must not cut across the back straight')
        entry=t.sample(t.pit_entry_s);pit=t.pit_stations[0]
        self.assertGreater(entry['tx']*pit['tx']+entry['ty']*pit['ty'],.94)

        teams,drivers=clone_initial_roster()
        driver=next(d for d in drivers if d.get('team_id'))
        race=RaceSession(t,{team['id']:team for team in teams},[driver],0,.1,driver['team_id'])
        race.flag_state='GREEN';race.lights_out=True
        car=race.cars[0]
        car.s=t.length_m*.80325-1;car.total_dist=car.s;car.v=45
        car.box_this_lap=True;car.auto_strategy=False
        race._update_xy(car)
        race._step_car(car,None,car,False,.1,lambda *_:None)
        self.assertFalse(car.in_pits,'A box call must not take the old back-straight shortcut')

    def test_yas_tunnel_crossing_does_not_move_surface_traffic(self):
        t=next(t for t in COMPILED_TRACKS if t.id=='abudhabi')
        teams,drivers=clone_initial_roster()
        drivers=[d for d in drivers if d.get('team_id')][:2]
        race=RaceSession(t,{v['id']:v for v in teams},drivers,0,.1,'williams')
        pit,surface=race.cars
        # The tunnel is traced from the geographic way. Its geometric midpoint
        # need not be the crossing; select the actual closest surface crossing.
        lo,hi=t.pit_tunnel_u
        def distance(u):
            p=t.sample_pit((t.pit_entry_s+u*t.pit_span_m)%t.length_m)
            return min((p['x']-s['x'])**2+(p['y']-s['y'])**2 for s in t.stations)
        u=min((lo+(hi-lo)*i/100 for i in range(101)),key=distance)
        pit.s=(t.pit_entry_s+u*t.pit_span_m)%t.length_m
        pit.total_dist=pit.s;pit.in_pits=True;pit.pit_phase='EXIT';pit.pit_apron=0
        race._update_xy(pit)
        k=min(range(t.NUM_STATIONS),key=lambda k:(t.stations[k]['x']-pit.x)**2+(t.stations[k]['y']-pit.y)**2)
        surface.s=k*t.ds_m;surface.total_dist=surface.s;surface.d=0
        race._update_xy(surface)
        self.assertIsNotNone(_sat_obb_penetration(pit,surface),'Test must overlap in the 2D projection')
        before=(surface.s,surface.d,pit.s)
        enforce_2d_car_separation(t,race.cars,True,race._update_xy)
        self.assertEqual((surface.s,surface.d,pit.s),before)

    def test_pit_lane_is_two_cars_wide_and_clear_of_track(self):
        from sim.car_geometry import CAR_WID_PX
        from sim.track_geometry import WORLD_UNITS_PER_M
        from sim.tracks import COMPILED_TRACKS

        two_car_px = 2.0 * CAR_WID_PX
        for t in COMPILED_TRACKS:
            # 1. Pit road width and un-occluded fast-lane corridor outside stall boxes must fit >= 2 cars side-by-side
            self.assertGreaterEqual(t.pit_width_px, two_car_px * 2.0, t.id)
            stall_inner_edge = t.pit_apron_offset_px - 3.76
            fast_outer_edge = -t.pit_width_px * 0.5
            fast_clear_px = stall_inner_edge - fast_outer_edge
            self.assertGreaterEqual(fast_clear_px, two_car_px + 4.0, f"{t.id} fast lane {fast_clear_px:.2f}px")

            # 2. Working garage corridor (outside tunnels) must stay clear of main track asphalt so >= 2 cars fit visually & physically
            glo, ghi = t.layout.get("garage_u_range", [0.275, 0.725])
            n_st = len(t.pit_stations)
            for idx, st in enumerate(t.pit_stations):
                u = idx / max(1, n_st - 1)
                if u < glo or u > ghi:
                    continue
                if t.pit_tunnel_u and t.pit_tunnel_u[0] <= u <= t.pit_tunnel_u[1]:
                    continue
                near = min(t.stations, key=lambda s: (s["x"] - st["x"]) ** 2 + (s["y"] - st["y"]) ** 2)
                edge_gap = math.hypot(st["x"] - near["x"], st["y"] - near["y"]) - near["width_px"] * 0.5
                unoccluded = min(t.pit_width_px, edge_gap + t.pit_width_px * 0.5)
                self.assertGreaterEqual(
                    unoccluded,
                    two_car_px + 4.0,
                    f"{t.id} working pit occluded to {unoccluded:.2f}px at u={u:.3f}",
                )
            self.assertGreater(t.pit_exit_blend_dist_m, 50.0 / WORLD_UNITS_PER_M, t.id)

    def test_pit_exit_release_and_blend_are_smooth(self):
        from sim.data import clone_initial_roster
        from sim.physics import RaceSession
        from sim.track_geometry import WORLD_UNITS_PER_M
        from sim.tracks import COMPILED_TRACKS

        teams, all_drivers = clone_initial_roster()
        teams_by_id = {t["id"]: t for t in teams}
        drivers = [d for d in all_drivers if d.get("team_id") in teams_by_id]
        by_id = {t.id: t for t in COMPILED_TRACKS}

        for tid in ("australia", "bahrain", "china", "hungary", "monaco", "vegas", "abudhabi"):
            t = by_id[tid]
            race = RaceSession(t, teams_by_id, drivers, 0.0, 0.0, "williams")
            race.lights_out = True
            race.lights_countdown = 0.0
            race.flag_state = "GREEN"
            car = race.cars[0]
            for other in race.cars[1:]:
                other.dnf = True
                other.v = 0.0

            box_s = race._team_pit_box_s(car)
            L = t.length_m
            car.s = box_s
            car.total_dist = L + box_s
            car.lap = 2
            car.pit_stops = 1
            car.in_pits = True
            car.pit_phase = "STOPPED"
            car.pit_timer = 0.1
            car.pit_apron = 1.0
            car.v = 0.0
            car.d = 0.0
            car.target_d = 0.0
            race._update_xy(car)

            dt = 0.05
            prev_x, prev_y, prev_h = car.x, car.y, car.heading
            prev_in_pits = True
            prev_phase = "STOPPED"
            prev_d = car.d
            saw_release_gradual = False
            saw_exit = False
            exit_dh_deg = None
            max_blend_lat_v = 0.0
            half_u_m = t.track_width_px * 0.39 / WORLD_UNITS_PER_M

            for _ in range(1200):
                race.step(dt, lambda *a: None)
                if prev_phase == "STOPPED" and car.pit_phase == "EXIT":
                    # Must smoothly pull out of stall rather than snapping pit_apron 1.0 -> 0.0 immediately
                    self.assertGreater(car.pit_apron, 0.5, f"{tid} apron snapped on release")
                    saw_release_gradual = True

                dh = abs(math.degrees((car.heading - prev_h + math.pi) % (2.0 * math.pi) - math.pi))
                if prev_in_pits and not car.in_pits:
                    saw_exit = True
                    exit_dh_deg = dh
                    step_px = math.hypot(car.x - prev_x, car.y - prev_y)
                    self.assertLess(step_px, 6.5, f"{tid} position jump {step_px:.2f}px at exit")
                elif saw_exit and car.pit_blend_active:
                    lat_v = abs(car.d - prev_d) * half_u_m / dt
                    max_blend_lat_v = max(max_blend_lat_v, lat_v)

                prev_x, prev_y, prev_h = car.x, car.y, car.heading
                prev_in_pits = car.in_pits
                prev_phase = car.pit_phase
                prev_d = car.d
                if saw_exit and not car.pit_blend_active:
                    break

            self.assertTrue(saw_release_gradual, f"{tid} did not gradually leave stall")
            self.assertTrue(saw_exit, f"{tid} did not exit pits")
            self.assertFalse(car.pit_blend_active, f"{tid} pit blend did not complete")
            self.assertIsNotNone(exit_dh_deg)
            self.assertLess(exit_dh_deg, 6.0, f"{tid} heading kink {exit_dh_deg:.2f} deg at exit")
            self.assertLessEqual(max_blend_lat_v, 3.05, f"{tid} abrupt blend lat_v {max_blend_lat_v:.2f} m/s")

    def test_pit_exit_blend_yields_to_fast_on_track_traffic(self):
        from sim.data import clone_initial_roster
        from sim.physics import RaceSession, _pit_exit_blend_target
        from sim.tracks import COMPILED_TRACKS

        teams, all_drivers = clone_initial_roster()
        teams_by_id = {t["id"]: t for t in teams}
        drivers = [d for d in all_drivers if d.get("team_id") in teams_by_id]
        t = next(tr for tr in COMPILED_TRACKS if tr.id == "australia")
        race = RaceSession(t, teams_by_id, drivers, 0.0, 0.0, "williams")
        exiting, traffic = race.cars[0], race.cars[1]
        for o in race.cars[2:]:
            o.dnf = True
        exiting.in_pits = False
        exiting.pit_blend_active = True
        exiting._pit_blend_u = 0.25
        exiting.s = (t.pit_exit_s + 30.0) % t.length_m
        exiting.v = 32.0
        exiting.d = 0.70 * t.pit_side
        traffic.in_pits = False
        traffic.dnf = False
        traffic.s = (exiting.s - 10.0) % t.length_m
        traffic.v = 65.0
        traffic.d = 0.40 * t.pit_side

        tgt = _pit_exit_blend_target(t, exiting, -0.66 * t.pit_side, race.cars)
        self.assertEqual(exiting._pit_blend_u, 0.25)
        self.assertAlmostEqual(tgt, (1.0 - (0.25 ** 2 * (3.0 - 2.0 * 0.25))) * (0.76 * t.pit_side) + (0.25 ** 2 * (3.0 - 2.0 * 0.25)) * (-0.66 * t.pit_side))

    def test_pit_entry_reference_fidelity_runoff_zones_and_smooth_racing_line(self):
        from sim.data import clone_initial_roster
        from sim.physics import RaceSession

        def point_to_polyline_dist(px: float, py: float, poly: list[tuple[float, float]]) -> float:
            best = 1e9
            for (x1, y1), (x2, y2) in zip(poly, poly[1:]):
                dx, dy = x2 - x1, y2 - y1
                seg_sq = dx * dx + dy * dy
                t_u = 0.0 if seg_sq <= 1e-9 else max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / seg_sq))
                d = math.hypot(px - (x1 + t_u * dx), py - (y1 + t_u * dy))
                if d < best:
                    best = d
            return best

        by_id = {t.id: t for t in COMPILED_TRACKS}
        for t in COMPILED_TRACKS:
            with self.subTest(track=t.id):
                self.assertEqual(len(t.pit_entry_blend_line), 25)
                self.assertEqual(t.to_client_payload()["pit_entry_blend_points"], t.pit_entry_blend_line)
                for pt in t.pit_entry_blend_line:
                    self.assertTrue(all(math.isfinite(v) for v in pt))
                rl = [st["racing_line_d"] for st in t.stations]
                n = len(rl)
                max_d1 = max(abs(rl[(k + 1) % n] - rl[k]) for k in range(n))
                max_d2 = max(abs(rl[(k + 1) % n] - 2.0 * rl[k] + rl[(k - 1) % n]) for k in range(n))
                self.assertLessEqual(max_d1, 0.11, f"{t.id} steep racing_line_d slope {max_d1:.4f}")
                self.assertLessEqual(max_d2, 0.035, f"{t.id} sharp racing_line_d accel {max_d2:.4f}")

        self.assertTrue(all(z["surface"] != "gravel" for z in by_id["monaco"].runoff_zones))
        for perm_id in ("australia", "britain", "italy", "japan", "belgium"):
            zones = by_id[perm_id].runoff_zones
            self.assertGreater(len(zones), 0, f"{perm_id} missing runoff_zones")
            self.assertTrue(any(z["surface"] == "gravel" for z in zones), f"{perm_id} missing gravel runoff")

        for tid in ("azerbaijan", "usa", "australia", "britain"):
            t = by_id[tid]
            raw_pts = [((x - 500) * t.map_scale + 500, (y - 325) * t.map_scale + 325) for x, y in t.layout["pit_points"]]
            max_dev = max(point_to_polyline_dist(p["x"], p["y"], raw_pts) for p in t.pit_stations[5:26])
            self.assertLessEqual(max_dev, 6.5, f"{tid} pit entry strayed {max_dev:.2f}px from reference map")

        teams, drivers = clone_initial_roster()
        teams_by_id = {tm["id"]: tm for tm in teams}
        for tid in ("azerbaijan", "usa", "australia", "monaco"):
            t = by_id[tid]
            race = RaceSession(t, teams_by_id, drivers[:1], 0.0, 0.0, drivers[0]["team_id"])
            race.lights_out = True
            race.lights_countdown = 0.0
            race.flag_state = "GREEN"
            car = race.cars[0]
            L = t.length_m
            car.s = (t.pit_entry_s - 125.0) % L
            car.total_dist = L + car.s
            car.lap = 2
            car.v = 72.0
            car.box_this_lap = True
            car.auto_strategy = False
            car.d = -0.35 * t.pit_side
            car.target_d = car.d
            race._update_xy(car)

            peeled = False
            entered = False
            min_v_before_entry = car.v
            prev_x, prev_y = car.x, car.y
            for _ in range(180):
                was_in_pits = car.in_pits
                v_before = car.v
                race.step(0.05, lambda *_: None)
                if not car.in_pits:
                    min_v_before_entry = min(min_v_before_entry, car.v)
                    if abs(car.target_d - 0.72 * t.pit_side) < 0.25:
                        peeled = True
                elif not was_in_pits:
                    entered = True
                    jump_px = math.hypot(car.x - prev_x, car.y - prev_y)
                    max_allowed_px = max(4.5, v_before * 0.05 * t.px_per_m + 1.5)
                    self.assertLessEqual(jump_px, max_allowed_px, f"{tid} pit entry jump {jump_px:.2f}px")
                    break
                prev_x, prev_y = car.x, car.y

            self.assertTrue(peeled, f"{tid} car never peeled toward pit entry lane")
            self.assertTrue(entered, f"{tid} car did not enter pit lane")
            self.assertLess(min_v_before_entry, 48.0, f"{tid} car did not brake smoothly for pit entry")


if __name__=='__main__':unittest.main()
