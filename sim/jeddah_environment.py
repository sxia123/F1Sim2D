"""Jeddah's mapped Corniche, marina and illustrated waterfront planting/lighting."""
import math


def enrich_jeddah(track, env, source, road, areas, free, rng, bounds, world_paths,
                  inside_feature, feature_bounds, rectangle):
    env['revision'] += '-jeddah-v1'
    env['palette'] = dict(ground='#514b40', water='#175d78', shoreline='#9bb9ab',
                          grass='#40583f', parking='#454b4f', sand='#a4916b')
    env['routes'] = []
    env['lights'] = []
    env['accuracy_note'] += ' Jeddah roads, promenades and marina piers are mapped; palms, boats and lighting are illustrative.'

    def in_bounds(x,y):
        return bounds[0]<=x<=bounds[2] and bounds[1]<=y<=bounds[3]

    def wet(x,y):
        return any(f['kind']=='water' and inside_feature(x,y,f['paths'])
                   for f in areas.query([x,y,x,y]))

    # Resampling avoids long chords cutting across an unrelated road or coastline.
    # Every visible segment, including piers, clears the complete racing/pit corridor.
    for raw in source.get('linear_features', []):
        points=world_paths([raw['points']])[0]
        width=raw['width_m']*track.px_per_m
        kind=raw['kind']
        group=[]
        def flush():
            if len(group)>1:
                env['routes'].append(dict(id=raw['id'],kind=kind,name=raw.get('name',''),
                    points=group[:],width=round(width,1),bounds=feature_bounds([group])))
            group.clear()
        for a,b in zip(points,points[1:]):
            length=math.dist(a,b)
            steps=max(1,math.ceil(length/18))
            for i in range(steps+1):
                u=i/steps;x=a[0]+(b[0]-a[0])*u;y=a[1]+(b[1]-a[1])*u
                if (in_bounds(x,y) and road.circle_safe(x,y,width/2+14)
                    and (kind=='pier' or not wet(x,y))):
                    p=[round(x,1),round(y,1)]
                    if not group or math.dist(group[-1],p)>.1:group.append(p)
                else:flush()
        flush()

    # Palm rows follow mapped landscaped pedestrian areas instead of random desert trees.
    palms={(int(t['x']//35),int(t['y']//35)) for t in env['trees']}
    for route in env['routes']:
        if route['kind']!='promenade':continue
        distance=0.0
        for a,b in zip(route['points'],route['points'][1:]):
            length=math.dist(a,b)
            if length<.1:continue
            distance+=length
            if distance<65:continue
            distance%=65
            nx,ny=-(b[1]-a[1])/length,(b[0]-a[0])/length
            for side in (-1,1):
                x,y=b[0]+nx*side*28,b[1]+ny*side*28
                planted=any(f['kind']=='grass' and inside_feature(x,y,f['paths'])
                            for f in areas.query([x,y,x,y]))
                key=(int(x//35),int(y//35))
                if planted and key not in palms and free(x,y,27):
                    env['trees'].append(dict(x=round(x,1),y=round(y,1),r=17.0,type='palm',shade=rng.randrange(3),rotation=round(rng.random()*6.28,2)))
                    palms.add(key)

    # Real marina piers locate the illustrative yachts; no boats in the lagoon or pools.
    boats=[]
    for route in env['routes']:
        if len(boats)>=24:break
        if route['kind']!='pier':continue
        distance=0
        for a,b in zip(route['points'],route['points'][1:]):
            length=math.dist(a,b)
            if length<.1:continue
            distance+=length
            if distance<85:continue
            distance%=85
            tx,ty=(b[0]-a[0])/length,(b[1]-a[1])/length
            angle=math.atan2(ty,tx)+math.pi/2
            for side in (-1,1):
                x,y=b[0]-ty*side*48,b[1]+tx*side*48
                hull=rectangle(x,y,54,18,angle)
                if (all(wet(*p) for p in hull) and road.circle_safe(x,y,40)
                    and all(math.hypot(x-v['x'],y-v['y'])>70 for v in boats)
                    and all(min(math.dist((x,y),p) for p in pier['points'])>35
                            for pier in env['routes'] if pier['kind']=='pier')):
                    boats.append(dict(x=round(x,1),y=round(y,1),len=54,width=18,angle=round(angle,3)))
                if len(boats)>=24:break
            if len(boats)>=24:break
    env['yachts']=boats

    # The floodlit circuit is characteristic of Jeddah. Halo footprints also clear the road.
    for station in track.stations[::9]:
        for side in (-1,1):
            offset=station['width_px']/2+46
            x,y=station['x']+station['nx']*side*offset,station['y']+station['ny']*side*offset
            if free(x,y,21) and not wet(x,y):
                env['lights'].append(dict(x=round(x,1),y=round(y,1),r=18.0))

    # Keep named local landmarks recognizable at their mapped footprint, without moving them.
    for f in env['buildings']:
        name=f.get('name','').lower()
        if any(n in name for n in ('diamond tower','sail tower','jeddah edition','red sea mall')):
            f['landmark']=True
            f['roof_color']='#879da5' if 'tower' in name else '#b5ab94'
