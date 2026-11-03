"""Realistic Formula 1 Team Radio System.
Generates situational, event-driven, technical, iconic driver, pit strategy, battle, and incident radio chatter.
All radio transmissions are triggered by genuine in-race events (mode changes, overtakes, spins, pit stops,
contact, safety cars, tyre cliffs, weather transitions, victory) rather than random background timers.
"""

from __future__ import annotations
import random
from typing import Any

# -----------------------------------------------------------------------------
# Driver-Specific Iconic & Characteristic Radio Transmissions
# -----------------------------------------------------------------------------
DRIVER_ICONIC_RADIOS: dict[str, list[str]] = {
    "hamilton": [
        "Bono, my tyres are dead!",
        "Still I rise! Keep pushing team, great balance on the car.",
        "This car is bouncing down the straight, but the pace is there.",
        "He didn't give me any space on the exit, man!",
        "It's Hammer Time! Pushing to the limit.",
    ],
    "verstappen": [
        "Simply lovely mate! Car is hooked up.",
        "Mate, why is he weaving on the straight?! That's so dangerous.",
        "Can we turn up the engine mode? I'm cruising here.",
        "My steering wheel has a slight vibration, check the data.",
        "Haha, yes boys! Car is on rails today.",
    ],
    "alonso": [
        "All the time you have to leave a space! All the time!",
        "GP2 engine! GP2! Argh!",
        "What a move! The car feels competitive today, let's go!",
        "I have no grip on the rear, but I will fight like a lion until the end.",
        "Karma! He didn't respect the track limits.",
    ],
    "leclerc": [
        "We are checking... Plan C, confirm Plan C!",
        "Nooo! What happened to the rear grip?!",
        "The car is sliding too much in Sector 2, check differential settings.",
        "Understood, head down and push.",
        "I gave it everything into Turn 1, car rotated nicely.",
    ],
    "sainz": [
        "Smooth operator... smooooth operaaator!",
        "Stop inventing! We need to focus on our own strategy.",
        "Tyres are holding on nicely, I can extend this stint.",
        "I'm quicker than the car ahead, what's the plan team?",
        "Clean air is king today. Pace is very strong.",
    ],
    "norris": [
        "It's Friday then... Saturday, Sunday, what?!",
        "My drink isn't working... no fluids in the car!",
        "He pushed me wide at the hairpin, check if he broke track limits.",
        "Car feels amazing! Keep me updated on the gap.",
        "Radio check! Loud and clear, let's keep hunting.",
    ],
    "russell": [
        "Crikey! That was close with the wall!",
        "I think we've got the pace for a podium today, keep the pressure on.",
        "Massive front vibration, check tyre wear on telemetry.",
        "He completely turned in on me at the apex!",
        "Understood team, managing the gap behind.",
    ],
    "piastri": [
        "Copy.",
        "Understood, closing the gap lap by lap.",
        "Tyres are good, plenty of life left in this set.",
        "Front wing has slight contact, but handling feels unchanged.",
        "Pace is comfortable, let's stick to the target delta.",
    ],
    "raikkonen": [
        "Leave me alone, I know what to do!",
        "Just leave me alone, I know what I'm doing.",
        "Is the drink connected?! I have no drink!",
        "Bwoah... car was okay, could be faster.",
        "Give me full power, I don't care about the temps.",
    ],
    "vettel": [
        "Mein Gott, muss das sein?!",
        "Grazie a tutti! Bella macchina, bella macchina!",
        "Blue flags, come on! I'm losing so much time in Sector 2!",
        "Ring-ding-ding-ding-ding! What a lap!",
        "He brake-tested me! Did you see that?!",
    ],
    "senna": [
        "If you no longer go for a gap that exists, you are no longer a racing driver.",
        "The balance is pure perfection today. Pushing to the edge.",
        "I have a feeling about this race, car is talking to me.",
        "Pole position pace. Every apex is precise.",
    ],
    "schumacher": [
        "Maximum attack for the next four laps. Let's make the gap.",
        "Car balance is very stable. Focus on every single apex.",
        "Pace is strong. We execute the strategy lap by lap.",
        "Understood. Keep the pit crew standing by.",
    ],
    "lauda": [
        "The car is understeering too much, adjust front flap at the stop.",
        "A wise man gets more use from his enemies than a fool from his friends.",
        "Keep the mind cool, the race is won at the finish.",
    ],
    "prost": [
        "Everything is calculated. Stint length is going according to plan.",
        "Preserve the front left through the long right-handers.",
        "Let the others burn their tyres, we strike in the final stint.",
    ],
    "hakkinen": [
        "Yes... it was a good lap. Car is fast.",
        "Sisu. Flat out through the sweepers.",
        "Maximum concentration into Turn 1.",
    ],
    "mansell": [
        "Red 5 giving it absolute everything!",
        "Huge G-forces through the neck, but I'm not lifting!",
        "Smoke in the cockpit, but I am keeping my foot pinned!",
    ],
    "tsunoda": [
        "What is this guy doing?! What a complete joke!",
        "Traffic! Always traffic in Sector 3!",
        "Understood! Pushing flat out!",
    ],
    "perez": [
        "He pushed me completely wide at the apex!",
        "Rears are getting hot, need some clean air to manage temps.",
        "Great traction out of Turn 4, closing the gap.",
    ],
    "bottas": [
        "To whom it may concern... let's push.",
        "Front axle temperature is rising, doing some lift and coast.",
        "Clean air ahead, setting my rhythm.",
    ],
    "albon": [
        "They race me so hard!",
        "Tyre deg is massive today, car is snapping on corner exit.",
        "Front end is biting nicely in the slow chicanes.",
    ],
    "gasly": [
        "What did he just do?! That was completely crazy!",
        "Mega pace! Let's hunt them down.",
        "Car is lively in the high-speed section, loving the balance.",
    ],
}

