// Sample only the selected geometry. Source SVGs remain unchanged.
const fs=require('fs');
const {chromium}=require('C:/Users/sidne/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const selectors={
'01_australia_albert_park.svg':[0],
'02_china_shanghai.svg':['path3612','path3614'],
'03_japan_suzuka.svg':['path3610','path3874'],
'04_bahrain_sakhir.svg':['path4003','path4820'],
'05_saudi_arabia_jeddah.svg':[12],
'06_usa_miami.svg':[0],
'07_canada_montreal.svg':[0],
'08_monaco.svg':['path4475','path4477','path4351'],
'09_spain_barcelona.svg':['path3965','path991'],
'10_austria_spielberg.svg':['path2746','path2748','path2750','path1271','path1265','path1273'],
'11_great_britain_silverstone.svg':['path2552-7','path3343-4'],
'12_belgium_spa.svg':['path2840','path2842','path2907'],
'13_hungary_hungaroring.svg':['path2406','path3179'],
'14_netherlands_zandvoort.svg':[0],
'15_italy_monza.svg':['path3113','path3115'],
'16_spain_madrid.svg':['path1','path3115'],
'17_azerbaijan_baku.svg':['path1403','path837'],
'18_singapore_marina_bay.svg':['path4158','path4928'],
'19_usa_austin.svg':['path3774','path3770','path3780','path3772','path3776'],
'20_mexico_mexico_city.svg':['Graphic 5','Graphic 8'],
'21_brazil_interlagos.svg':['path2840','path2842'],
'22_usa_las_vegas.svg':['path5483'],
'23_qatar_lusail.svg':['path2406','path3178'],
};
(async()=>{const browser=await chromium.launch({channel:'msedge',headless:true});const page=await browser.newPage();const out={};
for(const [file,ids] of Object.entries(selectors)){
 await page.setContent(fs.readFileSync('circuit_maps_2026/svg/'+file,'utf8'));
 out[file]=await page.evaluate(ids=>{
  const all=[...document.querySelectorAll('path,polyline,polygon,line')];
  const sample=(el,matrix)=>{const length=el.getTotalLength(),points=[];const n=Math.min(2000,Math.max(20,Math.ceil(length/3)));for(let i=0;i<=n;i++){const p=el.getPointAtLength(length*i/n),q=new DOMPoint(p.x,p.y).matrixTransform(matrix);points.push([q.x,q.y]);}return points;};
  const paths=ids.map(id=>{const el=typeof id==='number'?all[id]:document.getElementById(id);let parts=(el.getAttribute('d')||'').match(/[Mm][^Mm]*/g)||[];
   let last=[0,0];const subpaths=parts.map((d,i)=>{const p=document.createElementNS('http://www.w3.org/2000/svg','path');if(i>0&&d[0]==='m')d='M '+last.join(' ')+' '+d; p.setAttribute('d',d);document.querySelector('svg').appendChild(p);last=[p.getPointAtLength(p.getTotalLength()).x,p.getPointAtLength(p.getTotalLength()).y];const pts=sample(p,el.getCTM());p.remove();return pts;});
   return {id,points:sample(el,el.getCTM()),subpaths};});
  const flags=[...document.querySelectorAll('rect,path,polygon')].filter(el=>getComputedStyle(el).fill.startsWith('url(')&&!el.closest('defs')).map(el=>{const b=el.getBBox(),p=new DOMPoint(b.x+b.width/2,b.y+b.height/2).matrixTransform(el.getCTM());return [p.x,p.y];});
  return {paths,flags};
 },ids);console.log(file,out[file].paths.map(p=>[p.id,p.subpaths.map(s=>s.length)]),out[file].flags);
}
fs.writeFileSync('scratch/selected_reference_paths.json',JSON.stringify(out));await browser.close();})().catch(e=>{console.error(e);process.exit(1)});
