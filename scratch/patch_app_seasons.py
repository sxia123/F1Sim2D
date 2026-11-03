from pathlib import Path

path = Path("public/app.js")
text = path.read_text(encoding="utf-8")

# 1. Pit Wall click event: handle start_comp
pw_event_target = """      if (cmd === "auto") payload.auto_strategy = val === "true";
      else if (cmd === "box") payload.box_this_lap = val === "true";
      else if (cmd === "ncomp") payload.next_compound = val;"""

pw_event_repl = """      if (cmd === "auto") payload.auto_strategy = val === "true";
      else if (cmd === "box") payload.box_this_lap = val === "true";
      else if (cmd === "start_comp") {
        await this.apiPost("/api/set_starting_compound", { driver_id: driverId, compound: val });
        this.lastDomSyncMs = 0;
        return;
      }
      else if (cmd === "ncomp") payload.next_compound = val;"""

assert pw_event_target in text, "pw_event_target not found in app.js"
text = text.replace(pw_event_target, pw_event_repl, 1)

# 2. Header: show regulation era badge
hdr_target = """    const rndStr = String(tick.round).padStart(2, "0");
    const widthTxt = tick.track_width_m ? ` | ${tick.track_width_m.toFixed(1)}M WIDE` : "";
    document.getElementById("hdr-round").textContent = `${tick.season} FIA WORLD CHAMPIONSHIP | R${rndStr}/${tick.total_rounds} | ${tick.city.toUpperCase()}${widthTxt}`;"""

hdr_repl = """    const rndStr = String(tick.round).padStart(2, "0");
    const widthTxt = tick.track_width_m ? ` | ${tick.track_width_m.toFixed(1)}M WIDE` : "";
    const reg = tick.regulations;
    const eraBadge = reg ? `<span class="reg-era-pill ${reg.era_id === "V8_DRS" ? "era-v8" : "era-hybrid"}" title="${reg.description}">${reg.short_name.toUpperCase()}</span>` : "";
    document.getElementById("hdr-round").innerHTML = `${tick.season} FIA WORLD CHAMPIONSHIP | R${rndStr}/${tick.total_rounds} | ${tick.city.toUpperCase()}${widthTxt} ${eraBadge}`;"""

assert hdr_target in text, "hdr_target not found in app.js"
text = text.replace(hdr_target, hdr_repl, 1)

# 3. Timing Tower: DRS badges
tower_target = """        } else if (c.ovt) {
          badges += `<span class="badge b-ovt" title="2026 Overtake Mode Active">OVT</span>`;
        } else if (c.ovt_elig) {
          badges += `<span class="badge b-elig" title="Overtake Mode Armed (<1.0s at Detection)">ARM</span>`;
        } else if (c.aero === "STRAIGHT") {
          badges += `<span class="badge b-str">STR</span>`;
        }"""

tower_repl = """        } else if (c.drs || c.aero === "DRS") {
          badges += `<span class="badge b-drs" title="Classic Rear Wing DRS Active (+22 km/h)">DRS</span>`;
        } else if (c.drs_elig) {
          badges += `<span class="badge b-drs-arm" title="DRS Flap Armed (<1.0s at Detection)">DRS ARM</span>`;
        } else if (c.ovt) {
          badges += `<span class="badge b-ovt" title="2026 Overtake Mode Active">OVT</span>`;
        } else if (c.ovt_elig) {
          badges += `<span class="badge b-elig" title="Overtake Mode Armed (<1.0s at Detection)">ARM</span>`;
        } else if (c.aero === "STRAIGHT") {
          badges += `<span class="badge b-str">STR</span>`;
        }"""

assert tower_target in text, "tower_target not found in app.js"
text = text.replace(tower_target, tower_repl, 1)