# -----------------------------------------------------------------------------
# Driver-Specific Event Reactions
# -----------------------------------------------------------------------------
DRIVER_PUSH_RADIOS: dict[str, list[str]] = {
    "hamilton": [
        "It's Hammer Time! Pushing to the limit.",
        "Still I rise! Giving it everything, let's close this gap.",
    ],
    "verstappen": [
        "Can we turn up the engine mode? Pushing flat out boys!",
        "Understood, maximum attack! Car is hooked up.",
    ],
    "norris": [
        "Car feels amazing! Keep me updated on the gap, let's hunt!",
        "Pushing like hell! Time to hunt them down.",
    ],
    "leclerc": [
        "Understood, head down and push! Giving it everything.",
        "Push mode confirmed, car is rotating nicely into Turn 1.",
    ],
    "alonso": [
        "I will fight like a lion until the end! Let's go!",
        "Maximum attack, full power! Let's close this down!",
    ],
    "sainz": [
        "I have way more pace than the car ahead, let's attack!",
        "Pushing hard! Tyres are holding on nicely.",
    ],
    "russell": [
        "We've got the pace for a podium today, let's put the hammer down!",
        "Understood! Giving it 100% on every apex.",
    ],
    "piastri": [
        "Copy. Pushing now.",
        "Understood, closing the gap lap by lap.",
    ],
    "tsunoda": [
        "Understood! Pushing flat out!",
        "Maximum pace, let's get them!",
    ],
    "raikkonen": [
        "Give me full power, I don't care about the temps.",
        "Yeah yeah, I'm pushing.",
    ],
    "vettel": [
        "Full attack now! Bella macchina!",
        "Understood, pushing to the absolute limit.",
    ],
    "senna": [
        "Pole position pace. Pushing to the edge.",
        "If you no longer go for a gap that exists, you are no longer a racing driver.",
    ],
    "schumacher": [
        "Maximum attack for the next four laps. Let's make the gap.",
        "Pace is strong. We execute the strategy lap by lap.",
    ],
}

DRIVER_OVERTAKEN_RADIOS: dict[str, list[str]] = {
    "alonso": [
        "All the time you have to leave a space! All the time!",
        "Karma! He didn't respect track limits at the apex!",
    ],
    "hamilton": [
        "He didn't give me any space on the exit, man!",
        "He breezed past on the straight, straight-line deficit is huge.",
    ],
    "verstappen": [
        "Mate, why is he weaving on the straight?! That's so dangerous.",
        "I had zero rear grip out of the slow corner, sitting duck on the straight.",
    ],
    "norris": [
        "He pushed me wide at the apex! Check if he broke track limits!",
        "I had no battery to defend with, he sailed past on the straight.",
    ],
    "leclerc": [
        "Nooo! What happened to the rear grip?! Lost the position into Turn {turn}!",
        "He was so fast down the inside. The car was sliding everywhere.",
    ],
    "russell": [
        "Crikey! He completely turned in on me at the apex!",
        "He had too much straight-line speed with DRS, couldn't defend.",
    ],
    "tsunoda": [
        "What is this guy doing?! What a complete joke!",
        "Ah! Zero traction on corner exit, lost the place!",
    ],
    "albon": [
        "They race me so hard!",
        "Tyre deg is massive, car snapped and I couldn't hold the inside.",
    ],
    "piastri": [
        "Lost the position into Turn {turn}. He had strong top speed.",
        "Copy. Defending was impossible with that DRS delta.",
    ],
    "vettel": [
        "Mein Gott, muss das sein?!",
        "He completely squeezed me onto the grass into Turn {turn}!",
    ],
    "perez": [
        "He pushed me completely wide at the apex of Turn {turn}!",
        "Rears are overheated, I had zero drive out of the corner.",
    ],
}

DRIVER_OVERTAKE_RADIOS: dict[str, list[str]] = {
    "verstappen": [
        "Simply lovely mate! Car is on rails today.",
        "Haha, yes boys! That was a clean move into Turn {turn}.",
    ],
    "sainz": [
        "Smooth operator... smooooth operaaator! That is P{new_p}!",
        "Clean move! Pace is very strong in clear air.",
    ],
    "alonso": [
        "What a move! The car feels competitive today, let's go!",
        "Karma! We are faster than him!",
    ],
    "hamilton": [
        "Great move into Turn {turn}! Let's keep hunting down the next one.",
        "Yes! Clean exit out of Turn {turn}, great tow.",
    ],
    "norris": [
        "Haha, through on #{other_code}! That was on the absolute edge!",
        "Job done! Keep me updated on the gap ahead.",
    ],
    "piastri": [
        "Copy. That's one done.",
        "Understood. Moving forward.",
    ],
    "bottas": [
        "To whom it may concern... that is P{new_p}!",
    ],
    "gasly": [
        "Mega move! Let's hunt them down!",
    ],
    "vettel": [
        "Ring-ding-ding-ding-ding! What a pass!",
        "Grazie ragazzi! Clean move into Turn {turn}!",
    ],
}

