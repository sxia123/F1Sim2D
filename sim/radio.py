"""Event-driven team radio whose claims are supported by race state."""
from __future__ import annotations

import random
from collections import deque
from typing import Any

from sim.radio_messages import DRIVER_RADIOS, GENERIC_RADIOS, TEAM_RADIOS, driver, engineer

# Public collections retained for tools that inspect the dialogue library.
DRIVER_PUSH_RADIOS = {key: bank["push"] for key, bank in DRIVER_RADIOS.items() if "push" in bank}
DRIVER_OVERTAKEN_RADIOS = {key: bank["overtaken"] for key, bank in DRIVER_RADIOS.items() if "overtaken" in bank}
DRIVER_OVERTAKE_RADIOS = {key: bank["overtake"] for key, bank in DRIVER_RADIOS.items() if "overtake" in bank}
DRIVER_ICONIC_RADIOS = {key: [line for lines in bank.values() for line in lines] for key, bank in DRIVER_RADIOS.items()}
PUSH_MODE_RADIOS = GENERIC_RADIOS["push"]
CONSERVE_MODE_RADIOS = GENERIC_RADIOS["conserve"]
OVERTAKEN_RADIOS = GENERIC_RADIOS["overtaken"]
OVERTAKE_SUCCESS_RADIOS = GENERIC_RADIOS["overtake"]
BOX_CALL_RADIOS = GENERIC_RADIOS["box"]
PIT_EXIT_RADIOS = GENERIC_RADIOS["pit_exit"]
DIRTY_AIR_AND_BATTLE_RADIOS = GENERIC_RADIOS["battle"]
BLUE_FLAG_RADIOS = GENERIC_RADIOS["blue_attack"]
CONTACT_RADIOS = GENERIC_RADIOS["contact"]
FASTEST_LAP_RADIOS = GENERIC_RADIOS["fastest_lap"]
TYRE_CLIFF_RADIOS = GENERIC_RADIOS["tyre_cliff"]
WEATHER_RADIOS = GENERIC_RADIOS["rain"]
SPIN_RADIOS = GENERIC_RADIOS["spin"]
DAMAGE_RADIOS = GENERIC_RADIOS["damage"]
SAFETY_CAR_RADIOS = GENERIC_RADIOS["sc"]
SAFETY_CAR_IN_RADIOS = GENERIC_RADIOS["sc_in"]
RACE_WIN_RADIOS = GENERIC_RADIOS["win"]
# Ambient chatter stays disabled: every transmission needs a real event.
AMBIENT_TECHNICAL_RADIOS: list[str] = []


