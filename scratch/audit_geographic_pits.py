"""Review geographic pit roads against the selected GP centerline."""
from register_circuit_references import *
PIT_WAYS={
 'australia':[28119448], 'china':[107371147,107371138], 'japan':[120917578], 'bahrain':[187123422],
 'saudi':[1121870473,1257884703,1257884704], 'miami':[1017340352], 'canada':[413000959],
 'monaco':[850261588], 'barcelona':[33742214,178416729,178416733], 'austria':[289111668],
 'britain':[227902927], 'belgium':[323851541], 'hungary':[231417580], 'netherlands':[38144527],
 'italy':[38168747], 'madrid':[1552567031], 'azerbaijan':[1513267145], 'singapore':[100484287],
 'usa':[514836373], 'mexico':[638504647,772763791], 'brazil':[33779109], 'vegas':[1223479152],
 'qatar':[196193732,1037707300], 'abudhabi':[176695253,176695254,176695255],
}

def osm(tid,origin):
    elems=json.loads((ROOT/f'circuit_maps_2026/osm/{tid}.json').read_text(encoding='utf-8'))['elements']
    out=[]
    for e in elems:
        if len(e.get('geometry',[]))<2 or 'nodes' not in e:continue
        coords=[[g['lon'],g['lat']] for g in e['geometry']]
        out.append({**e,'points':project(coords,origin)})
    return out

if __name__=='__main__':
    folder=ROOT/'scratch/geographic_review';folder.mkdir(exist_ok=True)
    contact=Image.new('RGB',(2400,2100),'white')
    for i,tid in enumerate(LOCATIONS):
        main,origin=geographic(tid);roads=osm(tid,origin);lo=main.min(axis=0);hi=main.max(axis=0)
        scale=min(1050/(hi[0]-lo[0]),750/(hi[1]-lo[1]));off=np.array([600,420])-(lo+hi)*.5*scale
        xf=lambda p:np.asarray(p)*scale+off
        im=Image.new('RGB',(1200,850),'white');draw=ImageDraw.Draw(im)
        sf=main[0];audit=[]
        for e in roads:
            p=e['points'];dist=np.linalg.norm(p-sf,axis=1).min()
            if e['id'] in PIT_WAYS[tid] or (e['tags'].get('highway')=='raceway'):
                selected=e['id'] in PIT_WAYS[tid]
                draw.line([tuple(q) for q in xf(p)],fill='red' if selected else '#c0c0c0',width=2)
                if selected or dist<250:
                    draw.text(tuple(xf(p[len(p)//2])),str(e['id']),fill='red' if selected else '#888888')
            if dist<100 and e['tags'].get('highway') in {'raceway','service','unclassified'}:
                audit.append({'id':e['id'],'dist':round(dist,1),'length':round(np.linalg.norm(np.diff(p,axis=0),axis=1).sum(),1),'tags':e['tags']})
        draw.line([tuple(q) for q in xf(main)]+[tuple(xf(main[0]))],fill='black',width=3)
        draw.ellipse(tuple([*(xf(main[0])-5),*(xf(main[0])+5)]),fill='blue')
        draw.text((10,10),tid,fill='black')
        im.save(folder/f'{tid}.png');im.thumbnail((590,340));contact.paste(im,((i%4)*600,(i//4)*350))
        (folder/f'{tid}_roads.json').write_text(json.dumps(audit,ensure_ascii=True,indent=2))
    contact.save(folder/'pits.png')