# -----------------------------------------------------------------------------
# Situational Radio Message Collections (Event-Driven)
# -----------------------------------------------------------------------------
PUSH_MODE_RADIOS = [
    "PIT WALL ({short}): 'Confirming {mode} mode, #{num} {code}! Hammer time!'",
    "PIT WALL ({short}): '{mode} mode active! Clear air ahead, deploy maximum pace!'",
    "PIT WALL ({short}): 'Scenario 8, {mode} mode! Let's close this gap down now!'",
    "PIT WALL ({short}): 'Deploy everything #{code}! Overtake boost available on the straight!'",
    "PIT WALL ({short}): 'Gap ahead is under one second. Turn up the engine mode and attack!'",
    "DRIVER (#{num} {code}): 'Understood team, giving it everything!'",
    "DRIVER (#{num} {code}): 'Copy, maximum attack! Let's hunt them down!'",
    "DRIVER (#{num} {code}): 'Pushing flat out! Car feels hooked up!'",
    "DRIVER (#{num} {code}): 'Batteries armed! Going for the overtake!'",
    "DRIVER (#{num} {code}): 'Car feels amazing today, let's turn up the wick!'",
]

CONSERVE_MODE_RADIOS = [
    "PIT WALL ({short}): 'Switch to Conserve pace, #{code}. Look after the front tyres.'",
    "PIT WALL ({short}): 'Recharge mode on. Lift and coast into Turn {turn} to harvest energy.'",
    "PIT WALL ({short}): 'Manage tyre temperatures through the high-speed sector.'",
    "DRIVER (#{num} {code}): 'Copy, lifting and coasting on entry.'",
    "DRIVER (#{num} {code}): 'Understood, managing the rears to the end of the stint.'",
]

OVERTAKEN_RADIOS = [
    "DRIVER (#{num} {code}): 'He got me into Turn {turn}! He had massive straight-line speed with DRS!'",
    "DRIVER (#{num} {code}): 'I had zero traction on corner exit, couldn't defend into Turn {turn}!'",
    "DRIVER (#{num} {code}): 'Battery was empty, I was a sitting duck down that straight!'",
    "DRIVER (#{num} {code}): 'He forced me wide at the apex of Turn {turn}! Did the stewards see that?!'",
    "DRIVER (#{num} {code}): 'Lost the position into Turn {turn}. Dirty air is killing my front tyres.'",
    "DRIVER (#{num} {code}): 'He divebombed from so far back! That was completely over the edge!'",
    "DRIVER (#{num} {code}): 'Ah, lost position to #{other_code}. Car was sliding on the kerb.'",
    "PIT WALL ({short}): 'Copy #{code}, stay calm. Long race ahead, stay in his DRS train.'",
    "PIT WALL ({short}): 'Understood #{code}, head down. We will get him back on pit strategy.'",
    "PIT WALL ({short}): 'Tough break #{code}. Keep the pressure on, his tyres are wearing faster.'",
]

OVERTAKE_SUCCESS_RADIOS = [
    "DRIVER (#{num} {code}): 'Yes! Job done into Turn {turn}! That is P{new_p}!'",
    "DRIVER (#{num} {code}): 'Through on #{other_code}! Car felt incredible on the brakes!'",
    "DRIVER (#{num} {code}): 'Clean pass! Now let's hunt down the next one!'",
    "DRIVER (#{num} {code}): 'Haha, what a move into Turn {turn}! P{new_p} secured!'",
    "PIT WALL ({short}): 'Mega move #{code}! That is P{new_p}. Settle into your pace.'",
    "PIT WALL ({short}): 'Clinical pass #{code}! P{new_p} secured. Now build the gap!'",
]

BOX_CALL_RADIOS = [
    "PIT WALL ({short}): 'Box, box, box #{num} {code}! In this lap, confirm {comp} tyres.'",
    "PIT WALL ({short}): 'Box this lap, box this lap. Watch pit entry speed limit.'",
    "PIT WALL ({short}): 'In this lap, pit delta is positive. Push on pit entry.'",
    "PIT WALL ({short}): 'Box now! We are pitting for {comp} tyres, crew is ready.'",
    "DRIVER (#{num} {code}): 'Copy, boxing this lap. Keep the crew sharp!'",
    "DRIVER (#{num} {code}): 'Tyres are completely dead! Zero traction on exit, box this lap!'",
    "DRIVER (#{num} {code}): 'The cliff is here. Fronts are sliding everywhere, bringing it in!'",
]

