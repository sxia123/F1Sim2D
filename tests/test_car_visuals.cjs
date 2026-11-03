// Display-only contract: draw frozen telemetry, preserve physical wheel sizes,
// and reuse material canvases instead of rebuilding them on every frame.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

let canvasCount = 0;
function context2d() {
  const stack = [], wheelSizes = [];
  const ctx = {
    globalAlpha: 1, wheelSizes,
    getTransform: () => ({a:4,b:0,c:0,d:4,e:0,f:0}),
    save() { stack.push(this.globalAlpha); },
    restore() { assert.ok(stack.length, 'Unbalanced restore'); this.globalAlpha = stack.pop(); },
    createLinearGradient() { return { addColorStop(n) { assert.ok(n >= 0 && n <= 1); } }; },
    createPattern() { return { setTransform() {} }; },
    drawImage(image, ...coords) {
      assert.ok(image.width > 0 && image.height > 0);
      assert.ok(coords.every(Number.isFinite));
    },
    roundRect(x,y,w,h) { wheelSizes.push([w,h]); },
    assertBalanced() { assert.equal(stack.length, 0); assert.equal(this.globalAlpha, 1); },
  };
  for (const name of ['scale','translate','rotate','beginPath','closePath','moveTo','lineTo',
    'quadraticCurveTo','fill','stroke','clip','fillRect','rect','ellipse','arc','fillText','strokeText']) {
    ctx[name] = () => {};
  }
  return ctx;
}
const sandbox = vm.createContext({
  document: { createElement(kind) {
    assert.equal(kind,'canvas'); canvasCount++;
    const ctx = context2d();
    return {width:0,height:0,getContext:() => ctx};
  } },
  getTeamLogoImage: () => null,
});
const root = path.join(__dirname,'..');
const materials = fs.readFileSync(path.join(root,'public/car-materials.js'),'utf8')
  .replace(/^export /gm,'');
const renderer = fs.readFileSync(path.join(root,'public/canvas.js'),'utf8')
  .replace(/^import .*;\r?\n/gm,'').replace('export class CircuitRenderer','class CircuitRenderer');
vm.runInContext(`"use strict";\n${materials}\n${renderer}\nglobalThis.Renderer=CircuitRenderer;globalThis.surfaces=getCarSurfaces;`,sandbox);
const geometry = Object.freeze({...JSON.parse(fs.readFileSync(path.join(root,'public/car_geometry.json'))),world_units_per_m:3.2});
const draw = Object.create(sandbox.Renderer.prototype);
draw.track = Object.freeze({car_geometry:geometry});
draw.tick = Object.freeze({player_team_id:'ferrari'});
draw.selectedDriverId = 'selected';
const teams = ['mercedes','ferrari','redbull','mclaren','racingbulls','alpine','audi','haas','williams','aston','cadillac','custom'];
for (const tid of teams) {
  for (const variation of [0,1,2,3]) {
    const car = Object.freeze({id:variation === 1 ? 'selected' : 'test',tid,num:44,tcol:'#d32030',
      scol:'#dce5f0',helm:'#ffdd00',comp:variation === 2 ? 'INTER' : variation === 3 ? 'WET' : 'MEDIUM',
      wear:variation === 3 ? 80 : 10,steer:.21,dnf:variation === 3,elim:variation === 1,
      dmg:variation === 2 ? 60 : 0,dmg_side:'LEFT',braking:variation === 1,
      aero:variation === 2 ? 'STRAIGHT' : 'CORNER',kph:220,ovt:variation === 2});
    const before = JSON.stringify(car), ctx = context2d();
    draw._drawSingleCar(ctx,100,200,.5,car,1000);
    assert.equal(JSON.stringify(car),before,'Renderer mutated telemetry');
    ctx.assertBalanced();
    assert.equal(ctx.wheelSizes.length,4);
    for (let i=0;i<4;i++) {
      const axle=i<2?'front':'rear';
      assert.equal(ctx.wheelSizes[i][0],geometry[`${axle}_tyre_diameter_m`]*geometry.world_units_per_m);
      assert.equal(ctx.wheelSizes[i][1],geometry[`${axle}_tyre_width_m`]*geometry.world_units_per_m);
    }
    const warmed = canvasCount;
    draw._drawSingleCar(context2d(),100,200,.5,car,2000);
    assert.equal(canvasCount,warmed,'Repeated frames rebuilt material canvases');
  }
}
const paint = Object.freeze({body:'#123456',pod:'#234567',noseTip:'#345678',stripe:'#ffffff'});
const a=sandbox.surfaces(paint,'test',1,false,'MEDIUM',10);
const b=sandbox.surfaces(paint,'test',1,false,'MEDIUM',10);
assert.equal(a.body,b.body);
assert.equal(a.floor,b.floor);
assert.notEqual(a.rubber,sandbox.surfaces(paint,'test',1,false,'WET',10).rubber);
assert.notEqual(a.rubber,sandbox.surfaces(paint,'test',1,false,'MEDIUM',90).rubber);
assert.notEqual(a.body,sandbox.surfaces(paint,'test',2,false,'MEDIUM',10).body);
const small=sandbox.surfaces(paint,'test',1,false,'MEDIUM',10,2);
assert.ok(small.body.width<a.body.width);
assert.equal(small.body,sandbox.surfaces(paint,'test',1,false,'MEDIUM',10,2).body);
console.log('Car visual checks passed: 12 liveries, damage, wet/worn tyres, immutable telemetry, wheel dimensions, balanced drawing state, and cached materials.');
