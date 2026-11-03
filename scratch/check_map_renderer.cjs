const fs=require('fs');
const {chromium}=require('C:/Users/sidne/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
(async()=>{
const browser=await chromium.launch({channel:'msedge',headless:true});
const page=await browser.newPage({viewport:{width:1250,height:850},deviceScaleFactor:1});
const errors=[];page.on('pageerror',e=>errors.push(e.message));
page.on('console',m=>{if(m.type()==='error')errors.push(m.text())});
await page.route('http://maps.test/**',async route=>{
 const name=new URL(route.request().url()).pathname;
 if(name==='/')return route.fulfill({contentType:'text/html',body:'<body style="margin:0;background:#0b0c12"><div style="width:1250px;height:850px"><canvas id="map"></canvas></div><script type="module">import {CircuitRenderer} from "/canvas.js";window.renderer=new CircuitRenderer(document.querySelector("canvas"));</script>'});
 if(['/canvas.js','/logos.js','/scenery.js'].includes(name))return route.fulfill({contentType:'application/javascript',body:fs.readFileSync('public'+name,'utf8')});
 return route.fulfill({status:204,body:''});
});
await page.goto('http://maps.test/');await page.waitForFunction(()=>window.renderer);
const wanted=process.argv[5]?.split(',');
const fixtures=JSON.parse(fs.readFileSync(process.argv[2]||'scratch/map_fixtures.json','utf8')).filter(f=>!wanted||wanted.includes(f.track.id));
const output=process.argv[3]||'scratch/map_review';
const detail=process.argv[4]||'pit_detail';
fs.mkdirSync(output,{recursive:true});
for(const f of fixtures){
 await page.evaluate(f=>{const r=window.renderer;r.setTrack(f.track);r.pushTick(f.tick);r.setCameraMode('full');r._render(performance.now(),1);},f);
 await page.screenshot({path:output+'/'+f.track.id+'.png'});
}
const details=(wanted || (detail==='grid_detail'?['australia','belgium','monaco','miami','madrid','vegas']:['britain','netherlands','abudhabi','madrid'])).filter(id=>fixtures.some(f=>f.track.id===id));
for(const id of details){
 const f=fixtures.find(f=>f.track.id===id);
 await page.evaluate(({f,detail})=>{
  const r=window.renderer;r.setTrack(f.track);r.pushTick(f.tick);
  if(detail==='grid_detail'){
   const xs=f.tick.cars.map(c=>c.x),ys=f.tick.cars.map(c=>c.y),pad=f.track.track_width_px*2;
   const bounds={min_x:Math.min(...xs)-pad,max_x:Math.max(...xs)+pad,min_y:Math.min(...ys)-pad,max_y:Math.max(...ys)+pad};
   r.track={...f.track,bounds};r.camX=(bounds.min_x+bounds.max_x)/2;r.camY=(bounds.min_y+bounds.max_y)/2;r.camZoom=1;r.setCameraMode('full');
  }else{r.setSelectedDriver(f.tick.cars[0].id);r.setCameraMode('selected');r._updateCamera(1);}
  r._render(performance.now(),1);
 },{f,detail});
 await page.screenshot({path:output+'/'+id+'_'+detail+'.png'});
}
console.log(JSON.stringify({rendered:fixtures.length,details:details.length,errors}));
await browser.close();if(errors.length)process.exit(1);
})().catch(e=>{console.error(e);process.exit(1)});
