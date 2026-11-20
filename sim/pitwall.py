"""Rival race engineering using visible race state and the simulator's tyre model."""
from __future__ import annotations

import math
from dataclasses import dataclass

from sim.data import TIRE_COMPOUNDS, SETUP_LEVELS, tire_thermal_wear_mult

DRY = frozenset(("SOFT", "MEDIUM", "HARD"))


@dataclass
class PitCall:
    car: object
    compound: str
    reason: str
    gain_s: float
    priority: int = 1
    urgent: bool = False


class RivalPitWall:
    """Coordinate both cars without changing their physical state or seeing future weather."""

    def __init__(self, race):
        self.race = race
        self.next_review = 0.0
        self.managed_orders = {}
        self.team_order_cooldown = {}
        self.reverse_order_blocked_until = {}
        self.team_order_count = {}
        track = race.track
        self.lap_s = sum(track.ds_m / max(v, 20.0) for v in race.v_env)
        self.mean_speed = track.length_m / self.lap_s
        self.corner_share = max(0.35, sum(v < 75.0 for v in race.v_env) / len(race.v_env))
        start = int(track.pit_entry_s / track.ds_m)
        count = max(1, math.ceil(track.pit_span_m / track.ds_m))
        self.mainline_pit_s = sum(track.ds_m / max(race.v_env[(start + i) % len(race.v_env)], 20.0)
                                  for i in range(count))

    def eligible(self, car):
        return (car.team_id != self.race.player_team_id and car.auto_strategy
                and not car.dnf and not car.finished)

    def wear_per_lap(self, car, compound, observed=False):
        spec = TIRE_COMPOUNDS[compound]
        rate = (spec["wear_per_km"] * self.race.track.length_m / 1000.0
                * self.race.track.tire_abrasion
                * (1.0 - (car.skills["tire_mgmt"] - 85) * 0.012)
                * (1.0 - (car.upgrades["chassis"] - 5) * 0.018))
        if compound not in DRY and self.race.wetness < 0.08:
            rate *= 1.65
        setup_wear = SETUP_LEVELS.get(getattr(car, "setup_df", 0), {}).get("wear_mult", 1.0)
        rate *= setup_wear
        if getattr(car, "lift_coast", False):
            pace_mode = getattr(car, "pace_mode", "BALANCED")
            rate *= 0.96 if pace_mode == "ATTACK" else (0.94 if pace_mode == "PUSH" else 0.88)
        if observed and compound == car.compound:
            rate *= tire_thermal_wear_mult(compound, car.tire_temp)
            if car.tire_age_laps >= 2:
                measured = max(0.0, car.tire_wear - 0.02) / car.tire_age_laps
                rate = 0.5 * rate + 0.5 * min(rate * 2.0, max(rate * 0.75, measured))
        elif compound in DRY and car.tire_temp > spec["opt_temp_max"]:
            # Candidate tyres inherit part of the car/track thermal overheat above their window
            est_temp = spec["opt_temp_max"] + 0.65 * (car.tire_temp - spec["opt_temp_max"])
            rate *= tire_thermal_wear_mult(compound, est_temp)
        return max(0.005, rate)

    def projected_wetness(self, seconds):
        # Only current rain, surface state and drying temperature are observable.
        # Never read rain_start_clock, rain_duration, or rain_scheduled.
        race = self.race
        seconds = max(0.0, min(60.0, seconds))
        if race.rain_intensity > race.wetness:
            return race.rain_intensity + (race.wetness - race.rain_intensity) * math.exp(-0.022 * seconds)
        dry_rate = 0.0055 * (1.0 + (race.track_temp_c - 18.0) * 0.03)
        return max(0.0, race.wetness - dry_rate * seconds)

    def pit_loss(self, car, flag_state=None):
        race = self.race
        flag = race.flag_state if flag_state is None else flag_state
        neutral = 1.65 if flag == "SC" else 1.40 if flag == "VSC" else 1.0
        stop = 2.9 - car.upgrades["pit_crew"] * 0.098
        repairs = 7.4 if car.wing_damage >= 0.20 else 0.0
        lim_m = getattr(
            race.track,
            "fia_pit_length_m",
            (race.track.pit_speed_exit_u - race.track.pit_speed_entry_u) * race.track.pit_length_m,
        )
        ramp_m = max(0.0, race.track.pit_length_m - lim_m)
        pit_drive_s = lim_m / 22.22 + ramp_m / 33.5
        return max(4.0, pit_drive_s + stop + repairs
                   + min(10.0, car.time_penalty_s) - self.mainline_pit_s * neutral)

    def _lap_cost(self, compound, wear, wetness, damage=0.0):
        spec = TIRE_COMPOUNDS[compound]
        cliff = spec["cliff_wear"]
        wear_grip = 1.0 - min(wear, cliff) * 0.11 - max(0.0, wear - cliff) * 0.85
        if wetness > spec["optimal_wet_max"]:
            weather = max(0.52, 1.0 - (wetness - spec["optimal_wet_max"]) * 0.72)
        elif wetness < spec["optimal_wet_min"]:
            weather = max(0.76, 1.0 - (spec["optimal_wet_min"] - wetness) * 0.42)
        else:
            weather = 1.0 - wetness * 0.08
        grip = max(0.15, spec["base_grip"] * max(0.2, wear_grip) * weather * (1.0 - damage * 0.28))
        return self.lap_s * self.corner_share * (1.0 / math.sqrt(grip) - 1.0)

    def _stint_costs(self, car, compound, laps, wetness, fresh=False):
        wear = 0.01 if fresh else car.tire_wear
        rate = self.wear_per_lap(car, compound, observed=not fresh)
        costs = [0.0]
        for _ in range(laps):
            costs.append(costs[-1] + self._lap_cost(compound, wear + rate * 0.5, wetness,
                                                   0.0 if fresh else car.wing_damage))
            wear += rate
        return costs

    def _available(self, car):
        allocation = self.race.tire_allocations.get(car.driver_id, {})
        return [compound for compound in TIRE_COMPOUNDS if allocation.get(compound, 0) > 0]

    def _needs_second_dry(self, car):
        return (not self.race.is_sprint and not self.race.wet_declared
                and len(car.compounds_used & DRY) < 2)

    def _fresh_options(self, car, laps, wetness):
        available = self._available(car)
        if wetness < 0.17:
            dry = [compound for compound in available if compound in DRY]
            if dry:
                available = dry
        elif wetness > 0.25:
            wet = [compound for compound in available if compound not in DRY]
            if wet:
                available = wet
        if self._needs_second_dry(car) and wetness < 0.17:
            second = [compound for compound in available if compound not in car.compounds_used]
            if second:
                available = second
        return {compound: self._stint_costs(car, compound, laps, wetness, fresh=True)
                for compound in available}

    def _rejoin_traffic(self, car, loss):
        rejoin = car.total_dist - loss * self.mean_speed
        penalty = 0.0
        difficulty = max(0.6, min(1.6, 14.0 / self.race.track.track_width_m))
        for other in self.race.cars:
            if other is car or other.in_pits or other.box_this_lap or other.dnf or other.finished:
                continue
            gap = ((other.total_dist - rejoin) % self.race.track.length_m) / self.mean_speed
            if 0.0 < gap < 2.5:
                slower = max(0.0, (car.car_perf_index - other.car_perf_index) * 0.08)
                penalty += (2.5 - gap) * difficulty * (0.65 + min(0.8, slower))
        return min(7.0, penalty)

    def _battle_incentive(self, car, fresh_compound, wetness, loss):
        laps = max(1, self.race.total_laps - car.laps_completed)
        if (self.race.flag_state != "GREEN" or wetness >= 0.14 or laps <= 5
                or car.compound not in DRY or fresh_compound not in DRY):
            return 0.0, ""
        if car.pit_stops >= 2:
            return 0.0, ""
        if car.pit_stops == 1:
            if car.tire_age_laps < 6 or car.tire_wear < 0.48 or laps < 7:
                return 0.0, ""
            cand_end_wear = 0.02 + laps * self.wear_per_lap(car, fresh_compound, observed=False)
            if cand_end_wear > TIRE_COMPOUNDS[fresh_compound]["cliff_wear"] + 0.04:
                return 0.0, ""
        else:
            min_age = 8 if car.compound == "HARD" else 7 if car.compound == "MEDIUM" else 5
            min_wear = 0.38 if car.compound == "HARD" else 0.34 if car.compound == "MEDIUM" else 0.28
            if car.tire_age_laps < min_age or car.tire_wear < min_wear:
                return 0.0, ""
        gain = self._lap_cost(car.compound, car.tire_wear, wetness, car.wing_damage)
        gain -= self._lap_cost(fresh_compound, 0.02, wetness)
        if gain < 0.6:
            return 0.0, ""
        rivals = [other for other in self.race.cars if other.team_id != car.team_id
                  and not other.dnf and not other.finished]
        for other in rivals:
            gap = (other.total_dist - car.total_dist) / self.mean_speed
            if 0.25 < gap < 3.0 and not other.in_pits and other.tire_age_laps >= 3:
                return min(3.0, gain * 1.5), f"attempt an undercut on {other.code}"
            if (-loss - 4.0 < gap < 0.0 and other.pit_stops > car.pit_stops
                    and (other.in_pits or other.tire_age_laps <= 1)):
                return min(3.5, gain * 1.8), f"cover {other.code}'s pit stop"
        return 0.0, ""

    def plan(self, car):
        race = self.race
        laps = max(1, race.total_laps - car.laps_completed)
        if car.drive_through_pending and car.drive_through_laps_left <= 2:
            return PitCall(car, car.compound, "serve drive-through penalty", 0.0, 5, True)
        arrival = ((race.track.pit_entry_s - car.s) % race.track.length_m) / self.mean_speed
        wetness = 0.35 * race.wetness + 0.65 * self.projected_wetness(arrival + 25.0)
        options = self._fresh_options(car, laps, wetness)
        if not options:
            car.strategy_status = "No fresh sets available; manage remaining tyres"
            return None
        best = min(options, key=lambda compound: options[compound][-1])
        loss = self.pit_loss(car)
        current_lap = self._lap_cost(car.compound, car.tire_wear, wetness)
        fresh_lap = self._lap_cost(best, 0.02, wetness)
        weather_change = ((car.compound in DRY) != (best in DRY) or
                          (car.compound not in DRY and best != car.compound))
        weather_gain = (current_lap - fresh_lap) * min(laps, 3)
        # Hysteresis plus minimum payoff prevents crossover flip-flopping.
        urgent_weather = race.wetness > TIRE_COMPOUNDS[car.compound]["optimal_wet_max"] + 0.18
        if weather_change and (weather_gain > loss + 2.0 or
                               (urgent_weather and laps >= 2 and current_lap - fresh_lap > 1.5)):
            urgent = urgent_weather
            return PitCall(car, best, "switch tyres for changing track conditions", weather_gain - loss, 4, urgent)
        if car.wing_damage >= 0.65 and laps >= 2:
            return PitCall(car, best, "repair severe front-wing damage", 0.0, 5, True)
        if race.is_sprint:
            # A Sprint has no compulsory dry stop; only pay for a clear net gain.
            gain = (self._stint_costs(car, car.compound, laps, wetness)[-1]
                    - options[best][-1] - loss)
            if gain > 4.0 and car.tire_wear > TIRE_COMPOUNDS[car.compound]["cliff_wear"]:
                urgent = car.tire_wear > TIRE_COMPOUNDS[car.compound]["cliff_wear"] + 0.12
                return PitCall(car, best, "replace tyres past the cliff", gain, 3, urgent)
            car.strategy_status = "Protect track position; no compulsory Sprint stop"
            return None
        need_second = self._needs_second_dry(car)
        legal_change = best in DRY and best not in car.compounds_used
        if need_second and laps <= 2 and legal_change:
            return PitCall(car, best, "complete the required second dry compound", 0.0, 5, True)
        future_wet = self.projected_wetness(arrival + self.lap_s * 1.6)
        if not weather_change and car.compound in DRY and future_wet >= 0.16 and car.tire_wear < 0.85:
            car.strategy_status = "Hold track position for incoming rain before boxing"
            return None
        if not weather_change and car.compound not in DRY:
            if car.tire_wear < 0.72 or car.tire_age_laps < 5 or laps <= 5 or future_wet < 0.18:
                car.strategy_status = "Manage wet tyres to the crossover window"
                return None
        if not weather_change and car.compound in DRY:
            if car.pit_stops == 0:
                min_sc_age = 4 if car.compound == "SOFT" else 5
                if race.flag_state in ("SC", "VSC") and car.tire_age_laps < min_sc_age and car.tire_wear < 0.24:
                    car.strategy_status = "Early stint; hold track position under neutralisation"
                    return None
            else:
                if car.tire_age_laps < 6 and car.wing_damage < 0.65:
                    car.strategy_status = "Build the new stint; avoid another early stop"
                    return None
                if not need_second:
                    if laps <= 4 and car.wing_damage < 0.65 and car.tire_wear < 0.88:
                        car.strategy_status = "Manage tyres to the checkered flag"
                        return None
                    if car.pit_stops >= 2 and (car.tire_wear < 0.88 or laps < 5) and car.wing_damage < 0.65:
                        car.strategy_status = "Protect track position; carry current tyres to the finish"
                        return None
        current = self._stint_costs(car, car.compound, laps, wetness)
        stay = current[-1] + (1000.0 if need_second and wetness < 0.17 else 0.0)
        best_cost, best_delay, best_compound = stay, None, best
        neutral = race.flag_state in ("SC", "VSC")
        traffic = 0.0 if neutral else self._rejoin_traffic(car, loss)
        wear_rate = self.wear_per_lap(car, car.compound, observed=True)
        wear_at_entry = car.tire_wear + wear_rate * arrival / self.lap_s
        max_delay = max(0, math.floor((TIRE_COMPOUNDS[car.compound]["cliff_wear"] - 0.025 - wear_at_entry) / wear_rate))
        battle_reason = ""
        for compound, fresh in options.items():
            incentive, reason = self._battle_incentive(car, compound, wetness, loss)
            for delay in range(min(laps, max_delay + 1)):
                # Do not assume today's neutralisation lasts until a later lap.
                stop_loss = self.pit_loss(car, "GREEN") if delay > 0 else loss
                cost = current[delay] + stop_loss + fresh[laps - delay]
                if delay == 0:
                    cost += traffic - incentive
                # Planning far ahead is less certain than an immediate action.
                cost += delay * 0.04
                if cost < best_cost:
                    best_cost, best_delay, best_compound = cost, delay, compound
                    battle_reason = reason if delay == 0 and incentive > traffic else ""
        if car.pit_stops >= 1 and not need_second and not weather_change:
            stay_ok = not (car.pit_stops == 1 and car.tire_wear < 0.40 and car.wing_damage < 0.35)
            min_gain = 9.0 if car.pit_stops >= 2 else (4.5 if race.flag_state == "GREEN" else 3.0)
        else:
            stay_ok = True
            min_gain = 1.0
        if best_delay == 0 and stay_ok and stay - best_cost > min_gain:
            if (not weather_change and best_compound in DRY
                    and 0.02 + laps * self.wear_per_lap(car, best_compound, observed=False)
                    > TIRE_COMPOUNDS[best_compound]["cliff_wear"] - 0.02):
                viable_alts = [
                    c for c in options
                    if c in DRY and c != best_compound
                    and 0.02 + laps * self.wear_per_lap(car, c, observed=False)
                    <= TIRE_COMPOUNDS[c]["cliff_wear"] - 0.02
                    and (not need_second or c not in car.compounds_used)
                ]
                if viable_alts:
                    alt = min(viable_alts, key=lambda c: options[c][-1])
                    alt_cost = current[0] + loss + options[alt][-1] + traffic
                    if alt_cost < best_cost + 3.0 and stay - alt_cost > min_gain:
                        best_compound = alt
            reason = battle_reason or ("take a cheaper stop under neutralisation" if race.flag_state in ("SC", "VSC")
                                       else "replace worn tyres at the optimal stint window")
            if weather_change:
                reason = "switch tyres for changing track conditions"
            if car.wing_damage >= 0.20:
                reason = "combine front-wing repair with the tyre stop"
            gain = current[-1] - options[best_compound][-1] - loss - traffic
            urgent = car.tire_wear > TIRE_COMPOUNDS[car.compound]["cliff_wear"] + 0.12
            return PitCall(car, best_compound, reason, max(0.0, gain), 3 if urgent else 2, urgent)
        if traffic > 1.5 and best_delay is not None:
            car.strategy_status = "Extend stint to avoid traffic after the stop"
        elif best_delay is not None:
            car.strategy_status = f"Extend stint; pit window in {best_delay} {'lap' if best_delay == 1 else 'laps'}"
        else:
            car.strategy_status = "Tyres can reach the finish; preserve track position"
        return None

    def garage_arrival(self, car):
        race = self.race
        box = race._team_pit_box_s(car)
        if car.in_pits:
            if car.pit_phase == "STOPPED":
                return 0.0
            if car.pit_phase == "EXIT":
                return None
            return ((box - car.s) % race.track.length_m) / (22.22 * race.track.pit_distance_scale)
        approach = ((race.track.pit_entry_s - car.s) % race.track.length_m) / self.mean_speed
        lane = ((box - race.track.pit_entry_s) % race.track.length_m) / (22.22 * race.track.pit_distance_scale)
        return approach + lane

    def _garage_conflict(self, call):
        car = call.car
        arrival = self.garage_arrival(car)
        for other in self.race.cars:
            if other is car or other.team_id != car.team_id or other.dnf:
                continue
            if not (other.box_this_lap or other.in_pits):
                continue
            other_arrival = self.garage_arrival(other)
            if other_arrival is None:
                continue
            service = (max(0.0, other.pit_stop_timer) if other.pit_phase == "STOPPED" else
                       3.5 + min(10.0, other.time_penalty_s) + (7.4 if other.wing_damage >= 0.2 else 0.0))
            if other_arrival - 3.0 < arrival < other_arrival + service + 1.5:
                return True
        return False

    def manage_pace(self, car, event_cb):
        race = self.race
        if car.in_pits:
            return
        nearest_ahead, nearest_behind = 99.0, 99.0
        for other in race.cars:
            if other is car or other.dnf or other.finished or other.in_pits:
                continue
            gap = (other.total_dist - car.total_dist) / self.mean_speed
            if gap > 0:
                nearest_ahead = min(nearest_ahead, gap)
            else:
                nearest_behind = min(nearest_behind, -gap)
        spec = TIRE_COMPOUNDS[car.compound]
        hot = car.tire_temp > spec["opt_temp_max"] + 5.0
        at_cliff = car.tire_wear > spec["cliff_wear"] - 0.05
        wrong_weather = race.wetness > spec["optimal_wet_max"] + 0.16
        neutral = race.flag_state in ("SC", "VSC", "YELLOW")
        ratio = car.battery_mj / max(0.1, car.max_battery_mj)
        old_pace = car.pace_mode
        if neutral or hot or at_cliff or wrong_weather:
            car.pace_mode = "CONSERVE"
            car.ers_mode = "HARVEST" if neutral or ratio < 0.25 else "AUTO"
        elif car.box_this_lap or (race.total_laps - car.laps_completed <= 2 and min(nearest_ahead, nearest_behind) < 3.0):
            car.pace_mode = "ATTACK"
            car.ers_mode = "BOOST" if ratio > 0.30 else "AUTO"
        elif min(nearest_ahead, nearest_behind) < 1.5:
            car.pace_mode = "PUSH"
            car.ers_mode = "OVERTAKE" if car.overtake_eligible and ratio > 0.35 else "BOOST" if ratio > 0.55 else "AUTO"
        else:
            car.pace_mode = "BALANCED"
            charge = ratio < 0.35 or (car.ers_mode == "HARVEST" and ratio < 0.60)
            car.ers_mode = "HARVEST" if charge else "AUTO"
        if old_pace != car.pace_mode and race.flag_state != "CHEQUERED" and not car.finished:
            if race.race_clock - getattr(car, "_last_pace_radio_clock", -99.0) >= 25.0:
                car._last_pace_radio_clock = race.race_clock
                if car.pace_mode == "CONSERVE":
                    race.radio_dispatcher.trigger_conserve_mode(car, event_cb, race.race_clock)
                elif car.pace_mode in ("PUSH", "ATTACK"):
                    race.radio_dispatcher.trigger_push_mode(car, car.pace_mode, False, event_cb,
                                                            race.race_clock, flag_state=race.flag_state)

    def _team_orders(self, event_cb):
        race = self.race
        for driver_id, (target_id, expires) in list(self.managed_orders.items()):
            car = race.cars_by_id[driver_id]
            target = race.cars_by_id[target_id]
            if (race.race_clock >= expires or not self.eligible(car) or not self.eligible(target)
                    or car.in_pits or target.in_pits or car.box_this_lap or target.box_this_lap
                    or car.team_order != "YIELD" or race.flag_state != "GREEN"):
                if car.team_order == "YIELD" and car.swap_target_id == target_id:
                    car.team_order = "FREE"
                    car.swap_target_id = None
                if target.swap_pass_id == driver_id:
                    target.swap_pass_id = None
                self.team_order_cooldown[car.team_id] = max(
                    self.team_order_cooldown.get(car.team_id, 0.0), race.race_clock + 240.0
                )
                del self.managed_orders[driver_id]
        if race.flag_state != "GREEN":
            return
        min_laps = 2 if race.total_laps <= 12 else 4
        for car in race.cars:
            if not self.eligible(car) or car.in_pits or car.box_this_lap or car.team_order != "FREE":
                continue
            damaged = car.wing_damage >= 0.25
            if not damaged and car.laps_completed < min_laps:
                continue
            if not damaged and self.team_order_count.get(car.team_id, 0) >= 2:
                continue
            if not damaged and race.race_clock < self.team_order_cooldown.get(car.team_id, 0.0):
                continue
            for other in race.cars:
                if (other is car or other.team_id != car.team_id or not self.eligible(other)
                        or other.in_pits or other.box_this_lap or other.laps_completed != car.laps_completed):
                    continue
                gap = (car.total_dist - other.total_dist) / self.mean_speed
                if not 0.12 < gap < 0.78:
                    continue
                if not damaged and race.race_clock < self.reverse_order_blocked_until.get((car.driver_id, other.driver_id), 0.0):
                    continue
                v_ref_car = max(20.0, race.v_env[race.track.sample(car.s)["station"]])
                v_ref_other = max(20.0, race.v_env[race.track.sample(other.s)["station"]])
                # Comparing instantaneous free_air_target_v across braking/straight transitions creates false +40 m/s spikes.
                if not damaged and abs(v_ref_other - v_ref_car) > 8.0:
                    continue
                advantage = other.free_air_target_v * (v_ref_car / v_ref_other) - car.free_air_target_v
                tyre_delta = (other.tire_age_laps + 5 <= car.tire_age_laps
                              and (car.tire_wear - other.tire_wear) >= 0.14
                              and advantage > 1.3)
                if advantage > 2.8 or tyre_delta or damaged:
                    car.team_order = "YIELD"
                    car.swap_target_id = other.driver_id
                    other.swap_pass_id = car.driver_id
                    self.managed_orders[car.driver_id] = (other.driver_id, race.race_clock + 12.0)
                    self.team_order_cooldown[car.team_id] = race.race_clock + 240.0
                    self.reverse_order_blocked_until[(other.driver_id, car.driver_id)] = race.race_clock + 540.0
                    if not damaged:
                        self.team_order_count[car.team_id] = self.team_order_count.get(car.team_id, 0) + 1
                    event_cb("TEAM_ORDER", f"PIT WALL ({car.team_short} / #{car.number} {car.code}): '{car.code}, release the faster {other.code}; reassess in clean air.'")
                    break

    def _review_queued_stop(self, car, event_cb):
        if car.drive_through_pending:
            return
        arrival = ((self.race.track.pit_entry_s - car.s) % self.race.track.length_m) / self.mean_speed
        # Give the driver a stable final instruction right at pit-entry commit point.
        if arrival < 2.0:
            return
        if car.strategy_status.startswith("Box: switch tyres for changing track conditions"):
            if arrival < 4.0:
                return
            previous_status = car.strategy_status
            revised = self.plan(car)
            if revised is None:
                wetness = 0.35 * self.race.wetness + 0.65 * self.projected_wetness(arrival + 25.0)
                advantage = self._lap_cost(car.compound, car.tire_wear, wetness, car.wing_damage)
                advantage -= self._lap_cost(car.next_compound, 0.02, wetness)
                if advantage < 0.5:
                    car.box_this_lap = False
                    car.radio_box_announced = False
                    car.inlap_push_announced = False
                    event_cb("STRATEGY", f"PIT WALL ({car.team_short} / #{car.number} {car.code}): 'Stay out; the weather crossover no longer justifies a stop.'")
                else:
                    # A marginal shift in the estimated window is not a weather
                    # reversal. Keep a committed call stable while tyres suit it.
                    car.strategy_status = previous_status
                return
            car.next_compound = revised.compound
            car.strategy_status = f"Box: {revised.reason}"
        else:
            laps = max(1, self.race.total_laps - car.laps_completed)
            wetness = 0.35 * self.race.wetness + 0.65 * self.projected_wetness(arrival + 25.0)
            future_wet = self.projected_wetness(arrival + self.lap_s * 1.6)
            options = self._fresh_options(car, laps, wetness)
            if not options:
                return
            best = min(options, key=lambda compound: options[compound][-1])
            queued = car.next_compound
            weather_change = (best in DRY) != (queued in DRY)
            gain = self._lap_cost(queued, 0.02, wetness) - self._lap_cost(best, 0.02, wetness)
            if (queued in DRY and future_wet >= 0.16 and best in DRY
                    and car.tire_wear < 0.85 and car.wing_damage < 0.65
                    and not (self._needs_second_dry(car) and laps <= 2)):
                car.box_this_lap = False
                car.radio_box_announced = False
                car.inlap_push_announced = False
                event_cb("STRATEGY", f"PIT WALL ({car.team_short} / #{car.number} {car.code}): 'Stay out; rain arriving shortly before pit entry.'")
                return
            if arrival < 4.0 and not (weather_change and best not in DRY):
                return
            if queued not in options or (weather_change and (gain > 1.5 or best not in DRY)):
                car.next_compound = best
                event_cb("STRATEGY", f"PIT WALL ({car.team_short} / #{car.number} {car.code}): 'Revised pit tyre order to {best} tyres for the latest conditions.'")

    def step(self, event_cb):
        race = self.race
        if race.race_clock < self.next_review:
            return
        self.next_review = race.race_clock + 2.0
        calls = []
        for car in race.cars:
            if not self.eligible(car) or car.in_pits:
                continue
            if car.box_this_lap:
                self._review_queued_stop(car, event_cb)
            else:
                call = self.plan(car)
                if call is not None:
                    calls.append(call)
        # Urgent repairs/weather take precedence; otherwise the car arriving
        # first gets the garage, independent of iteration order in standings.
        calls.sort(key=lambda call: (-call.priority, self.garage_arrival(call.car), call.car.pos))
        for call in calls:
            car = call.car
            if not call.urgent and self._garage_conflict(call):
                car.strategy_status = "Extend stint to avoid stacking behind teammate"
                continue
            car.box_this_lap = True
            car.next_compound = call.compound
            car.strategy_status = f"Box: {call.reason}"
            car.strategy_gain_s = round(call.gain_s, 1)
            instruction = ("Drive through the pit lane to serve the penalty" if car.drive_through_pending else
                           f"Box this lap for {call.compound} tyres — {call.reason}")
            event_cb("STRATEGY", f"PIT WALL ({car.team_short} / #{car.number} {car.code}): '{instruction}.'")
        self._team_orders(event_cb)
        for car in race.cars:
            if self.eligible(car):
                self.manage_pace(car, event_cb)

    def project_rejoin(self, car, flag_state=None):
        """Compute live pit-exit rejoin track coordinates, projected position, and nearby traffic gap."""
        race = self.race
        loss = self.pit_loss(car, flag_state=flag_state)
        rejoin_dist = car.total_dist - loss * self.mean_speed
        L = race.track.length_m
        rejoin_s = rejoin_dist % L
        smp = race.track.sample(rejoin_s)

        cars_ahead = 0
        min_gap = 99.0
        for other in race.cars:
            if other is car or other.dnf:
                continue
            if other.finished or other.total_dist > rejoin_dist:
                cars_ahead += 1
            if other.in_pits or other.finished:
                continue
            dist_delta = (other.total_dist - rejoin_dist)
            # Check cars physically close along circuit lap where traffic slows rejoin outlap
            signed_s = (other.s - rejoin_s + 0.5 * L) % L - 0.5 * L
            gap_s = abs(signed_s) / self.mean_speed
            if gap_s < min_gap and (signed_s > -0.6 * self.mean_speed):
                min_gap = gap_s
            elif abs(dist_delta) / self.mean_speed < min_gap:
                min_gap = abs(dist_delta) / self.mean_speed

        traffic_pen = 0.0 if race.flag_state in ("SC", "VSC") else self._rejoin_traffic(car, loss)
        car.rejoin_x = round(smp["x"], 2)
        car.rejoin_y = round(smp["y"], 2)
        car.rejoin_pos = min(len(race.cars), cars_ahead + 1)
        car.rejoin_traffic_s = round(min_gap, 2)
        car.rejoin_traffic_penalty = round(traffic_pen, 2)
        return {
            "x": car.rejoin_x,
            "y": car.rejoin_y,
            "pos": car.rejoin_pos,
            "traffic_s": car.rejoin_traffic_s,
            "traffic_penalty": car.rejoin_traffic_penalty,
            "pit_loss": round(loss, 1),
        }

    def battle_forecast(self, car):
        """Estimate catch/defend lap countdown against nearest rival using recent pace and tyre state."""
        race = self.race
        if car.dnf or car.finished or car.in_pits or race.flag_state != "GREEN":
            return None
        standings = [c for c in getattr(race, "standings", []) if not c.dnf]
        try:
            idx = standings.index(car)
        except ValueError:
            return None

        def est_lap_s(target):
            rec = getattr(target, "recent_lap_times", None) or []
            if rec:
                return sum(rec[-2:]) / len(rec[-2:])
            pace_mod = {"ATTACK": -0.35, "PUSH": -0.18, "BALANCED": 0.0, "CONSERVE": 0.30}.get(target.pace_mode, 0.0)
            perf_mod = (82.0 - getattr(target, "car_perf_index", 82.0)) * 0.14
            return self.lap_s + self._lap_cost(target.compound, target.tire_wear, race.wetness, target.wing_damage) + pace_mod + perf_mod

        my_pace = est_lap_s(car)
        if idx > 0:
            ahead = standings[idx - 1]
            if not ahead.in_pits and 0.25 < car.interval_ahead < 18.0:
                rate = est_lap_s(ahead) - my_pace
                if rate >= 0.12:
                    return {
                        "type": "CATCH",
                        "target": ahead.code,
                        "target_pos": ahead.pos,
                        "rate_s": round(rate, 2),
                        "laps": min(25, max(1, math.ceil(car.interval_ahead / rate))),
                    }
        if idx + 1 < len(standings):
            behind = standings[idx + 1]
            gap_behind = getattr(behind, "interval_ahead", 0.0)
            if not behind.in_pits and 0.25 < gap_behind < 12.0:
                rate = my_pace - est_lap_s(behind)
                if rate >= 0.15:
                    return {
                        "type": "DEFEND",
                        "target": behind.code,
                        "target_pos": behind.pos,
                        "rate_s": round(rate, 2),
                        "laps": min(25, max(1, math.ceil(gap_behind / rate))),
                    }
        return None

    def advise(self, car):
        """Evaluate full pit/undercut/overcut window and rejoin telemetry without mutating orders."""
        proj = self.project_rejoin(car)
        if car.in_pits or car.dnf or car.finished:
            car.strategy_advice = None
            return None
        call = self.plan(car)
        cand_comp = call.compound if call is not None else car.next_compound
        fresh_two = 2.0 * (self._lap_cost(car.compound, car.tire_wear, self.race.wetness, car.wing_damage) - self._lap_cost(cand_comp, 0.02, self.race.wetness))
        undercut_s = round(fresh_two - proj["traffic_penalty"] * 0.65, 1)
        if call is not None:
            mode = "BOX_NOW"
            if "undercut" in call.reason:
                mode = "UNDERCUT"
            elif "cover" in call.reason:
                mode = "COVER"
            car.strategy_gain_s = round(call.gain_s, 1)
            advice = {
                "action": "BOX",
                "mode": mode,
                "compound": call.compound,
                "reason": call.reason,
                "gain_s": round(call.gain_s, 1),
                "undercut_s": undercut_s,
                "urgent": bool(call.urgent),
                "rejoin_pos": proj["pos"],
                "traffic_s": proj["traffic_s"],
            }
            car.strategy_advice = advice
            return call
        mode = "OVERCUT" if "traffic" in (car.strategy_status or "") else "STAY_OUT"
        car.strategy_advice = {
            "action": "STAY_OUT",
            "mode": mode,
            "compound": car.next_compound,
            "reason": car.strategy_status or "Monitor pace and track position",
            "gain_s": 0.0,
            "undercut_s": undercut_s,
            "urgent": False,
            "rejoin_pos": proj["pos"],
            "traffic_s": proj["traffic_s"],
        }
        return None
