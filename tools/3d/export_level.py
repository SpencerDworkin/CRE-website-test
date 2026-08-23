"""Export one playable level: the gameplay grid (tiles with world positions,
per-edge cover, solidity, height, spawns, capture zone) AND the art that sits on
it, from the same bundle so the two are guaranteed aligned.
"""
import UnityPy, os, json, sys

SRC = sys.argv[1] if len(sys.argv) > 1 else 'bundles/Theme_01_Levels_Gameplay'
PICK = int(sys.argv[2]) if len(sys.argv) > 2 else 0     # which grid in the bundle
OUT = sys.argv[3] if len(sys.argv) > 3 else 'level'
os.makedirs(OUT + '/tex', exist_ok=True)

POOL = {}
for f in sorted(os.listdir('bundles')):
    try:
        e = UnityPy.load(os.path.join('bundles', f))
    except Exception:
        continue
    for o in e.objects:
        if o.type.name == 'Texture2D':
            try:
                POOL.setdefault(o.read().m_Name, o)
            except Exception:
                pass
print('texture pool:', len(POOL))

env = UnityPy.load(SRC)
objs = {o.path_id: o for o in env.objects}
cache = {}
def tree(pid):
    if pid not in cache:
        o = objs.get(pid)
        try:
            cache[pid] = o.read_typetree() if o is not None else None
        except Exception:
            cache[pid] = None
    return cache[pid]

go_tr, tr = {}, {}
for pid, o in objs.items():
    if o.type.name != 'Transform':
        continue
    t = tree(pid)
    if not t:
        continue
    go = t.get('m_GameObject', {}).get('m_PathID')
    if go:
        go_tr[go] = pid
    tr[pid] = t

def qmul(a, b):
    ax,ay,az,aw=a; bx,by,bz,bw=b
    return [aw*bx+ax*bw+ay*bz-az*by, aw*by-ax*bz+ay*bw+az*bx,
            aw*bz+ax*by-ay*bx+az*bw, aw*bw-ax*bx-ay*by-az*bz]
def qrot(q, v):
    x,y,z,w=q; vx,vy,vz=v
    tx=2*(y*vz-z*vy); ty=2*(z*vx-x*vz); tz=2*(x*vy-y*vx)
    return [vx+w*tx+(y*tz-z*ty), vy+w*ty+(z*tx-x*tz), vz+w*tz+(x*ty-y*tx)]

def world(go_pid):
    pos, rot, scl = [0,0,0], [0,0,0,1], [1,1,1]
    node, guard, chain = go_tr.get(go_pid), 0, []
    while node and guard < 64:
        t = tr.get(node)
        if not t: break
        chain.append(t)
        node = t.get('m_Father', {}).get('m_PathID'); guard += 1
    for t in reversed(chain):
        p = t.get('m_LocalPosition', {}); q = t.get('m_LocalRotation', {}); s = t.get('m_LocalScale', {})
        lp=[p.get('x',0),p.get('y',0),p.get('z',0)]
        lq=[q.get('x',0),q.get('y',0),q.get('z',0),q.get('w',1)]
        ls=[s.get('x',1),s.get('y',1),s.get('z',1)]
        sp=[lp[i]*scl[i] for i in range(3)]
        rp=qrot(rot, sp)
        pos=[pos[i]+rp[i] for i in range(3)]
        rot=qmul(rot, lq)
        scl=[scl[i]*ls[i] for i in range(3)]
    return pos, rot, scl

# ---- grids, tiles, zones, spawns --------------------------------------
grids, tiles_by_go, zones, spawns = {}, {}, {}, {}
for pid, o in objs.items():
    if o.type.name != 'MonoBehaviour':
        continue
    t = tree(pid)
    if not t:
        continue
    go = t.get('m_GameObject', {}).get('m_PathID')
    k = set(t.keys()); plain = k - {'m_GameObject','m_Enabled','m_Script','m_Name'}
    if 'SizeX' in k and 'SizeY' in k:
        grids[go] = (t['SizeX'], t['SizeY'])
    elif 'TileIndexX' in k:
        tiles_by_go[go] = t
    elif plain == {'CaptureZone'}:
        zones[go] = 1
    elif plain == {'Direction','Team'}:
        spawns[go] = (t['Team'], t['Direction'])

def owner(go_pid):
    node, n = go_tr.get(go_pid), 0
    while node and n < 64:
        fa = tr.get(node, {}).get('m_Father', {}).get('m_PathID')
        if not fa: return None
        ft = tr.get(fa)
        if not ft: return None
        fgo = ft.get('m_GameObject', {}).get('m_PathID')
        if fgo in grids: return fgo
        node = fa; n += 1
    return None

buckets = {}
for go, t in tiles_by_go.items():
    g = owner(go)
    if g is None: continue
    buckets.setdefault(g, []).append((go, t))

order = sorted(buckets.keys(), key=lambda g: -len(buckets[g]))
print('grids in bundle:', [(grids[g], len(buckets[g])) for g in order])
G = order[PICK]
sx_, sy_ = grids[G]
print(f'exporting grid {sx_}x{sy_} with {len(buckets[G])} tiles')

