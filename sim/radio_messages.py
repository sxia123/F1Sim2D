"""Fictional race dialogue, keyed by the event that makes each line appropriate.

Driver voices travel with the driver; pit-wall voices belong to the current team.
These are game dialogue, not a collection of attributed real-world quotations.
"""


def engineer(*lines: str) -> list[str]:
    return ["PIT WALL ({short} / #{num} {code}): '" + line + "'" for line in lines]


def driver(*lines: str) -> list[str]:
    return ["DRIVER (#{num} {code}): '" + line + "'" for line in lines]


GENERIC_RADIOS = {
    "push": engineer(
        "{mode} selected, {code}. Push the pace now.",
        "We are going to {mode}. Give us your best pace.",
    ) + driver("Copy, {mode}. Pushing now.", "Understood. Giving it everything."),
    "boost": engineer("BOOST selected. Use the extra deployment where available."),
    "mode_restricted": engineer("{mode} selected, {code}. Respect race-control restrictions until green."),
    "overtake_mode": engineer("OVERTAKE selected. Use it when available."),
    "conserve": engineer(
        "Conserve pace, {code}. Look after the tyres.",
        "Reduce the pace and manage this set.",
    ) + driver("Copy. Taking some load out of the tyres.", "Understood. Managing the stint."),
    "harvest": engineer("HARVEST selected. Recharge the battery; expect less deployment.")
    + driver("Copy, harvesting. Building the battery back up."),
    "overtaken": driver(
        "Lost the place to {other_code} near Turn {turn}.",
        "{other_code} is through. Resetting and carrying on.",
    ) + engineer("{other_code} has gone through, {code}. Stay focused on your race."),
    "divebomb": driver("{other_code} came from a long way back near Turn {turn}. Lost the place."),
    "overtake": driver(
        "Through on {other_code}. That's P{new_p}.",
        "Got the position near Turn {turn}. P{new_p} now.",
    ) + engineer("Good move, {code}. P{new_p}.", "That's {other_code} behind us. P{new_p}."),
    "lead": engineer("That's the lead, {code}. P1. Keep your rhythm.")
    + driver("Into the lead. Let's keep this going."),
    "box": engineer(
        "Box, box, {code}. In this lap for {comp} tyres.",
        "Box this lap. {comp} tyres ready. Mind the pit entry speed.",
        "Confirm box this lap, {code}. We are fitting {comp} tyres.",
    ),
    "pit_exit": engineer(
        "Stop complete: {dur:.1f}s stationary. Rejoining on {comp} tyres.",
        "Back out on {comp}. {dur:.1f}s stationary; respect the pit exit line.",
    ),
    "drive_through": engineer("Box this lap to serve the drive-through, {code}. No stop or tyre change."),
    "contact": driver(
        "Contact with {other_code} near Turn {turn}. Checking the car.",
        "We've touched near Turn {turn}. Can you check the data?",
    ) + engineer("We saw contact with {other_code}, {code}. Report the balance."),
    "wing_damage": engineer("Front wing damage confirmed, {code}. Report the balance.")
    + driver("Front wing is damaged. Checking how the car responds."),
    "puncture": driver("Puncture near Turn {turn}. Losing tyre pressure.")
    + engineer("Puncture confirmed, {code}. Take care bringing the car back."),
    "damage": engineer("Damage reported near Turn {turn}, {code}. Assess the car."),
    "fastest_lap": engineer(
        "Fastest lap of the race, {code}: {time_str}.",
        "New fastest lap. {time_str}. Good work, {code}.",
    ),
    "spin": driver("I've spun near Turn {turn}. Checking the car.", "Lost it near Turn {turn}. Checking before I rejoin.")
    + engineer("We saw the spin, {code}. Check for traffic before rejoining."),
    "tyre_cliff": driver(
        "These tyres have dropped off. Struggling for grip now.",
        "The grip has gone away on this set. We need to review the stop.",
    ) + engineer("Tyre wear is beyond the target, {code}. Manage the grip."),
    "sc": engineer(
        "Safety Car deployed. No overtaking; follow the delta.",
        "Safety Car, Safety Car. Reduce speed and watch the delta.",
    ),
    "vsc": engineer(
        "Virtual Safety Car. VSC deployed. Keep the delta positive.",
        "VSC, VSC. No overtaking; respect the delta.",
    ),
    "sc_in": engineer(
        "Safety Car in this lap. Leader controls the pace; no passing before the line.",
        "Safety Car coming in. Prepare the tyres and wait for the restart.",
    ),
    "rain": engineer("Rain is arriving. Monitor the grip and report conditions.")
    + driver("Rain starting near Turn {turn}. Keeping an eye on the grip."),
    "rain_wet": engineer("Rain continuing on a wet track. Report any change in grip.")
    + driver("Rain here near Turn {turn}; the surface is already wet."),
    "rain_easing": engineer("Rain has eased. The track is still wet; keep assessing the grip."),
    "drying": engineer("Rain has eased and the surface is drying. Keep assessing the tyre crossover."),
    "win": engineer("P1, {code}! Chequered flag. You've won the race!")
    + driver("Yes! We did it! Thank you everyone, fantastic job today!"),
    "battle": driver(
        "Still close behind {other_code}. Looking for a way through.",
        "I'm staying with {other_code}. Keeping the pressure on.",
    ) + engineer("You're close to {other_code}, {code}. Be patient and pick your moment."),
    "blue_attack": driver("Catching lapped traffic: {other_code} ahead. Can we get blue flags?")
    + engineer("{other_code} ahead is a lap down, {code}. Take care getting through."),
    "blue_yield": engineer("Blue flags, {code}. Let the faster car through safely.")
    + driver("Copy blue flags. Making room for the car behind."),
}


