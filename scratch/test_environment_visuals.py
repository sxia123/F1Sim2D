import sys
import math
sys.path.insert(0, ".")

def check_js_syntax():
    with open("public/canvas.js", "r", encoding="utf-8") as f:
        code = f.read()

    assert "_drawEnvironment(ctx, now)" in code, "Missing _drawEnvironment call"
    assert "this._drawEnvironment(ctx, now);" in code, "Missing _drawEnvironment in _render"
    assert "this.scenery.draw" in code, "Missing scenery.draw in canvas.js"

    # Bracket balance check ignoring strings and comments
    stack = []
    i = 0
    in_single = False
    in_double = False
    in_template = False
    in_line_comment = False
    in_block_comment = False

    while i < len(code):
        c = code[i]
        nxt = code[i+1] if i + 1 < len(code) else ""

        if in_line_comment:
            if c == "\n":
                in_line_comment = False
            i += 1
            continue

        if in_block_comment:
            if c == "*" and nxt == "/":
                in_block_comment = False
                i += 2
                continue
            i += 1
            continue

        if in_single:
            if c == "\\" and nxt:
                i += 2
                continue
            if c == "'":
                in_single = False
            i += 1
            continue

        if in_double:
            if c == "\\" and nxt:
                i += 2
                continue
            if c == '"':
                in_double = False
            i += 1
            continue

        if in_template:
            if c == "\\" and nxt:
                i += 2
                continue
            if c == "`":
                in_template = False
            i += 1
            continue

        if c == "/" and nxt == "/":
            in_line_comment = True
            i += 2
            continue

        if c == "/" and nxt == "*":
            in_block_comment = True
            i += 2
            continue

        if c == "'":
            in_single = True
            i += 1
            continue

        if c == '"':
            in_double = True
            i += 1
            continue

        if c == "`":
            in_template = True
            i += 1
            continue

        if c in "({[":
            stack.append((c, i))
        elif c in ")}]":
            if not stack:
                raise AssertionError(f"Unexpected closing {c} at offset {i}")
            opener, pos = stack.pop()
            matches = {")": "(", "}": "{", "]": "["}
            if matches[c] != opener:
                raise AssertionError(f"Mismatched bracket: {opener} at {pos} closed by {c} at {i}")
        i += 1

    if stack:
        raise AssertionError(f"Unclosed brackets remaining: {stack[-5:]}")
    print("public/canvas.js syntax balance check passed cleanly!")

def check_all_tracks_environment():
    from sim.tracks import COMPILED_TRACKS

    print(f"Testing environment payload for all {len(COMPILED_TRACKS)} circuits...")

    for t in COMPILED_TRACKS:
        tid = t.id
        payload = t.to_client_payload()
        assert "environment" in payload, f"Track {tid} missing environment in client payload"
        env = payload["environment"]

        required_keys = ["theme", "water_bodies", "yachts", "landmarks", "buildings", "grandstands", "gravel_traps", "trees"]
        for rk in required_keys:
            assert rk in env, f"Track {tid} env missing key: {rk}"

        # Spot checks for signature themes
        if tid == "monaco":
            assert len(env["yachts"]) > 0, "Monaco must have yachts!"
            assert len(env["water_bodies"]) > 0, "Monaco Port Hercule water body missing!"
        elif tid == "bahrain":
            assert env["theme"] == "desert", "Bahrain should have desert theme!"
        elif tid == "belgium":
            assert env["theme"] == "forest", "Spa should have forest theme!"
            assert len(env["trees"]) > 1000, "Spa should have dense trees!"
        elif tid == "italy":
            assert env["theme"] == "forest", "Monza should have forest theme!"
        elif tid == "netherlands":
            assert env["theme"] == "dunes", "Zandvoort should have dunes theme!"

        print(f"  [OK] {t.name} ({tid}): theme={env['theme']}, water={len(env['water_bodies'])}, yachts={len(env['yachts'])}, buildings={len(env['buildings'])}, grandstands={len(env['grandstands'])}, trees={len(env['trees'])}")

    print(f"All {len(COMPILED_TRACKS)} circuits verified successfully!")

if __name__ == "__main__":
    check_js_syntax()
    check_all_tracks_environment()
