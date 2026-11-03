"""Bake returning tracks from retained geographic routes and OSM pit roads.

Uses the existing authoring dependencies (NumPy/SciPy/Pillow). No runtime deps.
FIA 2021 landmarks are baselines, not claims about unpublished 2027 overlays.
"""
import json, math, sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent/'pdf_tools'))
import numpy as np
from scipy import ndimage, optimize
from scipy.spatial import cKDTree
from PIL import Image, ImageDraw
from register_circuit_references import resample, project, xf

ROOT=Path(__file__).resolve().parents[1]
# Landmark positions on the retained, rendered FIA drawings. Corner numbers
# identify the real turn sequence, including multi-apex turns counted once.
CONFIG={
 'portugal':dict(location='Portimão',year=2021,width=14,pole=-1,
  pit_ways=[157790380],start=(432,703),control=(465,800),
  corners=[(308,378),(398,315),(489,347),(422,417),(529,769),(550,629),(494,482),(552,410),(607,630),(736,715),(750,775),(616,840),(610,959),(712,878),(593,1074)]),
 'turkey':dict(location='Istanbul',year=2021,width=14,pole=1,
  pit_ways=[295742111],start=(356,908),control=(242,937),
  corners=[(471,856),(511,723),(704,680),(716,604),(791,588),(781,540),(570,424),(803,359),(475,360),(487,409),(401,661),(85,860),(123,884),(134,940)]),
 'malaysia':dict(location='Sepang',year=2026,width=16,pole=-1,
  pit_ways=[23410526,144359483],start=(496,872),control=(582,873),
  corners=[(95,847),(172,820),(164,640),(532,494),(631,747),(784,698),(974,908),(936,982),(573,1004),(634,1072),(575,1220),(382,1066),(266,1093),(165,1014),(850,899)]),
}

def register(main, im, corner_hints):
    rgb=np.array(im);yy,xx=np.indices(rgb.shape[:2])
    hints=np.array(corner_hints);lo=hints.min(axis=0)-24;hi=hints.max(axis=0)+24
    mask=(rgb.max(axis=2)-rgb.min(axis=2)<22)&(rgb.mean(axis=2)>90)&(rgb.mean(axis=2)<235)
    mask&=(xx>lo[0])&(xx<hi[0])&(yy>lo[1])&(yy<hi[1])
    tree=cKDTree(np.column_stack(np.nonzero(mask))[:,::-1]);p=resample(main,600)
    center=(lo+hi)/2;span=hi-lo
    def residual(v):return tree.query(xf(p,v))[0]
    trials=[]
    for angle in range(0,360,3):
        r=xf(p,[1,angle,0,0]);scale=min(span/np.ptp(r,axis=0));pos=center-(r.min(axis=0)+r.max(axis=0))*.5*scale
        v=[scale,angle,*pos];trials.append((np.mean(np.minimum(residual(v),50)**2),v))
    fits=[]
    for _,v in sorted(trials,key=lambda t:t[0])[:5]:
        fit=optimize.least_squares(residual,v,max_nfev=200,diff_step=.001,loss='soft_l1',f_scale=3)
        fits.append((np.mean(residual(fit.x)**2),fit.x))
    return min(fits,key=lambda t:t[0])

def stitch(parts):
    result=parts.pop(0)
    while parts:
        choices=[(np.linalg.norm(result[-1]-p[0 if not rev else -1]),i,rev)
                 for i,p in enumerate(parts) for rev in (False,True)]
        d,i,rev=min(choices);p=parts.pop(i)
        if rev:p=p[::-1]
        result=np.vstack((result,p))
    return result

