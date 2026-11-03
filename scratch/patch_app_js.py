# Scratch patch for public/app.js

with open('public/app.js', 'r', encoding='utf-8') as f:
    js = f.read()

# 1. Update constructor
c_target = """    this.lastRoundKey = "";
    this.lastEventId = -1;
    this.lastDomSyncMs = 0;"""

c_repl = """    this.lastRoundKey = "";
    this.lastEventId = -1;
    this.lastDomSyncMs = 0;
    this.feedFilter = "all";
    this.lastEvents = [];
    this.driverSearchQuery = "";
    this.driverCategory = "all";
    this.driverSortColumn = "overall";
    this.driverSortAsc = false;"""

assert c_target in js, "c_target not found in app.js"
js = js.replace(c_target, c_repl, 1)

# 2. Add event listeners in _bindUI()
bind_target = """      if (res.ok) {
        this.showToast(`CONTRACT REGISTERED: ${res.message}`);
        this.fetchFullState();
      }
    });
  }"""

bind_repl = """      if (res.ok) {
        this.showToast(`CONTRACT REGISTERED: ${res.message}`);
        this.fetchFullState();
      }
    });

    // Feed filter buttons (All / Official / Radio)
    document.querySelectorAll(".feed-filter-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        document.querySelectorAll(".feed-filter-btn").forEach((b) => b.classList.remove("active"));
        btn.classList.add("active");
        this.feedFilter = btn.dataset.feedFilter;
        this.renderEventFeed(this.lastEvents, true);
      });
    });

    // Driver Database search input
    const drvSearch = document.getElementById("driver-search-input");
    if (drvSearch) {
      drvSearch.addEventListener("input", (e) => {
        this.driverSearchQuery = e.target.value.trim().toLowerCase();
        this.renderDriverDatabase();
      });
    }

    // Driver Database category filter buttons
    document.querySelectorAll(".drv-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        document.querySelectorAll(".drv-btn").forEach((b) => b.classList.remove("active"));
        btn.classList.add("active");
        this.driverCategory = btn.dataset.cat;
        this.renderDriverDatabase();
      });
    });

    // Driver Database sortable table headers
    document.querySelectorAll("#scouting-table th.sortable").forEach((th) => {
      th.addEventListener("click", () => {
        const col = th.dataset.sort;
        if (this.driverSortColumn === col) {
          this.driverSortAsc = !this.driverSortAsc;
        } else {
          this.driverSortColumn = col;
          this.driverSortAsc = (col === "name" || col === "team");
        }
        this.renderDriverDatabase();
      });
    });
  }"""

assert bind_target in js, "bind_target not found in app.js"
js = js.replace(bind_target, bind_repl, 1)

# 3. Update renderEventFeed
feed_target = """  renderEventFeed(events) {
    if (!events || events.length === 0) return;
    const latestId = events[events.length - 1].id;
    if (latestId === this.lastEventId) return;
    this.lastEventId = latestId;

    const list = document.getElementById("feed-list");
    list.innerHTML = [...events]
      .reverse()
      .map(
        (ev) => `
        <div class="feed-item feed-${ev.kind}">
          <span class="f-tag">${ev.tag} | ${ev.kind}</span>${ev.msg}
        </div>
      `
      )
      .join("");
  }"""

feed_repl = """  isOfficialEvent(ev) {
    const officialKinds = ["RACE_CONTROL", "STEWARDS", "PENALTY", "WEATHER", "OFFICIAL", "YELLOW", "SC", "VSC", "GRID", "STAGE", "CHEQUERED", "POLE"];
    if (officialKinds.includes(ev.kind)) return true;
    const msg = (ev.msg || "").toUpperCase();
    return msg.includes("RACE CONTROL") || msg.includes("STEWARDS") || msg.includes("PENALTY") ||
           msg.includes("SAFETY CAR") || msg.includes("VSC") || msg.includes("FLAG") || msg.includes("TRACK LIMITS") || msg.includes("WEATHER");
  }

  isRadioEvent(ev) {
    if (ev.kind === "RADIO" || ev.kind === "PIT_RADIO") return true;
    const msg = (ev.msg || "").toUpperCase();
    return msg.includes("RADIO") || msg.includes("TEAM ORDERS") || msg.includes("BOX, BOX") || msg.includes("ENGINEER");
  }

  renderEventFeed(events, force = false) {
    if (events && events.length > 0) {
      this.lastEvents = events;
    } else {
      events = this.lastEvents || [];
    }
    if (!events || events.length === 0) return;

    const latestId = events[events.length - 1].id;
    if (!force && latestId === this.lastEventId) return;
    this.lastEventId = latestId;

    let filtered = events;
    if (this.feedFilter === "official") {
      filtered = events.filter((ev) => this.isOfficialEvent(ev));
    } else if (this.feedFilter === "radio") {
      filtered = events.filter((ev) => this.isRadioEvent(ev));
    }

    const list = document.getElementById("feed-list");
    if (!list) return;

    if (filtered.length === 0) {
      const label = this.feedFilter === "radio" ? "radio transmissions" : "official notices";
      list.innerHTML = `<div class="feed-empty">No ${label} recorded yet in this session.</div>`;
      return;
    }

    list.innerHTML = [...filtered]
      .reverse()
      .map(
        (ev) => `
        <div class="feed-item feed-${ev.kind}">
          <span class="f-tag">${ev.tag} | ${ev.kind}</span>${ev.msg}
        </div>
      `
      )
      .join("");
  }"""

