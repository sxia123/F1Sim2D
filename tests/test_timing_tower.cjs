// Run with: node tests/test_timing_tower.cjs
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const list = { innerHTML: '' };
const gapHeading = { textContent: '', title: '' };
const context = vm.createContext({
  document: { getElementById: (id) => id === 'timing-gap-heading' ? gapHeading : list },
  window: { addEventListener() {} },
  teamLogoSVG: () => '',
});
const source = fs.readFileSync(path.join(__dirname, '../public/app.js'), 'utf8')
  .replace(/^import .*;\r?\n/gm, '');
vm.runInContext(`${source}\nglobalThis.F1App = F1App;`, context);

assert.equal(vm.runInContext('fmtLap(119.9996)', context), '2:00.000');
assert.equal(vm.runInContext('fmtLap(90.123)', context), '1:30.123');
assert.equal(vm.runInContext('fmtLap(null)', context), '--:--.---');
assert.equal(vm.runInContext('fmtSector(null)', context), '--.---');
assert.equal(vm.runInContext('timingClass(30, 30, 30)', context), 'time-session-best');
assert.equal(vm.runInContext('timingClass(31, 31, 30)', context), 'time-personal-best');
assert.equal(vm.runInContext('timingClass(32, 31, 30)', context), 'time-slower');

const driver = {
  id: 'test-driver', tid: 'williams', tcol: '#0077ff', code: 'TST', num: 23,
  pos: 3, comp: 'MEDIUM', wear: 5, bat: 72, gap: 12.345, intv: 1.234,
  last: 90.123, best: 89.321, sectors: [29.123, null, null],
  last_sectors: [30.123, 30, 30], best_sectors: [29.123, 29, 29],
};
const tick = {
  phase: 'RACE', flag: 'GREEN', player_team_id: 'williams',
  fastest_id: 'someone-else', fastest_time: 88,
  sector_bests: [29.123, 28, 28], cars: [driver],
};
const render = () => context.F1App.prototype.renderTimingTower.call(
  { selectedDriverId: driver.id }, tick);
render();
assert.match(list.innerHTML, /t-row selected my-car/);
assert.match(list.innerHTML, /<small>LAST<\/small>.*1:30\.123/);
assert.match(list.innerHTML, /<small>BEST<\/small>.*1:29\.321/);
assert.match(list.innerHTML, /Current lap sector 1: 29\.123 — Session best/);
assert.match(list.innerHTML, /Last lap sector 2: 30\.000/);
assert.match(list.innerHTML, /t-sector time-slower t-sector-previous t-sector-active/);
assert.equal((list.innerHTML.match(/<small>S[123]<\/small>/g) || []).length, 3);
assert.equal(gapHeading.textContent, 'GAP / INT');
assert.match(list.innerHTML, /t-gap-val" title="Gap to the race leader">\+12\.345/);
assert.match(list.innerHTML, /t-interval"[^>]*>INT \+1\.234/);
// Race gaps must come from race progress, even when lap deltas differ.
driver.last = 95;
driver.best = 94;
render();
assert.match(list.innerHTML, /t-gap-val"[^>]*>\+12\.345/);
assert.match(list.innerHTML, /t-interval"[^>]*>INT \+1\.234/);
tick.phase = 'SPRINT_RACE';
render();
assert.match(list.innerHTML, /t-gap-val"[^>]*>\+12\.345/);
assert.match(list.innerHTML, /t-interval"[^>]*>I