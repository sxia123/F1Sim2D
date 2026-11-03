// Isolated Chromium regression check. Does not open or modify a user browser profile.
const fs=require('node:fs');
const {chromium}=require('playwright');
const {createCanvas,loadImage}=require('@napi-rs/canvas');
(async()=>{
  const browser=await chromium.launch({headless:true,executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe'});
  try {
    const page=await browser.newPage({viewport:{width:1280,height:844},deviceScaleFactor:1});
    const errors=[];page.on('pageerror',e=>errors.push(e.message));
    await page.goto('file:///C:/Coding/F1Sim2D/scratch/scenery_standalone.html');
    await page.waitForFunction(()=>window.renderer?.track);
    let ids=await page.locator('select option').evaluateAll(opts=>opts.map(o=>o.value));
    if(process.argv[2])ids=ids.filter(id=>id===process.argv[2]);
    const sheet=createCanvas(2400,2400),sheetCtx=sheet.getContext('2d');
    let samples=0;
    for(let index=0;index<ids.length;index++) {
      const id=ids[index];await page.locator('select').selectOption(id);
      await page.waitForFunction(id=>window.renderer.track.id===id && window.renderer.scenery.cache?.key.startsWith(id+':'),id);
      const result=await page.evaluate(()=>{
        const r=window.renderer,t=r.track,b=t.bounds;
        r.camX=(b.min_x+b.max_x)/2;r.camY=(b.min_y+b.max_y)/2;r.camZoom=1;r._render(0,0);
        const start=performance.now();
        const c=r.scenery.cache;
        const pixels=c.canvas.getContext('2d').getImageData(0,0,c.canvas.width,c.canvas.height).data;
        let checked=0,failures=[];
        for(const [points,width,pit] of [[t.stations,t.track_width_px,false],[t.pit_points,t.pit_width_px,true]]) {
          for(let i=0;i<points.length;i++) {
            const p=points[i],x=pit?p[0]:p.x,y=pit?p[1]:p.y,next=points[(i+1)%points.length];
            let nx=pit?-(next[1]-y):p.nx,ny=pit?next[0]-x:p.ny;const len=Math.hypot(nx,ny)||1;nx/=len;ny/=len;
            for(const offset of [0,-(pit?width:p.width_px)/2,(pit?width:p.width_px)/2]) {
              const ix=Math.floor((x+nx*offset-c.left)*c.canvas.width/c.w),iy=Math.floor((y+ny*offset-c.top)*c.canvas.height/c.h);
              if(ix>=0&&iy>=0&&ix<c.canvas.width&&iy<c.canvas.height) {
                if(pixels[(iy*c.canvas.width+ix)*4+3]!==0)failures.push([pit,i,offset,pixels[(iy*c.canvas.width+ix)*4+3],x,y,ix,iy,{matrix:c.canvas.getContext('2d').getTransform().toJSON(),left:c.left,top:c.top,w:c.w,h:c.h,cw:c.canvas.width,ch:c.canvas.height}]);
                checked++;
              }
            }
          }
        }
        if(failures.length) {
          const f=failures[0],cx=c.canvas.getContext('2d'),fresh=document.createElement('canvas');
          fresh.width=c.canvas.width;fresh.height=c.canvas.height;
          const fc=fresh.getContext('2d');fc.fillRect(0,0,fresh.width,fresh.height);fc.setTransform(cx.getTransform());r.scenery.maskRoads(fc,t);
          r.scenery.maskRoads(cx,t);
          f.push({isolated:fc.getImageData(f[6],f[7],1,1).data[3],twice:cx.getImageData(f[6],f[7],1,1).data[3]});
        }
        const before=r.scenery.cache;r._render(0,0);
        if(before!==r.scenery.cache)throw Error('Cache not reused');
        // Zoom and camera changes rebuild at the appropriate resolution.
        const layer=new r.scenery.constructor(),canvas=document.createElement('canvas');canvas.width=800;canvas.height=600;
        const ctx=canvas.getContext('2d');layer.draw(ctx,t,{scale:.5,ox:0,oy:0},800,600,1);const first=layer.cache;
        layer.draw(ctx,t,{scale:1,ox:0,oy:0},800,600,1);if(layer.cache===first)throw Error('Zoom cache not rebuilt');
        const second=layer.cache;layer.draw(ctx,t,{scale:1,ox:-2000,oy:0},800,600,1);if(layer.cache===second)throw Error('Pan cache not rebuilt');
        return {checked,failures,ms:Math.round(performance.now()-start),trees:t.environment.trees.length,buildings:t.environment.buildings.length};
      });
      if(result.failures.length)throw Error(id+' scenery covers road: '+JSON.stringify(result.failures.slice(0,5)));
      samples+=result.checked;
      const png=await page.locator('canvas').screenshot();
      if(['australia','monaco','italy','bahrain','miami','vegas','saudi'].includes(id))fs.writeFileSync(`scratch/scenery_${id}.png`,png);
      sheetCtx.drawImage(await loadImage(png),index%4*600,Math.floor(index/4)*400,600,375);
      sheetCtx.fillStyle='#131b21';sheetCtx.fillRect(index%4*600,Math.floor(index/4)*400+375,600,25);
      sheetCtx.fillStyle='#eeeeee';sheetCtx.font='16px sans-serif';sheetCtx.fillText(id,index%4*600+12,Math.floor(index/4)*400+393);
      console.log(id,JSON.stringify(result));
    }
    if(errors.length)throw Error('Browser errors: '+errors.join('; '));
    if(ids.length===24)fs.writeFileSync('scratch/scenery_contact.png',sheet.toBuffer('image/png'));
    console.log('PASS:',ids.length,'circuits,',samples,'road/pit pixel samples; camera/cache checks; no browser errors');
  } finally {await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1});
