"""Pair each art bundle with the gameplay grid it actually belongs to, by testing
whether art geometry stands where the grid says a tile blocks sight."""
import UnityPy, os, collections, math

def art_occupancy(path):
    """Set of (x,z) integer cells that have art geometry above ground level."""
    try:
        env = UnityPy.load(path)
    except Exception:
        return None, None
    cells, ground = set(), set()
    for o in env.objects:
        if o.type.name != 'Mesh':
            continue
        try:
            txt = o.read().export()
        except Exception:
            continue
        for line in txt.splitlines():
            if not line.startswith('v '):
                continue
            p = line.split()
            x, y, z = float(p[1]), float(p[2]), float(p[3])
            ground.add((math.floor(x), math.floor(z)))
            if y > 0.7:
                cells.add((math.floor(x), math.floor(z)))
    return cells, ground

def grids_of(path):
    env = UnityPy.load(path)
    objs = {o.path_id: o for o in env.objects}
    cache = {}
    def tree(pid):
        if pid not in cache:
            o = objs.get(pid)
            try: cache[pid] = o.read_typetree() if o else None
            except Exception: cache[pid] = None
        return cache[pid]
    go_tr, tr = {}, {}
    for pid, o in objs.items():
        if o.type.name != 'Transform': continue
        t = tree(pid)
        if not t: continue
        g = t.get('m_GameObject', {}).get('m_PathID')
        if g: go_tr[g] = pid
        tr[pid] = t
    def qmul(a,b):
        ax,ay,az,aw=a; bx,by,bz,bw=b
        return [aw*bx+ax*bw+ay*bz-az*by, aw*by-ax*bz+ay*bw+az*bx,
                aw*bz+ax*by-ay*bx+az*bw, aw*bw-ax*bx-ay*by-az*bz]
    def qrot(q,v):
        x,y,z,w=q; vx,vy,vz=v
        tx=2*(y*vz-z*vy); ty=2*(z*vx-x*vz); tz=2*(x*vy-y*vx)
        return [vx+w*tx+(y*tz-z*ty), vy+w*ty+(z*tx-x*tz), vz+w*tz+(x*ty-y*tx)]
    def world(go):
        pos,rot,scl=[0,0,0],[0,0,0,1],[1,1,1]
        node,n,chain=go_tr.get(go),0,[]
        while node and n<64:
            t=tr.get(node)
            if not t: break
            chain.append(t); node=t.get('m_Father',{}).get('m_PathID'); n+=1
        for t in reversed(chain):
            p=t.get('m_LocalPosition',{}); q=t.get('m_LocalRotation',{}); s=t.get('m_LocalScale',{})
            lp=[p.get('x',0),p.get('y',0),p.get('z',0)]
            lq=[q.get('x',0),q.get('y',0),q.get('z',0),q.get('w',1)]
            ls=[s.get('x',1),s.get('y',1),s.get('z',1)]
            rp=qrot(rot,[lp[i]*scl[i] for i in range(3)])
            pos=[pos[i]+rp[i] for i in range(3)]
            rot=qmul(rot,lq); scl=[scl[i]*ls[i] for i in range(3)]
        return pos
    grids, tiles = {}, {}
    for pid,o in objs.items():
        if o.type.name!='MonoBehaviour': continue
        t=tree(pid)
        if not t: continue
        g=t.get('m_GameObject',{}).get('m_PathID')
        if 'SizeX' in t and 'SizeY' in t: grids[g]=(t['SizeX'],t['SizeY'])
        elif 'TileIndexX' in t: tiles[g]=t
    def owner(go):
        node,n=go_tr.get(go),0
        while node and n<64:
            fa=tr.get(node,{}).get('m_Father',{}).get('m_PathID')
            if not fa: return None
            ft=tr.get(fa)
            if not ft: return None
            fg=ft.get('m_GameObject',{}).get('m_PathID')
            if fg in grids: return fg
            node=fa; n+=1
        return None
    out={}
    for go,t in tiles.items():
        g=owner(go)
        if g is None: continue
        p=world(go)
        out.setdefault(g,[]).append((math.floor(p[0]), math.floor(p[2]), int(t['VisBlocker'])))
    return {grids[g]: v for g, v in out.items()}

GP = {}
for f in ('Theme_01_Levels_Gameplay','Theme_01_Levels_Gameplay_DLC1','Theme_02_Levels_Gameplay_DLC1'):
    p = os.path.join('bundles', f)
    if os.path.exists(p):
        for k, v in grids_of(p).items():
            GP[(f, k)] = v
print('grids:', len(GP))

art_bundles = [f for f in sorted(os.listdir('bundles')) if 'Skirmish' in f]
best_for_art = {}
for a in art_bundles:
    cells, ground = art_occupancy(os.path.join('bundles', a))
    if not cells:
        continue
    scores = []
    for key, tiles in GP.items():
        blocked = [(x, z) for x, z, v in tiles if v]
        openish = [(x, z) for x, z, v in tiles if not v]
        if not blocked:
            continue
        hit = sum(1 for c in blocked if c in cells) / len(blocked)
        clean = sum(1 for c in openish if c not in cells) / max(1, len(openish))
        cover = sum(1 for x, z, _ in tiles if (x, z) in ground) / len(tiles)
        scores.append((hit * 0.4 + clean * 0.3 + cover * 0.3, hit, clean, cover, key))
    scores.sort(reverse=True)
    if scores:
        s, hit, clean, cover, key = scores[0]
        best_for_art[a] = (s, key, hit, clean, cover)
        print(f'{a:24s} -> {key[1][0]}x{key[1][1]:<3d} [{key[0][:26]:26s}] '
              f'score={s:.3f} blockedHit={hit:.2f} openClean={clean:.2f} groundCover={cover:.2f}')
