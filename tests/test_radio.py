"""Radio claims must match the triggering event and the current driver/team."""
import random
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from sim.championship import ChampionshipWorld
from sim.data import INITIAL_DRIVERS, INITIAL_TEAMS
from sim.physics import RaceSession
from sim.radio import RadioDispatcher
from sim.radio_messages import DRIVER_RADIOS, GENERIC_RADIOS, TEAM_RADIOS
from sim.tracks import COMPILED_TRACKS


def car(driver_id="hamilton", team_id="ferrari", **changes):
    values = dict(driver_id=driver_id, team_id=team_id, team_short=team_id.title(),
                  number=44, code=driver_id[:3].upper(), compound="MEDIUM",
                  next_compound="HARD", dnf=False, finished=False, in_pits=False,
                  tailing_timer=5.0, blue_flag=False, s=100.0, v=60.0, lap=2,
                  spin_timer=0.0, last_radio_time=-99.0)
    values.update(changes)
    return SimpleNamespace(**values)


class RadioTests(unittest.TestCase):
    def setUp(self):
        self.rng_state = random.getstate()
        random.seed(75)
        self.addCleanup(random.setstate, self.rng_state)
        self.dispatcher = RadioDispatcher()
        self.events = []
        self.cb = lambda kind, message: self.events.append((kind, message))
        self.track = SimpleNamespace(length_m=5000.0, nearest_corner=lambda _: 4)

    @property
    def message(self):
        self.assertEqual(self.events[-1][0], "RADIO")
        return self.events[-1][1]

    def test_sc_and_vsc_never_announce_the_other_mode(self):
        for mode in ("SC", "VSC"):
            for _ in range(20):
                self.dispatcher.trigger_safety_car(mode, "debris", self.cb, cars=[car()])
                if mode == "SC":
                    self.assertIn("Safety Car", self.message)
                    self.assertNotIn("Virtual", self.message)
                    self.assertNotIn("VSC", self.message)
                else:
                    self.assertIn("VSC", self.message)
                    self.assertNotIn("bunch", self.message)
        self.dispatcher.trigger_safety_car("SC", "debris", self.cb)
        self.assertTrue(self.message.startswith("RACE CONTROL:"))

    def test_weather_reports_actual_rain_and_surface_conditions(self):
        for rain, wetness, expected in ((.5, .02, "rain"), (.5, .6, "wet"),
                                       (0, .6, "still wet"), (0, .05, "drying")):
            for _ in range(10):
                self.dispatcher = RadioDispatcher()
                self.dispatcher.trigger_weather_transition(rain, wetness, self.cb, 50, [car()], self.track)
                self.assertIn(expected, self.message.lower())
                self.assertNotIn("inters", self.message.lower())
                self.assertNotIn("minutes", self.message.lower())
                if rain:
                    self.assertNotIn("drying", self.message)

    def test_losing_a_clean_position_does_not_invent_an_incident(self):
        for driver_id in DRIVER_RADIOS:
            for index in range(8):
                self.dispatcher.trigger_overtaken(car(driver_id), car("norris"), 4, self.cb, index * 20 + 20)
                text = self.message.lower()
                self.assertNotIn("drs", text)
                self.assertNotIn("battery", text)
                self.assertNotIn("forced", text)
                self.assertNotIn("weav", text)
                self.assertNotIn("steward", text)
        self.dispatcher.trigger_overtaken(car(), car("norris"), 4, self.cb, 1000, maneuver="DIVEBOMB")
        self.assertIn("long way back", self.message)

    def test_taking_the_lead_has_no_car_ahead_to_hunt(self):
        self.dispatcher.trigger_overtake_success(car(), car("norris"), 1, 4, self.cb, 20)
        self.assertIn("lead", self.message.lower())
        self.assertNotIn("next", self.message.lower())

    def test_fastest_lap_reports_measured_time_without_inventing_sector_or_margin(self):
        for _ in range(10):
            self.dispatcher.trigger_fastest_lap(car(), "1:23.456", self.cb)
            self.assertIn("1:23.456", self.message)
            self.assertNotIn("sector", self.message.lower())
            self.assertNotIn("tenths", self.message.lower())

    def test_pit_calls_use_selected_tyres_and_do_not_assume_dead_tyres(self):
        for _ in range(15):
            self.dispatcher.trigger_box_call(car(next_compound="INTER"), self.cb)
            self.assertIn("INTER", self.message)
            self.assertNotIn("dead", self.message.lower())
        self.dispatcher.trigger_box_call(car(drive_through_pending=True), self.cb)
        self.assertIn("drive-through", self.message)
        self.assertNotIn("HARD", self.message)

    def test_slow_pit_stop_is_not_called_a_clean_or_good_stop(self):
        for _ in range(10):
            self.dispatcher.trigger_pit_exit(car(), 14.23, self.cb)
            self.assertIn("14.2s", self.message)
            self.assertIn("MEDIUM", self.message)
            for claim in ("clean stop", "good stop", "clear", "secured"):
                self.assertNotIn(claim, self.message.lower())

    def test_contact_does_not_invent_damage_or_assign_blame(self):
        for index in range(15):
            self.dispatcher.trigger_contact(car(), car("norris"), 4, self.cb, 20 + index * 10)
            self.assertTrue("contact" in self.message.lower() or "touched" in self.message.lower())
            body = self.message.split(": '", 1)[1].lower()
            for claim in ("damaged", "puncture", "turned", "wall", "-15%"):
                self.assertNotIn(claim, body)

    def test_damage_type_is_respected(self):
        for kind, expected in (("PUNCTURE", "puncture"), ("FRONT_WING", "front wing"), ("FLOOR", "damage")):
            self.dispatcher = RadioDispatcher()
            self.dispatcher.trigger_damage(car(), kind, 4, self.cb, 20)
            self.assertIn(expected, self.message.lower())
            if kind != "FRONT_WING":
                self.assertNotIn("wing", self.message.lower())

    def test_hamilton_tyre_message_has_no_assumed_engineer(self):
        for _ in range(10):
            self.dispatcher = RadioDispatcher()
            self.dispatcher.trigger_tyre_cliff(car(), self.cb, 20)
            self.assertNotIn("Bono", self.message)

    def test_team_voices_follow_current_employer_after_driver_transfer(self):
        transferred = car("hamilton", "mclaren", team_short="McLaren")
        # Select the last available pool/line: this deliberately exercises team voices.
        with patch("sim.radio.random.choice", side_effect=lambda options: options[-1]):
            self.dispatcher.trigger_race_win(transferred, self.cb, 20)
        self.assertIn("papaya", self.message)
        self.assertIn("McLaren", self.message)
        self.assertNotIn("Maranello", self.message)

    def test_driver_personality_travels_with_driver(self):
        with patch("sim.radio.random.choice", side_effect=lambda options: options[-1]):
            self.dispatcher.trigger_overtake_success(car("piastri", "williams"), car("norris"), 3, 4, self.cb, 20)
        self.assertIn("Through on NOR. Copy.", self.message)

    def test_all_starting_drivers_and_teams_have_special_dialogue(self):
        for person in INITIAL_DRIVERS:
            if person.get("team_id"):
                self.assertIn(person["id"], DRIVER_RADIOS)
        self.assertEqual(set(TEAM_RADIOS), {team["id"] for team in INITIAL_TEAMS})

    def test_all_dialogue_templates_format_without_leaking_placeholders(self):
        context = dict(mode="ATTACK", turn=4, new_p=3, other_code="NOR", comp="INTER",
                       dur=12.4, time_str="1:23.456")
        for person in INITIAL_DRIVERS:
            team = person.get("team_id") or "mclaren"
            for event in GENERIC_RADIOS:
                with self.subTest(driver=person["id"], event=event):
                    # Walk every eligible pool and every line, including personal/team variants.
                    def choose(options):
                        if isinstance(options[0], list):
                            for pool in options:
                                for line in pool:
                                    text = line.format(num=person["number"], code=person["code"],
                                                       short=team, **context)
                                    self.assertNotIn("{", text)
                        return options[0]
                    with patch("sim.radio.random.choice", side_effect=choose):
                        self.dispatcher._recent.clear()
                        self.dispatcher._emit(event, car(person["id"], team), self.cb, **context)

    def test_messages_vary_before_repeating_and_generic_drivers_have_fallback(self):
        for _ in range(12):
            self.dispatcher.trigger_box_call(car("generated_rookie", "new_team"), self.cb)
        messages = [text for _, text in self.events]
        self.assertEqual(len(set(messages[:3])), 3)
        self.assertTrue(all(first != second for first, second in zip(messages, messages[1:])))

    def test_manual_modes_acknowledge_correct_system_even_during_cooldown(self):
        c = car()
        self.dispatcher.trigger_push_mode(c, "ATTACK", True, self.cb, 0)
        self.dispatcher.trigger_conserve_mode(c, self.cb, 0, is_pit_wall=True, mode_name="HARVEST")
        self.assertIn("HARVEST", self.message)
        self.assertNotIn("tyres", self.message.lower())
        for mode in ("BOOST", "OVERTAKE"):
            self.dispatcher.trigger_push_mode(c, mode, True, self.cb, 0)
            self.assertIn(mode, self.message)
            self.assertNotIn("active", self.message.lower())
        self.assertTrue(all(text.startswith("PIT WALL") for _, text in self.events))
        self.dispatcher.trigger_push_mode(c, "ATTACK", True, self.cb, 0, flag_state="SC")
        self.assertIn("restrictions", self.message)

    def test_cooldown_also_works_at_race_clock_zero(self):
        self.dispatcher.trigger_push_mode(car(), "PUSH", False, self.cb, 0)
        self.dispatcher.trigger_push_mode(car("norris"), "PUSH", False, self.cb, 1)
        self.assertEqual(len(self.events), 1)
        self.dispatcher.trigger_push_mode(car("norris"), "PUSH", False, self.cb, 2)
        self.assertEqual(len(self.events), 2)

    def test_no_battles_under_restrictions_or_after_finish(self):
        for flag in ("GRID", "LIGHTS", "SC", "VSC", "YELLOW", "RED", "CHEQUERED"):
            self.dispatcher.step(.05, 20, [car(), car("norris", s=120)], self.track, 0, flag, self.cb)
        self.dispatcher.step(.05, 20, [car(finished=True), car("norris", s=120)], self.track, 0, "GREEN", self.cb)
        self.assertEqual(self.events, [])

    def test_stale_tailing_timer_in_clear_air_does_not_create_a_battle(self):
        self.dispatcher.step(.05, 20, [car(), car("norris", s=1000)], self.track, 0, "GREEN", self.cb)
        self.assertEqual(self.events, [])

    def test_blue_flag_recipient_yields_instead_of_complaining_about_backmarkers(self):
        self.dispatcher.step(.05, 20, [car(blue_flag=True, tailing_timer=0)], self.track, 0, "GREEN", self.cb)
        self.assertIn("blue flags", self.message.lower())
        self.assertTrue("car behind" in self.message or "Let the faster car through" in self.message)

    def test_leading_car_can_request_blue_flags_for_actual_lapped_traffic(self):
        self.dispatcher.step(.05, 20, [car(), car("norris", lap=1, s=120, tailing_timer=0)],
                             self.track, 0, "GREEN", self.cb)
        self.assertIn("NOR", self.message)
        self.assertTrue("lapped" in self.message or "lap down" in self.message)

    def test_lapped_traffic_is_identified_across_the_timing_line(self):
        leader = car(s=4990, total_dist=9990, lap=2)
        backmarker = car("norris", s=10, total_dist=5010, lap=2, tailing_timer=0)
        self.dispatcher.step(.05, 20, [leader, backmarker], self.track, 0, "GREEN", self.cb)
        self.assertTrue("lapped" in self.message or "lap down" in self.message)

    def test_win_does_not_claim_a_championship(self):
        for team in INITIAL_TEAMS:
            self.dispatcher.trigger_race_win(car("new_rookie", team["id"]), self.cb, 20)
            self.assertNotIn("champion", self.message.lower())

    def test_rain_easing_is_wired_into_race_session(self):
        teams = {team["id"]: team for team in INITIAL_TEAMS}
        drivers = [person for person in INITIAL_DRIVERS if person.get("team_id")]
        race = RaceSession(COMPILED_TRACKS[0], teams, drivers, 0, 0, "mclaren")
        race.rain_intensity, race.wetness, race.race_clock = .3, .7, 100
        race.weather_timer = 0
        with patch("sim.physics.random.random", return_value=1), patch("sim.physics.random.uniform", return_value=.5):
            race._step_weather(.05, self.cb)
        radios = [text for kind, text in self.events if kind == "RADIO"]
        self.assertEqual(len(radios), 1)
        self.assertIn("still wet", radios[0])

    def test_drive_through_exit_allows_future_box_calls(self):
        teams = {team["id"]: team for team in INITIAL_TEAMS}
        drivers = [person for person in INITIAL_DRIVERS if person.get("team_id")]
        race = RaceSession(COMPILED_TRACKS[0], teams, drivers, 0, 0, "mclaren")
        c = race.cars[0]
        c.s = (race.track.pit_entry_s + race.track.pit_span_m - .1) % race.track.length_m
        c.total_dist = c.s
        c.in_pits, c.pit_phase = True, "EXIT"
        c.radio_box_announced = c.inlap_push_announced = True
        race._step_pit_lane(c, False, .1, self.cb)
        self.assertFalse(c.in_pits)
        self.assertFalse(c.radio_box_announced)
        self.assertFalse(c.inlap_push_announced)
        self.assertFalse(any(kind == "RADIO" for kind, _ in self.events))

    def test_player_commands_use_dispatcher_and_box_call_is_not_duplicated(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1] / "scratch") as temp:
            world = ChampionshipWorld(save_path=Path(temp) / "career.json")
            teams = {team["id"]: team for team in world.teams}
            drivers = [person for person in world.drivers if person.get("team_id")]
            world.race_session = RaceSession(COMPILED_TRACKS[0], teams, drivers, 0, 0, world.player_team_id)
            world.phase = "RACE"
            race = world.race_session
            c = next(c for c in race.cars if c.team_id == world.player_team_id)
            with patch.object(world, "_push_event", side_effect=self.cb):
                for cmd in ({"pace_mode": "PUSH"}, {"ers_mode": "HARVEST"},
                            {"ers_mode": "OVERTAKE"}, {"box_this_lap": True}):
                    self.assertTrue(world.pit_wall_command(c.driver_id, cmd)["ok"])
                self.assertEqual(len(self.events), 4)
                self.assertIn("HARVEST", self.events[1][1])
                self.assertIn("OVERTAKE", self.events[2][1])
                self.assertTrue(c.radio_box_announced)
                # A repeated command and the next driving tick must not repeat the box call.
                world.pit_wall_command(c.driver_id, {"box_this_lap": True})
                c.auto_strategy = False
                race.flag_state = "GREEN"
                race._step_car(c, None, c, False, .05, world._push_event)
                self.assertEqual(len(self.events), 4)


if __name__ == "__main__":
    unittest.main()
