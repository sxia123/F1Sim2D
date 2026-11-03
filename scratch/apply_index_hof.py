with open("public/index.html", "r", encoding="utf-8") as f:
    text = f.read()

# 1. Add nav tab
nav_target = '<button class="nav-tab" data-tab="standings">CHAMPIONSHIP CLASSIFICATION</button>'
nav_replacement = ('<button class="nav-tab" data-tab="standings">CHAMPIONSHIP CLASSIFICATION</button>\n'
                   '      <button class="nav-tab" data-tab="hall-of-fame">HALL OF FAME</button>')
assert nav_target in text, "Could not find nav_target"
text = text.replace(nav_target, nav_replacement, 1)

# 2. Add tab-hall-of-fame right after tab-standings
pane_target = """          <div class="calendar-grid" id="calendar-grid"></div>
        </div>
      </section>"""

pane_replacement = """          <div class="calendar-grid" id="calendar-grid"></div>
        </div>

        <!-- TAB 7: FIA FORMULA 1 HALL OF FAME & RESULTS ARCHIVE -->
        <div class="tab-pane scroll-pane" id="tab-hall-of-fame">
          <div class="hof-header-wrap">
            <div class="hof-header-left">
              <div class="hof-pretitle">FIA FORMULA 1 WORLD CHAMPIONSHIP</div>
              <h2 class="hof-main-title">OFFICIAL HALL OF FAME &amp; RACE ARCHIVES</h2>
              <div class="hof-era-strip">
                <span class="hof-badge hof-badge-era" id="hof-era-badge">Active Aero Turbo-Hybrid Era</span>
                <span class="hof-badge hof-badge-engine" id="hof-engine-badge">1.6L V6 Turbo + 350kW MGU-K</span>
                <span class="hof-badge hof-badge-status" id="hof-status-badge">ARCHIVE RECORD</span>
              </div>
            </div>
            <div class="hof-season-selector-wrap">
              <div class="hof-selector-title">SELECT CHAMPIONSHIP SEASON</div>
              <div class="hof-season-buttons" id="hof-season-buttons">
                <button class="hof-season-btn active" data-year="2026">2026</button>
                <button class="hof-season-btn" data-year="2027">2027</button>
                <button class="hof-season-btn" data-year="2028">2028</button>
                <button class="hof-season-btn" data-year="2029">2029</button>
                <button class="hof-season-btn" data-year="2030">2030</button>
              </div>
            </div>
          </div>

          <!-- SEASON CHAMPIONS SHOWCASE BANNER -->
          <div class="hof-champions-grid" id="hof-champions-banner"></div>

          <!-- NARRATIVE SUMMARY -->
          <div class="hof-narrative-card" id="hof-narrative-card"></div>

          <!-- SUB-NAVIGATION BAR: RACES VS STANDINGS -->
          <div class="hof-subnav">
            <div class="hof-subnav-buttons">
              <button class="hof-sub-btn active" id="hof-sub-races">ALL GRAND PRIX RESULTS</button>
              <button class="hof-sub-btn" id="hof-sub-standings">SEASON CLASSIFICATION</button>
            </div>
            <div class="hof-meta-stat" id="hof-round-count">24 OF 24 GRANDS PRIX CONCLUDED</div>
          </div>

          <!-- RACE-BY-RACE RESULTS GRID -->
          <div class="hof-races-view" id="hof-races-view">
            <div class="hof-races-grid" id="hof-races-grid"></div>
          </div>

          <!-- SEASON FINAL STANDINGS VIEW -->
          <div class="hof-standings-view hidden" id="hof-standings-view">
            <div class="hof-standings-grid">
              <div class="hof-wdc-card">
                <h3 class="sec-title">WORLD DRIVERS' CHAMPIONSHIP STANDINGS</h3>
                <div class="table-wrap">
                  <table class="data-table" id="hof-wdc-table">
                    <thead>
                      <tr>
                        <th>POS</th>
                        <th>DRIVER</th>
                        <th>CONSTRUCTOR</th>
                        <th>WINS</th>
                        <th>PODIUMS</th>
                        <th>POLES</th>
                        <th style="text-align:right">PTS</th>
                      </tr>
                    </thead>
                    <tbody></tbody>
                  </table>
                </div>
              </div>
              <div class="hof-wcc-card">
                <h3 class="sec-title">WORLD CONSTRUCTORS' CHAMPIONSHIP STANDINGS</h3>
                <div class="table-wrap">
                  <table class="data-table" id="hof-wcc-table">
                    <thead>
                      <tr>
                        <th>POS</th>
                        <th>CONSTRUCTOR</th>
                        <th>ENGINE</th>
                        <th>WINS</th>
                        <th style="text-align:right">PTS</th>
                      </tr>
                    </thead>
                    <tbody></tbody>
                  </table>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>"""

assert pane_target in text, "Could not find pane_target"
text = text.replace(pane_target, pane_replacement, 1)

with open("public/index.html", "w", encoding="utf-8") as f:
    f.write(text)

print("public/index.html updated successfully!")

