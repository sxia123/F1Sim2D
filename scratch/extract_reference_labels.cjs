const fs=require('fs');
const {chromium}=require('C:/Users/sidne/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
(async()=>{const browser=await chromium.launch({channel:'msedge',headless:true});const page=await browser.newPage();const result={};
for(const file of fs.readdirSync('circuit_maps_2026/svg')){
await page.setContent(fs.readFileSync('circuit_maps_2026/svg/'+file,'utf8'));
result[file]=await page.evaluate(()=>[...document.querySelectorAll('text,[aria-label]')].filter(e=>!e.closest('defs')).map(e=>{
const text=(e.getAttribute('aria-label')||e.textContent).trim();if(!/^\d{1,2}$/.test(text))return null;
const b=e.getBBox(),m=e.getCTM(),p=new DOMPoint(b.x+b.width/2,b.y+b.height/2).matrixTransform(m);
return {number:+text,point:[p.x,p.y]};}).filter(Boolean));}
fs.writeFileSync('scratch/reference_labels.json',JSON.stringify(result));await browser.close();console.log('Extracted reference turn-label positions.');})().catch(e=>{console.error(e);process.exit(1)});