def build():
    geo=json.loads((ROOT/'circuit_maps_2026/geographic/f1-circuits.geojson').read_text(encoding='utf-8'))
    output=ROOT/'sim/track_layouts.json';layouts=json.loads(output.read_text(encoding='utf-8'))
    audit={};folder=ROOT/'circuit_maps_2026/future';folder.mkdir(exist_ok=True)
    for tid,c in CONFIG.items():
        coords=next(f['geometry']['coordinates'] for f in geo['features'] if f['properties']['Location']==c['location'])
        origin=np.mean(coords,axis=0);main=resample(project(coords,origin),4000)
        main=ndimage.gaussian_filter1d(main,1.2,axis=0,mode='wrap')
        imgpath=ROOT/(f'scratch/fia_review/{tid}_circuit.png' if tid!='malaysia' else 'circuit_maps_2026/png/supplement_malaysia_sepang_fia_circuit.png')
        im=Image.open(imgpath).convert('RGB');error,v=register(main,im,c['corners'])
        projected=xf(main,v);tree=cKDTree(projected)
        control=int(tree.query(c['control'])[1]);main=np.roll(main,-control,axis=0)
        projected=xf(main,v);tree=cKDTree(projected)
        markers=[int(tree.query(p)[1]) for p in c['corners']]
        if markers!=sorted(markers):
            main=np.vstack((main[0],main[:0:-1]));projected=xf(main,v);tree=cKDTree(projected)
            markers=[int(tree.query(p)[1]) for p in c['corners']]
        if markers!=sorted(markers):raise ValueError(f'{tid}: wrong turn sequence {markers}')
        start=int(tree.query(c['start'])[1])/4000
        if start>.5:start-=1
        elements=json.loads((ROOT/f'circuit_maps_2026/osm/{tid}.json').read_text(encoding='utf-8'))['elements']
        if not c['pit_ways']:
            c['pit_ways']=[e['id'] for e in elements if e.get('tags',{}).get('highway')=='raceway' and 'pit' in e.get('tags',{}).get('name','').lower()]
        roads=[project([[g['lon'],g['lat']] for g in e['geometry']],origin) for wid in c['pit_ways'] for e in elements if e['id']==wid and e['type']=='way']
        pit=stitch(roads);tree=cKDTree(main);entry,exit=tree.query(pit[[0,-1]])[1]
        if (exit-entry)%4000>2000:pit=pit[::-1];entry,exit=exit,entry
        pit[0]=main[entry];pit[-1]=main[exit];pit=resample(pit,600,False)
        pit=ndimage.gaussian_filter1d(pit,.65,axis=0,mode='nearest');pit[0]=main[entry];pit[-1]=main[exit]
        # Select the longest straight portion for 11 garages, leaving join room.
        angles=np.unwrap(np.arctan2(*np.gradient(pit,axis=0)[:,::-1].T));best=(0,0,0)
        for a in range(20,540):
            b=a+1
            while b<580 and abs(angles[b]-angles[a])<math.radians(4):b+=1
            best=max(best,(b-a,a,b))
        _,a,b=best;garages=[(a+(b-a)*.12)/599,(a+(b-a)*.88)/599]
        shift=np.array([500,325])-(main.min(axis=0)+main.max(axis=0))*.5
        url=('https://www.fia.com/sites/default/files/doc_1_-_2021_'+('portuguese' if tid=='portugal' else 'turkish')+'_grand_prix_-_circuit_map'+('_1' if tid=='portugal' else '')+'.pdf')
        pdf=f'circuit_maps_2026/fia_reference/{tid}_2021.pdf'
        if tid=='malaysia':
            pdf='circuit_maps_2026/fia_pdf/supplement_malaysia_sepang.pdf'
            url='https://www.fia.com/system/files/decision-document/2026_bahrain_grand_prix_in_malaysia_-_competition_notes_-_circuit_map_pit_lane_drawing_emergency_exits_map_and_red_zone.pdf'
        layouts[tid]=dict(points=np.round(main+shift,4).tolist(),pit_points=np.round(pit+shift,4).tolist(),
            width_profile_m=[c['width']]*4000,corner_count=len(markers),
            corner_markers=[dict(number=i+1,fraction=k/4000) for i,k in enumerate(markers)],
            pit_entry_fraction=int(entry)/4000,pit_exit_fraction=int(exit)/4000,start_line_fraction=start,
            grid_slot_pitch_m=8,pole_side=c['pole'],pit_tunnel_u=None,garage_u_range=garages,
            source='circuit_maps_2026/geographic/f1-circuits.geojson',reference_pdf=pdf,reference_year=c['year'],reference_url=url,
            pit_reference='OpenStreetMap ways '+','.join(map(str,c['pit_ways'])),
            width_note='Nominal constant width; local road boundaries have not been surveyed.',
            accuracy_note='Geographic centerline and independent OSM pit roads. FIA baseline supplies turn sequence and approximate start/control landmarks. Future event overlays, widths and garage allocations are simulation estimates.')
        draw=ImageDraw.Draw(im);draw.line([tuple(p) for p in projected]+[tuple(projected[0])],fill='magenta',width=2)
        draw.line([tuple(p) for p in xf(pit,v)],fill='red',width=3)
        for label,p in [('START',projected[round(start*4000)%4000]),('CONTROL',projected[0])]:
            draw.ellipse((p[0]-5,p[1]-5,p[0]+5,p[1]+5),fill='green');draw.text(tuple(p),label,fill='green')
        im.save(folder/f'{tid}_reference_overlay.png')
        audit[tid]=dict(reference_year=c['year'],fit_rms_px=round(math.sqrt(error),2),pit_ways=c['pit_ways'],
            pit_length_m=round(np.linalg.norm(np.diff(pit,axis=0),axis=1).sum()),start_fraction=start,turns=len(markers))
        print(tid,audit[tid],flush=True)
    output.write_text(json.dumps(layouts,separators=(',',':')),encoding='utf-8')
    (folder/'geometry_audit.json').write_text(json.dumps(audit,indent=2),encoding='utf-8')

if __name__=='__main__':build()