assert feed_target in js, "feed_target not found in app.js"
js = js.replace(feed_target, feed_repl, 1)

# 4. Update free agent cards with legend badge and scouting-table to use renderDriverDatabase()
fa_target = """    document.getElementById("free-agent-list").innerHTML = freeAgents
      .map(
        (d) => `
        <div class="fa-item">
          <div>
            <strong>#${d.number} ${d.name.toUpperCase()}</strong> <span style="color:#e10600;font-weight:900;margin-left:6px">INDEX ${d.overall}</span>
            <div style="font-size:11px;color:#8f90a6">AGE ${d.age} | PACE ${d.pace} | CRAFT ${d.racecraft} | RETAINER $${d.salary_m}M/YR</div>
          </div>
          <button class="btn-outline btn-sm" data-sign-fa="${d.id}">SIGN ($${d.signing_m.toFixed(1)}M + BUYOUT)</button>
        </div>
      `
      )
      .join("");"""

fa_repl = """    document.getElementById("free-agent-list").innerHTML = freeAgents
      .map(
        (d) => `
        <div class="fa-item">
          <div>
            <strong>#${d.number} ${d.name.toUpperCase()}</strong>${d.legend ? '<span class="legend-badge">LEGEND</span>' : ''} <span style="color:#e10600;font-weight:900;margin-left:6px">INDEX ${d.overall}</span>
            <div style="font-size:11px;color:#8f90a6">AGE ${d.age} | PACE ${d.pace} | CRAFT ${d.racecraft} | RETAINER $${d.salary_m}M/YR</div>
          </div>
          <button class="btn-outline btn-sm" data-sign-fa="${d.id}">SIGN ($${d.signing_m.toFixed(1)}M + BUYOUT)</button>
        </div>
      `
      )
      .join("");"""

assert fa_target in js, "fa_target not found in app.js"
js = js.replace(fa_target, fa_repl, 1)

# 5. Replace scouting-table rendering with call to this.renderDriverDatabase()
scout_target = """    document.querySelector("#scouting-table tbody").innerHTML = st.drivers
      .map(
        (d) => `
        <tr class="${d.team_id === st.player_team_id ? "highlight-me" : ""}">
          <td><strong>#${d.number} ${d.name}</strong></td>
          <td>
            <span class="inline-team" style="color:${d.team_color};font-weight:700">
              ${d.team_id ? teamLogoSVG(d.team_id, 14) : ""}
              ${d.team_short.toUpperCase()}
            </span>
          </td>
          <td>${d.age}</td>
          <td><strong>${d.overall}</strong></td>
          <td>${d.pace}</td>
          <td>${d.racecraft}</td>
          <td>${d.defense}</td>
          <td>${d.consistency}</td>
          <td>${d.tire_mgmt}</td>
          <td>${d.wet_skill}</td>
          <td>$${d.salary_m.toFixed(1)}M</td>
          <td>$${d.value_m.toFixed(1)}M</td>
        </tr>
      `
      )
      .join("");"""

scout_repl = """    this.renderDriverDatabase();"""

assert scout_target in js, "scout_target not found in app.js"
js = js.replace(scout_target, scout_repl, 1)