# Short, event-specific voices. No assumed engineer, employer, car fault or gap.
DRIVER_RADIOS = {
    "hamilton": {
        "push": ["Copy. Giving it everything, team.", "Time to push. Let's do this together."],
        "overtake": ["That's P{new_p}. Let's keep building on this."],
        "tyre_cliff": ["My tyres are gone, guys. I'm struggling for grip.", "There's very little left in this set. What's our plan?"],
        "win": ["Yes! Thank you so much, everyone. We kept believing!"],
    },
    "verstappen": {
        "push": ["Copy, mate. Pushing now.", "Understood. Let's get on with it."],
        "overtake": ["Simply lovely. That's P{new_p}.", "Okay, we're through on {other_code}."],
        "overtaken": ["{other_code} is through, mate. What's the plan from here?"],
        "tyre_cliff": ["Mate, these tyres are finished. The grip has really dropped."],
        "win": ["Haha, yes boys! Simply lovely. Great work all weekend."],
    },
    "leclerc": {
        "push": ["Understood. Head down, pushing now.", "Okay. I will give it everything."],
        "box": ["Copy, box for {comp}. Confirmed."],
        "tyre_cliff": ["The grip is going away. We need a plan for these tyres."],
        "win": ["Yes! Come on! Thank you, everyone. That one feels good!"],
    },
    "sainz": {
        "push": ["Copy. Let's execute this properly."],
        "box": ["Box for {comp}, understood. Let's make the stop count."],
        "conserve": ["Understood. I'll manage the tyres; keep me updated on the strategy."],
        "win": ["Smooth operator! Vamos! Thank you, team!"],
    },
    "norris": {
        "push": ["Okay, let's go. Pushing now.", "Yep, understood. I'll give it a go."],
        "overtake": ["Yes! Got {other_code}. That's P{new_p}."],
        "tyre_cliff": ["These tyres are really struggling now. Not much grip left."],
        "win": ["Let's go! Yes! Thank you everyone. We did it!"],
    },
    "piastri": {
        "push": ["Copy. Pushing.", "Understood. On it."],
        "overtake": ["That's one done. P{new_p}.", "Through on {other_code}. Copy."],
        "overtaken": ["Lost that one. Back to work."],
        "conserve": ["Copy. Managing."],
        "win": ["Nice. That'll do. Thanks everyone, great job."],
    },
    "russell": {
        "push": ["Understood. Maximum commitment now."],
        "overtake": ["Yes, come on! P{new_p}."],
        "contact": ["Contact with {other_code}. Have a look at the data, please."],
        "win": ["Come on! Brilliant job, everyone. That's a win!"],
    },
    "antonelli": {
        "push": ["Okay, pushing. Keep talking me through it."],
        "overtake": ["Yes! P{new_p}. Staying focused."],
        "win": ["Yes! We won! Thank you for believing in me, everyone!"],
    },
    "alonso": {
        "push": ["Okay. Let's make every lap count."],
        "overtaken": ["{other_code} is through. Let's think about how we recover this."],
        "conserve": ["Understood. We need to think about the whole race."],
        "win": ["Yes! Never stop believing. What a race, thank you!"],
    },
    "stroll": {
        "push": ["Yep, understood. Picking up the pace."],
        "spin": ["Lost it near Turn {turn}. Checking the car before I move."],
        "win": ["Yes! Amazing job, guys. Thank you so much!"],
    },
    "albon": {
        "push": ["Okay, I'll push. Let's make this work."],
        "battle": ["Still right behind {other_code}. Trying to find an opening."],
        "win": ["Yes! No way! We've actually done it. Thank you, everyone!"],
    },
    "gasly": {
        "push": ["Copy. Let's go for it, guys."],
        "overtake": ["Yes, come on! Through on {other_code}."],
        "win": ["Yes! Come on! What a feeling. Thank you, team!"],
    },
    "colapinto": {
        "push": ["Okay, vamos. Giving it everything."],
        "overtake": ["Vamos! That's P{new_p}."],
        "win": ["Vamos! What a race! Thank you so much, everyone!"],
    },
    "hadjar": {
        "push": ["Understood. Fully focused, pushing now."],
        "overtaken": ["Ah, lost that place. Resetting now."],
        "win": ["Yes! We did it! Thank you, everyone. Unbelievable!"],
    },
    "lawson": {
        "push": ["Yep, copy. Let's get stuck in."],
        "overtake": ["That's the move done. P{new_p}."],
        "win": ["Yes! Awesome, guys. Thanks for all the hard work!"],
    },
    "lindblad": {
        "push": ["Copy. I'll build the pace now."],
        "overtake": ["Got the place. P{new_p}. Staying on it."],
        "win": ["Yes! That is incredible. Thank you, everyone!"],
    },
    "hulkenberg": {
        "push": ["Copy. Time to get to work."],
        "overtake": ["Job done on {other_code}. P{new_p}."],
        "win": ["Yes! That's a good day's work. Thank you, everyone!"],
    },
    "bortoleto": {
        "push": ["Okay, understood. I'll push now."],
        "conserve": ["Copy. Managing the stint, lap by lap."],
        "win": ["Yes! We did it! Thank you, team. What a day!"],
    },
    "ocon": {
        "push": ["Understood. I'll give you everything I've got."],
        "battle": ["Keeping the pressure on {other_code}. Waiting for the opportunity."],
        "win": ["Yes! What a team effort. Thank you, everyone!"],
    },
    "bearman": {
        "push": ["Copy, pushing now. Keep the updates coming."],
        "overtake": ["Nice! That's P{new_p}. Back to the rhythm."],
        "win": ["Yes! Incredible! Thank you so much, everyone!"],
    },
    "perez": {
        "push": ["Copy. Let's make this stint count."],
        "conserve": ["Understood. Looking after the tyres for later."],
        "win": ["Vamos! Great work, everyone. We earned that one!"],
    },
    "bottas": {
        "push": ["Copy. Time to push."],
        "overtake": ["That's P{new_p}. Job done."],
        "win": ["Yes! That's what we came here for. Thank you, everyone!"],
    },
    "tsunoda": {
        "push": ["Okay! Pushing flat out now!"],
        "overtaken": ["Ah! Lost it to {other_code}. Need to get back on it."],
        "win": ["Yes! Yes! We did it, guys! Thank you!"],
    },
    "raikkonen": {
        "push": ["Yeah, yeah. I'm pushing."],
        "conserve": ["Okay. I know what to do."],
        "win": ["Good. Thanks, everyone. Nice race."],
    },
    "vettel": {
        "push": ["Understood. Full focus now."],
        "overtake": ["Yes! That's P{new_p}. Keep it going."],
        "win": ["Yes! We did it! Fantastic job, everyone!"],
    },
    "senna": {"push": ["Understood. Total concentration now."], "win": ["Yes! Thank you, team. We gave everything today."]},
    "schumacher": {"push": ["Copy. Maximum effort, every lap."], "win": ["Yes! Fantastic work. That was a team victory!"]},
    "lauda": {"conserve": ["Understood. Let's bring the car home."], "win": ["Good work. We did what we needed to do."]},
    "prost": {"conserve": ["Copy. Let's keep something for the end."], "win": ["Excellent. A very good race from the whole team."]},
    "hakkinen": {"push": ["Yes. Pushing now."], "win": ["Yes! Good race. Thank you, everyone."]},
    "mansell": {"push": ["Giving it absolutely everything!"], "win": ["Yes! What a race! Thank you all!"]},
    "fangio": {"conserve": ["Understood. We must make it to the finish."], "win": ["Thank you, everyone. A fine race together."]},
}


