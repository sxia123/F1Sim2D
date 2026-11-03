"""Locate and label black start-line symbols beside each FIA pit straight."""
from audit_geographic_pits import *
from scipy import ndimage
reg=json.loads((ROOT/'scratch/fia_registration/registration.json').read_text())
# Reviewed alternate fits: the older drawings' corner labels include legend glyphs.
reg['brazil']['transform']=[.920,.227,687.204,816.108]
reg['abudhabi']['transform']=[.619,1.139,727.449,1008.922]

def stitch(roads):
    parts=[p.copy() for p in roads]
    result=parts.pop(0)
    while parts:
        choices=[]
        for i,p in enumerate(parts):
            for end in (False,True):
                for rev in (False,True):
                    near=result[0] if end else result[-1]
                    endpoint=p[-1] if (end!=rev) else p[0]
                    choices.append((np.linalg.norm(near-endpoint),i,end,rev))
        dist,i,prepend,rev=min(choices);p=parts.pop(i)
        if rev:p=p[::-1]
        result=np.vstack((p,result)) if prepend else np.vstack((result,p))
    return result

if __name__=='__main__':
    folder=ROOT/'scratch/grid_landmarks';folder.mkdir(exist_ok=True)
    contact=Image.new('RGB',(2400,2400),'white');found={}
    for i,tid in enumerate(LOCATIONS):
        main,origin=geographic(tid);v=reg[tid]['transform'];q=xf(resample(main,3000),v);tree=cKDTree(q)
        roads=osm(tid,origin);pit=stitch([e['points'] for e in roads if e['id'] in PIT_WAYS[tid]])
        pit_px=xf(pit,v);a,b=tree.query(pit_px[[0,-1]])[1]
        # Select the shorter start/finish portion between pit connections.
        if (b-a)%3000>1500:a,b=b,a
        img=Image.open(ROOT/f'scratch/fia_review/{tid}_circuit.png').convert('RGB');rgb=np.array(img)
        mask=rgb.max(axis=2)<80
        lab,n=ndimage.label(mask)
        candidates=[];draw=ImageDraw.Draw(img)
        for label,sl in enumerate(ndimage.find_objects(lab),1):
            if sl is None:continue
            y,x=sl;w=x.stop-x.start;h=y.stop-y.start
            if w*h<30 or w*h>1200:continue
            yy,xx=np.nonzero(lab[sl]==label);area=len(xx)
            if area<20 or area>550:continue
            coords=np.column_stack((xx+x.start,yy+y.start));center=coords.mean(axis=0)
            eig=np.linalg.eigvalsh(np.cov(coords.T));ratio=math.sqrt(eig[-1]/max(eig[0],.1))
            if ratio<2.4:continue
            d,k=tree.query(center)
            if d/v[0]>80 or (k-a)%3000>(b-a)%3000:continue
            j=len(candidates);candidates.append({'point':center.tolist(),'area':area,'ratio':ratio,'fraction':k/3000,'distance_m':d/v[0]})
            draw.rectangle([x.start-3,y.start-3,x.stop+3,y.stop+3],outline='magenta',width=2)
            draw.text((x.start,y.start-15),str(j),fill='magenta')
        found[tid]=candidates
        lo=np.minimum(pit_px.min(axis=0),q[[a,b]].min(axis=0))-100;hi=np.maximum(pit_px.max(axis=0),q[[a,b]].max(axis=0))+100
        crop=img.crop((max(0,int(lo[0])),max(0,int(lo[1])),min(img.width,int(hi[0])),min(img.height,int(hi[1]))))
        crop_size=crop.size;crop.thumbnail((590,370));reg[tid]['crop']={'lo':np.maximum(lo,0).astype(int).tolist(),'scale':crop.width/crop_size[0]}
        contact.paste(crop,((i%4)*600,(i//4)*400+25));ImageDraw.Draw(contact).text(((i%4)*600+5,(i//4)*400+5),tid,fill='black')
        img.save(folder/f'{tid}.png')
        print(tid,[(j,round(c['area']),round(c['ratio'],1),round(c['fraction'],3)) for j,c in enumerate(candidates)],flush=True)
    contact.save(folder/'starts.png')
    (folder/'candidates.json').write_text(json.dumps(found),encoding='utf-8')
    (ROOT/'scratch/fia_registration/registration.json').write_text(json.dumps(reg),encoding='utf-8')
