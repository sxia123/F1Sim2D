// Run with: node tests/test_engine_audio.cjs
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

function makeParam(initial = 0) {
  return {
    value: initial,
    setTargetAtTime(v) { this.value = v; },
    setValueAtTime(v) { this.value = v; },
    linearRampToValueAtTime(v) { this.value = v; },
    exponentialRampToValueAtTime(v) { this.value = v; },
    cancelScheduledValues() {},
  };
}

class MockAudioContext {
  constructor() {
    this.state = 'running';
    this.currentTime = 1.0;
    this.sampleRate = 48000;
    this.destination = { connected: true };
    this.oscillators = [];
    this.gains = [];
    this.filters = [];
  }
  resume() { this.state = 'running'; return Promise.resolve(); }
  createGain() {
    const g = { gain: makeParam(1.0), connect() {} };
    this.gains.push(g);
    return g;
  }
  createOscillator() {
    const osc = { type: 'sine', frequency: makeParam(440), detune: makeParam(0), connect() {}, start() {} };
    this.oscillators.push(osc);
    return osc;
  }
  createBiquadFilter() {
    const f = { type: 'lowpass', frequency: makeParam(1000), Q: makeParam(1), gain: makeParam(0), connect() {} };
    this.filters.push(f);
    return f;
  }
  createWaveShaper() {
    return { curve: null, oversample: 'none', connect() {} };
  }
  createDynamicsCompressor() {
    return { threshold: makeParam(0), knee: makeParam(0), ratio: makeParam(1), attack: makeParam(0), release: makeParam(0), connect() {} };
  }
  createBuffer(channels, len) {
    return { getChannelData: () => new Float32Array(len) };
  }
  createBufferSource() {
    return { buffer: null, loop: false, connect() {}, start() {} };
  }
}

const source = fs.readFileSync(path.join(__dirname, '../public/app.js'), 'utf8')
  .replace(/^import .*;\r?\n/gm, '');

// 1) Headless / non-browser safety check
const headlessCtx = vm.createContext({
  document: { getElementById: () => null },
  window: { addEventListener() {} },
  teamLogoSVG: () => '',
});
vm.runInContext(`${source}\nglobalThis.F1EngineAudio = F1EngineAudio;`, headlessCtx);
const headlessAudio = new headlessCtx.F1EngineAudio();
headlessAudio.unlock();
headlessAudio.update({ phase: 'RACE', flag: 'GREEN', sim_speed: 1, cars: [{ id: 'ver', kph: 300 }] }, 'ver', 'full');
assert.equal(headlessAudio.enabled, true);

// 2) Full Web Audio graph + RPM / gear / toggle simulation
const ctx = vm.createContext({
  document: { getElementById: () => null },
  window: { addEventListener() {}, AudioContext: MockAudioContext },
  performance,
  teamLogoSVG: () => '',
});
vm.runInContext(`${source}\nglobalThis.F1EngineAudio = F1EngineAudio;`, ctx);
const audio = new ctx.F1EngineAudio();
audio.unlock();
assert.ok(audio.ctx instanceof MockAudioContext);

const car = {
  id: 'ham', tid: 'ferrari', code: 'HAM', num: 44, pos: 1,
  kph: 160, braking: false, drs: false, ovt: false, boost: false,
  rech: false, lift_coast: false, in_pit: false, pit_ph: '',
  battle: false, intv: 2.5, dnf: false, elim: false, quali_phase: '',
};

const baseTick = {
  phase: 'RACE',
  flag: 'GREEN',
  lights: 0,
  sim_speed: 1,
  regulations: { era_id: 'HYBRID_2026' },
  cars: [car],
};

audio.update(baseTick, 'ham', 'selected');
assert.ok(audio.masterGain.gain.value > 0.05);
const fLow = audio.fundOsc.frequency.value;

car.kph = 345;
car.drs = true;
audio.update(baseTick, 'ham', 'selected');
assert.equal(audio._gear, 8);
assert.ok(audio.fundOsc.frequency.value > fLow);

// 2028 V8 era scales higher than 2026 V6 at equivalent high speed
const v8Tick = { ...baseTick, regulations: { era_id: 'V8_DRS' } };
audio.update(v8Tick, 'ham', 'selected');
assert.ok(audio.fundOsc.frequency.value > 650);

// Downshift under braking invokes overrun crackle & blip cleanly
car.kph = 110;
car.braking = true;
audio.update(baseTick, 'ham', 'selected');
assert.ok(audio._gear <= 3);

// Pit limiter / paused / non-session / mute silence checks
audio.update({ ...baseTick, sim_speed: 0 }, 'ham', 'selected');
assert.equal(audio.masterGain.gain.value, 0);
audio.update({ ...baseTick, phase: 'PRE_WEEKEND' }, 'ham', 'selected');
assert.equal(audio.masterGain.gain.value, 0);
assert.equal(audio.toggle(), false);
assert.equal(audio.masterGain.gain.value, 0);
assert.equal(audio.toggle(), true);

// Broadcast SFX helpers (headless-safe & active AudioContext)
headlessAudio.playStartLightBeep(false);
headlessAudio.playRadioChirp();
headlessAudio.playPitGun();
headlessAudio.playFlagChime('SC');

const oscCountBefore = audio.ctx.oscillators.length;
audio.playStartLightBeep(false);
audio.playStartLightBeep(true);
audio.playRadioChirp();
audio.playPitGun();
audio.playFlagChime('RED_FLAG');
assert.ok(audio.ctx.oscillators.length >= oscCountBefore + 5);

console.log('Engine audio checks passed.');
