// FOM Broadcast & Pit Wall Controller — Zero Emojis, Vector Team Logos & Live 20Hz SSE
import { CircuitRenderer } from "/canvas.js";
import { teamLogoSVG } from "/logos.js";

const TIRE_META = {
  SOFT:   { code: "S", color: "#ff2800", optMin: 90, optMax: 106 },
  MEDIUM: { code: "M", color: "#ffd200", optMin: 95, optMax: 113 },
  HARD:   { code: "H", color: "#f0f2f5", optMin: 100, optMax: 120 },
  INTER:  { code: "I", color: "#38b000", optMin: 70, optMax: 92 },
  WET:    { code: "W", color: "#0096ff", optMin: 60, optMax: 85 },
};

function getTempColor(comp, ttemp) {
  const tm = TIRE_META[comp] || TIRE_META.MEDIUM;
  if (!ttemp) return "#d4d4e0";
  if (ttemp > tm.optMax + 10) return "#ff2800"; // Blistering
  if (ttemp > tm.optMax) return "#ff8c00";      // Overheating
  if (ttemp < tm.optMin - 8) return "#0096ff";  // Cold
  if (ttemp < tm.optMin) return "#00d2be";      // Warming
  return "#00d26a";                             // Optimal
}

function getTempStatus(comp, ttemp) {
  const tm = TIRE_META[comp] || TIRE_META.MEDIUM;
  if (!ttemp) return "OPTIMAL";
  if (ttemp > tm.optMax + 10) return "BLISTERING";
  if (ttemp > tm.optMax) return "OVERHEATING";
  if (ttemp < tm.optMin - 8) return "COLD";
  if (ttemp < tm.optMin) return "WARMING";
  return "OPTIMAL";
}

function fmtLap(sec) {
  if (!Number.isFinite(sec) || sec <= 0) return "--:--.---";
  const ms = Math.round(sec * 1000);
  const m = Math.floor(ms / 60000);
  const s = Math.floor((ms % 60000) / 1000);
  return `${m}:${String(s).padStart(2, "0")}.${String(ms % 1000).padStart(3, "0")}`;
}

function fmtSector(sec) {
  return Number.isFinite(sec) && sec > 0 ? sec.toFixed(3) : "--.---";
}

function fmtGap(sec) {
  return Number.isFinite(sec) ? `+${Math.max(0, sec).toFixed(3)}` : "--.---";
}

function timingClass(time, personalBest, sessionBest) {
  if (!Number.isFinite(time) || time <= 0) return "time-pending";
  if (sessionBest != null && time <= sessionBest + 0.0005) return "time-session-best";
  if (personalBest != null && time <= personalBest + 0.0005) return "time-personal-best";
  return "time-slower";
}

function fmtMoney(m) {
  const sign = m < 0 ? "-" : "";
  return `${sign}$${Math.abs(m).toFixed(2)}M`;
}

const SETUP_LABELS = {
  "-2": "MONZA LOW DF",
  "-1": "LOW-MED DF",
  "0": "BALANCED DF",
  "1": "MED-HIGH DF",
  "2": "MAX DOWNFORCE",
};

function fmtAdvice(advice) {
  if (!advice) return "";
  if (typeof advice === "string") return advice;
  const act = advice.action === "BOX"
    ? `${advice.mode || "BOX"} -> ${advice.compound || ""}${advice.gain_s ? ` (${advice.gain_s > 0 ? "+" : ""}${Number(advice.gain_s).toFixed(1)}s)` : ""}`
    : `${advice.mode || "STAY OUT"}`;
  const rsn = advice.reason ? ` · ${advice.reason}` : "";
  return `${act}${rsn}`;
}

class F1App {
  constructor() {
    this.fullState = null;
    this.liveTick = null;
    this.selectedDriverId = null;
    this.compareDriverId = null;
    this._negBound = false;
    this.activeTab = "circuit";
    this.lastRoundKey = "";
    this.lastEventId = -1;
    this.lastDomSyncMs = 0;
    this.feedFilter = "all";
    this.lastEvents = [];
    this.driverSearchQuery = "";
    this.driverCategory = "all";
    this.driverSortColumn = "overall";
    this.driverSortAsc = false;
    this._lastHeaderLogoTeam = "";
    this.selectedHofSeason = 2026;
    this.hofViewMode = "races";

    const canvas = document.getElementById("track-canvas");
    this.renderer = new CircuitRenderer(canvas, (drvId) => this.selectDriver(drvId));

    this._bindUI();
    this.fetchFullState();
    this._connectSSE();
  }

