const fs=require('fs');
const assert=require('assert/strict');
const {chromium}=require('C:/Users/sidne/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
(async()=>{
 const browser=await chromium.launch({channel:'msedge',headless:true});
 const page=await browser.newPage({viewport:{width:1000,height:600}});
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.route('http://scale.test/**',async route=>{
  const path=new URL(route.request().url()).pathname;
  if(path==='/')return route.fulfill({contentType:'text/html',body:'<canvas width="1000" height="600"></canvas><script type="module">import {CircuitRenderer} from "/canvas.js";window.CircuitRenderer=CircuitRenderer;</script>'});
  if(['/canvas.js','/logos.js'].includes(path))return route.fulfill({contentType:'application/javascript',body:fs.readFileSync('public'+path,'utf8')});
  return route.fulfill({status:204,body:''});
 });
 await page.goto('http://scale.test/');await page.waitForFunction(()=>window.CircuitRenderer);
 const fixture=JSON.parse(fs.readFileSync('scratch/grid_fixtures.json'))[0];
 const result=await page.evaluate(f=>{
  const canvas=document.querySelector('canvas'),ctx=canvas.getContext('2d');
  // Use the real drawing method without the animation loop or camera transform.
  const r=Object.create(window.CircuitRenderer.prototype);r.track=f.track;r.tick=null;r.selectedDriverId=null;
  const tyres=[],nose=[],rear=[];
  const rr=ctx.roundRect.bind(ctx),mt=ctx.moveTo.bind(ctx),fr=ctx.fillRect.bind(ctx);
  const pt=(x,y)=>new DOMPoint(x,y).matrixTransform(ctx.getTransform());
  ctx.roundRect=(x,y,w,h,...rest)=>{tyres.push({center:pt(x+w/2,y+h/2),a:pt(x,y),b:pt(x+w,y),c:pt(x,y+h)});rr(x,y,w,h,...rest)};
  ctx.moveTo=(x,y)=>{if(x===9.1&&y===0)nose.push(pt(x,y));mt(x,y)};
  ctx.fillRect=(x,y,w,h)=>{if(x===-8.35)rear.push(pt(x,0));fr(x,y,w,h)};
  const c={...f.tick.cars[0],ovt:false,boost:false,man:null,rech:true,braking:false,steer:.42,elim:false,dnf:false};
  r._drawSingleCar(ctx,0,0,0,c,0);
  const ppm=f.track.car_geometry.world_units_per_m;
  const distance=(a,b)=>Math.hypot(a.x-b.x,a.y-b.y)/ppm;
  return {length:(nose[0].x-rear[0].x)/ppm,nose:nose[0].x/ppm,rear:rear[0].x/ppm,
   wheelbase:(tyres[0].center.x-tyres[2].center.x)/ppm,
   tyres:tyres.map(t=>({diameter:distance(t.a,t.b),width:distance(t.a,t.c)}))};
 },fixture);
 // Canvas transforms use float precision internally; allow one micrometre.
 const near=(a,b)=>assert.ok(Math.abs(a-b)<1e-6,`${a} != ${b}`);
 const g=fixture.track.car_geometry;
 near(result.length,g.length_m);near(result.nose,g.length_m/2);near(result.rear,-g.length_m/2);
 near(result.wheelbase,g.wheelbase_m);assert.equal(result.tyres.length,4);
 result.tyres.forEach((t,i)=>{near(t.diameter,i<2?g.front_tyre_diameter_m:g.rear_tyre_diameter_m);near(t.width,i<2?g.front_tyre_width_m:g.rear_tyre_width_m)});
 assert.deepEqual(errors,[]);console.log(JSON.stringify({physicalRendererMeasurements:result,errors}));
 await browser.close();
})().catch(e=>{console.error(e);process.exit(1)});
