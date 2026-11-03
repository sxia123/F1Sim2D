with open("server.py", "r", encoding="utf-8") as f:
    text = f.read()

target = """        if path == "/api/tick":
            self._send_json(self.world.build_live_tick_payload())
            return"""

replacement = """        if path == "/api/tick":
            self._send_json(self.world.build_live_tick_payload())
            return
        if path == "/api/hall_of_fame":
            self._send_json(self.world.get_hall_of_fame_data())
            return"""

assert target in text, "Could not find target in server.py"
text = text.replace(target, replacement, 1)

with open("server.py", "w", encoding="utf-8") as f:
    f.write(text)

print("server.py updated successfully!")