# 4. Pit Wall card: starting tyre selection during GRID_WALK / pre-race, and KERS/DRS labeling
pw_render_target = """    wrap.innerHTML = myCars
      .map((c) => {
        const tm = TIRE_META[c.comp] || TIRE_META.MEDIUM;
        const isRace = (tick.phase === "RACE" || tick.phase === "SPRINT_RACE") && !c.dnf;
        const dis = isRace ? "" : "disabled";
        return `
          <div class="pw-card" style="border-top-color:${c.tcol}">
            <div class="pw-top">
              <div class="pw-driver">
                ${teamLogoSVG(c.tid, 16)}
                <span>P${c.pos}  #${c.num} ${c.name}</span>
                ${c.man ? `<span class="badge b-man">${c.man}</span>` : ""}
                ${c.ovt ? `<span class="badge b-ovt">OVT DEPLOY</span>` : c.ovt_elig ? `<span class="badge b-elig">OVT ARMED</span>` : ""}
                ${c.elim ? `<span class="badge b-elim">OUT ${c.estg}</span>` : ""}
                ${c.pen > 0 ? `<span class="badge b-pen">+${c.pen}S PEN</span>` : ""}
                ${c.dmg > 15 ? `<span class="badge b-pen">FW DMG (${c.dmg_side || "FW"} -${c.dmg}%)</span>` : ""}
              </div>
              <div class="pw-metrics">
                <span><strong>${c.kph}</strong> KPH</span>
                <span>LAT <strong>${c.g_lat != null ? Math.abs(c.g_lat).toFixed(1) : "0.0"}G</strong></span>
                <span>AERO <strong style="color:${c.aero === "STRAIGHT" ? "#00d2be" : "#ffffff"}">${c.aero === "STRAIGHT" ? "STR" : "CRN"}</strong></span>
                <span>ERS <strong>${c.bat}%</strong></span>
                <span><span class="pirelli-badge" style="border-color:${tm.color};width:14px;height:14px;font-size:8.5px">${tm.code}</span> ${100 - c.wear}% (${c.tage}L)</span>
              </div>
            </div>

            <div class="pw-controls">
              <div class="pw-group">
                <button class="pw-btn ${c.auto ? "auto-on" : ""}" ${dis} data-pw-cmd="auto" data-drv="${c.id}" data-val="${!c.auto}" title="Toggle AI Chief Strategist">
                  ${c.auto ? "STRAT: AUTO" : "STRAT: MAN"}
                </button>
                <button class="pw-btn ${c.box ? "box-active" : ""}" ${dis} data-pw-cmd="box" data-drv="${c.id}" data-val="${!c.box}">
                  ${c.in_pit ? "IN PIT LANE" : c.box ? "BOX CONFIRMED" : "BOX THIS LAP"}
                </button>
              </div>

              <div class="pw-group" title="Next Pit-Stop Tyre Compound">
                <span class="pw-lbl">TYRE</span>
                ${["SOFT", "MEDIUM", "HARD", "INTER", "WET"]
                  .map(
                    (k) =>
                      `<button class="pw-btn ${c.ncomp === k ? "active" : ""}" ${dis} data-pw-cmd="ncomp" data-drv="${c.id}" data-val="${k}" style="${c.ncomp === k ? "" : `color:${TIRE_META[k].color}`}">${TIRE_META[k].code}</button>`
                  )
                  .join("")}
              </div>

              <div class="pw-group" title="Target Pace Mode">
                <span class="pw-lbl">PACE</span>
                ${[
                  ["CONSERVE", "LIFT"],
                  ["BALANCED", "STD"],
                  ["PUSH", "PUSH"],
                  ["ATTACK", "MAX"],
                ]
                  .map(
                    ([k, lbl]) =>
                      `<button class="pw-btn ${c.pace === k ? "active" : ""}" ${dis} data-pw-cmd="pace" data-drv="${c.id}" data-val="${k}">${lbl}</button>`
                  )
                  .join("")}
              </div>

              <div class="pw-group" title="2026 MGU-K Deployment Profile">
                <span class="pw-lbl">ERS</span>
                ${[
                  ["HARVEST", "HRV"],
                  ["AUTO", "AUTO"],
                  ["BOOST", "BST"],
                  ["OVERTAKE", "OVT"],
                ]
                  .map(
                    ([k, lbl]) =>
                      `<button class="pw-btn ${c.ers === k ? "active" : ""}" ${dis} data-pw-cmd="ers" data-drv="${c.id}" data-val="${k}">${lbl}</button>`
                  )
                  .join("")}
              </div>"""