PIT_EXIT_RADIOS = [
    "PIT WALL ({short}): 'Clean stop, {dur:.1f}s stationary! Watch the white blend line at pit exit.'",
    "PIT WALL ({short}): 'Exit is clear! Cold tyres, manage the delta through Turn 1 and 2.'",
    "PIT WALL ({short}): 'Good stop team! Track position secured ahead of traffic, hammer time now!'",
    "PIT WALL ({short}): 'Out-lap is critical, push hard to defend against the undercut!'",
    "DRIVER (#{num} {code}): 'Copy, cold tyres are snappy on the kerbs. Building temps.'",
]

DIRTY_AIR_AND_BATTLE_RADIOS = [
    "DRIVER (#{num} {code}): 'I can't follow in this dirty air! The front tyres are overheating!'",
    "DRIVER (#{num} {code}): 'He is moving under braking at Turn {turn}! That is dangerous!'",
    "DRIVER (#{num} {code}): 'Tell him to hurry up or move! He's parking it on every apex!'",
    "DRIVER (#{num} {code}): 'I have way more pace than him, give me more engine mode!'",
    "DRIVER (#{num} {code}): 'He's weaving all over the straight trying to break the tow!'",
    "DRIVER (#{num} {code}): 'I'm burning up my rear tyres sitting in his gearbox!'",
    "DRIVER (#{num} {code}): 'He squeezed me off the track! Did you report that to stewards?!'",
    "PIT WALL ({short}): 'Understood #{num} {code}, stay patient. DRS zone coming up, prepare the battery.'",
    "PIT WALL ({short}): 'Mode 7 is available for the straight, use overtake boost on exit.'",
]

BLUE_FLAG_RADIOS = [
    "DRIVER (#{num} {code}): 'Blue flags! Blue flags! Why is this backmarker still racing me?!'",
    "DRIVER (#{num} {code}): 'Come on, get this guy out of the way! I just lost a second in Sector 2!'",
    "DRIVER (#{num} {code}): 'Tell the blue-flag car to move, he's parking right on the racing line!'",
]

CONTACT_RADIOS = [
    "DRIVER (#{num} {code}): 'He just turned right across my nose! Did you see that?!'",
    "DRIVER (#{num} {code}): 'I was ahead at the apex and he squeezed me into the wall!'",
    "DRIVER (#{num} {code}): 'Wheel-to-wheel contact! Check front wing data on telemetry!'",
    "DRIVER (#{num} {code}): 'Front wing is damaged! I have massive steering vibrations!'",
    "DRIVER (#{num} {code}): 'Someone touched my rear wheel, check for a puncture!'",
    "DRIVER (#{num} {code}): 'Debris on the racing line at Turn {turn}, almost took off my floor!'",
    "PIT WALL ({short}): 'Copy #{num} {code}, telemetry shows tyre pressures holding. Stay out.'",
    "PIT WALL ({short}): 'We see front wing endplate loss (-15% downforce). Report handling balance.'",
]

FASTEST_LAP_RADIOS = [
    "PIT WALL ({short}): 'Fastest lap of the race, #{num} {code}! Purple in sector 2 ({time_str}). Mega drive mate!'",
    "PIT WALL ({short}): 'Purple lap! You are the fastest car on track by three tenths. Keep this rhythm.'",
    "DRIVER (#{num} {code}): 'Yeah! The car felt on rails that lap!'",
    "DRIVER (#{num} {code}): 'That was a mega lap! We have serious pace today.'",
]

TYRE_CLIFF_RADIOS = [
    "DRIVER (#{num} {code}): 'The cliff is here! Tyres are dead, I'm losing five tenths a lap!'",
    "DRIVER (#{num} {code}): 'I have zero rear traction out of slow corners, sliding everywhere!'",
    "DRIVER (#{num} {code}): 'Front left is down to the canvas, car is completely understeering.'",
    "PIT WALL ({short}): 'Lap times are falling off, losing three tenths a lap. Pit window is open.'",
    "PIT WALL ({short}): 'Tyre temps are critical, do some lift and coast into Turn 1.'",
]

WEATHER_RADIOS = [
    "DRIVER (#{num} {code}): 'I can see rain spots on my visor at Turn {turn}! Rain is starting!'",
    "DRIVER (#{num} {code}): 'Track is getting greasy, especially on the painted kerbs.'",
    "DRIVER (#{num} {code}): 'Standing water into Turn 1! Inters needed very soon!'",
    "PIT WALL ({short}): 'Weather radar confirms rain cell arriving in 2 minutes. Stand by for Inters call.'",
    "PIT WALL ({short}): 'Track is drying quickly on the racing line, prepare for slicks.'",
]

SPIN_RADIOS = [
    "DRIVER (#{num} {code}): 'I spun! I lost the rear on the kerb into Turn {turn}!'",
    "DRIVER (#{num} {code}): 'Big snap on corner exit! Checking for flat spots...'",
    "DRIVER (#{num} {code}): 'Car snapped completely without warning at Turn {turn}!'",
    "PIT WALL ({short}): 'Yellow flag Turn {turn}, #{code} had a spin. Check tyres, can you rejoin?'",
]

