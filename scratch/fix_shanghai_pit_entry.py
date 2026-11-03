"""Rebake only Shanghai's pit route, including the actual T16 entry connector.

Uses the same projection/smoothing as build_geographic_layouts, leaving every
GP centerline, width, turn, grid and other circuit unchanged.
"""
from build_geographic_layouts import (
    ROOT, np, ndimage, geographic, resample, osm, stitch, PIT_WAYS, garage_range,
)
from scipy.spatial import cKDTree
import json
import math


def repair():
    path=ROOT/'sim/track_layouts.json'
    layouts=json.loads(path.read_text())
    track=layouts['china']
    old=json.loads(json.dumps(track))
    raw,origin=geographic('china')
    geographic_main=ndimage.gaussian_filter1d(resample(raw,4000),1.2,axis=0,mode='wrap')
    shift=np.array([500,325])-(geographic_main.min(axis=0)+geographic_main.max(axis=0))*.5
    main=np.asarray(track['points'])
    parts=[e for e in osm('china',origin) if e['id'] in PIT_WAYS['china']]
    if {e['id'] for e in parts} != {107371147,107371138}:
        raise ValueError('Missing cached Shanghai entry connector or garage road')
    pit=stitch([e['points']+shift for e in parts])
    entry,exit=cKDTree(main).query(pit[[0,-1]])[1]
    if (exit-entry)%len(main)>len(main)/2:
        pit=pit[::-1];entry,exit=exit,entry
    # On the FIA drawing the pit split is on the T15–T16 approach, not the back straight.
    turns={c['number']:c['fraction'] for c in track['corner_markers']}
    if not turns[15]<entry/len(main)<turns[16]:
        raise ValueError('Shanghai pit entry must precede the final corner after T15')
    pit[0]=main[entry];pit[-1]=main[exit]
    pit=resample(pit,600,False)
    pit=ndimage.gaussian_filter1d(pit,.65,axis=0,mode='nearest')
    pit[0]=main[entry];pit[-1]=main[exit]
    track['pit_points']=np.round(pit,4).tolist()
    track['pit_entry_fraction']=float(entry/len(main))
    track['pit_exit_fraction']=float(exit/len(main))
    track['garage_u_range']=garage_range(pit)
    track['pit_reference']='OpenStreetMap ways 107371147,107371138; checked against the 2026 FIA pit-lane drawing'
    track['pit_entry_note']='Entry connector leaves the T15–T16 approach; the infield/back-straight junction is not the pit split.'
    for key in ('points','width_profile_m','corner_markers','start_line_fraction','pole_side'):
        if old[key]!=track[key]:raise AssertionError(f'Unexpected race geometry change: {key}')
    path.write_text(json.dumps(layouts,separators=(',',':')),encoding='utf-8')
    audit_path=ROOT/'circuit_maps_2026/geometry_audit.json'
    audit=json.loads(audit_path.read_text())
    audit['china']['pit_ways']=[107371147,107371138]
    audit['china']['pit_entry_fraction']=track['pit_entry_fraction']
    audit['china']['pit_entry_note']=track['pit_entry_note']
    audit['china']['pit_length_m']=round(float(np.linalg.norm(np.diff(pit,axis=0),axis=1).sum()))
    audit_path.write_text(json.dumps(audit,indent=2),encoding='utf-8')
    print('Shanghai pit entry:',old['pit_entry_fraction'],'->',track['pit_entry_fraction'])
    print('Pit exit:',track['pit_exit_fraction'],'garage range:',track['garage_u_range'])


if __name__=='__main__':repair()