pw_render_repl = """    wrap.innerHTML = myCars
      .map((c) => {
        const tm = TIRE_META[c.comp] || TIRE_META.MEDIUM;
        const isPreRace = tick.phase === "GRID_WALK" || (tick.phase === "RACE" && tick.lights > 0);
        const isRace = (tick.phase === "RACE" || tick.phase === "SPRINT_RACE") && !c.dnf;
        const dis = (isRace || isPreRace) ? "" : "disabled";
        const isV8 = tick.regulations && tick.regulations.era_id === "V8_DRS";
        const ersLabel = isV8 ? "KERS" : "ERS";
        const aeroLabel = (c.aero === "DRS" || c.drs) ? "DRS" : (c.aero === "STRAIGHT" ? "STR" : "CRN");
        const aeroColor = (c.aero === "DRS" || c.drs) ? "#00d26a" : (c.aero === "STRAIGHT" ? "#00d2be" : "#ffffff");
        return `
          <div class="pw-card" style="border-top-color:${c.tcol}">
            <div class="pw-top">
              <div class="pw-driver">
                ${teamLogoSVG(c.tid, 16)}
                <span>P${c.pos}  #${c.num} ${c.name}</span>
                ${c.man ? `<span class="badge b-man">${c.man}</span>` : ""}
                ${(c.drs || c.aero === "DRS") ? `<span class="badge b-drs">DRS ACTIVE</span>` : c.drs_elig ? `<span class="badge b-drs-arm">DRS ARMED</span>` : c.ovt ? `<span class="badge b-ovt">OVT DEPLOY</span>` : c.ovt_elig ? `<span class="badge b-elig">OVT ARMED</span>` : ""}
                ${c.elim ? `<span class="badge b-elim">OUT ${c.estg}</span>` : ""}
                ${c.pen > 0 ? `<span class="badge b-pen">+${c.pen}S PEN</span>` : ""}
                ${c.dmg > 15 ? `<span class="badge b-pen">FW DMG (${c.dmg_side || "FW"} -${c.dmg}%)</span>` : ""}
              </div>
              <div class="pw-metrics">
                <span><strong>${c.kph}</strong> KPH</span>
                <span>LAT <strong>${c.g_lat != null ? Math.abs(c.g_lat).toFixed(1) : "0.0"}G</strong></span>
                <span>AERO <strong style="color:${aeroColor}">${aeroLabel}</strong></span>
                <span>${ersLabel} <strong>${c.bat}%</strong></span>
                <span><span class="pirelli-badge" style="border-color:${tm.color};width:14px;height:14px;font-size:8.5px">${tm.code}</span> ${100 - c.wear}% (${c.tage}L)</span>
              </div>
            </div>

            <div class="pw-controls">
              <div class="pw-group">
                <button class="pw-btn ${c.auto ? "auto-on" : ""}" ${dis} data-pw-cmd="auto" data-drv="${c.id}" data-val="${!c.auto}" title="Toggle AI Chief Strategist">
                  ${c.auto ? "STRAT: AUTO" : "STRAT: MAN"}
                </button>
                <button class="pw-btn ${c.box ? "box-active" : ""}" ${dis} data-pw-cmd="box" data-drv="${c.id}" data-val="${!c.box}">
                  ${c.in_pit ? "IN PIT LANE" : c.box ? "BOX CONFIRMED" : "BOX THIS LAP"}
                </button>
              </div>

              ${isPreRace ? `
              <div class="pw-group" title="Select Starting Tyre Compound Before Lights Out">
                <span class="pw-lbl" style="color:#00d2be;font-weight:900">START TYRE</span>
                ${["SOFT", "MEDIUM", "HARD", "INTER", "WET"]
                  .map(
                    (k) =>
                      `<button class="pw-btn ${c.comp === k ? "active" : ""}" data-pw-cmd="start_comp" data-drv="${c.id}" data-val="${k}" style="${c.comp === k ? "" : `color:${TIRE_META[k].color}`}">${TIRE_META[k].code}</button>`
                  )
                  .join("")}
              </div>
              ` : `
              <div class="pw-group" title="Next Pit-Stop Tyre Compound">
                <span class="pw-lbl">TYRE</span>
                ${["SOFT", "MEDIUM", "HARD", "INTER", "WET"]
                  .map(
                    (k) =>
                      `<button class="pw-btn ${c.ncomp === k ? "active" : ""}" ${dis} data-pw-cmd="ncomp" data-drv="${c.id}" data-val="${k}" style="${c.ncomp === k ? "" : `color:${TIRE_META[k].color}`}">${TIRE_META[k].code}</button>`
                  )
                  .join("")}
              </div>
              `}

              <div class="pw-group" title="Target Pace Mode">
                <span class="pw-lbl">PACE</span>
                ${[
                  ["CONSERVE", "LIFT"],
                  ["BALANCED", "STD"],
                  ["PUSH", "PUSH"],
                  ["ATTACK", "MAX"],
                ]
                  .map(
                    ([k, lbl]) =>
                      `<button class="pw-btn ${c.pace === k ? "active" : ""}" ${dis} data-pw-cmd="pace" data-drv="${c.id}" data-val="${k}">${lbl}</button>`
                  )
                  .join("")}
              </div>

              <div class="pw-group" title="${isV8 ? "120kW KERS Deployment Profile" : "2026 MGU-K Deployment Profile"}">
                <span class="pw-lbl">${ersLabel}</span>
                ${[
                  ["HARVEST", "HRV"],
                  ["AUTO", "AUTO"],
                  ["BOOST", "BST"],
                  ["OVERTAKE", "OVT"],
                ]
                  .map(
                    ([k, lbl]) =>
                      `<button class="pw-btn ${c.ers === k ? "active" : ""}" ${dis} data-pw-cmd="ers" data-drv="${c.id}" data-val="${k}">${lbl}</button>`
                  )
                  .join("")}
              </div>"""

