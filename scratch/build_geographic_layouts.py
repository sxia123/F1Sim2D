"""Bake geographic GP routes, pit roads, FIA landmarks and spatial width data.

Authoring dependencies live in scratch/pdf_tools; runtime needs only stdlib.
Sources, dates and uncertainty are preserved with every circuit.
"""
from find_grid_landmarks import *
from scipy import ndimage,optimize

# Coordinates in the reviewed 600 x 400 start/control-line contact panels.
GRID_HINTS={
 'australia':(132,198,146,162), 'china':(268,166,354,184),
 'japan':(129,212,119,145), 'bahrain':(35,174,53,279),
 'saudi':(220,157,306,230), 'miami':(354,135,243,100),
 'canada':(137,212,131,225), 'monaco':(16,123,71,120),
 'barcelona':(111,218,153,184), 'austria':(296,235,370,245),
 'britain':(64,172,38,210), 'belgium':(83,184,153,245),
 'hungary':(254,298,295,282), 'netherlands':(98,173,93,230),
 'italy':(38,154,74,240), 'madrid':(322,220,425,183),
 'azerbaijan':(172,173,153,219), 'singapore':(187,155,196,250),
 'usa':(318,242,166,220), 'mexico':(35,231,52,275),
 'brazil':(48,232,64,230), 'vegas':(214,238,166,266),
 'qatar':(88,182,144,253), 'abudhabi':(188,293,134,272),
}
TUM=dict(zip(['usa','hungary','barcelona','australia','mexico','canada','italy','bahrain','brazil','china','britain','belgium','austria','japan','abudhabi','netherlands'],['Austin','Budapest','Catalunya','Melbourne','MexicoCity','Montreal','Monza','Sakhir','SaoPaulo','Shanghai','Silverstone','Spa','Spielberg','Suzuka','YasMarina','Zandvoort']))
DEFAULT_WIDTHS=dict(zip(LOCATIONS,[11,13,10,13,12,12,10,10,11,12,12,10,10,10,10,13.4,9,9,13,14,10,13,12,12]))
FIA=json.loads((ROOT/'circuit_maps_2026/fia_reference_manifest.json').read_text())
FIA={v['id']:v for v in FIA}
backup=ROOT/'scratch/pre_accuracy_layouts.json'
if not backup.exists():backup.write_bytes((ROOT/'sim/track_layouts.json').read_bytes())
OLD=json.loads(backup.read_text())

def length(p,closed=False):
    return np.linalg.norm(np.diff(np.vstack((p,p[0])) if closed else p,axis=0),axis=1).sum()

def align(source,target):
    """Similarity registration used only to transfer external width/turn data."""
    p=resample(source,350);q=resample(target,1800);tree=cKDTree(q)
    center=(q.min(axis=0)+q.max(axis=0))*.5;span=np.ptp(q,axis=0)
    def resid(v):return tree.query(xf(p,v))[0]
    trials=[]
    for angle in range(0,360,10):
        r=xf(p,[1,angle,0,0]);scale=min(span/np.ptp(r,axis=0));pos=center-(r.min(axis=0)+r.max(axis=0))*.5*scale
        v=[scale,angle,*pos];trials.append((np.mean(np.minimum(resid(v),70)**2),v))
    best=[]
    for _,v in sorted(trials,key=lambda t:t[0])[:3]:
        fit=optimize.least_squares(resid,v,max_nfev=100,diff_step=.001,loss='soft_l1',f_scale=5,
            bounds=([v[0]*.85,v[1]-18,v[2]-200,v[3]-200],[v[0]*1.15,v[1]+18,v[2]+200,v[3]+200]))
        best.append((np.mean(resid(fit.x)**2),fit.x))
    return min(best,key=lambda t:t[0])

