with open("scratch/test_event_triggered_radio.py", "r", encoding="utf-8") as f:
    text = f.read()

target = """    lead_car = world.race_session.cars_by_id[lead_drv["id"]]

    initial_events = len([ev for ev in world.event_feed if ev["kind"] == "RADIO"])"""

replacement = """    lead_car = world.race_session.cars_by_id[lead_drv["id"]]
    lead_car.pace_mode = "BALANCED"

    initial_events = len([ev for ev in world.event_feed if ev["kind"] == "RADIO"])"""

assert target in text, "Could not find target in test_event_triggered_radio.py"
text = text.replace(target, replacement, 1)

with open("scratch/test_event_triggered_radio.py", "w", encoding="utf-8") as f:
    f.write(text)

print("test_event_triggered_radio.py updated successfully!")