DAMAGE_RADIOS = [
    "DRIVER (#{num} {code}): 'Front wing damage! Massive steering vibrations into Turn {turn}!'",
    "DRIVER (#{num} {code}): 'I feel damage on the front end, car is understeering heavily!'",
    "PIT WALL ({short}): 'Telemetry shows wing endplate loss on #{code}. Box this lap to change the nose.'",
]

SAFETY_CAR_RADIOS = [
    "PIT WALL ({short}): 'Safety Car deployed! Safety Car! Delta positive, stay positive on the delta!'",
    "PIT WALL ({short}): 'Virtual Safety Car! VSC deployed! Watch your dash delta immediately!'",
    "PIT WALL ({short}): 'Safety Car deployed! Pack bunching up, maintain delta to car ahead.'",
]

SAFETY_CAR_IN_RADIOS = [
    "PIT WALL ({short}): 'Safety Car in this lap! Warm the brakes and tyres, full-throttle restart!'",
    "PIT WALL ({short}): 'Safety Car peeling in this lap. Leader controls the restart to the line.'",
]

RACE_WIN_RADIOS = [
    "PIT WALL ({short}): 'P1! P1! Chequered flag #{code}! What a fantastic drive, champion!'",
    "DRIVER (#{num} {code}): 'YESSSS! Haha! What a race! Thank you everyone back at the factory, amazing car!'",
]

AMBIENT_TECHNICAL_RADIOS = [
    "PIT WALL ({short}): 'Mode 8, fail 20. Fail 20 on the steering wheel.'",
    "PIT WALL ({short}): 'Scenario 7 for two laps, let's close the gap to the car ahead.'",
    "PIT WALL ({short}): 'Recharge on, recharge on. We need battery for the DRS straight.'",
    "PIT WALL ({short}): 'Look after the front left tyre, high lateral load in Sector 2.'",
    "PIT WALL ({short}): 'Gap behind is 2.8s, you are pulling away by two tenths per lap.'",
    "DRIVER (#{num} {code}): 'Wind has picked up heavily down the main straight, huge headwind.'",
    "DRIVER (#{num} {code}): 'Something is loose in the cockpit near my feet, checking pedal box.'",
    "DRIVER (#{num} {code}): 'The kerbs are very harsh today, car is bottoming out on the floor.'",
    "DRIVER (#{num} {code}): 'Drink bottle is empty... it is like a sauna in this cockpit!'",
    "DRIVER (#{num} {code}): 'Debris on the verge at Turn {turn}, stay alert.'",
]