def widths(tid,main,origin):
    base=DEFAULT_WIDTHS[tid];out=np.full(len(main),base,dtype=float);source='FIA licensed reference width; local boundary variation unavailable'
    if tid=='madrid':return out,'existing nominal width; no published boundary survey available'
    if tid in TUM:
        data=np.loadtxt(ROOT/f'circuit_maps_2026/width_reference/{TUM[tid]}.csv',delimiter=',')
        if np.ptp(data[:,2:].sum(axis=1))<1:
            return out,'FIA licensed reference width; discarded constant external placeholder'
        pts=data[:,:2]*[1,-1]
        error,v=align(pts,main);pts=xf(pts,v);dist,idx=cKDTree(pts).query(main)
        valid=dist<12
        out[valid]=np.clip(data[idx[valid],2:].sum(axis=1),base,24)
        source='TUMFTM satellite width variation above FIA reference width; matched within 12m of unchanged roadway; FIA reference elsewhere'
        print('  width fit',tid,round(math.sqrt(error),1),round(valid.mean(),2),flush=True)
    # Prefer explicit OSM road-width tags where the closest way is the GP road.
    roads=[e for e in osm(tid,origin) if e['tags'].get('highway')=='raceway' and e['id'] not in PIT_WAYS[tid] and e['tags'].get('width')]
    for e in roads:
        try:w=float(e['tags']['width'])
        except ValueError:continue
        if not 7<=w<=24:continue
        p=resample(e['points'],max(2,int(length(e['points'])/4)),False)
        dist,_=cKDTree(p).query(main)
        out[dist<6]=w
    if tid=='japan':out=np.clip(out,10,16) # Suzuka's published course-width range.
    return ndimage.gaussian_filter1d(out,3,mode='wrap'),source

def garage_range(pit):
    p=resample(pit,600,False);step=length(pit)/599
    tangent=np.gradient(p,axis=0);angles=np.unwrap(np.arctan2(tangent[:,1],tangent[:,0]));best=(0,0,0)
    for a in range(0,540,3):
        b=a+1
        while b<599 and abs(angles[b]-angles[a])<math.radians(5):b+=1
        if b-a>best[0]:best=(b-a,a,b)
    _,a,b=best
    # Leave generous space for pit-entry and exit acceleration lanes.
    return [(a+(b-a)*.12)/599,(a+(b-a)*.88)/599]