  async apiPost(path, body = {}) {
    try {
      const res = await fetch(path, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (!data.ok) {
        this.showToast(`NOTICE: ${data.error || "Request declined"}`);
      }
      return data;
    } catch {
      this.showToast("CONNECTION LOST: Unable to reach simulation server");
      return { ok: false };
    }
  }

  async fetchFullState() {
    try {
      const res = await fetch("/api/state");
      const data = await res.json();
      this.fullState = data;
      if (data.track) {
        this.renderer.setTrack(data.track);
      }
      if (!this.selectedDriverId && data.drivers.length > 0) {
        const myFirst = data.drivers.find((d) => d.team_id === data.player_team_id);
        this.selectDriver(myFirst ? myFirst.id : data.drivers[0].id);
      }
      this.renderManagementViews();
    } catch (e) {
      console.error("State sync failed", e);
    }
  }

  _connectSSE() {
    const connEl = document.getElementById("hdr-conn");
    const es = new EventSource("/api/stream");

    es.onopen = () => {
      connEl.textContent = "LIVE";
      connEl.classList.remove("offline");
    };

    es.onmessage = (ev) => {
      const tick = JSON.parse(ev.data);
      this.onLiveTick(tick);
    };

    es.onerror = () => {
      connEl.textContent = "SYNC";
      connEl.classList.add("offline");
    };
  }

  selectDriver(driverId) {
    this.selectedDriverId = driverId;
    this.renderer.setSelectedDriver(driverId);
    if (this.liveTick) {
      this.renderTelemetry(this.liveTick);
      this.renderTimingTower(this.liveTick);
    }
  }

  toggleCompareDriver(driverId) {
    this.compareDriverId = this.compareDriverId === driverId ? null : driverId;
    if (this.liveTick) {
      this.renderTelemetry(this.liveTick);
      this.renderTimingTower(this.liveTick);
    }
  }

  showToast(msg) {
    const el = document.getElementById("toast");
    el.textContent = msg;
    el.classList.remove("hidden");
    clearTimeout(this._toastTimer);
    this._toastTimer = setTimeout(() => el.classList.add("hidden"), 3400);
  }

  _bindUI() {
    document.querySelectorAll(".nav-tab").forEach((btn) => {
      btn.addEventListener("click", () => {
        document.querySelectorAll(".nav-tab").forEach((b) => b.classList.remove("active"));
        document.querySelectorAll(".tab-pane").forEach((p) => p.classList.remove("active"));
        btn.classList.add("active");
        this.activeTab = btn.dataset.tab;
        document.getElementById(`tab-${this.activeTab}`).classList.add("active");
        if (this.activeTab === "circuit") {
          setTimeout(() => this.renderer.resize(), 20);
        } else {
          this.fetchFullState();
        }
      });
    });

    document.querySelectorAll(".spd-btn").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const spd = parseFloat(btn.dataset.speed);
        await this.apiPost("/api/speed", { speed: spd });
      });
    });

    document.getElementById("btn-skip").addEventListener("click", async () => {
      const btn = document.getElementById("btn-skip");
      btn.disabled = true;
      const res = await this.apiPost("/api/skip");
      btn.disabled = false;
      if (res.ok) {
        this.lastDomSyncMs = 0;
        this.fetchFullState();
      }
    });

    document.querySelectorAll(".cam-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        document.querySelectorAll(".cam-btn").forEach((b) => b.classList.remove("active"));
        btn.classList.add("active");
        this.renderer.setCameraMode(btn.dataset.cam);
      });
    });

    document.getElementById("timing-list").addEventListener("pointerdown", (e) => {
      const vsBtn = e.target.closest("button[data-vs-id]");
      if (vsBtn) {
        e.stopPropagation();
        this.toggleCompareDriver(vsBtn.dataset.vsId);
        return;
      }
      const row = e.target.closest(".t-row");
      if (row && row.dataset.id) {
        this.selectDriver(row.dataset.id);
      }
    });

    document.getElementById("pitwall-cards").addEventListener("pointerdown", async (e) => {
      const btn = e.target.closest("button[data-pw-cmd]");
      if (!btn || btn.disabled) return;
      const driverId = btn.dataset.drv;
      const cmd = btn.dataset.pwCmd;
      const val = btn.dataset.val;
      const payload = { driver_id: driverId };

      if (cmd === "setup_df") {
        const res = await this.apiPost("/api/set_setup", { driver_id: driverId, setup_df: Number(val) });
        if (res.ok) {
          this.showToast(`SETUP CONFIRMED: #${driverId.toUpperCase()} -> ${res.setup_label}`);
          this.fetchFullState();
          this.lastDomSyncMs = 0;
        }
        return;
      }
      if (cmd === "auto") payload.auto_strategy = val === "true";
      else if (cmd === "box") payload.box_this_lap = val === "true";
      else if (cmd === "lift_coast") payload.lift_coast = val === "true";
      else if (cmd === "prefer_fresh") payload.prefer_fresh = val === "true";
      else if (cmd === "start_comp") {
        const res = await this.apiPost("/api/set_starting_compound", { driver_id: driverId, compound: val });
        if (res.ok) {
          this.showToast(`START TYRE CONFIRMED: #${driverId.toUpperCase()} on ${val} tyres!`);
          if (this.liveTick && this.liveTick.cars) {
            const myCar = this.liveTick.cars.find(c => c.id === driverId);
            if (myCar) {
              const oldComp = myCar.comp;
              myCar.comp = val;
              myCar.ncomp = val;
              if (myCar.tsets && oldComp !== val) {
                if (myCar.tsets[oldComp] != null) myCar.tsets[oldComp]++;
                if (myCar.tsets[val] != null && myCar.tsets[val] > 0) myCar.tsets[val]--;
              }
              this.renderPitWall(this.liveTick);
            }
          }
        }
        this.lastDomSyncMs = 0;
        return;
      }
      else if (cmd === "ncomp") payload.next_compound = val;
      else if (cmd === "pace") payload.pace_mode = val;
      else if (cmd === "ers") payload.ers_mode = val;
      else if (cmd === "order") payload.team_order = val;

      const res = await this.apiPost("/api/pit_wall", payload);
      if (res.ok) {
        if (cmd === "ncomp") {
          this.showToast(`NEXT TYRE QUEUED: #${driverId.toUpperCase()} on ${val} tyres!`);
          if (this.liveTick && this.liveTick.cars) {
            const myCar = this.liveTick.cars.find(c => c.id === driverId);
            if (myCar) {
              myCar.ncomp = val;
              this.renderPitWall(this.liveTick);
            }
          }
        }
        this.lastDomSyncMs = 0;
      }
    });

    const modal = document.getElementById("team-modal");
    document.getElementById("btn-open-team-modal").addEventListener("click", () => {
      this.renderTeamModal();
      modal.classList.remove("hidden");
    });
    document.getElementById("btn-close-modal").addEventListener("click", () => modal.classList.add("hidden"));
    document.getElementById("btn-reset-career").addEventListener("click", async () => {
      const tid = this.fullState ? this.fullState.player_team_id : "williams";
      const res = await this.apiPost("/api/reset", { team_id: tid, year: 2026 });
      if (res.ok) {
        modal.classList.add("hidden");
        this.showToast("SEASON RESET: 2026 FIA Formula 1 World Championship initialized");
        this.fetchFullState();
      }
    });

    const btnReset2028 = document.getElementById("btn-reset-2028");
    if (btnReset2028) {
      btnReset2028.addEventListener("click", async () => {
        const tid = this.fullState ? this.fullState.player_team_id : "williams";
        const res = await this.apiPost("/api/reset", { team_id: tid, year: 2028 });
        if (res.ok) {
          modal.classList.add("hidden");
          this.showToast("SEASON LAUNCH: 2028 FIA 2.4L V8 & Classic DRS Era initialized!");
          this.fetchFullState();
        }
      });
    }

    const evalHandler = () => this.previewTradeValuation();
    document.getElementById("trade-my-driver").addEventListener("change", evalHandler);
    document.getElementById("trade-target-driver").addEventListener("change", evalHandler);
    document.getElementById("trade-cash-slider").addEventListener("input", () => {
      const v = parseFloat(document.getElementById("trade-cash-slider").value);
      document.getElementById("trade-cash-label").textContent = fmtMoney(v);
      this.previewTradeValuation();
    });

    document.getElementById("btn-exec-trade").addEventListener("click", async () => {
      const myId = document.getElementById("trade-my-driver").value;
      const tgtId = document.getElementById("trade-target-driver").value;
      const cash = parseFloat(document.getElementById("trade-cash-slider").value);
      const res = await this.apiPost("/api/execute_trade", {
        my_driver_id: myId,
        target_driver_id: tgtId,
        cash_offer_m: cash,
      });
      if (res.ok) {
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

    const gotoDbBtn = document.getElementById("btn-goto-database");
    if (gotoDbBtn) {
      gotoDbBtn.addEventListener("click", () => {
        const tabBtn = document.querySelector('.nav-tab[data-tab="database"]');
        if (tabBtn) tabBtn.click();
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

    // Hall of Fame season selector buttons (2026 - 2030)
    document.querySelectorAll(".hof-season-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        document.querySelectorAll(".hof-season-btn").forEach((b) => b.classList.remove("active"));
        btn.classList.add("active");
        this.selectedHofSeason = parseInt(btn.dataset.year);
        this.renderHallOfFame();
      });
    });

    // Hall of Fame subnav toggle: Races vs Standings
    const subRacesBtn = document.getElementById("hof-sub-races");
    const subStandingsBtn = document.getElementById("hof-sub-standings");
    if (subRacesBtn && subStandingsBtn) {
      subRacesBtn.addEventListener("click", () => {
        subRacesBtn.classList.add("active");
        subStandingsBtn.classList.remove("active");
        const racesView = document.getElementById("hof-races-view");
        const stView = document.getElementById("hof-standings-view");
        if (racesView) racesView.classList.remove("hidden");
        if (stView) stView.classList.add("hidden");
        this.hofViewMode = "races";
      });
      subStandingsBtn.addEventListener("click", () => {
        subStandingsBtn.classList.add("active");
        subRacesBtn.classList.remove("active");
        const racesView = document.getElementById("hof-races-view");
        const stView = document.getElementById("hof-standings-view");
        if (racesView) racesView.classList.add("hidden");
        if (stView) stView.classList.remove("hidden");
        this.hofViewMode = "standings";
      });
    }

    const analyticsModal = document.getElementById("analytics-modal");
    const closeAnalyticsBtn = document.getElementById("btn-close-analytics");
    if (analyticsModal && closeAnalyticsBtn) {
      closeAnalyticsBtn.addEventListener("click", () => analyticsModal.classList.add("hidden"));
      analyticsModal.addEventListener("click", (e) => {
        if (e.target === analyticsModal) analyticsModal.classList.add("hidden");
      });
    }

    const phaseOv = document.getElementById("phase-overlay");
    if (phaseOv) {
      phaseOv.addEventListener("click", (e) => {
        if (e.target.closest("button[data-open-podium-analytics]") && this.liveTick?.podium) {
          this.openAnalyticsModal(this.liveTick.podium);
        }
      });
    }

    // Hall of Fame expandable Top 10 classifications & Analytics Modal
    const racesGrid = document.getElementById("hof-races-grid");
    if (racesGrid) {
      racesGrid.addEventListener("click", (e) => {
        const analyticsBtn = e.target.closest("button[data-analytics-round]");
        if (analyticsBtn) {
          const rNum = Number(analyticsBtn.dataset.analyticsRound);
          const archive = this.fullState?.season_archives?.seasons?.[String(this.selectedHofSeason)];
          const raceObj = archive?.races?.find((item) => item.round === rNum);
          if (raceObj) this.openAnalyticsModal(raceObj);
          return;
        }
        const btn = e.target.closest(".hof-card-btn");
        if (!btn) return;
        const roundNum = btn.dataset.round;
        const drawer = document.getElementById(`hof-top10-${roundNum}`);
        if (drawer) {
          const isHidden = drawer.classList.contains("hidden");
          drawer.classList.toggle("hidden");
          btn.textContent = isHidden ? "HIDE TOP 10 CLASSIFICATION" : "VIEW TOP 10 CLASSIFICATION";
        }
      });
    }
  }

  onLiveTick(tick) {
    const prevPhase = this.liveTick ? this.liveTick.phase : "";
    this.liveTick = tick;
    this.renderer.pushTick(tick);

    const roundKey = `${tick.season}-${tick.round}-${tick.track_id}`;
    if (
      roundKey !== this.lastRoundKey ||
      (prevPhase === "RACE" && tick.phase === "PODIUM") ||
      (prevPhase === "SPRINT_RACE" && tick.phase !== "SPRINT_RACE") ||
      (prevPhase === "OFF_SEASON" && tick.phase !== "OFF_SEASON")
    ) {
      this.lastRoundKey = roundKey;
      this.fetchFullState();
    }

    this.renderHeader(tick);
    this.renderLightsAndPhaseOverlay(tick);

    const now = performance.now();
    if (now - this.lastDomSyncMs > 190) {
      this.lastDomSyncMs = now;
      this.renderTimingTower(tick);
      this.renderPitWall(tick);
      this.renderTelemetry(tick);
      this.renderEventFeed(tick.events);
    }
  }

  renderHeader(tick) {
    const rndStr = String(tick.round).padStart(2, "0");
    const widthTxt = tick.track_width_m ? ` | ${tick.track_width_m.toFixed(1)}M WIDE` : "";
    const reg = tick.regulations;
    const eraBadge = reg ? `<span class="reg-era-pill ${reg.era_id === "V8_DRS" ? "era-v8" : "era-hybrid"}" title="${reg.description}">${reg.short_name.toUpperCase()}</span>` : "";
    document.getElementById("hdr-round").innerHTML = `${tick.season} FIA WORLD CHAMPIONSHIP | R${rndStr}/${tick.total_rounds} | ${tick.city.toUpperCase()}${widthTxt} ${eraBadge}`;
    const gpEl = document.getElementById("hdr-gp");
    gpEl.innerHTML = `${tick.gp_name}${tick.is_sprint_weekend ? '<span class="sprint-pill">SPRINT</span>' : ""}`;

    const sessEl = document.getElementById("hdr-session");
    if (tick.phase === "RACE") {
      sessEl.textContent = `GP LAP ${tick.lap} / ${tick.total_laps}`;
    } else if (tick.phase === "SPRINT_RACE") {
      sessEl.textContent = `SPRINT ${tick.lap} / ${tick.total_laps}`;
    } else if (tick.phase === "QUALIFYING" || tick.phase === "SPRINT_QUALIFYING") {
      const stg = tick.quali_stage || (tick.phase === "SPRINT_QUALIFYING" ? "SQ" : "QUALI");
      const m = Math.floor(tick.clock / 60);
      const s = Math.floor(tick.clock % 60);
      sessEl.textContent = `${stg}  ${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
    } else if (tick.phase === "GRID_WALK") {
      sessEl.textContent = `FORMATION  00:${String(Math.ceil(tick.phase_timer)).padStart(2, "0")}`;
    } else if (tick.phase === "PODIUM") {
      sessEl.textContent = `POST-RACE  00:${String(Math.ceil(tick.phase_timer)).padStart(2, "0")}`;
    } else if (tick.phase === "OFF_SEASON") {
      sessEl.textContent = `WINTER TEST  00:${String(Math.ceil(tick.phase_timer)).padStart(2, "0")}`;
    } else {
      sessEl.textContent = `BUILD-UP  00:${String(Math.ceil(tick.phase_timer)).padStart(2, "0")}`;
    }

    // Dynamic Phase-Aware Action Label & Tooltip for the Advance Button (#btn-skip)
    const skipBtn = document.getElementById("btn-skip");
    if (tick.phase === "PRE_WEEKEND") {
      skipBtn.textContent = tick.is_sprint_weekend ? "START SQ1 >>" : "START Q1 >>";
      skipBtn.title = tick.is_sprint_weekend
        ? "Skip build-up countdown and launch Sprint Qualifying (SQ1) immediately"
        : "Skip build-up countdown and launch Qualifying (Q1) immediately";
    } else if (tick.phase === "SPRINT_QUALIFYING" || tick.phase === "QUALIFYING") {
      const stg = tick.quali_stage || "QUALI";
      skipBtn.textContent = `FINISH ${stg} >>`;
      skipBtn.title = `Fast-forward ${stg} knockout stage to the Chequered Flag`;
    } else if (tick.phase === "SPRINT_RACE") {
      skipBtn.textContent = "SIM SPRINT >>";
      skipBtn.title = "Fast-simulate the remaining laps of the Sprint Race to the finish";
    } else if (tick.phase === "GRID_WALK") {
      skipBtn.textContent = "LIGHTS OUT >>";
      skipBtn.title = "Skip grid walk countdown and start the 5 Red Lights sequence immediately";
    } else if (tick.phase === "RACE") {
      skipBtn.textContent = "SIM RACE >>";
      skipBtn.title = "Fast-simulate the remaining laps of the Grand Prix to the Chequered Flag";
    } else if (tick.phase === "PODIUM") {
      skipBtn.textContent = tick.round >= tick.total_rounds ? "OFF-SEASON >>" : "NEXT ROUND >>";
      skipBtn.title = "Skip podium celebration and advance to the next Grand Prix weekend";
    } else if (tick.phase === "OFF_SEASON") {
      skipBtn.textContent = "NEW SEASON >>";
      skipBtn.title = "Complete off-season regulations & driver contracts and start Round 1";
    }

    const flagEl = document.getElementById("hdr-flag");
    flagEl.className = "flag-box";
    if (tick.flag === "LIGHTS") {
      flagEl.textContent = "START SEQUENCE";
      flagEl.classList.add("flag-lights");
    } else if (tick.flag === "YELLOW") {
      flagEl.textContent = `YELLOW SEC ${tick.yellow_sector || ""}`;
      flagEl.classList.add("flag-yellow");
    } else if (tick.flag === "VSC") {
      flagEl.textContent = "VSC DEPLOYED";
      flagEl.classList.add("flag-sc");
    } else if (tick.flag === "SC") {
      flagEl.textContent = tick.sc && tick.sc.in_lap ? "SC IN THIS LAP" : "SAFETY CAR";
      flagEl.classList.add("flag-sc");
    } else if (tick.flag === "CHEQUERED") {
      flagEl.textContent = "CHEQUERED FLAG";
      flagEl.classList.add("flag-cheq");
    } else {
      flagEl.textContent = "TRACK CLEAR";
      flagEl.classList.add("flag-green");
    }

    document.getElementById("hdr-temp").textContent = `${tick.temp_c}°C`;
    document.getElementById("hdr-wet").textContent =
      tick.wetness > 50 ? `WET ${tick.wetness}%` : tick.wetness > 14 ? `DAMP ${tick.wetness}%` : `DRY ${tick.wetness}%`;
    document.getElementById("hdr-rain").textContent = `${tick.rain_risk}%`;

    document.getElementById("hdr-team-stripe").style.background = tick.player_team_color;
    document.getElementById("hdr-team-name").textContent = tick.player_team_short.toUpperCase();
    document.getElementById("hdr-budget").textContent = `$${tick.player_budget_m.toFixed(1)}M`;
    if (this._lastHeaderLogoTeam !== tick.player_team_id) {
      this._lastHeaderLogoTeam = tick.player_team_id;
      document.getElementById("hdr-team-logo").innerHTML = teamLogoSVG(tick.player_team_id, 20);
    }

    document.querySelectorAll(".spd-btn").forEach((b) => {
      b.classList.toggle("active", parseFloat(b.dataset.speed) === tick.sim_speed);
    });

    const flChip = document.getElementById("tower-fastest");
    if (tick.fastest_id && tick.fastest_time) {
      const fc = tick.cars.find((c) => c.id === tick.fastest_id);
      const pfx = tick.phase === "QUALIFYING" || tick.phase === "SPRINT_QUALIFYING" ? (tick.quali_stage || "P1") : "FL";
      flChip.textContent = `${pfx} ${fc ? fc.code : ""} ${fmtLap(tick.fastest_time)}`;
    } else {
      flChip.textContent = "FL --:--.---";
    }
  }

  renderLightsAndPhaseOverlay(tick) {
    const gantry = document.getElementById("lights-overlay");
    if ((tick.phase === "RACE" || tick.phase === "SPRINT_RACE") && tick.flag === "LIGHTS" && tick.lights > 0) {
      gantry.classList.remove("hidden");
      const litCount = Math.min(5, Math.max(1, Math.ceil(6.0 - tick.lights)));
      for (let i = 1; i <= 5; i++) {
        document.getElementById(`lp-${i}`).classList.toggle("on", i <= litCount);
      }
    } else {
      gantry.classList.add("hidden");
    }

    const ov = document.getElementById("phase-overlay");
    if (tick.phase === "PODIUM" && tick.podium) {
      const r = tick.podium.round_rec;
      const sprInfo = r.is_sprint && r.sprint_winner_code
        ? `<div style="color:#ff9f1c;font-weight:700">SPRINT P1: <strong>${r.sprint_winner_code}</strong></div>`
        : "";
      ov.classList.remove("hidden");
      ov.innerHTML = `
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px">
          <strong style="color:#ffffff;font-style:italic;font-size:13px;letter-spacing:0.6px">${r.gp.toUpperCase()} — PROVISIONAL PODIUM</strong>
          <span style="color:#8f90a6;font-size:10.5px;font-weight:700">NEXT ROUND IN ${tick.phase_timer.toFixed(0)}S</span>
        </div>
        <div style="display:flex;gap:16px;font-size:12px;align-items:center;flex-wrap:wrap">
          <div><span style="color:#e10600;font-weight:900">P1</span> <strong>${r.winner_name.toUpperCase()}</strong> (${r.winner_team})</div>
          <div><span style="color:#8f90a6;font-weight:900">P2</span> <strong>${r.p2_code}</strong></div>
          <div><span style="color:#8f90a6;font-weight:900">P3</span> <strong>${r.p3_code}</strong></div>
          <div style="color:#a855f7;font-weight:700">FASTEST LAP: <strong>${r.fastest_lap_code}</strong></div>
          ${sprInfo}
          ${(tick.podium.lap_chart?.length || tick.podium.stints) ? `<button class="btn-outline btn-sm" data-open-podium-analytics style="margin-left:auto">POSITION CHART &amp; STINTS</button>` : ""}
        </div>
      `;
    } else if (tick.phase === "OFF_SEASON") {
      ov.classList.remove("hidden");
      ov.innerHTML = `
        <strong style="color:#ffffff;font-style:italic;font-size:13.5px;letter-spacing:0.6px">${tick.season} FIA WORLD CHAMPIONSHIP CONCLUDED</strong>
        <p style="color:#b4b5c8;margin-top:4px;font-size:11.5px">Constructors' prize pool settled, technical regulations updated — ${tick.season + 1} Pre-Season concludes in ${tick.phase_timer.toFixed(0)}s.</p>
      `;
    } else if (tick.phase === "PRE_WEEKEND" || tick.phase === "GRID_WALK") {
      const fmtDesc = tick.is_sprint_weekend && tick.phase === "PRE_WEEKEND"
        ? `FIA SPRINT FORMAT (SQ1/SQ2/SQ3 + ${tick.sprint_laps}L SPRINT + Q1/Q2/Q3 + ${tick.total_laps}L GP)`
        : `${tick.total_laps} LAPS`;
      const widthInfo = tick.track_width_m ? `  |  TRACK WIDTH ${tick.track_width_m.toFixed(1)}M` : "";
      ov.classList.remove("hidden");
      ov.innerHTML = `
        <div style="display:flex;justify-content:space-between;align-items:center;gap:14px">
          <div>
            <strong style="color:#ffffff;font-style:italic;letter-spacing:0.6px">${tick.phase === "GRID_WALK" ? "STARTING GRID — CHOOSE TYRE COMPOUND ON PIT WALL" : `${tick.circuit_name.toUpperCase()}`}</strong>
            <div style="color:#8f90a6;font-size:11px;margin-top:2px;font-weight:600">${tick.gp_name.toUpperCase()}  |  ${fmtDesc}${widthInfo}  |  RAIN ${tick.rain_risk}%</div>
          </div>
          <span style="font-weight:900;font-style:italic;font-size:16px;color:#e10600">${tick.phase_timer.toFixed(0)}S</span>
        </div>
      `;
    } else {
      ov.classList.add("hidden");
    }
  }

  renderTimingTower(tick) {
    const list = document.getElementById("timing-list");
    const isQuali = tick.phase === "QUALIFYING" || tick.phase === "SPRINT_QUALIFYING";
    const gapHeading = document.getElementById("timing-gap-heading");
    if (gapHeading) {
      gapHeading.textContent = isQuali ? "LAP DELTA" : "GAP / INT";
      gapHeading.title = isQuali
        ? "Difference between best qualifying laps"
        : "Gap to the race leader / interval to the car ahead";
    }
    if (!tick.cars || tick.cars.length === 0) {
      list.innerHTML = `<div style="padding:14px;color:#8f90a6;font-size:11.5px;letter-spacing:0.4px">CARS IN GARAGE — SESSION PREPARING</div>`;
      return;
    }

    const manShort = {
      DIVEBOMB: "DIVE",
      OUTSIDE: "OUTS",
      SWITCHBACK: "SWBK",
      DUMMY: "DUMY",
      SLIPSTREAM: "TOW",
      DEFEND: "DEF",
    };

    list.innerHTML = tick.cars
      .map((c) => {
        const isSel = c.id === this.selectedDriverId;
        const isMine = c.tid === tick.player_team_id;
        const isFL = c.id === tick.fastest_id;
        const tm = TIRE_META[c.comp] || TIRE_META.MEDIUM;

        let badges = "";
        if (isQuali && c.elim) {
          badges += `<span class="badge b-elim">OUT ${c.estg}</span>`;
        } else if (isQuali && c.quali_phase && c.quali_phase !== "PUSH") {
          const qpMap = { GARAGE: "GAR", EXIT: "EXIT", OUTLAP: "OUT", INLAP: "IN" };
          badges += `<span class="badge" style="background:#212334;color:#9ea2bd">${qpMap[c.quali_phase] || c.quali_phase}</span>`;
        } else if (c.in_pit) {
          badges += `<span class="badge b-pit">PIT</span>`;
        } else if (c.man && manShort[c.man] && !isQuali) {
          const mCls = c.man === "OUTSIDE" ? "b-man-out" : "b-man";
          badges += `<span class="badge ${mCls}" title="Overtaking Maneuver: ${c.man}">${manShort[c.man]}</span>`;
        } else if (c.drs || c.aero === "DRS") {
          badges += `<span class="badge b-drs" title="Classic Rear Wing DRS Active (+22 km/h)">DRS</span>`;
        } else if (c.drs_elig) {
          badges += `<span class="badge b-drs-arm" title="DRS Flap Armed (<1.0s at Detection)">DRS ARM</span>`;
        } else if (c.ovt) {
          badges += `<span class="badge b-ovt" title="2026 Overtake Mode Active">OVT</span>`;
        } else if (c.ovt_elig) {
          badges += `<span class="badge b-elig" title="Overtake Mode Armed (<1.0s at Detection)">ARM</span>`;
        } else if (c.aero === "STRAIGHT") {
          badges += `<span class="badge b-str">STR</span>`;
        }

        if (c.dt_pen) badges += `<span class="badge b-pen">DT</span>`;
        else if (c.pen > 0) badges += `<span class="badge b-pen">+${c.pen}S</span>`;

        let gapStr = "LEADER";
        let intervalStr = "";
        let gapTitle = "Gap to the race leader";
        if (isQuali) {
          gapTitle = c.pos === 1 || c.elim
            ? "Best qualifying lap"
            : "Best lap difference to the qualifying leader";
          if (c.elim) {
            gapStr = fmtLap(c.best);
          } else {
            gapStr = c.pos === 1 ? fmtLap(c.best) : c.best ? fmtGap(c.gap) : "OUT LAP";
          }
        } else if (c.dnf) {
          gapStr = "OUT";
        } else if (c.pos > 1) {
          gapStr = fmtGap(c.gap);
          intervalStr = fmtGap(c.intv);
        }

        const batColor = c.ovt ? "#00d26a" : c.rech ? "#ffd000" : "#00d2be";
        const sectors = c.sectors || [null, null, null];
        const activeSector = sectors.findIndex((time) => time == null);
        const isRunning = !c.dnf && !c.elim && !c.in_pit && tick.flag !== "LIGHTS" &&
          (isQuali || tick.phase === "RACE" || tick.phase === "SPRINT_RACE");
        const sectorCells = sectors.map((currentTime, index) => {
          const time = currentTime ?? c.last_sectors?.[index];
          const previous = currentTime == null && time != null;
          const status = timingClass(time, c.best_sectors?.[index], tick.sector_bests?.[index]);
          const source = previous ? "Last lap" : "Current lap";
          const timingLabel = status === "time-session-best" ? "Session best" :
            status === "time-personal-best" ? "Personal best" : "";
          return `<span class="t-sector ${status} ${previous ? "t-sector-previous" : ""} ${isRunning && index === activeSector ? "t-sector-active" : ""}"
            title="${source} sector ${index + 1}: ${fmtSector(time)}${timingLabel ? ` — ${timingLabel}` : ""}">
            <small>S${index + 1}</small><strong>${fmtSector(time)}</strong>
          </span>`;
        }).join("");
        const cutDivider =
          isQuali && tick.quali_cut > 0 && c.pos === tick.quali_cut
            ? `<div class="knockout-cut-row"><span>ELIMINATION ZONE</span><span>P${tick.quali_cut + 1}-P${tick.quali_cut === 16 ? 22 : 16} OUT IN ${tick.quali_stage}</span></div>`
            : "";

        return `
          <div class="t-row ${isSel ? "selected" : ""} ${isMine ? "my-car" : ""} ${c.dnf ? "dnf" : ""} ${c.elim ? "elim" : ""}" data-id="${c.id}">
            <div class="t-pos">${c.pos}</div>
            <div class="t-drv">
              <span class="t-bar" style="background:${c.tcol}"></span>
              ${teamLogoSVG(c.tid, 14)}
              <span class="t-code">${c.code}</span>
              <span class="t-num ${c.num === 1 ? "champ-1" : ""}">${c.num}</span>
              ${isFL ? `<span class="t-fl-bar" title="Fastest Lap"></span>` : ""}
              <button class="t-vs-btn ${this.compareDriverId === c.id ? "active" : ""}" data-vs-id="${c.id}" title="Compare Head-to-Head in Telemetry">VS</button>
            </div>
            <div class="t-modes">${badges}</div>
            <div class="t-tyre">
              <span class="pirelli-badge" style="border-color:${tm.color}">${tm.code}</span>
              <span style="color:#8f90a6;font-size:9.5px;font-weight:700">${100 - c.wear}%</span>
            </div>
            <div class="t-gap">
              <span class="t-gap-val" title="${gapTitle}">${gapStr}</span>
              ${intervalStr ? `<span class="t-interval" title="Interval to the car ahead in race order">INT ${intervalStr}</span>` : ""}
              <span class="ers-mini"><i style="width:${Math.min(100, Math.max(0, c.bat))}%;background:${batColor}"></i></span>
            </div>
            <div class="t-lap-times">
              <span title="Last completed lap"><small>LAST</small><strong class="${timingClass(c.last, c.best, tick.fastest_time)}">${fmtLap(c.last)}</strong></span>
              <span title="Personal best lap in this session"><small>BEST</small><strong class="${timingClass(c.best, c.best, tick.fastest_time)}">${fmtLap(c.best)}</strong></span>
            </div>
            <div class="t-sector-times">${sectorCells}</div>
          </div>
          ${cutDivider}
        `;
      })
      .join("");
  }

  renderPitWall(tick) {
    const wrap = document.getElementById("pitwall-cards");
    document.getElementById("pw-title").textContent = `${tick.player_team_short.toUpperCase()} STRATEGY WALL`;

    const myCars = tick.cars.filter((c) => c.tid === tick.player_team_id);
    if (myCars.length === 0) {
      if (tick.phase === "PRE_WEEKEND" && this.fullState) {
        const myDrivers = (this.fullState.drivers || []).filter((d) => d.team_id === this.fullState.player_team_id);
        const setups = this.fullState.driver_setups || {};
        const locked = Boolean(tick.parc_ferme);
        const prof = tick.track_profile || this.fullState.track_profile || {};
        wrap.innerHTML = myDrivers
          .map((d) => {
            const curDf = setups[d.id] != null ? setups[d.id] : (prof.recommended_df || 0);
            return `
              <div class="pw-card" style="border-top-color:${d.team_color || "#00d2be"}">
                <div class="pw-top">
                  <div class="pw-driver">
                    ${teamLogoSVG(d.team_id, 16)}
                    <span>#${d.number} ${d.name}</span>
                    <span class="badge" style="background:#1c2030;color:#00d2be">OVR ${d.overall}</span>
                  </div>
                  <div class="pw-metrics">
                    <span>TRACK <strong>${prof.label || "BALANCED"}</strong></span>
                    <span>REC WING <strong>${prof.recommended_df != null ? (prof.recommended_df >= 0 ? `+${prof.recommended_df}` : prof.recommended_df) : "0"}</strong></span>
                    <span style="color:${locked ? "#ff3b30" : "#00d26a"}"><strong>${locked ? "PARC FERME LOCKED" : "GARAGE SETUP OPEN"}</strong></span>
                  </div>
                </div>
                <div class="pw-controls">
                  <div class="pw-group" title="Pre-Weekend Wing Downforce (-2 Low Drag Speed .. +2 High Cornering Grip)">
                    <span class="pw-lbl">WING SETUP</span>
                    ${[-2, -1, 0, 1, 2]
                      .map((lvl) => {
                        const lbl = lvl === 0 ? "0 BAL" : lvl > 0 ? `+${lvl} DF` : `${lvl} SPD`;
                        return `<button class="pw-btn ${curDf === lvl ? "active" : ""}" ${locked ? "disabled" : ""} data-pw-cmd="setup_df" data-drv="${d.id}" data-val="${lvl}">${lbl}</button>`;
                      })
                      .join("")}
                  </div>
                </div>
              </div>
            `;
          })
          .join("");
        return;
      }
      wrap.innerHTML = `<div style="color:#8f90a6;font-size:11.5px;padding:6px 0">TELEMETRY STANDBY — AWAITING TRACK SESSION (${tick.phase})</div>`;
      return;
    }

    wrap.innerHTML = myCars
      .map((c) => {
        const tm = TIRE_META[c.comp] || TIRE_META.MEDIUM;
        const isPreRace = tick.phase === "GRID_WALK"
          || tick.phase === "PRE_WEEKEND"
          || tick.flag === "GRID"
          || tick.flag === "LIGHTS"
          || ((tick.phase === "RACE" || tick.phase === "SPRINT_RACE") && (tick.lights > 0 || (c.lap <= 1 && c.kph < 25)));
        const isRace = (tick.phase === "RACE" || tick.phase === "SPRINT_RACE") && !c.dnf;
        const dis = (isRace || isPreRace) ? "" : "disabled";
        const isV8 = tick.regulations && tick.regulations.era_id === "V8_DRS";
        const ersLabel = isV8 ? "KERS" : "ERS";
        const aeroLabel = (c.aero === "DRS" || c.drs) ? "DRS" : (c.aero === "STRAIGHT" ? "STR" : "CRN");
        const aeroColor = (c.aero === "DRS" || c.drs) ? "#00d26a" : (c.aero === "STRAIGHT" ? "#00d2be" : "#ffffff");
        const tCol = getTempColor(c.comp, c.ttemp);
        const tStat = getTempStatus(c.comp, c.ttemp);
        const fuelMargin = c.fuel_margin != null ? c.fuel_margin : 0.0;
        const fuelCol = fuelMargin < -0.15 ? "#ff3b30" : fuelMargin < 0.25 ? "#ffd000" : "#00d26a";
        const trafS = c.rejoin_traffic_s != null ? c.rejoin_traffic_s : null;
        const rejoinCol = trafS != null && trafS < 1.2 ? "#ff3b30" : trafS != null && trafS < 2.2 ? "#ffd000" : "#00d2be";
        const rejoinBadge = (isRace && c.rejoin_pos != null && !c.in_pit)
          ? `<span class="pw-rejoin-pill" style="color:${rejoinCol}">REJOIN P${c.rejoin_pos} (${trafS != null && trafS < 2.2 ? `+${trafS.toFixed(1)}s` : "CLEAR"})</span>`
          : "";
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
                ${c.scrubbed ? `<span class="badge" style="background:#2b2714;color:#ffd000">SCRUB</span>` : ""}
              </div>
              <div class="pw-metrics">
                <span><strong>${c.kph}</strong> KPH</span>
                <span>LAT <strong>${c.g_lat != null ? Math.abs(c.g_lat).toFixed(1) : "0.0"}G</strong></span>
                <span>AERO <strong style="color:${aeroColor}">${aeroLabel}</strong></span>
                <span>${ersLabel} <strong>${Math.min(100, Math.max(0, c.bat))}%</strong></span>
                <span>FUEL <strong style="color:${fuelCol}">${c.fuel_pct != null ? c.fuel_pct : 100}% (${fuelMargin >= 0 ? "+" : ""}${fuelMargin.toFixed(1)}L)</strong></span>
                <span><span class="pirelli-badge" style="border-color:${tm.color};width:14px;height:14px;font-size:8.5px">${tm.code}</span> ${100 - c.wear}% (${c.tage}L) · <strong style="color:${tCol}" title="Tyre Temperature: ${c.ttemp}°C (${tStat})">${c.ttemp}°C</strong></span>
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
                <button class="pw-btn ${c.lift_coast ? "lc-on" : ""}" ${isRace ? "" : "disabled"} data-pw-cmd="lift_coast" data-drv="${c.id}" data-val="${!c.lift_coast}" title="Lift-and-Coast saves fuel (~20%) and cools tyres/PU">
                  ${c.lift_coast ? "L&C: ON" : "L&C"}
                </button>
              </div>

              ${isPreRace ? `
              <div class="pw-group" title="Select Starting Tyre Compound Before Lights Out (Allocations Remaining)">
                <span class="pw-lbl" style="color:#00d2be;font-weight:900">START TYRE</span>
                ${["SOFT", "MEDIUM", "HARD", "INTER", "WET"]
                  .map((k) => {
                    const setsLeft = (c.tsets && c.tsets[k] != null) ? c.tsets[k] : 0;
                    const det = c.tsets_detail?.[k];
                    const fTag = det ? ` (${det.fresh}F+${det.scrubbed}S)` : "";
                    const isActive = c.comp === k;
                    const canSelect = isActive || setsLeft > 0;
                    const btnDis = canSelect ? "" : "disabled";
                    const btnStyle = isActive
                      ? ""
                      : `color:${TIRE_META[k].color};${setsLeft <= 0 ? "opacity:0.35;cursor:not-allowed;" : ""}`;
                    return `<button class="pw-btn ${isActive ? "active" : ""}" ${btnDis} data-pw-cmd="start_comp" data-drv="${c.id}" data-val="${k}" style="${btnStyle}" title="${k}: ${setsLeft} set${setsLeft === 1 ? '' : 's'} remaining${fTag}">${TIRE_META[k].code} (${setsLeft})</button>`;
                  })
                  .join("")}
                <button class="pw-btn ${c.prefer_fresh === false ? "scrub-on" : ""}" data-pw-cmd="prefer_fresh" data-drv="${c.id}" data-val="${c.prefer_fresh === false}" title="Prefer Fresh or Scrubbed Qualifying sets when available">
                  ${c.prefer_fresh === false ? "USE SCRUB" : "USE FRESH"}
                </button>
              </div>
              ` : `
              <div class="pw-group" title="Next Pit-Stop Tyre Compound (Allocations Remaining)">
                <span class="pw-lbl">TYRE</span>
                ${["SOFT", "MEDIUM", "HARD", "INTER", "WET"]
                  .map((k) => {
                    const setsLeft = (c.tsets && c.tsets[k] != null) ? c.tsets[k] : 0;
                    const det = c.tsets_detail?.[k];
                    const fTag = det ? ` (${det.fresh}F+${det.scrubbed}S)` : "";
                    const isActive = c.ncomp === k;
                    const canSelect = isRace && (isActive || setsLeft > 0);
                    const btnDis = canSelect ? "" : "disabled";
                    const btnStyle = isActive
                      ? ""
                      : `color:${TIRE_META[k].color};${setsLeft <= 0 ? "opacity:0.35;cursor:not-allowed;" : ""}`;
                    return `<button class="pw-btn ${isActive ? "active" : ""}" ${btnDis} data-pw-cmd="ncomp" data-drv="${c.id}" data-val="${k}" style="${btnStyle}" title="${k}: ${setsLeft} set${setsLeft === 1 ? '' : 's'} remaining${fTag}">${TIRE_META[k].code} (${setsLeft})</button>`;
                  })
                  .join("")}
                <button class="pw-btn ${c.prefer_fresh === false ? "scrub-on" : ""}" ${isRace ? "" : "disabled"} data-pw-cmd="prefer_fresh" data-drv="${c.id}" data-val="${c.prefer_fresh === false}" title="Prefer Fresh or Scrubbed Qualifying sets on next stop">
                  ${c.prefer_fresh === false ? "SCRUB" : "FRESH"}
                </button>
              </div>
              `}

              <div class="pw-group" title="Target Pace Mode">
                <span class="pw-lbl">PACE</span>
                ${[
                  ["CONSERVE", "CON"],
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
              </div>

              <div class="pw-group" title="Team Orders">
                ${[
                  ["FREE", "RACE"],
                  ["HOLD", "HOLD"],
                  ["YIELD", "SWAP"],
                ]
                  .map(
                    ([k, lbl]) =>
                      `<button class="pw-btn ${c.order === k ? "active" : ""}" ${dis} data-pw-cmd="order" data-drv="${c.id}" data-val="${k}">${lbl}</button>`
                  )
                  .join("")}
              </div>
            </div>
            ${(rejoinBadge || c.advice || c.strategy) ? `
            <div class="pw-advice">
              <span>${fmtAdvice(c.advice) || c.strategy || ""}</span>
              ${rejoinBadge}
            </div>` : ""}
          </div>
        `;
      })
      .join("");
  }

  renderTelemetry(tick) {
    const body = document.getElementById("telemetry-body");
    const tag = document.getElementById("tel-car-tag");
    const car = tick.cars.find((c) => c.id === this.selectedDriverId) || tick.cars[0];
    if (!car) {
      tag.textContent = "STANDBY";
      body.innerHTML = `<div style="color:#8f90a6;font-size:11.5px">Awaiting live car telemetry...</div>`;
      return;
    }

    tag.innerHTML = `<span class="inline-team">${teamLogoSVG(car.tid, 14)} #${car.num} ${car.code} | P${car.pos}</span>`;
    const spdPct = Math.min(100, (car.kph / 360) * 100);
    const spdColor = car.ovt ? "#00d26a" : car.kph > 290 ? "#00d2be" : "#e10600";
    const tCol = getTempColor(car.comp, car.ttemp);
    const tStat = getTempStatus(car.comp, car.ttemp);
    const manDisplay = {
      DIVEBOMB: "DIVEBOMB INSIDE",
      OUTSIDE: "OUTSIDE SEND",
      SWITCHBACK: "SWITCHBACK CUT",
      DUMMY: "DUMMY FEINT",
      SLIPSTREAM: "SLIPSTREAM TOW",
      DEFEND: "DEFENDING APEX",
    }[car.man] || (car.battle ? "WHEEL-TO-WHEEL" : "RACING LINE");
    const pitStr = car.lpit > 0 ? `${car.pits} (${car.lpit.toFixed(2)}s)` : `${car.pits} ${car.in_pit ? "(PIT)" : ""}`;
    const setupName = SETUP_LABELS[String(car.setup_df ?? 0)] || "BALANCED DF";
    const fMargin = car.fuel_margin != null ? car.fuel_margin : 0;
    const fStr = `${car.fuel_kg != null ? car.fuel_kg.toFixed(1) : "--"} KG (${fMargin >= 0 ? "+" : ""}${fMargin.toFixed(1)}L)`;
    const cmp = (this.compareDriverId && this.compareDriverId !== car.id)
      ? tick.cars.find((c) => c.id === this.compareDriverId)
      : null;

    let h2hHtml = "";
    if (cmp) {
      const spdDiff = car.kph - cmp.kph;
      const batDiff = car.bat - cmp.bat;
      const lifeA = 100 - car.wear;
      const lifeB = 100 - cmp.wear;
      const bestDiff = (car.best > 0 && cmp.best > 0) ? (car.best - cmp.best) : null;
      const lastDiff = (car.last > 0 && cmp.last > 0) ? (car.last - cmp.last) : null;
      const fmtDelta = (v, unit = "s", invertGood = false) => {
        if (v == null || !Number.isFinite(v)) return "—";
        const good = invertGood ? v < 0 : v > 0;
        const col = Math.abs(v) < 0.001 ? "#d4d4e0" : good ? "#00d26a" : "#ff4d4f";
        return `<span style="color:${col}">${v > 0 ? "+" : ""}${unit === "s" ? v.toFixed(3) : Math.round(v)}${unit}</span>`;
      };
      h2hHtml = `
        <div class="h2h-card">
          <div class="h2h-hdr">
            <span>H2H: ${car.code} (P${car.pos}) vs ${cmp.code} (P${cmp.pos})</span>
            <button class="h2h-clear" id="btn-clear-h2h">CLEAR</button>
          </div>
          <div class="h2h-row"><strong>${car.kph} KPH</strong><span>SPEED ${fmtDelta(spdDiff, " km/h")}</span><strong>${cmp.kph} KPH</strong></div>
          <div class="h2h-row"><strong>${car.bat}%</strong><span>MGU-K ${fmtDelta(batDiff, "%")}</span><strong>${cmp.bat}%</strong></div>
          <div class="h2h-row"><strong>${car.comp[0]} ${lifeA}%</strong><span>TYRE LIFE ${fmtDelta(lifeA - lifeB, "%")}</span><strong>${cmp.comp[0]} ${lifeB}%</strong></div>
          <div class="h2h-row"><strong>${fmtLap(car.last)}</strong><span>LAST ${fmtDelta(lastDiff, "s", true)}</span><strong>${fmtLap(cmp.last)}</strong></div>
          <div class="h2h-row"><strong>${fmtLap(car.best)}</strong><span>BEST ${fmtDelta(bestDiff, "s", true)}</span><strong>${fmtLap(cmp.best)}</strong></div>
        </div>
      `;
    }

    body.innerHTML = `
      <div class="tel-speed-row">
        <div class="tel-kph">${car.kph} <small>KM/H</small></div>
        <div>
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
        <strong style="color:#ffffff">${Math.min(100, Math.max(0, car.bat))}%</strong>
      </div>
      <div class="bar-meter"><span style="width:${Math.min(100, Math.max(0, car.bat))}%;background:${car.rech ? "#ffd000" : "#00d2be"}"></span></div>

      <div class="tel-grid">
        <div class="tel-kv"><span>Compound</span><strong>${car.comp}${car.scrubbed ? " (SCRUB)" : ""} (${100 - car.wear}%)</strong></div>
        <div class="tel-kv"><span>Tyre Temp</span><strong style="color:${tCol}">${car.ttemp}°C (${tStat})</strong></div>
        <div class="tel-kv"><span>Fuel Load</span><strong style="color:${fMargin < 0 ? "#ff4d4f" : "#00d26a"}">${fStr}${car.lift_coast ? " [L&amp;C]" : ""}</strong></div>
        <div class="tel-kv"><span>Wing Setup</span><strong>${setupName} (${car.setup_df >= 0 ? "+" : ""}${car.setup_df ?? 0})</strong></div>
        <div class="tel-kv"><span>Tyre Sets Left</span><strong style="color:#00d2be;font-size:10.5px">${car.tsets ? `S:${car.tsets.SOFT ?? 0} M:${car.tsets.MEDIUM ?? 0} H:${car.tsets.HARD ?? 0} I:${car.tsets.INTER ?? 0} W:${car.tsets.WET ?? 0}` : "—"}</strong></div>
        <div class="tel-kv"><span>Maneuver</span><strong style="color:${car.man ? "#ffb366" : "#d4d4e0"}">${manDisplay}</strong></div>
        <div class="tel-kv"><span>Last Lap</span><strong>${fmtLap(car.last)}</strong></div>
        <div class="tel-kv"><span>Personal Best</span><strong style="color:#a855f7">${fmtLap(car.best)}</strong></div>
        <div class="tel-kv"><span>Pit Stops</span><strong>${pitStr}</strong></div>
        <div class="tel-kv"><span>Track Limits</span><strong>${car.tl}/4 ${car.pen > 0 ? `(+${car.pen}S)` : ""}</strong></div>
      </div>
      ${car.advice ? `<div class="tel-strategy"><span>CHIEF STRATEGIST</span>${fmtAdvice(car.advice)}</div>` : car.strategy ? `<div class="tel-strategy"><span>PIT WALL PLAN</span>${car.strategy}</div>` : ""}
      ${h2hHtml}
    `;
    const clrBtn = document.getElementById("btn-clear-h2h");
    if (clrBtn) {
      clrBtn.addEventListener("click", () => this.toggleCompareDriver(this.compareDriverId));
    }
  }

  isOfficialEvent(ev) {
    const officialKinds = ["RACE_CONTROL", "STEWARDS", "PENALTY", "WEATHER", "OFFICIAL", "YELLOW", "SC", "VSC", "GRID", "STAGE", "CHEQUERED", "POLE"];
    if (officialKinds.includes(ev.kind)) return true;
    const msg = (ev.msg || "").toUpperCase();
    return msg.includes("RACE CONTROL") || msg.includes("STEWARDS") || msg.includes("PENALTY") ||
           msg.includes("SAFETY CAR") || msg.includes("VSC") || msg.includes("FLAG") || msg.includes("TRACK LIMITS") || msg.includes("WEATHER");
  }

  isRadioEvent(ev) {
    if (["RADIO", "PIT_RADIO", "STRATEGY", "TEAM_ORDER"].includes(ev.kind)) return true;
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
  }

  renderDriverDatabase() {
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
        .replace(/[̀-ͯ]/g, "");
      list = list.filter((d) => {
        const normName = (d.name || "")
          .normalize("NFD")
          .replace(/[̀-ͯ]/g, "")
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
          <td colspan="13" style="text-align:center;padding:26px 12px;color:#8f90a6;font-style:italic">
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
            <strong>#${d.number} ${d.name}</strong>${d.number === 1 ? ' <span class="champ-badge">WDC #1</span>' : ""}
            ${d.legend ? '<span class="legend-badge">LEGEND</span>' : ""}
          </td>
          <td>
            <span class="inline-team" style="color:${d.team_color};font-weight:700">
              ${d.team_id ? teamLogoSVG(d.team_id, 14) : ""}
              ${d.team_short.toUpperCase()}
            </span>
          </td>
          <td>${d.age}</td>
          <td>
            <strong style="color:${d.overall >= 95 ? "#e10600" : "#ffffff"}">${d.overall}</strong>${d.last_ovr_change ? ` <span style="font-size:10px;font-weight:700;color:${d.last_ovr_change > 0 ? '#00e676' : '#ff5252'}">${d.last_ovr_change > 0 ? '+' : ''}${d.last_ovr_change}</span>` : ""}
          </td>
          <td>${d.pace}</td>
          <td>${d.racecraft}</td>
          <td>${d.defense}</td>
          <td>${d.consistency}</td>
          <td>${d.tire_mgmt}</td>
          <td>${d.wet_skill}</td>
          <td>${d.risk ?? 70}</td>
          <td>$${d.salary_m.toFixed(2)}M/yr</td>
          <td>$${d.value_m.toFixed(1)}M</td>
        </tr>
      `
      )
      .join("");
  }

  renderManagementViews() {
    if (!this.fullState) return;
    const st = this.fullState;
    const pt = st.player_team;
    const upgradeAllowance = st.upgrade_allowance || { limit: 3, used: 0, remaining: 3 };

    // 1. Technical R&D Tab
    const prof = st.track_profile || { category: "BALANCED", label: "Balanced Circuit Profile", recommended_df: 0, weights: {} };
    const deptShort = { power_unit: "PU", active_aero: "AERO", chassis: "CHASSIS", suspension: "SUSP", reliability: "REL", pit_crew: "PIT" };
    document.getElementById("rd-header").innerHTML = `
      <div style="display:flex;align-items:center;gap:12px">
        ${teamLogoSVG(pt.id, 36)}
        <div>
          <div style="font-size:10px;color:#8f90a6;font-weight:700;letter-spacing:0.9px">ENGINEERING HEADQUARTERS | ${st.season} FIA TECHNICAL REGULATIONS</div>
          <div style="font-size:18px;font-weight:900;font-style:italic;text-transform:uppercase">${pt.name}
            <span style="color:#e10600;margin-left:8px">INDEX ${pt.car_rating.toFixed(1)}</span>
            ${pt.circuit_rating != null ? `<span style="color:#00d2be;margin-left:8px;font-size:14px">CIRCUIT ${pt.circuit_rating.toFixed(1)}</span>` : ""}
          </div>
        </div>
      </div>
      <div style="text-align:right">
        <div style="font-size:10px;color:#8f90a6;font-weight:700;letter-spacing:0.8px">AVAILABLE TEAM CASH</div>
        <div style="font-size:21px;font-weight:900;color:#00d26a">$${pt.budget_m.toFixed(2)}M</div>
        <div style="font-size:11px;color:#c8c9d8;margin-top:4px">${upgradeAllowance.used}/${upgradeAllowance.limit} UPGRADES THIS GRAND PRIX</div>
      </div>
    `;

    const myDriversList = st.drivers.filter((d) => d.team_id === st.player_team_id);
    const setupPanel = document.getElementById("setup-circuit-panel");
    if (setupPanel) {
      const weightsHtml = Object.entries(prof.weights || {})
        .map(([k, w]) => {
          const cls = w >= 1.12 ? "high" : w <= 0.88 ? "low" : "";
          return `<span class="dna-pill ${cls}">${deptShort[k] || k.toUpperCase()} ${Number(w).toFixed(2)}x</span>`;
        })
        .join("");
      const setupsMap = st.driver_setups || {};
      const locked = Boolean(st.parc_ferme);
      setupPanel.innerHTML = `
        <div class="circuit-dna-card">
          <div>
            <div style="font-size:10px;color:#8f90a6;font-weight:800;letter-spacing:0.6px">${(st.track?.circuit || "CIRCUIT").toUpperCase()} — CIRCUIT DNA</div>
            <div style="font-size:14px;font-weight:900;color:#ffffff;margin-top:2px">${prof.label.toUpperCase()} · REC WING ${prof.recommended_df >= 0 ? `+${prof.recommended_df}` : prof.recommended_df}</div>
            <div class="dna-weights">${weightsHtml}</div>
          </div>
          <div>
            <div style="display:flex;justify-content:space-between;align-items:center">
              <span style="font-size:10px;color:#8f90a6;font-weight:800">PRE-WEEKEND DOWNFORCE SETUP</span>
              <span style="font-size:10px;font-weight:900;color:${locked ? "#ff4d4f" : "#00d26a"}">${locked ? "PARC FERME LOCKED" : "GARAGE OPEN"}</span>
            </div>
            ${myDriversList
              .map((d) => {
                const cur = setupsMap[d.id] != null ? setupsMap[d.id] : prof.recommended_df || 0;
                return `
                  <div class="setup-driver-row">
                    <strong style="font-size:11.5px;color:#ffffff">#${d.number} ${d.code}</strong>
                    <div class="setup-btns">
                      ${[-2, -1, 0, 1, 2]
                        .map((lvl) => `<button class="setup-btn ${cur === lvl ? "active" : ""}" data-setup-drv="${d.id}" data-setup-val="${lvl}" ${locked ? "disabled" : ""}>${lvl >= 0 ? `+${lvl}` : lvl}</button>`)
                        .join("")}
                    </div>
                  </div>
                `;
              })
              .join("")}
          </div>
        </div>
      `;
      setupPanel.querySelectorAll("button[data-setup-drv]").forEach((btn) => {
        btn.addEventListener("click", async () => {
          const res = await this.apiPost("/api/set_setup", {
            driver_id: btn.dataset.setupDrv,
            setup_df: Number(btn.dataset.setupVal),
          });
          if (res.ok) {
            this.showToast(`WING SETUP: #${btn.dataset.setupDrv.toUpperCase()} -> ${res.setup_label}`);
            this.fetchFullState();
          }
        });
      });
    }

    document.getElementById("upgrade-cards").innerHTML = st.upgrades
      .map((u) => {
        const maxed = u.level >= u.max_level;
        const canAfford = pt.budget_m >= u.cost_m && !maxed && upgradeAllowance.remaining > 0;
        const pips = Array.from({ length: u.max_level }, (_, i) => `<span class="pip ${i < u.level ? "filled" : ""}"></span>`).join("");
        const w = u.track_weight != null ? Number(u.track_weight) : 1.0;
        const wColor = w >= 1.12 ? "#00d26a" : w <= 0.88 ? "#8f90a6" : "#d4d4e0";
        return `
          <div class="upg-card">
            <div>
              <div class="upg-head">
                <div><span class="upg-code">${u.code}</span><span class="upg-title">${u.name}</span></div>
                <strong style="color:#ffffff;font-size:12px">SPEC ${u.level}/${u.max_level} <small style="color:${wColor};margin-left:4px">${w.toFixed(2)}x</small></strong>
              </div>
              <p class="upg-desc" style="margin-top:6px">${u.desc}</p>
            </div>
            <div class="lvl-pips">${pips}</div>
            <button class="btn-primary btn-sm" data-upg="${u.key}" ${canAfford ? "" : "disabled"}>
              ${maxed ? "MAXIMUM FIA HOMOLOGATION" : upgradeAllowance.remaining === 0 ? "WEEKEND LIMIT REACHED" : `COMMISSION SPEC ${u.level + 1} ($${u.cost_m.toFixed(2)}M)`}
            </button>
          </div>
        `;
      })
      .join("");

    document.querySelectorAll("button[data-upg]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const res = await this.apiPost("/api/upgrade", { dept: btn.dataset.upg });
        if (res.ok) {
          this.showToast(`R&D HOMOLOGATED: ${btn.dataset.upg.toUpperCase()} upgraded to Spec ${res.level}`);
        }
        this.fetchFullState();
      });
    });

    document.getElementById("power-rank-list").innerHTML = st.teams
      .map(
        (t, idx) => `
        <div class="pr-row">
          <strong style="color:#8f90a6;font-style:italic">P${idx + 1}</strong>
          ${teamLogoSVG(t.id, 18)}
          <span style="font-weight:900;text-transform:uppercase;color:${t.id === st.player_team_id ? "#ffffff" : "#d4d4e0"}">${t.short}</span>
          <div class="bar-meter"><span style="width:${((t.car_rating - 65) / 30) * 100}%;background:${t.color}"></span></div>
          <strong style="text-align:right">${t.car_rating.toFixed(1)}${t.circuit_rating != null ? ` <small style="color:#00d2be">(${t.circuit_rating.toFixed(1)})</small>` : ""}</strong>
        </div>
      `
      )
      .join("");

    const puPanel = document.getElementById("pu-pool-panel");
    if (puPanel && st.pu_pools && st.pu_specs) {
      const puKeys = Object.keys(st.pu_specs);
      puPanel.innerHTML = myDriversList
        .map((d) => {
          const pool = st.pu_pools[d.id] || {};
          const pend = pool.pending_penalty || 0;
          const rowsHtml = puKeys
            .map((ck) => {
              const spec = st.pu_specs[ck];
              const el = pool[ck] || { used: 1, wear: 0 };
              const wearPct = Math.round((el.wear || 0) * 100);
              const barCol = wearPct >= 75 ? "#ff3b30" : wearPct >= 50 ? "#ffd000" : "#00d26a";
              const overNext = el.used >= spec.limit;
              const nextPen = el.used === spec.limit ? spec.first_penalty : spec.extra_penalty;
              const btnLabel = overNext ? `+${nextPen}P SWAP` : "FRESH SWAP";
              return `
                <div class="pu-comp-row">
                  <strong style="color:#d4d4e0">${spec.short}</strong>
                  <div class="pu-bar"><span style="width:${wearPct}%;background:${barCol}"></span></div>
                  <span style="color:${barCol};font-weight:800">${wearPct}%</span>
                  <span style="color:#8f90a6">${el.used}/${spec.limit}</span>
                  <button class="btn-outline btn-sm" data-pu-drv="${d.id}" data-pu-comp="${ck}" style="padding:2px 6px;font-size:9px">${btnLabel}</button>
                </div>
              `;
            })
            .join("");
          return `
            <div class="pu-driver-card">
              <div class="pu-driver-hdr">
                <span>#${d.number} ${d.name.toUpperCase()}</span>
                ${pend > 0 ? `<span class="badge b-pen">+${pend}P QUEUED NEXT GP</span>` : `<span style="color:#00d26a;font-size:10px">NO PENALTY QUEUED</span>`}
              </div>
              ${rowsHtml}
            </div>
          `;
        })
        .join("");

      puPanel.querySelectorAll("button[data-pu-comp]").forEach((btn) => {
        btn.addEventListener("click", async () => {
          const res = await this.apiPost("/api/replace_pu_component", {
            driver_id: btn.dataset.puDrv,
            component: btn.dataset.puComp,
          });
          if (res.ok) {
            const penNote = res.penalty_added > 0 ? ` (+${res.penalty_added}P FIA Grid Drop)` : " (Within Seasonal Quota)";
            this.showToast(`PU ALLOCATION: Fresh ${btn.dataset.puComp.toUpperCase()} fitted${penNote}`);
            this.fetchFullState();
          }
        });
      });
    }

    // 2. Driver Contracts & Trades Tab
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
    const freeAgents = st.drivers.filter((d) => !d.team_id);

    const mySel = document.getElementById("trade-my-driver");
    const prevMy = mySel.value;
    mySel.innerHTML = myDrivers
      .map((d) => `<option value="${d.id}">#${d.number} ${d.name} (INDEX ${d.overall} | VAL $${d.value_m}M)</option>`)
      .join("");
    if (myDrivers.some((d) => d.id === prevMy)) mySel.value = prevMy;

    const tgtSel = document.getElementById("trade-target-driver");
    const prevTgt = tgtSel.value;
    tgtSel.innerHTML = rivalDrivers
      .map((d) => `<option value="${d.id}">#${d.number} ${d.name} — ${d.team_short.toUpperCase()} (INDEX ${d.overall} | VAL $${d.value_m}M)</option>`)
      .join("");
    if (rivalDrivers.some((d) => d.id === prevTgt)) tgtSel.value = prevTgt;

    const relSel = document.getElementById("fa-release-driver");
    relSel.innerHTML = myDrivers
      .map((d) => `<option value="${d.id}">#${d.number} ${d.name} (BUYOUT FEE: $${d.buyout_m.toFixed(2)}M)</option>`)
      .join("");

    document.getElementById("free-agent-list").innerHTML = freeAgents
      .map(
        (d) => `
        <div class="fa-item">
          <div>
            <strong>#${d.number} ${d.name.toUpperCase()}</strong>${d.legend ? '<span class="legend-badge">LEGEND</span>' : ''} <span style="color:#e10600;font-weight:900;margin-left:6px">INDEX ${d.overall}</span>
            <div style="font-size:11px;color:#8f90a6">AGE ${d.age} | PACE ${d.pace} | CRAFT ${d.racecraft} | RETAINER $${d.salary_m}M/YR</div>
          </div>
          <button class="btn-outline btn-sm" data-sign-fa="${d.id}" ${windowOpen ? "" : "disabled"} title="${windowOpen ? "Sign driver" : "Transfer window is locked until next season"}">
            ${windowOpen ? `SIGN ($${d.signing_m.toFixed(1)}M + BUYOUT)` : "WINDOW LOCKED"}
          </button>
        </div>
      `
      )
      .join("");

    document.querySelectorAll("button[data-sign-fa]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const relId = document.getElementById("fa-release-driver").value;
        const res = await this.apiPost("/api/sign_free_agent", {
          release_driver_id: relId,
          free_agent_id: btn.dataset.signFa,
        });
        if (res.ok) {
          this.showToast(`CONTRACT EXECUTED: Reserve driver signed (-$${res.cost_m.toFixed(2)}M)`);
          this.fetchFullState();
        }
      });
    });

    this.renderDriverDatabase();

    this.previewTradeValuation();
    this.renderContractNegotiator();

    // 3. Commercial & Finances Tab
    const finances = st.finances;
    const financeSummary = document.getElementById("finance-summary");
    if (finances && financeSummary) {
      financeSummary.innerHTML = `
        <h3 class="sec-title">SEASON FUNDING &amp; PAYROLL</h3>
        <div class="finance-metrics">
          <div><span>ANNUAL FUNDING</span><strong>$${finances.annual_budget_m.toFixed(1)}M</strong></div>
          <div><span>DRIVER PAYROLL / YEAR</span><strong>$${finances.annual_payroll_m.toFixed(2)}M</strong></div>
          <div><span>FACTORY &amp; LOGISTICS / YEAR</span><strong>$${finances.annual_operations_m.toFixed(1)}M</strong></div>
          <div><span>FIXED COSTS / GRAND PRIX</span><strong>$${(finances.payroll_per_race_m + finances.operations_per_race_m).toFixed(2)}M</strong></div>
        </div>
        <p class="muted-note">Payroll and running costs settle across ${finances.race_count} Grands Prix.
          <a href="${finances.salary_source}" target="_blank" rel="noopener noreferrer">Opening 2026 salaries</a> are reported base-pay estimates, excluding bonuses; career contracts evolve.
          Team funding uses game-balanced allocations around a
          <a href="${finances.budget_source}" target="_blank" rel="noopener noreferrer">$400M real-world spending benchmark</a>.
          Available cash carries over each season.</p>
      `;
    }
    document.getElementById("sponsor-list").innerHTML = st.sponsors
      .map((sp) => {
        const active = pt.sponsor_id === sp.id;
        return `
          <div class="sp-item ${active ? "active" : ""}">
            <div>
              <strong>${sp.name.toUpperCase()}</strong> <span style="font-size:10px;color:#8f90a6;margin-left:6px">${sp.tier.toUpperCase()}</span>
              <div style="font-size:11.5px;color:#c8c9d8;margin-top:3px">${sp.desc}</div>
            </div>
            <button class="${active ? "btn-outline" : "btn-primary"} btn-sm" data-sp="${sp.id}" ${active ? "disabled" : ""}>
              ${active ? "CONTRACTED" : "SELECT PARTNER"}
            </button>
          </div>
        `;
      })
      .join("");

    document.querySelectorAll("button[data-sp]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const res = await this.apiPost("/api/select_sponsor", { sponsor_id: btn.dataset.sp });
        if (res.ok) {
          this.showToast("COMMERCIAL AGREEMENT REGISTERED");
          this.fetchFullState();
        }
      });
    });

    document.querySelector("#ledger-table tbody").innerHTML = st.ledger
      .map(
        (row) => `
        <tr>
          <td>${row.season} R${String(row.round).padStart(2, "0")}</td>
          <td><strong>${row.category}</strong></td>
          <td>${row.desc}</td>
          <td style="text-align:right;font-weight:900;color:${row.amount_m >= 0 ? "#00d26a" : "#ff554d"}">
            ${row.amount_m >= 0 ? "+" : ""}${fmtMoney(row.amount_m)}
          </td>
          <td style="text-align:right">$${row.balance_m.toFixed(2)}M</td>
        </tr>
      `
      )
      .join("");

    // 4. Championship Classification Tab
    document.getElementById("wdc-title").textContent = `${st.season} FIA WORLD DRIVERS' CHAMPIONSHIP`;
    document.getElementById("wcc-title").textContent = `${st.season} FIA WORLD CONSTRUCTORS' CHAMPIONSHIP`;

    document.querySelector("#wdc-table tbody").innerHTML = st.wdc
      .map(
        (r) => `
        <tr class="${r.team_id === st.player_team_id ? "highlight-me" : ""}">
          <td><strong style="font-style:italic">${r.rank}</strong></td>
          <td><strong>#${r.number} ${r.name}</strong></td>
          <td>
            <span class="inline-team" style="color:${r.team_color};font-weight:700">
              ${r.team_id ? teamLogoSVG(r.team_id, 14) : ""}
              ${r.team_short.toUpperCase()}
            </span>
          </td>
          <td>${r.wins}</td>
          <td>${r.podiums}</td>
          <td>${r.poles}</td>
          <td style="color:${r.penalty_points >= 8 ? "#ffd000" : "#8f90a6"}">${r.penalty_points}/12</td>
          <td style="text-align:right;font-weight:900">${r.points}</td>
        </tr>
      `
      )
      .join("");

    document.querySelector("#wcc-table tbody").innerHTML = st.wcc
      .map(
        (r) => `
        <tr class="${r.id === st.player_team_id ? "highlight-me" : ""}">
          <td><strong style="font-style:italic">${r.rank}</strong></td>
          <td>
            <span class="inline-team" style="font-weight:900">
              ${teamLogoSVG(r.id, 16)}
              <span style="color:${r.color}">${r.name.toUpperCase()}</span>
            </span>
          </td>
          <td>${r.engine}</td>
          <td>${r.car_rating.toFixed(1)}</td>
          <td>${r.wins}</td>
          <td>$${r.budget_m.toFixed(1)}M</td>
          <td style="text-align:right;font-weight:900">${r.points}</td>
        </tr>
      `
      )
      .join("");

    const hofEl = document.getElementById("hof-list");
    if (st.hall_of_fame.length === 0) {
      hofEl.innerHTML = `<div class="muted-note">Complete Round 24 (Abu Dhabi Grand Prix) to record the first FIA World Champion in the archive.</div>`;
    } else {
      hofEl.innerHTML = st.hall_of_fame
        .map(
          (h) => `
          <div class="hof-item">
            <div><strong>${h.season} WDC:</strong> ${h.wdc_name.toUpperCase()} (${h.wdc_team}) — ${h.wdc_points} PTS (${h.wdc_wins} WINS)</div>
            <div><strong>WCC:</strong> <span style="color:${h.wcc_color};font-weight:700">${h.wcc_name.toUpperCase()}</span> (${h.wcc_points} PTS)</div>
          </div>
        `
        )
        .join("");
    }

    document.getElementById("calendar-title").textContent = `${st.season} FORMULA 1 CALENDAR`;
    document.getElementById("calendar-note").textContent = st.calendar_info?.note || "";
    document.getElementById("calendar-grid").innerHTML = st.calendar
      .map((c) => {
        const res = c.result;
        const sprBadge = c.is_sprint ? `<span class="sprint-pill">SPRINT</span>` : "";
        const sprRes = res && res.sprint_winner_code ? ` | SPR ${res.sprint_winner_code}` : "";
        return `
          <div class="cal-card ${c.round === st.round ? "current" : ""}">
            <div style="display:flex;justify-content:space-between;align-items:center">
              <span style="font-size:9.5px;color:#8f90a6;font-weight:700;letter-spacing:0.7px">ROUND ${String(c.round).padStart(2, "0")} | ${c.country}</span>
              ${sprBadge}
            </div>
            <div style="font-weight:900;text-transform:uppercase;margin:3px 0 5px">${c.name}</div>
            ${
              res
                ? `<div style="font-size:11px;color:#00d26a;font-weight:700">P1 ${res.winner_code} (${res.winner_team.toUpperCase()}) | POLE ${res.pole_code}${sprRes}</div>`
                : `<div style="font-size:11px;color:#8f90a6">${c.city.toUpperCase()} | ${c.is_sprint ? `${c.sprint_laps}L SPR + ` : ""}${c.laps}L GP | ${c.track_width_m.toFixed(1)}M</div>`
            }
          </div>
        `;
      })
      .join("");

    this.renderHallOfFame();
  }

  async previewTradeValuation() {
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
  }

  renderTeamModal() {
    if (!this.fullState) return;
    const grid = document.getElementById("team-picker-grid");
    grid.innerHTML = this.fullState.teams
      .map(
        (t) => `
        <div class="tp-pick-card ${t.id === this.fullState.player_team_id ? "active" : ""}" data-pick-team="${t.id}">
          <div style="display:flex;justify-content:space-between;align-items:center">
            <span class="inline-team">
              ${teamLogoSVG(t.id, 20)}
              <strong style="color:#ffffff;font-size:13px;text-transform:uppercase">${t.short}</strong>
            </span>
            <span style="font-size:11px;color:#00d26a;font-weight:900">$${t.budget_m.toFixed(1)}M</span>
          </div>
          <div style="font-size:10.5px;color:#8f90a6;margin-top:5px;font-weight:700">${t.engine.toUpperCase()} PU  |  INDEX ${t.car_rating.toFixed(1)}</div>
        </div>
      `
      )
      .join("");

    grid.querySelectorAll("[data-pick-team]").forEach((card) => {
      card.addEventListener("click", async () => {
        const res = await this.apiPost("/api/select_team", { team_id: card.dataset.pickTeam });
        if (res.ok) {
          document.getElementById("team-modal").classList.add("hidden");
          this.showToast(`APPOINTED TEAM PRINCIPAL: ${card.dataset.pickTeam.toUpperCase()}`);
          this.fetchFullState();
        }
      });
    });
  }
  renderHallOfFame() {
    if (!this.fullState) return;
    const st = this.fullState;
    const archives = st.season_archives;
    if (!archives || !archives.seasons) return;

    if (!this.selectedHofSeason) {
      this.selectedHofSeason = st.season || 2026;
    }

    const yearKey = String(this.selectedHofSeason);
    const seasonData = archives.seasons[yearKey];
    if (!seasonData) return;

    // 1. Update active button in season selector
    document.querySelectorAll(".hof-season-btn").forEach((btn) => {
      const yr = parseInt(btn.dataset.year);
      btn.classList.toggle("active", yr === this.selectedHofSeason);
    });

    // 2. Header Badges
    const isCurrent = this.selectedHofSeason === st.season;
    const eraBadge = document.getElementById("hof-era-badge");
    const engineBadge = document.getElementById("hof-engine-badge");
    const statusBadge = document.getElementById("hof-status-badge");

    if (eraBadge) eraBadge.textContent = seasonData.era_name || "Formula 1 Regulations";
    if (engineBadge) engineBadge.textContent = seasonData.engine_type || "V6 Turbo-Hybrid";
    if (statusBadge) {
      if (isCurrent) {
        statusBadge.textContent = `LIVE CAREER SEASON (ROUND ${st.round} / ${seasonData.total_rounds || 24})`;
        statusBadge.className = "hof-badge hof-badge-live";
      } else if (seasonData.status === "COMPLETED") {
        statusBadge.textContent = "OFFICIAL FIA ARCHIVE RECORD";
        statusBadge.className = "hof-badge hof-badge-status";
      } else {
        statusBadge.textContent = "SCHEDULED FUTURE REGULATIONS";
        statusBadge.className = "hof-badge hof-badge-era";
      }
    }

    // 3. Champions Hero Banner
    const wdc = seasonData.wdc_champion || {};
    const wcc = seasonData.wcc_champion || {};
    const champBanner = document.getElementById("hof-champions-banner");

    if (champBanner) {
      const wdcTitle = isCurrent ? "CURRENT CHAMPIONSHIP LEADER" : "WORLD DRIVERS' CHAMPION";
      const wccTitle = isCurrent ? "CONSTRUCTORS' TITLE LEADER" : "WORLD CONSTRUCTORS' CHAMPION";

      champBanner.innerHTML = `
        <div class="hof-champ-card wdc">
          <div class="hof-champ-header">
            <div class="hof-trophy-tag">
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M6 9H4.5a2.5 2.5 0 0 1 0-5H6"></path>
                <path d="M18 9h1.5a2.5 2.5 0 0 0 0-5H18"></path>
                <path d="M4 22h16"></path>
                <path d="M10 14.66V17c0 .55-.45 1-1 1H7"></path>
                <path d="M14 14.66V17c0 .55.45 1 1 1h2"></path>
                <path d="M18 2H6v7a6 6 0 0 0 12 0V2Z"></path>
              </svg>
              <span>${this.selectedHofSeason} ${wdcTitle}</span>
            </div>
            <div class="hof-champ-points-badge">${wdc.points || 0} PTS</div>
          </div>
          <div class="hof-champ-identity">
            <div class="hof-champ-num">#${wdc.number || 1}</div>
            <div>
              <div class="hof-champ-name">${wdc.name || "TBD"}</div>
              <div class="hof-champ-team-line" style="color:${wdc.team_color || '#ff8000'}">
                ${teamLogoSVG(wdc.team_id || "mclaren", 16)}
                <span>${(wdc.team || "McLaren").toUpperCase()}</span>
              </div>
            </div>
          </div>
          <div class="hof-stats-row">
            <div class="hof-stat-cell">
              <div class="hof-stat-val">${wdc.wins || 0}</div>
              <div class="hof-stat-lbl">WINS</div>
            </div>
            <div class="hof-stat-cell">
              <div class="hof-stat-val">${wdc.podiums || 0}</div>
              <div class="hof-stat-lbl">PODIUMS</div>
            </div>
            <div class="hof-stat-cell">
              <div class="hof-stat-val">${wdc.poles || 0}</div>
              <div class="hof-stat-lbl">POLES</div>
            </div>
            <div class="hof-stat-cell">
              <div class="hof-stat-val">${wdc.points || 0}</div>
              <div class="hof-stat-lbl">PTS</div>
            </div>
          </div>
        </div>

        <div class="hof-champ-card wcc">
          <div class="hof-champ-header">
            <div class="hof-trophy-tag">
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M6 9H4.5a2.5 2.5 0 0 1 0-5H6"></path>
                <path d="M18 9h1.5a2.5 2.5 0 0 0 0-5H18"></path>
                <path d="M4 22h16"></path>
                <path d="M10 14.66V17c0 .55-.45 1-1 1H7"></path>
                <path d="M14 14.66V17c0 .55.45 1 1 1h2"></path>
                <path d="M18 2H6v7a6 6 0 0 0 12 0V2Z"></path>
              </svg>
              <span>${this.selectedHofSeason} ${wccTitle}</span>
            </div>
            <div class="hof-champ-points-badge">${wcc.points || 0} PTS</div>
          </div>
          <div class="hof-champ-identity">
            <div style="min-width:42px;display:flex;justify-content:center">
              ${teamLogoSVG(wcc.id || "mclaren", 32)}
            </div>
            <div>
              <div class="hof-champ-name" style="color:${wcc.color || '#00d2be'}">${(wcc.name || "Constructor").toUpperCase()}</div>
              <div class="hof-champ-team-line" style="color:var(--muted)">
                <span>POWER UNIT: ${wcc.engine || "Formula 1"}</span>
              </div>
            </div>
          </div>
          <div class="hof-stats-row">
            <div class="hof-stat-cell">
              <div class="hof-stat-val">${wcc.wins || 0}</div>
              <div class="hof-stat-lbl">WINS</div>
            </div>
            <div class="hof-stat-cell">
              <div class="hof-stat-val">${seasonData.total_rounds || 24}</div>
              <div class="hof-stat-lbl">GRANDS PRIX</div>
            </div>
            <div class="hof-stat-cell">
              <div class="hof-stat-val">${seasonData.has_active_aero ? "ACTIVE AERO" : "CLASSIC DRS"}</div>
              <div class="hof-stat-lbl">AERO REG</div>
            </div>
            <div class="hof-stat-cell">
              <div class="hof-stat-val">${wcc.points || 0}</div>
              <div class="hof-stat-lbl">PTS</div>
            </div>
          </div>
        </div>
      `;
    }

    // 4. Narrative Card
    const narrativeEl = document.getElementById("hof-narrative-card");
    if (narrativeEl) {
      narrativeEl.innerHTML = `<strong>${this.selectedHofSeason} SEASON REPORT:</strong> ${seasonData.narrative || "Official Formula 1 Championship World Tour."}`;
    }

    // 5. Total Rounds Meta Stat
    const metaRoundEl = document.getElementById("hof-round-count");
    if (metaRoundEl) {
      const done = seasonData.completed_rounds ?? (seasonData.races ? seasonData.races.length : 0);
      const tot = seasonData.total_rounds || (seasonData.races ? seasonData.races.length : 24);
      metaRoundEl.textContent = `${done} OF ${tot} GRANDS PRIX RECORDED`;
    }

    // 6. Race-by-Race Results Grid
    const racesGrid = document.getElementById("hof-races-grid");
    if (racesGrid && seasonData.races) {
      racesGrid.innerHTML = seasonData.races.map((r) => {
        const sprPill = r.is_sprint ? `<span class="sprint-pill" style="font-size:8px">SPRINT</span>` : "";
        const top10Rows = (r.top10 || []).map((car) => `
          <tr>
            <td style="font-weight:800;color:${car.pos <= 3 ? '#ffd000' : 'var(--muted)'}">P${car.pos}</td>
            <td style="font-weight:700">#${car.number || ''} ${car.name}</td>
            <td style="color:${car.team_color || 'var(--text)'};font-weight:700">${car.team}</td>
            <td style="color:var(--muted)">${car.gap}</td>
            <td style="text-align:right;font-weight:900;color:#ffffff">+${car.points}</td>
          </tr>
        `).join("");

        return `
          <div class="hof-race-card" style="--team-accent:${r.winner_color || '#e10600'}">
            <div class="hof-race-card-hdr">
              <div class="hof-round-pill">ROUND ${String(r.round).padStart(2, '0')}</div>
              <div>${sprPill}</div>
            </div>
            <div>
              <div class="hof-race-card-title">${r.gp.toUpperCase()}</div>
              <div class="hof-track-sub">${r.circuit} • ${r.city}, ${r.country} (${r.laps} LAPS)</div>
            </div>

            <!-- WINNER -->
            <div class="hof-winner-box">
              <div class="hof-winner-main">
                <span class="hof-p1-tag">P1</span>
                <div>
                  <div class="hof-winner-drv">#${r.winner_number || ''} ${r.winner_name}</div>
                  <div class="hof-winner-team" style="color:${r.winner_color || 'var(--muted)'}">
                    ${teamLogoSVG(r.winner_team_id || 'mclaren', 12)}
                    ${(r.winner_team || '').toUpperCase()}
                  </div>
                </div>
              </div>
              <div style="font-size:16px;font-weight:900;color:#ffd000;font-style:italic">25 PTS</div>
            </div>

            <!-- PODIUM P2 & P3 -->
            <div class="hof-podium-strip">
              <div class="hof-podium-item">
                <span class="hof-pos-tag">P2</span>
                <span style="color:${r.p2_color || 'var(--text)'};font-weight:700">${r.p2_code}</span>
                <span>${r.p2_name}</span>
              </div>
              <div class="hof-podium-item">
                <span class="hof-pos-tag">P3</span>
                <span style="color:${r.p3_color || 'var(--text)'};font-weight:700">${r.p3_code}</span>
                <span>${r.p3_name}</span>
              </div>
            </div>

            <!-- POLE & FASTEST LAP -->
            <div class="hof-extra-strip">
              <div>POLE: <span style="color:#ffffff;font-weight:800">${r.pole_code || '---'}</span></div>
              <div>FL: <span style="color:#a855f7;font-weight:800">${r.fastest_lap_code || '---'}</span></div>
              ${r.is_sprint && r.sprint_winner_code ? `<div>SPRINT: <span style="color:#00d2be;font-weight:800">${r.sprint_winner_code}</span></div>` : ''}
            </div>

            <button class="hof-card-btn" data-round="${r.round}">VIEW TOP 10 CLASSIFICATION</button>
            ${(r.lap_chart?.length || r.stints) ? `<button class="hof-card-btn" data-analytics-round="${r.round}" style="margin-top:4px;border-color:#00d2be;color:#00d2be">STRATEGY &amp; POSITION CHART</button>` : ""}

            <!-- COLLAPSIBLE TOP 10 DRAWER -->
            <div class="hof-top10-collapse hidden" id="hof-top10-${r.round}">
              <table class="hof-top10-table">
                <thead>
                  <tr>
                    <th>POS</th>
                    <th>DRIVER</th>
                    <th>TEAM</th>
                    <th>GAP</th>
                    <th style="text-align:right">PTS</th>
                  </tr>
                </thead>
                <tbody>
                  ${top10Rows}
                </tbody>
              </table>
            </div>
          </div>
        `;
      }).join("");
    }

    // 7. Season Classification Tables
    const wdcTbody = document.querySelector("#hof-wdc-table tbody");
    if (wdcTbody && seasonData.wdc_standings) {
      wdcTbody.innerHTML = seasonData.wdc_standings.map((d) => `
        <tr class="${d.rank === 1 ? 'highlight-me' : ''}">
          <td><strong style="font-style:italic">${d.rank || 1}</strong></td>
          <td><strong>#${d.number || ''} ${d.name}</strong></td>
          <td>
            <span class="inline-team" style="color:${d.team_color};font-weight:700">
              ${teamLogoSVG(d.team_id, 14)}
              ${(d.team || '').toUpperCase()}
            </span>
          </td>
          <td>${d.wins || 0}</td>
          <td>${d.podiums || 0}</td>
          <td>${d.poles || 0}</td>
          <td style="text-align:right;font-weight:900">${d.points || 0}</td>
        </tr>
      `).join("");
    }

    const wccTbody = document.querySelector("#hof-wcc-table tbody");
    if (wccTbody && seasonData.wcc_standings) {
      wccTbody.innerHTML = seasonData.wcc_standings.map((t) => `
        <tr class="${t.rank === 1 ? 'highlight-me' : ''}">
          <td><strong style="font-style:italic">${t.rank || 1}</strong></td>
          <td>
            <span class="inline-team" style="font-weight:900">
              ${teamLogoSVG(t.id, 16)}
              <span style="color:${t.color}">${(t.name || '').toUpperCase()}</span>
            </span>
          </td>
          <td>${t.engine || 'Formula 1'}</td>
          <td>${t.wins || 0}</td>
          <td style="text-align:right;font-weight:900">${t.points || 0}</td>
        </tr>
      `).join("");
    }
  }

  renderContractNegotiator() {
    if (!this.fullState) return;
    const st = this.fullState;
    const drvSel = document.getElementById("neg-driver");
    const relSel = document.getElementById("neg-release-driver");
    const relWrap = document.getElementById("neg-release-wrap");
    const yearsSel = document.getElementById("neg-years");
    const salSlider = document.getElementById("neg-salary-slider");
    const execBtn = document.getElementById("btn-exec-neg");
    if (!drvSel || !relSel || !yearsSel || !salSlider || !execBtn) return;

    const myDrivers = st.drivers.filter((d) => d.team_id === st.player_team_id);
    const otherDrivers = st.drivers.filter((d) => d.team_id !== st.player_team_id);
    const prevDrv = drvSel.value;
    drvSel.innerHTML = [
      ...myDrivers.map((d) => `<option value="${d.id}">[RENEW] #${d.number} ${d.name} (${d.contract_years}Y | $${d.salary_m}M/yr | OVR ${d.overall})</option>`),
      ...otherDrivers.map((d) => `<option value="${d.id}">[${d.team_id ? d.team_short.toUpperCase() : "FREE AGENT"}] #${d.number} ${d.name} (OVR ${d.overall} | $${d.salary_m}M/yr)</option>`),
    ].join("");
    if ([...myDrivers, ...otherDrivers].some((d) => d.id === prevDrv)) drvSel.value = prevDrv;

    const prevRel = relSel.value;
    relSel.innerHTML = myDrivers.map((d) => `<option value="${d.id}">#${d.number} ${d.name} (OVR ${d.overall})</option>`).join("");
    if (myDrivers.some((d) => d.id === prevRel)) relSel.value = prevRel;

    const syncVisibilityAndDefault = () => {
      const target = st.drivers.find((d) => d.id === drvSel.value);
      const isOwn = target && target.team_id === st.player_team_id;
      if (relWrap) relWrap.style.opacity = isOwn ? "0.4" : "1.0";
      relSel.disabled = Boolean(isOwn);
    };
    syncVisibilityAndDefault();

    if (!this._negBound) {
      this._negBound = true;
      drvSel.addEventListener("change", () => {
        const target = this.fullState?.drivers.find((d) => d.id === drvSel.value);
        if (target) {
          salSlider.value = String(Math.min(60, Math.max(1, target.salary_m)));
        }
        syncVisibilityAndDefault();
        this.previewContractNegotiation();
      });
      relSel.addEventListener("change", () => this.previewContractNegotiation());
      yearsSel.addEventListener("change", () => this.previewContractNegotiation());
      salSlider.addEventListener("input", () => {
        const lbl = document.getElementById("neg-salary-label");
        if (lbl) lbl.textContent = `$${Number(salSlider.value || 5).toFixed(1)}M/YR`;
        clearTimeout(this._negTimer);
        this._negTimer = setTimeout(() => this.previewContractNegotiation(), 100);
      });
      execBtn.addEventListener("click", async () => {
        const res = await this.apiPost("/api/negotiate_contract", {
          driver_id: drvSel.value,
          salary_m: Number(salSlider.value),
          years: Number(yearsSel.value),
          release_driver_id: relSel.value,
        });
        if (res.ok) {
          this.showToast(`CONTRACT SIGNED: ${res.message}`);
          this.fetchFullState();
        }
      });
    }

    const curTarget = st.drivers.find((d) => d.id === drvSel.value);
    if (curTarget && !prevDrv) {
      salSlider.value = String(Math.min(60, Math.max(1, curTarget.salary_m)));
    }
    this.previewContractNegotiation();
  }

  async previewContractNegotiation() {
    const drvSel = document.getElementById("neg-driver");
    const relSel = document.getElementById("neg-release-driver");
    const yearsSel = document.getElementById("neg-years");
    const salSlider = document.getElementById("neg-salary-slider");
    const salLabel = document.getElementById("neg-salary-label");
    const evalBox = document.getElementById("neg-eval-box");
    const execBtn = document.getElementById("btn-exec-neg");
    if (!drvSel || !salSlider || !evalBox) return;

    const sal = Number(salSlider.value || 5);
    if (salLabel) salLabel.textContent = `$${sal.toFixed(1)}M/YR`;

    const res = await this.apiPost("/api/negotiate_contract", {
      action: "evaluate",
      driver_id: drvSel.value,
      salary_m: sal,
      years: Number(yearsSel?.value || 2),
      release_driver_id: relSel?.value,
    });
    if (!res.ok) {
      evalBox.innerHTML = `<span style="color:#ff4d4f">${res.error || "Unable to evaluate contract."}</span>`;
      if (execBtn) execBtn.disabled = true;
      return;
    }
    const costStr = res.total_upfront_m > 0
      ? ` · Upfront Buyout/Signing: <strong>$${res.total_upfront_m.toFixed(1)}M</strong>`
      : " · No transfer fee (Renewal)";
    const badge = res.accepted
      ? `<span style="color:#00d26a;font-weight:900">ACCEPTED</span>`
      : `<span style="color:#ffd000;font-weight:900">DECLINED</span>`;
    evalBox.innerHTML = `${badge} — ${res.reason} <span style="color:#8f90a6">(Demand: $${res.asked_salary_m.toFixed(1)}M/yr${costStr})</span>`;
    if (execBtn) execBtn.disabled = !res.accepted;
  }

  openAnalyticsModal(raceObj) {
    const modal = document.getElementById("analytics-modal");
    const titleEl = document.getElementById("analytics-modal-title");
    const posWrap = document.getElementById("analytics-pos-chart");
    const stintsWrap = document.getElementById("analytics-stints-chart");
    if (!modal || !posWrap || !stintsWrap) return;

    const rec = raceObj.round_rec || raceObj;
    const gpName = rec.gp || "Grand Prix";
    const lapChart = raceObj.lap_chart || rec.lap_chart || [];
    const stintsMap = raceObj.stints || rec.stints || {};
    const top10 = raceObj.top10 || rec.top10 || [];
    const dMeta = raceObj.driver_meta || rec.driver_meta || {};

    if (titleEl) titleEl.textContent = `${gpName.toUpperCase()} — STRATEGY & POSITION CHART`;

    const metaLookup = (did) => {
      if (dMeta[did]) return dMeta[did];
      const tRow = top10.find((r) => r.id === did || r.driver_id === did);
      if (tRow) return { code: tRow.code, team_color: tRow.team_color || "#888888", name: tRow.name };
      const stDrv = this.fullState?.drivers?.find((d) => d.id === did);
      return stDrv ? { code: stDrv.code, team_color: stDrv.team_color || "#888888", name: stDrv.name } : { code: did.slice(0, 3).toUpperCase(), team_color: "#888888", name: did };
    };

    // 1. Render SVG Lap-by-Lap Position Trace
    if (lapChart.length >= 2) {
      const laps = lapChart.map((l) => l.lap);
      const minLap = laps[0];
      const maxLap = laps[laps.length - 1];
      const driverIds = Object.keys(lapChart[lapChart.length - 1].positions || {});
      const maxPos = Math.max(10, ...driverIds.map((id) => lapChart[lapChart.length - 1].positions[id] || 10));
      const focusIds = driverIds.filter((id) => (lapChart[lapChart.length - 1].positions[id] || 99) <= 12);
      const W = 860;
      const H = 290;
      const padL = 36;
      const padR = 54;
      const padT = 18;
      const padB = 26;
      const xOf = (lap) => padL + ((lap - minLap) / Math.max(1, maxLap - minLap)) * (W - padL - padR);
      const yOf = (pos) => padT + ((pos - 1) / Math.max(1, maxPos - 1)) * (H - padT - padB);

      const gridLines = [];
      for (let p = 1; p <= maxPos; p += maxPos > 14 ? 3 : 2) {
        const y = yOf(p);
        gridLines.push(`<line x1="${padL}" y1="${y}" x2="${W - padR}" y2="${y}" stroke="rgba(255,255,255,0.06)" stroke-width="1" />`);
        gridLines.push(`<text x="${padL - 6}" y="${y + 3}" fill="#8f90a6" font-size="9" text-anchor="end" font-weight="700">P${p}</text>`);
      }
      const stepLap = Math.max(1, Math.ceil(laps.length / 8));
      for (let i = 0; i < laps.length; i += stepLap) {
        const x = xOf(laps[i]);
        gridLines.push(`<text x="${x}" y="${H - 7}" fill="#8f90a6" font-size="9" text-anchor="middle" font-weight="700">L${laps[i]}</text>`);
      }

      const paths = focusIds.map((did) => {
        const m = metaLookup(did);
        const pts = lapChart
          .map((l) => {
            const p = l.positions[did];
            return p != null ? `${xOf(l.lap).toFixed(1)},${yOf(p).toFixed(1)}` : null;
          })
          .filter(Boolean)
          .join(" ");
        const lastPos = lapChart[lapChart.length - 1].positions[did] || 1;
        return `
          <polyline fill="none" stroke="${m.team_color}" stroke-width="2.1" stroke-linejoin="round" opacity="0.92" points="${pts}" />
          <text x="${W - padR + 6}" y="${(yOf(lastPos) + 3).toFixed(1)}" fill="${m.team_color}" font-size="9.5" font-weight="800">${m.code} P${lastPos}</text>
        `;
      }).join("");

      posWrap.innerHTML = `<svg viewBox="0 0 ${W} ${H}" style="width:100%;height:auto;display:block">${gridLines.join("")}${paths}</svg>`;
    } else {
      posWrap.innerHTML = `<div style="padding:14px;color:#8f90a6;font-size:11px">Lap-by-lap trace available once at least 2 laps are completed.</div>`;
    }

    // 2. Render Compound-Colored Tyre Stint Timeline
    const stKeys = Object.keys(stintsMap);
    const totalLaps = Math.max(1, rec.laps || (lapChart.length ? lapChart[lapChart.length - 1].lap : 20));
    if (stKeys.length > 0) {
      const orderIds = top10.map((r) => r.id || r.driver_id).filter((id) => stintsMap[id]);
      for (const id of stKeys) {
        if (!orderIds.includes(id)) orderIds.push(id);
      }
      stintsWrap.innerHTML = orderIds.slice(0, 14).map((did) => {
        const m = metaLookup(did);
        const list = stintsMap[did] || [];
        const bars = list.map((s) => {
          const span = Math.max(1, (s.end_lap || s.start_lap) - s.start_lap + 1);
          const pct = Math.max(4, Math.min(100, (span / totalLaps) * 100));
          const meta = TIRE_META[s.compound] || TIRE_META.MEDIUM;
          const lbl = `${meta.code} ${span}L${s.scrubbed ? " S" : ""}`;
          return `<div class="stint-seg" style="width:${pct.toFixed(1)}%;background:${meta.color}" title="${s.compound} (L${s.start_lap}-L${s.end_lap}${s.scrubbed ? ', Scrubbed' : ''})">${span >= 2 ? lbl : meta.code}</div>`;
        }).join("");
        return `
          <div class="stint-driver-row">
            <strong style="color:${m.team_color};white-space:nowrap">${m.code}</strong>
            <div class="stint-track">${bars}</div>
          </div>
        `;
      }).join("");
    } else {
      stintsWrap.innerHTML = `<div style="padding:10px;color:#8f90a6;font-size:11px">No tyre stint history recorded for this round.</div>`;
    }

    modal.classList.remove("hidden");
  }
}

window.addEventListener("DOMContentLoaded", () => {
  new F1App();
});