# 6. Add renderDriverDatabase method definition right before renderManagementViews or at end
driver_db_method = """  renderDriverDatabase() {
    if (!this.fullState || !this.fullState.drivers) return;
    const st = this.fullState;
    const allDrivers = st.drivers;

    // Update category counters
    const cntAll = document.getElementById("cnt-all");
    const cntGrid = document.getElementById("cnt-grid");
    const cntFa = document.getElementById("cnt-fa");
    const cntLeg = document.getElementById("cnt-leg");

    const gridDrivers = allDrivers.filter((d) => d.team_id);
    const faDrivers = allDrivers.filter((d) => !d.team_id);
    const legDrivers = allDrivers.filter((d) => d.legend);

    if (cntAll) cntAll.textContent = allDrivers.length;
    if (cntGrid) cntGrid.textContent = gridDrivers.length;
    if (cntFa) cntFa.textContent = faDrivers.length;
    if (cntLeg) cntLeg.textContent = legDrivers.length;

    // Filter by active category
    let list = [...allDrivers];
    if (this.driverCategory === "active") {
      list = gridDrivers;
    } else if (this.driverCategory === "fa") {
      list = faDrivers;
    } else if (this.driverCategory === "legend") {
      list = legDrivers;
    }

    // Filter by search query
    if (this.driverSearchQuery) {
      const q = this.driverSearchQuery
        .normalize("NFD")
        .replace(/[\u0300-\u036f]/g, "");
      list = list.filter((d) => {
        const normName = (d.name || "")
          .normalize("NFD")
          .replace(/[\u0300-\u036f]/g, "")
          .toLowerCase();
        const normTeam = (d.team_short || "").toLowerCase();
        const normCode = (d.code || "").toLowerCase();
        const normNat = (d.nationality || "").toLowerCase();
        const numStr = String(d.number || "");
        return (
          normName.includes(q) ||
          normTeam.includes(q) ||
          normCode.includes(q) ||
          normNat.includes(q) ||
          numStr === q
        );
      });
    }

    // Sort list
    const col = this.driverSortColumn || "overall";
    const asc = this.driverSortAsc;
    list.sort((a, b) => {
      let valA, valB;
      if (col === "name") {
        valA = a.name.toLowerCase();
        valB = b.name.toLowerCase();
      } else if (col === "team") {
        valA = (a.team_short || "").toLowerCase();
        valB = (b.team_short || "").toLowerCase();
      } else {
        valA = Number(a[col]) || 0;
        valB = Number(b[col]) || 0;
      }
      if (valA < valB) return asc ? -1 : 1;
      if (valA > valB) return asc ? 1 : -1;
      return 0;
    });

    // Update sort icons in table headers
    document.querySelectorAll("#scouting-table th.sortable").forEach((th) => {
      const icon = th.querySelector(".sort-icon");
      if (!icon) return;
      if (th.dataset.sort === col) {
        icon.textContent = asc ? "▲" : "▼";
      } else {
        icon.textContent = "";
      }
    });

    const tbody = document.querySelector("#scouting-table tbody");
    if (!tbody) return;

    if (list.length === 0) {
      tbody.innerHTML = `
        <tr>
          <td colspan="12" style="text-align:center;padding:26px 12px;color:#8f90a6;font-style:italic">
            No drivers found matching current filter or search criteria.
          </td>
        </tr>
      `;
      return;
    }

    tbody.innerHTML = list
      .map(
        (d) => `
        <tr class="${d.team_id === st.player_team_id ? "highlight-me" : ""}">
          <td>
            <strong>#${d.number} ${d.name}</strong>
            ${d.legend ? '<span class="legend-badge">LEGEND</span>' : ""}
          </td>
          <td>
            <span class="inline-team" style="color:${d.team_color};font-weight:700">
              ${d.team_id ? teamLogoSVG(d.team_id, 14) : ""}
              ${d.team_short.toUpperCase()}
            </span>
          </td>
          <td>${d.age}</td>
          <td><strong style="color:${d.overall >= 95 ? "#e10600" : "#ffffff"}">${d.overall}</strong></td>
          <td>${d.pace}</td>
          <td>${d.racecraft}</td>
          <td>${d.defense}</td>
          <td>${d.consistency}</td>
          <td>${d.tire_mgmt}</td>
          <td>${d.wet_skill}</td>
          <td>$${d.salary_m.toFixed(1)}M</td>
          <td>$${d.value_m.toFixed(1)}M</td>
        </tr>
      `
      )
      .join("");
  }
"""

js = js.replace("  renderManagementViews() {", driver_db_method + "\n  renderManagementViews() {", 1)

with open('public/app.js', 'w', encoding='utf-8', newline='\r\n') as f:
    f.write(js)

print("Successfully patched public/app.js")