class RadioDispatcher:
    """Select event-appropriate driver/team voices with cooldowns and variety."""

    def __init__(self) -> None:
        self.last_global_radio_clock = -99.0
        self.last_driver_radio_clock: dict[str, float] = {}
        self.last_contact_radio_clock = -99.0
        self._recent: dict[str, deque[str]] = {}

    @staticmethod
    def _driver_key(car: Any) -> str:
        return str(getattr(car, "driver_id", "") or getattr(car, "number", "TEAM"))

    def _can_broadcast(self, car: Any, clock: float, min_global_cd: float = 2.2,
                       min_driver_cd: float = 14.0) -> bool:
        return (clock - self.last_global_radio_clock >= min_global_cd
                and clock - self.last_driver_radio_clock.get(self._driver_key(car), -99.0) >= min_driver_cd)

    def _mark_broadcast(self, car: Any, clock: float | None) -> None:
        if clock is None:
            return
        self.last_global_radio_clock = clock
        self.last_driver_radio_clock[self._driver_key(car)] = clock
        if car is not None and hasattr(car, "last_radio_time"):
            car.last_radio_time = clock

    def _emit(self, event: str, car: Any, event_cb, clock: float | None = None,
              pit_wall: bool = False, **context: Any) -> None:
        """Keep personal lines tied to events and employer lines tied to team_id."""
        generic = GENERIC_RADIOS[event]
        if pit_wall:
            generic = [line for line in generic if line.startswith("PIT WALL")]
        pools = [generic] if generic else []
        driver_id = str(getattr(car, "driver_id", "")).lower()
        team_id = str(getattr(car, "team_id", "")).lower()
        personal = DRIVER_RADIOS.get(driver_id, {}).get(event, [])
        team = TEAM_RADIOS.get(team_id, {}).get(event, [])
        if personal and not pit_wall:
            pools.extend([driver(*personal)] * 2)
        if team:
            pools.extend([engineer(*team)] * 2)

        recent = self._recent.setdefault(self._driver_key(car), deque(maxlen=6))
        fresh = [[line for line in pool if line not in recent] for pool in pools]
        available = [pool for pool in fresh if pool]
        if not available:
            # Small banks may be exhausted, but still avoid consecutive repeats.
            fresh = [[line for line in pool if not recent or line != recent[-1]] for pool in pools]
            available = [pool for pool in fresh if pool] or pools
        template = random.choice(random.choice(available))
        recent.append(template)
        values = dict(num=getattr(car, "number", ""), code=getattr(car, "code", ""),
                      short=getattr(car, "team_short", ""))
        values.update(context)
        if car is None:
            template = template.replace("PIT WALL ({short} / #{num} {code})", "RACE CONTROL")
        message = template.format(**values)
        self._mark_broadcast(car, clock)
        event_cb("RADIO", message)

    @staticmethod
    def _active(car: Any) -> bool:
        return (not getattr(car, "dnf", False) and not getattr(car, "in_pits", False)
                and not getattr(car, "finished", False))

    def trigger_push_mode(self, car: Any, mode_name: str, is_pit_wall: bool,
                          event_cb, clock: float = 0.0, turn: int = 1,
                          flag_state: str = "GREEN") -> None:
        if not is_pit_wall and not self._can_broadcast(car, clock, 1.8, 10.0):
            return
        # Selecting an ERS setting does not guarantee deployment or OVT eligibility.
        event = {"BOOST": "boost", "OVERTAKE": "overtake_mode"}.get(mode_name.upper(), "push")
        if flag_state != "GREEN":
            event = "mode_restricted"
        self._emit(event, car, event_cb, clock, pit_wall=is_pit_wall, mode=mode_name, turn=turn)

    def trigger_conserve_mode(self, car: Any, event_cb, clock: float = 0.0,
                              turn: int = 1, is_pit_wall: bool = False,
                              mode_name: str = "CONSERVE") -> None:
        if not is_pit_wall and not self._can_broadcast(car, clock, 2.5, 16.0):
            return
        event = "harvest" if mode_name.upper() == "HARVEST" else "conserve"
        self._emit(event, car, event_cb, clock, pit_wall=is_pit_wall, turn=turn)

    def trigger_overtaken(self, overtaken_car: Any, overtaker_car: Any, turn: int,
                          event_cb, clock: float = 0.0, maneuver: str = "") -> None:
        if not self._can_broadcast(overtaken_car, clock, 2.0, 12.0):
            return
        event = "divebomb" if maneuver.upper() == "DIVEBOMB" else "overtaken"
        self._emit(event, overtaken_car, event_cb, clock, other_code=overtaker_car.code, turn=turn)

    def trigger_overtake_success(self, overtaker_car: Any, overtaken_car: Any,
                                 new_p: int, turn: int, event_cb, clock: float = 0.0) -> None:
        if not self._can_broadcast(overtaker_car, clock, 2.0, 12.0):
            return
        self._emit("lead" if new_p == 1 else "overtake", overtaker_car, event_cb, clock,
                   other_code=overtaken_car.code, new_p=new_p, turn=turn)

    def trigger_overtake_event(self, overtaker: Any, overtaken: Any, new_p: int,
                               turn: int, event_cb, clock: float = 0.0,
                               maneuver: str = "") -> None:
        if not self._active(overtaker) or not self._active(overtaken):
            return
        # Either side may react, falling back to the other if one is cooling down.
        if random.random() < 0.55:
            if self._can_broadcast(overtaken, clock, 2.0, 12.0):
                self.trigger_overtaken(overtaken, overtaker, turn, event_cb, clock, maneuver)
            else:
                self.trigger_overtake_success(overtaker, overtaken, new_p, turn, event_cb, clock)
        elif self._can_broadcast(overtaker, clock, 2.0, 12.0):
            self.trigger_overtake_success(overtaker, overtaken, new_p, turn, event_cb, clock)
        else:
            self.trigger_overtaken(overtaken, overtaker, turn, event_cb, clock, maneuver)

    def trigger_box_call(self, car: Any, event_cb, clock: float | None = None,
                         is_pit_wall: bool = False) -> None:
        comp = getattr(car, "next_compound", None) or getattr(car, "compound", "selected")
        self._emit("drive_through" if getattr(car, "drive_through_pending", False) else "box",
                   car, event_cb, clock, pit_wall=is_pit_wall, comp=comp)

    def trigger_pit_exit(self, car: Any, duration: float, event_cb,
                         clock: float | None = None) -> None:
        self._emit("pit_exit", car, event_cb, clock, dur=duration, comp=car.compound)

    def trigger_contact(self, c1: Any, c2: Any, turn: int, event_cb, clock: float) -> None:
        if clock - self.last_contact_radio_clock < 7.0:
            return
        active = [car for car in (c1, c2) if not getattr(car, "dnf", False)
                  and not getattr(car, "finished", False)]
        if not active:
            return
        self.last_contact_radio_clock = clock
        talker = random.choice(active)
        other = c2 if talker is c1 else c1
        # A collision alone proves neither blame nor any particular damage.
        self._emit("contact", talker, event_cb, clock, turn=turn, other_code=other.code)

    def trigger_fastest_lap(self, car: Any, lap_time_str: str, event_cb,
                            clock: float | None = None) -> None:
        self._emit("fastest_lap", car, event_cb, clock, time_str=lap_time_str)

    def trigger_spin(self, car: Any, turn: int, event_cb, clock: float = 0.0) -> None:
        if not self._can_broadcast(car, clock, 2.0, 10.0):
            return
        self._emit("spin", car, event_cb, clock, turn=turn)

    def trigger_damage(self, car: Any, dmg_type: str, turn: int, event_cb,
                       clock: float = 0.0) -> None:
        if not self._can_broadcast(car, clock, 2.0, 10.0):
            return
        damage = dmg_type.upper().replace(" ", "_")
        if "PUNCTURE" in damage:
            event = "puncture"
        elif "WING" in damage:
            event = "wing_damage"
        else:
            event = "damage"
        self._emit(event, car, event_cb, clock, turn=turn)

    def trigger_tyre_cliff(self, car: Any, event_cb, clock: float = 0.0) -> None:
        if not self._can_broadcast(car, clock, 3.0, 25.0):
            return
        self._emit("tyre_cliff", car, event_cb, clock)

    def trigger_safety_car(self, mode: str, reason: str, event_cb, clock: float = 0.0,
                           cars: list[Any] | None = None) -> None:
        if mode.upper() not in ("SC", "VSC"):
            return
        active = [car for car in (cars or []) if self._active(car)]
        car = random.choice(active) if active else None
        self._emit(mode.lower(), car, event_cb, clock, pit_wall=True)

    def trigger_safety_car_in(self, event_cb, clock: float = 0.0,
                              cars: list[Any] | None = None) -> None:
        active = [car for car in (cars or []) if self._active(car)]
        self._emit("sc_in", random.choice(active) if active else None, event_cb, clock, pit_wall=True)

    def trigger_weather_transition(self, rain_intensity: float, wetness: float, event_cb,
                                   clock: float, cars: list[Any], track: Any) -> None:
        active = [car for car in cars if self._active(car)
                  and self._can_broadcast(car, clock, 4.0, 25.0)]
        if not active:
            return
        car = random.choice(active)
        if rain_intensity >= 0.06:
            event = "rain_wet" if wetness >= 0.15 else "rain"
        else:
            event = "rain_easing" if wetness >= 0.15 else "drying"
        turn = track.nearest_corner(car.s) if hasattr(track, "nearest_corner") else 1
        self._emit(event, car, event_cb, clock, turn=turn)

    def trigger_race_win(self, winner: Any, event_cb, clock: float = 0.0) -> None:
        # Winning a race does not imply winning a championship.
        self._emit("win", winner, event_cb, clock)

    def step(self, dt: float, clock: float, cars: list[Any], track: Any, wetness: float,
             flag_state: str, event_cb) -> None:
        """Only discuss battles that are still happening under green flags."""
        if flag_state != "GREEN":
            return
        active = [car for car in cars if self._active(car) and getattr(car, "spin_timer", 0.0) <= 0.0]
        candidates = []
        length = getattr(track, "length_m", 0.0)
        for car in active:
            if not self._can_broadcast(car, clock, 3.5, 22.0):
                continue
            if getattr(car, "blue_flag", False):
                candidates.append((car, "blue_yield", None))
                continue
            if getattr(car, "tailing_timer", 0.0) < 3.5 or length <= 0:
                continue
            ahead = [(other, (other.s - car.s) % length) for other in active
                     if other is not car and (other.s - car.s) % length > 0.0]
            if not ahead:
                continue
            target, distance = min(ahead, key=lambda pair: pair[1])
            if distance >= 95.0 or distance / max(getattr(car, "v", 0.0), 25.0) >= 1.0:
                continue
            # Progress resolves lapping across the start line, where raw lap
            # counters can temporarily match despite a full lap between cars.
            if hasattr(car, "total_dist") and hasattr(target, "total_dist"):
                laps_ahead = round((car.total_dist + distance - target.total_dist) / length)
            else:
                laps_ahead = getattr(car, "lap", 1) - getattr(target, "lap", 1)
            if laps_ahead < 0:
                continue
            event = "blue_attack" if laps_ahead > 0 else "battle"
            candidates.append((car, event, target))
        if candidates:
            car, event, target = random.choice(candidates)
            car.tailing_timer = 0.0
            self._emit(event, car, event_cb, clock, other_code=getattr(target, "code", ""))