assert pw_render_target in text, "pw_render_target not found in app.js"
text = text.replace(pw_render_target, pw_render_repl, 1)

# 5. Telemetry update with DRS and V8 details
tel_target = """        <div>
          ${
            car.ovt
              ? `<span class="badge b-ovt">OVERTAKE OVERRIDE (&gt;290 KPH)</span>`
              : car.aero === "STRAIGHT"
              ? `<span class="badge b-str">STRAIGHT AERO (X-MODE)</span>`
              : `<span class="badge" style="background:#232331;color:#d4d4e0">CORNER AERO (Z-MODE)</span>`
          }
        </div>
      </div>
      <div class="bar-meter"><span style="width:${spdPct}%;background:${spdColor}"></span></div>

      <div style="display:flex;justify-content:space-between;font-size:10.5px;color:#8f90a6;font-weight:700;letter-spacing:0.4px">
        <span>MGU-K 350KW STORE (${car.rech ? "HARVESTING" : car.ovt ? "OVT DEPLOY" : car.boost ? "BOOST DEPLOY" : "BALANCED"})</span>
        <strong style="color:#ffffff">${car.bat}%</strong>
      </div>"""

tel_repl = """        <div>
          ${
            (car.drs || car.aero === "DRS")
              ? `<span class="badge b-drs">DRS OPEN (+22 KM/H DRAG REDUCTION)</span>`
              : car.ovt
              ? `<span class="badge b-ovt">OVERTAKE OVERRIDE (&gt;290 KPH)</span>`
              : car.aero === "STRAIGHT"
              ? `<span class="badge b-str">STRAIGHT AERO (X-MODE)</span>`
              : `<span class="badge" style="background:#232331;color:#d4d4e0">CORNER AERO (Z-MODE)</span>`
          }
        </div>
      </div>
      <div class="bar-meter"><span style="width:${spdPct}%;background:${spdColor}"></span></div>

      <div style="display:flex;justify-content:space-between;font-size:10.5px;color:#8f90a6;font-weight:700;letter-spacing:0.4px">
        <span>${(tick.regulations && tick.regulations.era_id === "V8_DRS") ? "KERS 120KW RECOVERY" : "MGU-K 350KW STORE"} (${car.rech ? "HARVESTING" : car.ovt ? "OVT DEPLOY" : car.boost ? "BOOST DEPLOY" : "BALANCED"})</span>
        <strong style="color:#ffffff">${car.bat}%</strong>
      </div>"""

assert tel_target in text, "tel_target not found in app.js"
text = text.replace(tel_target, tel_repl, 1)

# 6. Driver Market: update transfer window banner and disable buttons when locked
market_target = """    // 2. Driver Contracts & Trades Tab
    const myDrivers = st.drivers.filter((d) => d.team_id === st.player_team_id);
    const rivalDrivers = st.drivers.filter((d) => d.team_id && d.team_id !== st.player_team_id);
    const freeAgents = st.drivers.filter((d) => !d.team_id);"""

