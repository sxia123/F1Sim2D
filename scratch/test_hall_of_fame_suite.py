import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sim.championship import ChampionshipWorld
from sim.hall_of_fame import generate_default_season_archives, record_live_race_to_archive, sync_live_season_status

def test_js_and_html_syntax():
    print("[1] Verifying public/index.html, public/app.js and public/styles.css...")

    with open("public/index.html", "r", encoding="utf-8") as f:
        html = f.read()
    assert 'data-tab="hall-of-fame"' in html, "Missing hall-of-fame nav-tab in index.html"
    assert 'id="tab-hall-of-fame"' in html, "Missing tab-hall-of-fame pane in index.html"
    assert 'id="hof-season-buttons"' in html, "Missing hof-season-buttons in index.html"
    assert 'id="hof-races-grid"' in html, "Missing hof-races-grid in index.html"
    assert 'id="hof-wdc-table"' in html, "Missing hof-wdc-table in index.html"
    assert 'id="hof-wcc-table"' in html, "Missing hof-wcc-table in index.html"
    print("  index.html structure verified.")

    with open("public/styles.css", "r", encoding="utf-8") as f:
        css = f.read()
    assert ".hof-header-wrap" in css, "Missing .hof-header-wrap in styles.css"
    assert ".hof-season-btn" in css, "Missing .hof-season-btn in styles.css"
    assert ".hof-champ-card" in css, "Missing .hof-champ-card in styles.css"
    assert ".hof-race-card" in css, "Missing .hof-race-card in styles.css"
    print("  styles.css rules verified.")

    with open("public/app.js", "r", encoding="utf-8") as f:
        js = f.read()
    assert "selectedHofSeason" in js, "Missing selectedHofSeason in app.js"
    assert "renderHallOfFame()" in js, "Missing renderHallOfFame method in app.js"
    assert "this.renderHallOfFame()" in js, "renderHallOfFame not called in app.js"
    assert ".hof-season-btn" in js, "Missing hof-season-btn handler in app.js"
    assert "hof-card-btn" in js, "Missing hof-card-btn handler in app.js"
    print("  app.js integrations verified.")


def test_hall_of_fame_generation_all_seasons():
    print("[2] Verifying full 2026-2030 season archives generation...")
    archives = generate_default_season_archives()

    expected_years = ["2026", "2027", "2028", "2029", "2030"]
    for yr in expected_years:
        assert yr in archives, f"Year {yr} missing from generated archives"
        s = archives[yr]
        assert s["season"] == int(yr)
        assert s["status"] in ("COMPLETED", "IN_PROGRESS")
        assert "era_name" in s
        assert "engine_type" in s
        assert "wdc_champion" in s
        assert "wcc_champion" in s
        assert "races" in s
        assert len(s["races"]) >= 23, f"Year {yr} has insufficient races: {len(s['races'])}"
        assert len(s["wdc_standings"]) > 10, f"Year {yr} missing WDC standings"
        assert len(s["wcc_standings"]) >= 10, f"Year {yr} missing WCC standings"

        # Verify each race in the season
        for r in s["races"]:
            assert "round" in r
            assert "gp" in r
            assert "circuit" in r
            assert "winner_name" in r
            assert "winner_code" in r
            assert "p2_name" in r
            assert "p3_name" in r
            assert "pole_code" in r
            assert "fastest_lap_code" in r
            assert "top10" in r
            assert len(r["top10"]) == 10, f"Race {r['gp']} top 10 count != 10: {len(r['top10'])}"

        print(f"  [OK] Season {yr}: {len(s['races'])} races, WDC: {s['wdc_champion']['name']} ({s['wdc_champion']['team']}), WCC: {s['wcc_champion']['name']}")


def test_championship_world_integration():
    print("[3] Verifying ChampionshipWorld state and live updates...")
    world = ChampionshipWorld()
    payload = world.build_full_state_payload()

    assert "season_archives" in payload, "Missing season_archives in full state payload"
    hof_data = payload["season_archives"]
    assert hof_data["available_years"] == [2026, 2027, 2028, 2029, 2030]
    assert hof_data["current_year"] == world.season_year

    # Verify get_hall_of_fame_data method
    api_data = world.get_hall_of_fame_data()
    assert api_data["available_years"] == [2026, 2027, 2028, 2029, 2030]
    assert "2026" in api_data["seasons"]
    assert "2028" in api_data["seasons"]
    assert "2030" in api_data["seasons"]

    # Test live race recording: finish Melbourne race and check live overwrite
    world._start_qualifying()
    world.skip_session() # skip to race
    world._prepare_race_grid()
    world._start_race()

    rs = world.race_session
    rs.lights_countdown = 0.0
    rs.flag_state = "GREEN"

    # Finish race artificially
    world._conclude_race()

    # Check that calendar_results has round 1
    assert len(world.calendar_results) > 0
    last_res = world.calendar_results[-1]
    assert "top10" in last_res
    assert len(last_res["top10"]) > 0

    # Verify that the live race was written into 2026 archive
    arch_2026 = world.season_archives[str(world.season_year)]
    live_r1 = next(r for r in arch_2026["races"] if r["round"] == last_res["round"])
    assert live_r1["winner_code"] == last_res["winner_code"]
    assert live_r1["winner_name"] == last_res["winner_name"]
    assert len(live_r1["top10"]) == 10
    print(f"  Live race successfully written to Hall of Fame archive: Round {last_res['round']} winner = {live_r1['winner_name']} ({live_r1['winner_team']})")


if __name__ == "__main__":
    test_js_and_html_syntax()
    test_hall_of_fame_generation_all_seasons()
    test_championship_world_integration()
    print("\nALL HALL OF FAME TESTS PASSED CLEANLY!")
