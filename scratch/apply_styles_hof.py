css_rules = """
/* ==========================================================================
   HALL OF FAME & MULTI-SEASON RESULTS ARCHIVE (2026-2030)
   ========================================================================== */

.hof-header-wrap {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 16px;
  background: linear-gradient(135deg, #181924 0%, #12131b 100%);
  border: 1px solid var(--line);
  border-left: 4px solid var(--f1-red);
  padding: 16px 20px;
  margin-bottom: 16px;
  border-radius: 4px;
}

.hof-header-left {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.hof-pretitle {
  font-size: 10px;
  letter-spacing: 1.2px;
  color: var(--muted);
  font-weight: 700;
  text-transform: uppercase;
}

.hof-main-title {
  font-size: 20px;
  font-weight: 900;
  font-style: italic;
  letter-spacing: 0.8px;
  color: var(--text);
  margin: 0;
  text-transform: uppercase;
}

.hof-era-strip {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 4px;
  flex-wrap: wrap;
}

.hof-badge {
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.6px;
  padding: 3px 8px;
  border-radius: 2px;
  text-transform: uppercase;
}

.hof-badge-era {
  background: rgba(225, 6, 0, 0.15);
  border: 1px solid rgba(225, 6, 0, 0.4);
  color: #ff4d47;
}

.hof-badge-engine {
  background: rgba(143, 144, 166, 0.15);
  border: 1px solid var(--line);
  color: var(--text);
}

.hof-badge-status {
  background: rgba(255, 208, 0, 0.15);
  border: 1px solid rgba(255, 208, 0, 0.45);
  color: #ffd000;
}

.hof-badge-live {
  background: rgba(0, 210, 106, 0.15);
  border: 1px solid rgba(0, 210, 106, 0.45);
  color: #00d26a;
}

.hof-season-selector-wrap {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 6px;
}

.hof-selector-title {
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.9px;
  color: var(--muted);
  text-transform: uppercase;
}

.hof-season-buttons {
  display: flex;
  gap: 6px;
}

.hof-season-btn {
  background: var(--bg-carbon);
  color: var(--text);
  border: 1px solid var(--line);
  padding: 6px 14px;
  font-size: 13px;
  font-weight: 800;
  font-style: italic;
  letter-spacing: 0.5px;
  cursor: pointer;
  border-radius: 2px;
  transition: all 0.15s ease;
}

.hof-season-btn:hover {
  background: var(--bg-elev);
  border-color: var(--line-bright);
}

.hof-season-btn.active {
  background: var(--f1-red);
  color: #ffffff;
  border-color: var(--f1-red);
  box-shadow: 0 0 10px rgba(225, 6, 0, 0.4);
}

/* CHAMPIONS HERO GRID */
.hof-champions-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
  gap: 14px;
  margin-bottom: 14px;
}

.hof-champ-card {
  background: var(--bg-carbon);
  border: 1px solid var(--line);
  border-radius: 4px;
  padding: 16px;
  position: relative;
  overflow: hidden;
}

.hof-champ-card.wdc {
  border-top: 3px solid #ffd000;
}

.hof-champ-card.wcc {
  border-top: 3px solid #00d2be;
}

.hof-champ-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.hof-trophy-tag {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.8px;
  text-transform: uppercase;
}

.hof-champ-card.wdc .hof-trophy-tag { color: #ffd000; }
.hof-champ-card.wcc .hof-trophy-tag { color: #00d2be; }

.hof-champ-points-badge {
  font-size: 14px;
  font-weight: 900;
  font-style: italic;
  color: #ffffff;
  background: rgba(255, 255, 255, 0.08);
  padding: 3px 8px;
  border-radius: 2px;
}

.hof-champ-identity {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 14px;
}

.hof-champ-num {
  font-size: 26px;
  font-weight: 900;
  font-style: italic;
  color: var(--muted);
  min-width: 42px;
  text-align: center;
}

.hof-champ-name {
  font-size: 20px;
  font-weight: 900;
  font-style: italic;
  text-transform: uppercase;
  color: #ffffff;
  letter-spacing: 0.5px;
}

.hof-champ-team-line {
  font-size: 12px;
  font-weight: 700;
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 2px;
}

.hof-stats-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 8px;
  background: var(--bg-panel);
  border: 1px solid var(--line);
  padding: 8px 10px;
  border-radius: 3px;
}

.hof-stat-cell {
  text-align: center;
}

.hof-stat-val {
  font-size: 16px;
  font-weight: 900;
  color: #ffffff;
}

.hof-stat-lbl {
  font-size: 9px;
  font-weight: 700;
  color: var(--muted);
  letter-spacing: 0.5px;
  text-transform: uppercase;
}

/* NARRATIVE */
.hof-narrative-card {
  background: rgba(255, 255, 255, 0.03);
  border: 1px dashed var(--line);
  padding: 10px 14px;
  font-size: 12px;
  color: #c4c5d6;
  font-style: italic;
  line-height: 1.5;
  margin-bottom: 14px;
  border-radius: 3px;
}

/* SUBNAV */
.hof-subnav {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
  flex-wrap: wrap;
  gap: 10px;
}

.hof-subnav-buttons {
  display: flex;
  gap: 6px;
}

.hof-sub-btn {
  background: var(--bg-panel);
  border: 1px solid var(--line);
  color: var(--muted);
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.7px;
  padding: 7px 14px;
  cursor: pointer;
  border-radius: 2px;
  text-transform: uppercase;
  transition: all 0.15s ease;
}

.hof-sub-btn:hover {
  color: #ffffff;
  border-color: var(--line-bright);
}

.hof-sub-btn.active {
  background: var(--bg-elev);
  border-color: var(--f1-red);
  color: #ffffff;
}

.hof-meta-stat {
  font-size: 11px;
  font-weight: 700;
  color: var(--muted);
  letter-spacing: 0.5px;
}

/* RACES GRID */
.hof-races-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(290px, 1fr));
  gap: 10px;
  margin-bottom: 24px;
}

.hof-race-card {
  background: var(--bg-carbon);
  border: 1px solid var(--line);
  border-top: 3px solid var(--line-bright);
  border-radius: 3px;
  padding: 11px 13px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  transition: transform 0.12s ease, border-color 0.12s ease;
}

.hof-race-card:hover {
  border-color: var(--line-bright);
  transform: translateY(-1px);
}

.hof-race-card.winner-accent {
  border-top-color: var(--team-accent, var(--f1-red));
}

.hof-race-card-hdr {
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
  padding-bottom: 6px;
}

.hof-round-pill {
  font-size: 10px;
  font-weight: 900;
  font-style: italic;
  color: var(--muted);
  letter-spacing: 0.5px;
}

.hof-race-card-title {
  font-size: 14px;
  font-weight: 900;
  font-style: italic;
  color: #ffffff;
  letter-spacing: 0.3px;
}

.hof-track-sub {
  font-size: 11px;
  color: var(--muted);
}

.hof-winner-box {
  background: var(--bg-panel);
  border: 1px solid var(--line);
  padding: 7px 9px;
  border-radius: 2px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.hof-winner-main {
  display: flex;
  align-items: center;
  gap: 8px;
}

.hof-p1-tag {
  background: #ffd000;
  color: #000000;
  font-size: 9px;
  font-weight: 900;
  padding: 1px 4px;
  border-radius: 2px;
}

.hof-winner-drv {
  font-size: 13px;
  font-weight: 900;
  color: #ffffff;
}

.hof-winner-team {
  font-size: 10px;
  font-weight: 700;
  color: var(--muted);
}

.hof-podium-strip {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 6px;
  font-size: 11px;
}

.hof-podium-item {
  background: rgba(255, 255, 255, 0.03);
  padding: 4px 6px;
  border-radius: 2px;
  display: flex;
  align-items: center;
  gap: 5px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.hof-pos-tag {
  font-size: 9px;
  font-weight: 800;
  color: var(--muted);
}

.hof-extra-strip {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 10px;
  font-weight: 700;
  color: var(--muted);
  border-top: 1px solid rgba(255, 255, 255, 0.05);
  padding-top: 5px;
}

.hof-card-btn {
  background: var(--bg-elev);
  border: 1px solid var(--line);
  color: var(--text);
  font-size: 10px;
  font-weight: 800;
  letter-spacing: 0.5px;
  padding: 4px 8px;
  border-radius: 2px;
  cursor: pointer;
  text-align: center;
  text-transform: uppercase;
  margin-top: 4px;
  transition: all 0.15s ease;
}

.hof-card-btn:hover {
  background: var(--f1-red);
  color: #ffffff;
  border-color: var(--f1-red);
}

.hof-top10-collapse {
  background: #0e0e14;
  border: 1px solid var(--line);
  border-radius: 2px;
  margin-top: 4px;
  padding: 6px 8px;
  font-size: 11px;
}

.hof-top10-table {
  width: 100%;
  border-collapse: collapse;
}

.hof-top10-table th, .hof-top10-table td {
  padding: 3px 4px;
  text-align: left;
}

.hof-top10-table th {
  font-size: 9px;
  color: var(--muted);
  font-weight: 700;
  border-bottom: 1px solid var(--line);
}

.hof-standings-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(420px, 1fr));
  gap: 16px;
  margin-bottom: 24px;
}
"""

with open("public/styles.css", "a", encoding="utf-8") as f:
    f.write(css_rules)

print("public/styles.css updated successfully!")

