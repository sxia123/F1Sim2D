with open("public/app.js", "r", encoding="utf-8") as f:
    text = f.read()

# 1. Constructor properties
target_ctor = 'this._lastHeaderLogoTeam = "";\n'
new_ctor = ('this._lastHeaderLogoTeam = "";\n'
            '    this.selectedHofSeason = 2026;\n'
            '    this.hofViewMode = "races";\n')
if target_ctor in text:
    text = text.replace(target_ctor, new_ctor, 1)

# 2. _bindUI listeners
target_bind_end = """        this.renderDriverDatabase();
      });
    });
  }"""

new_bind_listeners = """        this.renderDriverDatabase();
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

    // Hall of Fame expandable Top 10 classifications
    const racesGrid = document.getElementById("hof-races-grid");
    if (racesGrid) {
      racesGrid.addEventListener("click", (e) => {
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
  }"""

if target_bind_end in text:
    text = text.replace(target_bind_end, new_bind_listeners, 1)

# 3. Call renderHallOfFame in renderManagementViews()
target_render_end = """      })
      .join("");
  }

  async previewTradeValuation() {"""

new_render_end = """      })
      .join("");

    this.renderHallOfFame();
  }

  async previewTradeValuation() {"""

assert target_render_end in text, "Could not find target_render_end"
text = text.replace(target_render_end, new_render_end, 1)

# 4. Add renderHallOfFame method
hof_method = """
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
"""

text += hof_method

with open("public/app.js", "w", encoding="utf-8") as f:
    f.write(text)

print("public/app.js updated successfully!")