TEAM_RADIOS = {
    "ferrari": {
        "push": ["Andiamo, {code}. {mode} now. Give it everything."],
        "box": ["Box, box, {code}. {comp} tyres. Confermato."],
        "conserve": ["Manage the tyres, {code}. We take this stint lap by lap."],
        "win": ["P1! Grande, {code}! For everyone at Maranello!"],
    },
    "mercedes": {
        "push": ["{code}, {mode} confirmed. Let's execute."],
        "box": ["Box this lap, {code}. {comp} tyres. Keep the entry tidy."],
        "conserve": ["Conserve pace, {code}. Keep the tyre management disciplined."],
        "win": ["Get in there, {code}! P1! Brackley will love that one."],
    },
    "redbull": {
        "push": ["Okay {code}, {mode}. Let's get on with it."],
        "box": ["Box, box. {comp} tyres, {code}. Nice and tidy on the entry."],
        "conserve": ["Take a little out of the tyres now, {code}. Conserve pace."],
        "win": ["That's P1, {code}. An excellent day's work. Well done, mate."],
    },
    "mclaren": {
        "push": ["{mode}, {code}. You can push now. Nice and focused."],
        "box": ["Box this lap, {code}. {comp} tyres ready. Let's nail the stop."],
        "conserve": ["Conserve pace, {code}. Let's keep this set working for us."],
        "win": ["P1, {code}! A papaya win! Thank you from everyone in Woking."],
    },
    "williams": {
        "push": ["{code}, {mode}. Let's make this opportunity count."],
        "box": ["Box, {code}. {comp} tyres ready. Let's put the plan together."],
        "conserve": ["Manage this set, {code}. Keep the race coming to us."],
        "win": ["P1! A Williams victory, {code}! This one's for Grove!"],
    },
    "aston": {
        "push": ["{mode}, {code}. Let's put the work in now."],
        "box": ["Box this lap for {comp}, {code}. Confirm the call."],
        "conserve": ["Conserve pace, {code}. Keep the bigger picture in mind."],
        "win": ["P1! A win in green, {code}! Brilliant work from the whole team."],
    },
    "alpine": {
        "push": ["Allez, {code}. {mode}. Keep the commitment."],
        "box": ["Box this lap, {code}. {comp} tyres. Let's make it count."],
        "conserve": ["Conserve pace, {code}. Protect this stint."],
        "win": ["P1! Magnifique, {code}! What a result for the whole team!"],
    },
    "racingbulls": {
        "push": ["{mode}, {code}. Stay sharp and commit."],
        "box": ["Box, box, {code}. {comp} tyres; focus on the entry."],
        "conserve": ["Conserve pace, {code}. Stay patient with the tyres."],
        "win": ["P1, {code}! Faenza, you've got a race winner!"],
    },
    "haas": {
        "push": ["Okay {code}, {mode}. Let's get the job done."],
        "box": ["Box for {comp}, {code}. In this lap. Keep it clean."],
        "conserve": ["Conserve pace, {code}. Take care of the tyres."],
        "win": ["P1! A Haas victory, {code}! What a day for this team!"],
    },
    "audi": {
        "push": ["{mode} confirmed, {code}. Precision and commitment."],
        "box": ["Box this lap, {code}. {comp} tyres. Execute the stop."],
        "conserve": ["Conserve pace confirmed. Keep the stint controlled, {code}."],
        "win": ["P1, {code}! An Audi win. Excellent execution from everyone."],
    },
    "cadillac": {
        "push": ["{mode}, {code}. Let's go to work."],
        "box": ["Box this lap, {code}. {comp} tyres ready. Bring it in."],
        "conserve": ["Conserve pace, {code}. Play the long game with this set."],
        "win": ["P1! Cadillac wins, {code}! What a moment for the whole team!"],
    },
}
