"""Fit geographic centerlines to FIA drawing coordinates for authoring landmarks.

Only a similarity transform is permitted: no stretching either axis or moving
corners to accommodate a grid. The resulting registration is review material,
not a claim that the drawings are survey plans.
"""
import json,math,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent/'pdf_tools'))
import numpy as np
from scipy import ndimage,optimize
from scipy.spatial import cKDTree
from PIL import Image,ImageDraw

ROOT=Path(__file__).resolve().parents[1]
LOCATIONS=dict(zip(['australia','china','japan','bahrain','saudi','miami','canada','monaco','barcelona','austria','britain','belgium','hungary','netherlands','italy','madrid','azerbaijan','singapore','usa','mexico','brazil','vegas','qatar','abudhabi'],['Melbourne','Shanghai','Suzuka','Sakhir','Jeddah','Miami','Montreal','Monaco','Barcelona','Spielberg','Silverstone','Spa Francorchamps','Budapest','Zandvoort','Monza','Madrid','Baku','Singapore','Austin','Mexico City','Sao Paulo','Las Vegas','Lusail','Yas Marina']))
COUNTS=dict(zip(LOCATIONS,[14,16,18,15,27,19,14,19,14,10,18,19,14,14,11,22,20,19,20,17,15,17,16,16]))
geo=json.loads((ROOT/'circuit_maps_2026/geographic/f1-circuits.geojson').read_text(encoding='utf-8'))
meta=json.loads((ROOT/'scratch/fia_review/metadata.json').read_text())

def resample(p,n,closed=True):
    p=np.asarray(p,float)
    if closed and np.linalg.norm(p[0]-p[-1])>1e-7:p=np.vstack((p,p[0]))
    keep=np.r_[True,np.linalg.norm(np.diff(p,axis=0),axis=1)>1e-7];p=p[keep]
    c=np.r_[0,np.cumsum(np.linalg.norm(np.diff(p,axis=0),axis=1))]
    s=np.linspace(0,c[-1],n,endpoint=not closed)
    return np.column_stack([np.interp(s,c,p[:,k]) for k in range(2)])

def project(lonlat,origin):
    p=np.asarray(lonlat,float)
    return (p-np.array(origin))*[111195*math.cos(math.radians(origin[1])),-111195]

def geographic(tid):
    f=next(f for f in geo['features'] if f['properties']['Location']==LOCATIONS[tid])
    coords=f['geometry']['coordinates'];origin=np.mean(coords,axis=0).tolist()
    p=project(coords,origin)
    return p,origin

def xf(p,v):
    scale,angle,x,y=v
    a=math.radians(angle);rot=np.array([[math.cos(a),math.sin(a)],[-math.sin(a),math.cos(a)]])
    return p@rot*scale+np.array([x,y])

def corners(tid):
    out={}
    for s in meta[tid]['spans']:
        t=s['text'].strip();c=s['color'];r=(c>>16)&255;g=(c>>8)&255;b=c&255
        if t.isdigit() and 1<=int(t)<=COUNTS[tid] and b>140 and b>r*1.3 and b>g*1.25 and (box:=s['bbox'])[1]>150:
            box=s['bbox'];height=box[3]-box[1]
            if int(t) not in out or height>out[int(t)][0]:
                out[int(t)]=(height,np.array([(box[0]+box[2]),(box[1]+box[3])]))
    return {k:v[1] for k,v in out.items()}

if __name__=='__main__':
    result={}
    folder=ROOT/'scratch/fia_registration';folder.mkdir(exist_ok=True)
    for tid in LOCATIONS:
        p,origin=geographic(tid);q=resample(p,500)
        im=Image.open(ROOT/f'scratch/fia_review/{tid}_circuit.png').convert('RGB');rgb=np.array(im).astype(float)
        nums=corners(tid);marker=np.array(list(nums.values()))
        # Restrict to the track panel, excluding the page furniture.
        gray=(rgb.max(axis=2)-rgb.min(axis=2)<22)&(rgb.mean(axis=2)>75)&(rgb.mean(axis=2)<240)
        if len(marker):lo=marker.min(axis=0)-35;hi=marker.max(axis=0)+35
        else:lo=np.array([20,im.height*.25]);hi=np.array([im.width-20,im.height*.90])
        yy,xx=np.indices(gray.shape);gray&=(xx>lo[0])&(xx<hi[0])&(yy>lo[1])&(yy<hi[1])
        connected=ndimage.binary_closing(gray,iterations=2)
        lab,n=ndimage.label(connected);sizes=np.bincount(lab.ravel());sizes[0]=0
        mask=gray
        # Track is by far the longest connected grey feature.
        target=np.column_stack(np.nonzero(mask))[:,::-1]
        tree=cKDTree(target)
        if len(marker):
            center=(marker.min(axis=0)+marker.max(axis=0))*.5;span=np.ptp(marker,axis=0)
        else:
            center=(target.min(axis=0)+target.max(axis=0))*.5;span=np.ptp(target,axis=0)
        def residual(v):return tree.query(xf(q,v))[0]
        candidates=[]
        for angle in range(0,360,3):
            rotated=xf(q,[1,angle,0,0]);scale=min(span/np.ptp(rotated,axis=0))
            pos=center-(rotated.min(axis=0)+rotated.max(axis=0))*.5*scale
            v=[scale,angle,*pos];candidates.append((np.mean(np.minimum(residual(v),80)**2),v))
        trials=[]
        for _,v in sorted(candidates,key=lambda c:c[0])[:4]:
            fit=optimize.least_squares(residual,v,max_nfev=160,diff_step=.001,loss='soft_l1',f_scale=3,
                bounds=([v[0]*.8,v[1]-16,v[2]-120,v[3]-120],[v[0]*1.2,v[1]+16,v[2]+120,v[3]+120]))
            trials.append((np.mean(residual(fit.x)**2),fit.x))
        score,v=min(trials,key=lambda c:c[0])
        preview=im.copy();draw=ImageDraw.Draw(preview);coords=xf(resample(p,1400),v)
        draw.line([tuple(v) for v in coords]+[tuple(coords[0])],fill=(255,0,180),width=2)
        for k in range(0,len(coords),100):draw.text(tuple(coords[k]),str(k//100),fill='black')
        preview.save(folder/f'{tid}.png')
        Image.fromarray((mask*255).astype('uint8')).save(folder/f'{tid}_mask.png')
        result[tid]={'origin':origin,'transform':v.tolist(),'rms_px':math.sqrt(score),'corners':{str(k):x.tolist() for k,x in nums.items()}}
        print(tid,round(math.sqrt(score),2),np.round(v,3),len(nums),flush=True)
    (folder/'registration.json').write_text(json.dumps(result),encoding='utf-8')