tiles, xs, zs = [], [], []
for go, t in buckets[G]:
    p, _, _ = world(go)
    xs.append(p[0]); zs.append(p[2])
    tiles.append({
        'x': t['TileIndexX'], 'y': t['TileIndexY'],
        'w': [round(v, 4) for v in p],
        'h': t['Height'], 'vis': int(t['VisBlocker']),
        'cover': [t['NorthCover'], t['EastCover'], t['SouthCover'], t['WestCover']],
        'solid': [int(t['SolidNorth']), int(t['SolidEast']), int(t['SolidSouth']), int(t['SolidWest'])],
        'cap': 1 if go in zones else 0,
        'spawn': spawns[go][0] + 1 if go in spawns else 0,
    })
bx = (min(xs) - 6, max(xs) + 6)
bz = (min(zs) - 6, max(zs) + 6)
print(f'grid world bounds x {bx[0]:.1f}..{bx[1]:.1f}   z {bz[0]:.1f}..{bz[1]:.1f}')

# ---- art that sits on this grid ---------------------------------------
tex_index, textures = {}, []
def save_tex(obj, key):
    if key in tex_index: return tex_index[key]
    try:
        t = obj.read(); img = t.image
        if img is None: return -1
        name = f'{t.m_Name}.png'
        img.save(os.path.join(OUT, 'tex', name))
    except Exception:
        return -1
    tex_index[key] = len(textures); textures.append(name)
    return tex_index[key]

def texture_for(mat_pid):
    mt = tree(mat_pid)
    if not mt: return -1
    mname = (mt.get('m_Name') or '').replace('_Placeholder', '')
    if mname in POOL: return save_tex(POOL[mname], 'pool:' + mname)
    envs = mt.get('m_SavedProperties', {}).get('m_TexEnvs')
    tp = None
    if isinstance(envs, list):
        for e in envs:
            try: kk, vv = e
            except Exception: continue
            if kk.get('name') == '_MainTex': tp = vv.get('m_Texture', {}).get('m_PathID')
    if tp and tp in objs: return save_tex(objs[tp], 'local:%d' % tp)
    return -1

def parse_obj(text):
    V, T, F = [], [], []
    for line in text.splitlines():
        if line.startswith('v '): V.append([float(x) for x in line.split()[1:4]])
        elif line.startswith('vt '): T.append([float(x) for x in line.split()[1:3]])
        elif line.startswith('f '):
            idx=[]
            for part in line.split()[1:]:
                b=part.split('/'); vi=int(b[0])-1
                ti=int(b[1])-1 if len(b)>1 and b[1] else vi
                idx.append((vi,ti))
            for i in range(1,len(idx)-1): F.append((idx[0],idx[i],idx[i+1]))
    pos,uv,tri,remap = [],[],[],{}
    for f in F:
        for vi,ti in f:
            kk=(vi,ti)
            if kk not in remap:
                remap[kk]=len(pos)//3
                v=V[vi] if vi<len(V) else [0,0,0]
                t=T[ti] if ti<len(T) else [0,0]
                pos+= [v[0],v[1],v[2]]; uv+= [t[0],t[1]]
            tri.append(remap[kk])
    return pos,uv,tri

mesh_index, meshes, nodes = {}, [], []
renderer_by_go = {}
for pid, o in objs.items():
    if o.type.name == 'MeshRenderer':
        mr = tree(pid)
        if mr: renderer_by_go[mr.get('m_GameObject', {}).get('m_PathID')] = mr

for pid, o in objs.items():
    if o.type.name != 'MeshFilter':
        continue
    mf = tree(pid)
    if not mf: continue
    go = mf.get('m_GameObject', {}).get('m_PathID')
    mp = mf.get('m_Mesh', {}).get('m_PathID')
    if not mp or mp not in objs: continue
    p, q, s = world(go)
    if not (bx[0] <= p[0] <= bx[1] and bz[0] <= p[2] <= bz[1]):
        continue                                    # art belonging to another grid
    tex_i = -1
    mr = renderer_by_go.get(go)
    if mr:
        mats = mr.get('m_Materials') or []
        if mats: tex_i = texture_for(mats[0].get('m_PathID'))
    if mp not in mesh_index:
        try:
            m = objs[mp].read(); pos, uv, tri = parse_obj(m.export())
        except Exception:
            continue
        if not tri: continue
        mesh_index[mp] = len(meshes)
        meshes.append({'pos': pos, 'uv': uv, 'idx': tri})
    nodes.append({'mesh': mesh_index[mp], 'tex': tex_i,
                  'p': [round(v,4) for v in p], 'q': [round(v,5) for v in q], 's': [round(v,4) for v in s]})

out = {'grid': [sx_, sy_], 'tiles': tiles, 'textures': textures, 'meshes': meshes, 'nodes': nodes}
json.dump(out, open(os.path.join(OUT, 'level.json'), 'w'), separators=(',', ':'))
tri_total = sum(len(m['idx'])//3 for m in meshes)
print(f'tiles {len(tiles)}  art nodes {len(nodes)}  meshes {len(meshes)}  textures {len(textures)}  tris {tri_total:,}')
print('level.json', os.path.getsize(os.path.join(OUT, 'level.json')), 'bytes')