class RadioDispatcher:
    """
    Manages event-driven team radio broadcast timing, cooldowns, and situational dialogue.
    Transmissions occur upon explicit race events (push/max mode, overtakes, spins, damage,
    pit stops, fastest laps, safety cars, weather shifts) rather than random background timers.
    """

    def __init__(self) -> None:
        self.radio_timer: float = 0.0
        self.last_global_radio_clock: float = -99.0
        self.last_driver_radio_clock: dict[str, float] = {}
        self.last_contact_radio_clock: float = -99.0
        self.last_box_radio_clock: float = -99.0

    def _can_broadcast(
        self,
        car: Any,
        clock: float,
        min_global_cd: float = 2.2,
        min_driver_cd: float = 14.0,
    ) -> bool:
        """Rate limit broadcasts so radio feed remains readable and distinct."""
        if clock > 0.0 and (clock - self.last_global_radio_clock) < min_global_cd:
            return False
        drv_id = getattr(car, "driver_id", "") or str(getattr(car, "number", ""))
        if clock > 0.0 and (clock - self.last_driver_radio_clock.get(drv_id, -99.0)) < min_driver_cd:
            return False
        return True

    def _mark_broadcast(self, car: Any, clock: float) -> None:
        """Update cooldown timestamps for the driver and globally."""
        if clock > 0.0:
            self.last_global_radio_clock = clock
            drv_id = getattr(car, "driver_id", "") or str(getattr(car, "number", ""))
            self.last_driver_radio_clock[drv_id] = clock
        if hasattr(car, "last_radio_time") and clock > 0.0:
            car.last_radio_time = clock

    # -------------------------------------------------------------------------
    # Event: Push / Max / Attack / Boost Mode Activation
    # -------------------------------------------------------------------------
    def trigger_push_mode(
        self,
        car: Any,
        mode_name: str,
        is_pit_wall: bool,
        event_cb,
        clock: float = 0.0,
        turn: int = 1,
    ) -> None:
        """Triggered when driver or pit wall activates Push / Attack / Max / Boost mode."""
        if not is_pit_wall and not self._can_broadcast(car, clock, min_global_cd=1.8, min_driver_cd=10.0):
            return
        self._mark_broadcast(car, clock)

        drv_id = getattr(car, "driver_id", "").lower()
        iconic_quotes = DRIVER_PUSH_RADIOS.get(drv_id, [])

        if not is_pit_wall and iconic_quotes and random.random() < 0.70:
            quote = random.choice(iconic_quotes)
            msg = f"TEAM RADIO (#{car.number} {car.code}): '{quote}'"
        else:
            tpl = random.choice(PUSH_MODE_RADIOS)
            msg = tpl.format(
                num=car.number,
                code=car.code,
                short=car.team_short,
                mode=mode_name,
                turn=turn,
            )
        event_cb("RADIO", msg)

    # -------------------------------------------------------------------------
    # Event: Conserve / Harvest Mode Activation
    # -------------------------------------------------------------------------
    def trigger_conserve_mode(
        self,
        car: Any,
        event_cb,
        clock: float = 0.0,
        turn: int = 1,
        is_pit_wall: bool = False,
    ) -> None:
        """Triggered when driver or pit wall activates Conserve / Harvest mode."""
        if not is_pit_wall and not self._can_broadcast(car, clock, min_global_cd=2.5, min_driver_cd=16.0):
            return
        self._mark_broadcast(car, clock)

        tpl = random.choice(CONSERVE_MODE_RADIOS)
        msg = tpl.format(
            num=car.number,
            code=car.code,
            short=car.team_short,
            turn=turn,
        )
        event_cb("RADIO", msg)

    # -------------------------------------------------------------------------
    # Event: Driver Gets Overtaken
    # -------------------------------------------------------------------------
    def trigger_overtaken(
        self,
        overtaken_car: Any,
        overtaker_car: Any,
        turn: int,
        event_cb,
        clock: float = 0.0,
        maneuver: str = "",
    ) -> None:
        """Triggered when a driver is passed by an opponent."""
        if not self._can_broadcast(overtaken_car, clock, min_global_cd=2.0, min_driver_cd=12.0):
            return
        self._mark_broadcast(overtaken_car, clock)

        drv_id = getattr(overtaken_car, "driver_id", "").lower()
        iconic_quotes = DRIVER_OVERTAKEN_RADIOS.get(drv_id, [])

        if iconic_quotes and random.random() < 0.75:
            quote = random.choice(iconic_quotes)
            quote_formatted = quote.format(turn=turn) if "{turn}" in quote else quote
            msg = f"TEAM RADIO (#{overtaken_car.number} {overtaken_car.code}): '{quote_formatted}'"
        else:
            # Divebomb complaints only trigger if the maneuver was an authentic divebomb
            available_radios = [
                tpl for tpl in OVERTAKEN_RADIOS
                if "divebomb" not in tpl.lower() or maneuver == "DIVEBOMB"
            ]
            tpl = random.choice(available_radios)
            msg = tpl.format(
                num=overtaken_car.number,
                code=overtaken_car.code,
                short=overtaken_car.team_short,
                other_code=overtaker_car.code,
                turn=turn,
            )
        event_cb("RADIO", msg)

    # -------------------------------------------------------------------------
    # Event: Successful Overtake
    # -------------------------------------------------------------------------
    def trigger_overtake_success(
        self,
        overtaker_car: Any,
        overtaken_car: Any,
        new_p: int,
        turn: int,
        event_cb,
        clock: float = 0.0,
    ) -> None:
        """Triggered when a driver successfully passes an opponent."""
        if not self._can_broadcast(overtaker_car, clock, min_global_cd=2.0, min_driver_cd=12.0):
            return
        self._mark_broadcast(overtaker_car, clock)

        drv_id = getattr(overtaker_car, "driver_id", "").lower()
        iconic_quotes = DRIVER_OVERTAKE_RADIOS.get(drv_id, [])

        if iconic_quotes and random.random() < 0.70:
            quote = random.choice(iconic_quotes)
            quote_formatted = quote.format(turn=turn, new_p=new_p, other_code=overtaken_car.code)
            msg = f"TEAM RADIO (#{overtaker_car.number} {overtaker_car.code}): '{quote_formatted}'"
        else:
            tpl = random.choice(OVERTAKE_SUCCESS_RADIOS)
            msg = tpl.format(
                num=overtaker_car.number,
                code=overtaker_car.code,
                short=overtaker_car.team_short,
                other_code=overtaken_car.code,
                new_p=new_p,
                turn=turn,
            )
        event_cb("RADIO", msg)

    # -------------------------------------------------------------------------
    # Event: Overtake Reaction Dispatcher (Handles either side of an overtake)
    # -------------------------------------------------------------------------
    def trigger_overtake_event(
        self,
        overtaker: Any,
        overtaken: Any,
        new_p: int,
        turn: int,
        event_cb,
        clock: float = 0.0,
        maneuver: str = "",
    ) -> None:
        """Dispatches an authentic radio response from either the overtaken driver or overtaker."""
        # Favor the overtaken driver expressing frustration or pit wall reassurance ~55% of the time
        if random.random() < 0.55:
            if self._can_broadcast(overtaken, clock, min_global_cd=2.0, min_driver_cd=12.0):
                self.trigger_overtaken(overtaken, overtaker, turn, event_cb, clock, maneuver=maneuver)
                return
            if self._can_broadcast(overtaker, clock, min_global_cd=2.0, min_driver_cd=12.0):
                self.trigger_overtake_success(overtaker, overtaken, new_p, turn, event_cb, clock)
                return
        else:
            if self._can_broadcast(overtaker, clock, min_global_cd=2.0, min_driver_cd=12.0):
                self.trigger_overtake_success(overtaker, overtaken, new_p, turn, event_cb, clock)
                return
            if self._can_broadcast(overtaken, clock, min_global_cd=2.0, min_driver_cd=12.0):
                self.trigger_overtaken(overtaken, overtaker, turn, event_cb, clock, maneuver=maneuver)
                return

    # -------------------------------------------------------------------------
    # Event: Pit Stop In-Lap (Box Call)
    # -------------------------------------------------------------------------
    def trigger_box_call(self, car: Any, event_cb) -> None:
        """Triggered when a car confirms pit stop this lap."""
        tpl = random.choice(BOX_CALL_RADIOS)
        comp = getattr(car, "next_compound", getattr(car, "compound", "TYRES"))
        msg = tpl.format(
            num=car.number,
            code=car.code,
            short=car.team_short,
            comp=comp,
        )
        event_cb("RADIO", msg)

    # -------------------------------------------------------------------------
    # Event: Pit Stop Out-Lap (Exit)
    # -------------------------------------------------------------------------
    def trigger_pit_exit(self, car: Any, duration: float, event_cb) -> None:
        """Triggered when a car rejoins the track after a pit stop."""
        tpl = random.choice(PIT_EXIT_RADIOS)
        msg = tpl.format(
            num=car.number,
            code=car.code,
            short=car.team_short,
            dur=duration,
        )
        event_cb("RADIO", msg)

    # -------------------------------------------------------------------------
    # Event: Physical Contact / Collision
    # -------------------------------------------------------------------------
    def trigger_contact(self, c1: Any, c2: Any, turn: int, event_cb, clock: float) -> None:
        """Triggered upon significant physical collision between two cars."""
        if clock > 0.0 and (clock - self.last_contact_radio_clock) < 7.0:
            return
        self.last_contact_radio_clock = clock
        talker, _ = (c1, c2) if random.random() < 0.5 else (c2, c1)
        self._mark_broadcast(talker, clock)
        tpl = random.choice(CONTACT_RADIOS)
        msg = tpl.format(
            num=talker.number,
            code=talker.code,
            short=talker.team_short,
            turn=turn,
        )
        event_cb("RADIO", msg)

    # -------------------------------------------------------------------------
    # Event: Fastest Lap of the Race
    # -------------------------------------------------------------------------
    def trigger_fastest_lap(self, car: Any, lap_time_str: str, event_cb) -> None:
        """Triggered when a car sets the fastest purple lap of the race."""
        tpl = random.choice(FASTEST_LAP_RADIOS)
        msg = tpl.format(
            num=car.number,
            code=car.code,
            short=car.team_short,
            time_str=lap_time_str,
        )
        event_cb("RADIO", msg)

    # -------------------------------------------------------------------------
    # Event: Spin / Off-Track Excursion
    # -------------------------------------------------------------------------
    def trigger_spin(self, car: Any, turn: int, event_cb, clock: float = 0.0) -> None:
        """Triggered when a driver loses control and spins."""
        if not self._can_broadcast(car, clock, min_global_cd=2.0, min_driver_cd=10.0):
            return
        self._mark_broadcast(car, clock)
        tpl = random.choice(SPIN_RADIOS)
        msg = tpl.format(
            num=car.number,
            code=car.code,
            short=car.team_short,
            turn=turn,
        )
        event_cb("RADIO", msg)

    # -------------------------------------------------------------------------
    # Event: Structural / Wing Damage Sustained
    # -------------------------------------------------------------------------
    def trigger_damage(self, car: Any, dmg_type: str, turn: int, event_cb, clock: float = 0.0) -> None:
        """Triggered when a car suffers front wing damage or puncture."""
        if not self._can_broadcast(car, clock, min_global_cd=2.0, min_driver_cd=10.0):
            return
        self._mark_broadcast(car, clock)
        tpl = random.choice(DAMAGE_RADIOS)
        msg = tpl.format(
            num=car.number,
            code=car.code,
            short=car.team_short,
            turn=turn,
        )
        event_cb("RADIO", msg)

    # -------------------------------------------------------------------------
    # Event: Tyre Cliff Crossed
    # -------------------------------------------------------------------------
    def trigger_tyre_cliff(self, car: Any, event_cb, clock: float = 0.0) -> None:
        """Triggered when tyre degradation crosses the cliff wear threshold."""
        if not self._can_broadcast(car, clock, min_global_cd=3.0, min_driver_cd=25.0):
            return
        self._mark_broadcast(car, clock)

        drv_id = getattr(car, "driver_id", "").lower()
        if drv_id == "hamilton":
            msg = f"TEAM RADIO (#{car.number} {car.code}): 'Bono, my tyres are dead!'"
        elif drv_id == "leclerc":
            msg = f"TEAM RADIO (#{car.number} {car.code}): 'The rear tyres are gone, sliding everywhere!'"
        else:
            tpl = random.choice(TYRE_CLIFF_RADIOS)
            msg = tpl.format(num=car.number, code=car.code, short=car.team_short)
        event_cb("RADIO", msg)

    # -------------------------------------------------------------------------
    # Event: Safety Car / VSC Deployed
    # -------------------------------------------------------------------------
    def trigger_safety_car(
        self,
        mode: str,
        reason: str,
        event_cb,
        clock: float = 0.0,
        cars: list[Any] = None,
    ) -> None:
        """Triggered when race control initiates Safety Car or Virtual Safety Car."""
        active = [c for c in (cars or []) if not getattr(c, "dnf", False)]
        car = random.choice(active) if active else None
        short = getattr(car, "team_short", "RACE") if car else "TEAM"
        tpl = random.choice(SAFETY_CAR_RADIOS)
        msg = tpl.format(short=short)
        event_cb("RADIO", msg)

    # -------------------------------------------------------------------------
    # Event: Safety Car Ending
    # -------------------------------------------------------------------------
    def trigger_safety_car_in(self, event_cb, clock: float = 0.0, cars: list[Any] = None) -> None:
        """Triggered when Safety Car peeling in this lap is announced."""
        active = [c for c in (cars or []) if not getattr(c, "dnf", False)]
        car = random.choice(active) if active else None
        short = getattr(car, "team_short", "RACE") if car else "TEAM"
        tpl = random.choice(SAFETY_CAR_IN_RADIOS)
        msg = tpl.format(short=short)
        event_cb("RADIO", msg)

    # -------------------------------------------------------------------------
    # Event: Weather Shift (Rain arriving or track drying)
    # -------------------------------------------------------------------------
    def trigger_weather_transition(
        self,
        rain_intensity: float,
        wetness: float,
        event_cb,
        clock: float,
        cars: list[Any],
        track: Any,
    ) -> None:
        """Triggered when atmospheric precipitation shifts significantly."""
        active = [c for c in cars if not getattr(c, "dnf", False) and not getattr(c, "in_pits", False)]
        if not active:
            return
        car = random.choice(active)
        if not self._can_broadcast(car, clock, min_global_cd=4.0, min_driver_cd=25.0):
            return
        self._mark_broadcast(car, clock)

        turn = track.nearest_corner(car.s) if hasattr(track, "nearest_corner") else 3
        tpl = random.choice(WEATHER_RADIOS)
        msg = tpl.format(num=car.number, code=car.code, short=car.team_short, turn=turn)
        event_cb("RADIO", msg)

    # -------------------------------------------------------------------------
    # Event: Chequered Flag / Race Victory
    # -------------------------------------------------------------------------
    def trigger_race_win(self, winner: Any, event_cb, clock: float = 0.0) -> None:
        """Triggered when the race winner crosses the start/finish line."""
        self._mark_broadcast(winner, clock)
        drv_id = getattr(winner, "driver_id", "").lower()
        if drv_id == "hamilton":
            msg = f"TEAM RADIO (#{winner.number} {winner.code}): 'Still I rise! Thank you to everyone back at the factory, amazing job!'"
        elif drv_id == "verstappen":
            msg = f"TEAM RADIO (#{winner.number} {winner.code}): 'Haha, yes boys! Simply lovely! What an incredible race!'"
        elif drv_id == "sainz":
            msg = f"TEAM RADIO (#{winner.number} {winner.code}): 'Smooth operator... smooooth operaaator! Vamos!'"
        elif drv_id == "norris":
            msg = f"TEAM RADIO (#{winner.number} {winner.code}): 'YESSSS! Let's go! What a car today!'"
        elif drv_id == "alonso":
            msg = f"TEAM RADIO (#{winner.number} {winner.code}): 'Yes! Always believe! Incredible race, thank you team!'"
        else:
            tpl = random.choice(RACE_WIN_RADIOS)
            msg = tpl.format(
                num=winner.number,
                code=winner.code,
                short=winner.team_short,
            )
        event_cb("RADIO", msg)

    # -------------------------------------------------------------------------
    # Situational Battle Pressure Check
    # (Evaluates genuine trailing dirty air and blue flags; no random periodic chatter)
    # -------------------------------------------------------------------------
    def step(
        self,
        dt: float,
        clock: float,
        cars: list[Any],
        track: Any,
        wetness: float,
        flag_state: str,
        event_cb,
    ) -> None:
        """Evaluates genuine close-quarters battle pressure (dirty air, backmarkers)."""
        if flag_state in ("LIGHTS", "RED"):
            return

        active_cars = [c for c in cars if not getattr(c, "dnf", False) and not getattr(c, "in_pits", False)]
        if not active_cars:
            return

        # Check for prolonged dirty air tailing pressure (behind another car for >= 3.5s)
        battle_candidates = [
            c for c in active_cars
            if getattr(c, "tailing_timer", 0.0) >= 3.5
            and self._can_broadcast(c, clock, min_global_cd=3.5, min_driver_cd=22.0)
        ]
        if battle_candidates:
            car = random.choice(battle_candidates)
            self._mark_broadcast(car, clock)
            car.tailing_timer = 0.0
            turn = track.nearest_corner(car.s) if hasattr(track, "nearest_corner") else 3

            # Check if trailing a lapped car
            is_lapped = getattr(car, "blue_flag", False)
            if is_lapped:
                tpl = random.choice(BLUE_FLAG_RADIOS)
            else:
                tpl = random.choice(DIRTY_AIR_AND_BATTLE_RADIOS)
            msg = tpl.format(num=car.number, code=car.code, short=car.team_short, turn=turn)
            event_cb("RADIO", msg)