def build():
    layouts={};audit={};folder=ROOT/'scratch/accurate_review';folder.mkdir(exist_ok=True)
    contact=Image.new('RGB',(2400,2100),'white')
    reg=json.loads((ROOT/'scratch/fia_registration/registration.json').read_text())
    for i,tid in enumerate(LOCATIONS):
        raw,origin=geographic(tid);main=resample(raw,4000)
        if tid=='singapore':main=main[::-1]
        main=ndimage.gaussian_filter1d(main,1.2,axis=0,mode='wrap')
        v=reg[tid]['transform'];q=xf(main,v);tree=cKDTree(q)
        crop=reg[tid]['crop'];hints=np.array(GRID_HINTS[tid],float).reshape(2,2)
        hints[:,1]-=25;hints=hints/crop['scale']+crop['lo']
        start,control=tree.query(hints)[1]
        # Timing origin is explicit; it is never moved to fit the grid.
        main=np.roll(main,-int(control),axis=0);q=np.roll(q,-int(control),axis=0)
        start_f=((int(start)-int(control))%4000)/4000
        if start_f>.5:start_f-=1
        nums=reg[tid]['corners'];markers=[]
        if tid=='vegas':
            # The legend also contains a larger blue "15"; select the actual
            # T15 label at the end of the Strip rather than the legend glyph.
            nums={**nums,'15':[201.65908,1475.38678]}
        if len(nums)==COUNTS[tid]:
            tree=cKDTree(q)
            for n in range(1,COUNTS[tid]+1):
                candidates=[nums[str(n)]]
                for span in meta[tid]['spans']:
                    c=span['color'];red=(c>>16)&255;blue=c&255;green=(c>>8)&255
                    if span['text'].strip()==str(n) and blue>140 and blue>red*1.3 and blue>green*1.25:
                        box=span['bbox'];candidates.append([box[0]+box[2],box[1]+box[3]])
                # Legend glyphs can be larger than actual corner labels. The
                # relevant label is the one beside the GP roadway.
                point=min(candidates,key=lambda point:tree.query(point)[0])
                idx=tree.query(point)[1]
                markers.append({'number':n,'fraction':float(idx/4000)})
        else:
            old=OLD[tid];_,transform=align(old['points'],main)
            transformed=xf(np.array(old['points']),transform);tree=cKDTree(main)
            for c in old['corner_markers']:
                point=transformed[int(c['fraction']*len(transformed))%len(transformed)]
                markers.append({'number':c['number'],'fraction':float(tree.query(point)[1]/4000)})
        if len(markers)!=COUNTS[tid]:raise ValueError(f'Missing official turns: {tid}')
        roads=osm(tid,origin);parts=[e for e in roads if e['id'] in PIT_WAYS[tid]]
        pit=stitch([e['points'] for e in parts]);tree=cKDTree(main)
        entry,exit=tree.query(pit[[0,-1]])[1]
        if (exit-entry)%4000>2000:pit=pit[::-1];entry,exit=exit,entry
        pit[0]=main[entry];pit[-1]=main[exit]
        pit=resample(pit,600,False)
        pit=ndimage.gaussian_filter1d(pit,.65,axis=0,mode='nearest')
        pit[0]=main[entry];pit[-1]=main[exit]
        w,width_source=widths(tid,main,origin)
        # Keep source metres with a uniform scale; the runtime calibrates lap length.
        shift=np.array([500,325])-(main.min(axis=0)+main.max(axis=0))*.5
        tunnel=[]
        for e in parts:
            if e['tags'].get('tunnel')=='yes':
                idx=cKDTree(pit).query(e['points']) [1]
                tunnel.extend(idx.tolist())
        u_tunnel=[max(0,(min(tunnel)-2)/599),min(1,(max(tunnel)+2)/599)] if tunnel else None
        # Grid pole sides come from explicit FIA pit drawings, never inferred at runtime.
        pole_file=ROOT/'circuit_maps_2026/pole_reference_manifest.json'
        poles={r['id']:r['pole_side'] for r in json.loads(pole_file.read_text())} if pole_file.exists() else {}
        pole=1 if poles.get(tid)=='RHS' or tid in {'vegas','abudhabi'} else -1
        layout={'points':np.round(main+shift,4).tolist(),'pit_points':np.round(pit+shift,4).tolist(),
          'width_profile_m':np.round(w,3).tolist(),'corner_count':COUNTS[tid],'corner_markers':markers,
          'pit_entry_fraction':float(entry/4000),'pit_exit_fraction':float(exit/4000),
          'start_line_fraction':start_f,'grid_slot_pitch_m':8.0,'pole_side':pole,
          'pit_tunnel_u':u_tunnel,'garage_u_range':garage_range(pit),
          'source':'circuit_maps_2026/geographic/f1-circuits.geojson',
          'reference_pdf':FIA[tid]['pdf'],'reference_year':FIA[tid]['year'],'reference_url':FIA[tid]['source_url'],
          'pit_reference':'OpenStreetMap ways '+','.join(str(e['id']) for e in parts),
          'width_note':width_source,'accuracy_note':'Geographic centerline and pit roads checked against FIA drawings. Diagram landmarks and satellite-derived widths have finite precision; nominal widths remain where no reliable boundary data is available.'}
        layouts[tid]=layout
        audit[tid]={'reference_year':layout['reference_year'],'start_fraction':round(start_f,4),
          'turns':len(markers),'pit_length_m':round(length(pit)),'width_range_m':[round(w.min(),1),round(w.max(),1)],
          'width_source':width_source,'pit_ways':PIT_WAYS[tid]}
        # Authoring overlay: geographic GP route and independent pit lane on the FIA page.
        im=Image.open(ROOT/f'scratch/fia_review/{tid}_circuit.png').convert('RGB');draw=ImageDraw.Draw(im)
        draw.line([tuple(p) for p in q]+[tuple(q[0])],fill='#ff00aa',width=2)
        pp=xf(pit,v);draw.line([tuple(p) for p in pp],fill='red',width=3)
        for text,point,color in [('START',q[(start-control)%4000],'green'),('CONTROL',q[0],'black')]:
            x,y=point;draw.ellipse((x-4,y-4,x+4,y+4),fill=color);draw.text((x+6,y),text,fill=color)
        im.save(folder/f'{tid}_overlay.png');im.thumbnail((590,340));contact.paste(im,((i%4)*600,(i//4)*350))
        print(tid,audit[tid],flush=True)
    (ROOT/'sim/track_layouts.json').write_text(json.dumps(layouts,separators=(',',':')),encoding='utf-8')
    (ROOT/'circuit_maps_2026/geometry_audit.json').write_text(json.dumps(audit,indent=2),encoding='utf-8')
    contact.save(folder/'overlays.png')

if __name__=='__main__':build()
