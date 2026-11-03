import concurrent.futures,json,sys
from pathlib import Path
from fetch_circuit_documents import EVENTS,fetch,ROOT
sys.path.insert(0,str(Path(__file__).parent/'pdf_tools'))
import fitz,re
items=[(k,('Spanish Grand Prix' if k=='barcelona' else v[0],2025)) for k,v in EVENTS.items() if k!='madrid']
results=[]
with concurrent.futures.ThreadPoolExecutor(4) as pool:
    futures={pool.submit(fetch,item):item[0] for item in items}
    for future in concurrent.futures.as_completed(futures):
        tid=futures[future]
        try:
            record=future.result();doc=fitz.open(ROOT/record['pdf'])
            text=' '.join(p.get_text() for p in doc)
            match=re.search(r'Pole\s+(LHS|RHS)',text,re.I)
            record['pole_side']=match.group(1).upper() if match else None
            results.append(record);print(tid,record['pole_side'],flush=True)
        except Exception as exc:print('FAILED',tid,str(exc),flush=True)
(ROOT/'circuit_maps_2026/pole_reference_manifest.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