market_repl = """    // 2. Driver Contracts & Trades Tab
    const windowOpen = st.transfer_window_open !== false;
    const winBadge = document.getElementById("window-status-badge");
    const winDesc = document.getElementById("window-status-desc");
    if (winBadge && winDesc) {
      if (windowOpen) {
        winBadge.className = "window-badge window-open";
        winBadge.textContent = "TRANSFER WINDOW: OPEN";
        winDesc.textContent = "Season opening transfer period active (Round 1 & Off-Season). Driver trades and free agent signings are permitted.";
      } else {
        winBadge.className = "window-badge window-locked";
        winBadge.textContent = "TRANSFER WINDOW: LOCKED (ROUNDS 2-24)";
        winDesc.textContent = "FIA regulations restrict driver transfers and signings during mid-season. The transfer window opens at the start of next season (Round 1 & Off-Season).";
      }
    }

    const myDrivers = st.drivers.filter((d) => d.team_id === st.player_team_id);
    const rivalDrivers = st.drivers.filter((d) => d.team_id && d.team_id !== st.player_team_id);
    const freeAgents = st.drivers.filter((d) => !d.team_id);"""

assert market_target in text, "market_target not found in app.js"
text = text.replace(market_target, market_repl, 1)

# Free Agent button disabled when transfer window closed
fa_btn_target = """          <button class="btn-outline btn-sm" data-sign-fa="${d.id}">SIGN ($${d.signing_m.toFixed(1)}M + BUYOUT)</button>"""
fa_btn_repl = """          <button class="btn-outline btn-sm" data-sign-fa="${d.id}" ${windowOpen ? "" : "disabled"} title="${windowOpen ? "Sign driver" : "Transfer window is locked until next season"}">
            ${windowOpen ? `SIGN ($${d.signing_m.toFixed(1)}M + BUYOUT)` : "WINDOW LOCKED"}
          </button>"""

assert fa_btn_target in text, "fa_btn_target not found in app.js"
text = text.replace(fa_btn_target, fa_btn_repl, 1)

# 7. In previewTradeValuation, check windowOpen
trade_eval_target = """  async previewTradeValuation() {
    const myId = document.getElementById("trade-my-driver").value;
    const tgtId = document.getElementById("trade-target-driver").value;
    const cash = parseFloat(document.getElementById("trade-cash-slider").value || "0");
    if (!myId || !tgtId) return;

    const res = await fetch("/api/evaluate_trade", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ my_driver_id: myId, target_driver_id: tgtId, cash_offer_m: cash }),
    }).then((r) => r.json());

    const box = document.getElementById("trade-eval-box");
    const btn = document.getElementById("btn-exec-trade");
    if (res.ok) {
      box.className = `trade-eval-box ${res.accepted ? "ok" : "no"}`;
      box.textContent = res.reason;
      btn.disabled = !res.accepted;
    }
  }"""

trade_eval_repl = """  async previewTradeValuation() {
    const myId = document.getElementById("trade-my-driver").value;
    const tgtId = document.getElementById("trade-target-driver").value;
    const cash = parseFloat(document.getElementById("trade-cash-slider").value || "0");
    const box = document.getElementById("trade-eval-box");
    const btn = document.getElementById("btn-exec-trade");
    if (!myId || !tgtId) return;

    const windowOpen = this.fullState && this.fullState.transfer_window_open !== false;
    if (!windowOpen) {
      box.className = "trade-eval-box no";
      box.textContent = "TRANSFER WINDOW LOCKED: FIA regulations permit driver trades and free agent signings only at the start of each season (Round 1 or Off-Season).";
      btn.disabled = true;
      btn.title = "Transfer window locked during mid-season.";
      return;
    }

    const res = await fetch("/api/evaluate_trade", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ my_driver_id: myId, target_driver_id: tgtId, cash_offer_m: cash }),
    }).then((r) => r.json());

    if (res.ok) {
      box.className = `trade-eval-box ${res.accepted ? "ok" : "no"}`;
      box.textContent = res.reason;
      btn.disabled = !res.accepted;
    } else {
      box.className = "trade-eval-box no";
      box.textContent = res.error || "Unable to evaluate trade.";
      btn.disabled = true;
    }
  }"""

assert trade_eval_target in text, "trade_eval_target not found in app.js"
text = text.replace(trade_eval_target, trade_eval_repl, 1)

path.write_text(text, encoding="utf-8")
print("Successfully patched public/app.js!")
