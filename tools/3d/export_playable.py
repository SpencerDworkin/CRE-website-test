"""Export a playable level from an ART bundle alone.

The archived data does not bind a Skirmish art level to a gameplay grid - the
scene that placed one against the other is not in the client - so the grid is
derived from the geometry instead: rasterise the real meshes into 1-unit cells,
take floor height from the ground surface and cover from what stands on it.
"""
import UnityPy, os, json, sys, math

SRC = sys.argv[1] if len(sys.argv) > 1 else 'bundles/Theme_01_Skirmish_09'
OUT = sys.argv[2] if len(sys.argv) > 2 else 'play'
os.makedirs(OUT + '/tex', exist_ok=True)

POOL = {}
for f in sorted(os.listdir('bundles')):
    try:
        e = UnityPy.load(os.path.join('bundles', f))
    except Exception:
        continue
    for o in e.objects:
        if o.type.name == 'Texture2D':
            try: POOL.setdefault(o.read().m_Name, o)
            except Exception: pass

env = UnityPy.load(SRC)
objs = {o.path_id: o for o in env.objects}
cache = {}
def tree(pid):
    if pid not in cache:
        o = objs.get(pid)
        try: cache[pid] = o.read_typetree() if o else None
        except Exception: cache[pid] = None
    return cache[pid]

tex_index, textures = {}, []
def save_tex(obj, key):
    if key in tex_index: return tex_index[key]
    try:
        t = obj.read(); img = t.image
        if img is None: return -1
        img.save(os.path.join(OUT, 'tex', f'{t.m_Name}.png'))
    except Exception:
        return -1
    tex_index[key] = len(textures); textures.append(f'{t.m_Name}.png')
    return tex_index[key]

def texture_for(mat_pid):
    mt = tree(mat_pid)
    if not mt: return -1
    mn = (mt.get('m_Name') or '').replace('_Placeholder', '')
    if mn in POOL: return save_tex(POOL[mn], 'pool:' + mn)
    envs = mt.get('m_SavedProperties', {}).get('m_TexEnvs')
    tp = None
    if isinstance(envs, list):
        for e in envs:
            try: k, v = e
            except Exception: continue
            if k.get('name') == '_MainTex': tp = v.get('m_Texture', {}).get('m_PathID')
    if tp and tp in objs: return save_tex(objs[tp], 'local:%d' % tp)
    return -1

def parse_obj(text):
    V, T, F = [], [], []
    for line in text.splitlines():
        if line.startswith('v '): V.append([float(x) for x in line.split()[1:4]])
        elif line.startswith('vt '): T.append([float(x) for x in line.split()[1:3]])
        elif line.startswith('f '):
            idx = []
            for part in line.split()[1:]:
                b = part.split('/'); vi = int(b[0]) - 1
                ti = int(b[1]) - 1 if len(b) > 1 and b[1] else vi
                idx.append((vi, ti))
            for i in range(1, len(idx) - 1): F.append((idx[0], idx[i], idx[i+1]))
    pos, uv, tri, remap = [], [], [], {}
    for f in F:
        for vi, ti in f:
            k = (vi, ti)
            if k not in remap:
                remap[k] = len(pos) // 3
                v = V[vi] if vi < len(V) else [0,0,0]
                t = T[ti] if ti < len(T) else [0,0]
                pos += [v[0], v[1], v[2]]; uv += [t[0], t[1]]
            tri.append(remap[k])
    return pos, uv, tri

renderer_by_go = {}
for pid, o in objs.items():
    if o.type.name == 'MeshRenderer':
        mr = tree(pid)
        if mr: renderer_by_go[mr.get('m_GameObject', {}).get('m_PathID')] = mr

meshes, nodes, mesh_index = [], [], {}
floor_h, top_h = {}, {}                      # cell -> ground height / tallest geometry
for pid, o in objs.items():
    if o.type.name != 'MeshFilter':
        continue
    mf = tree(pid)
    if not mf: continue
    go = mf.get('m_GameObject', {}).get('m_PathID')
    mp = mf.get('m_Mesh', {}).get('m_PathID')
    if not mp or mp not in objs: continue
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
    mi = mesh_index[mp]
    nodes.append({'mesh': mi, 'tex': tex_i, 'p': [0,0,0], 'q': [0,0,0,1], 's': [1,1,1]})
    # rasterise this mesh's vertices into the occupancy map
    P = meshes[mi]['pos']
    for i in range(0, len(P), 3):
        x, y, z = P[i], P[i+1], P[i+2]
        c = (math.floor(x), math.floor(z))
        if abs(y) < 0.45:
            floor_h[c] = min(floor_h.get(c, 99), y)
        top_h[c] = max(top_h.get(c, -99), y)

cells = sorted(floor_h.keys())
minx = min(c[0] for c in cells); maxx = max(c[0] for c in cells)
minz = min(c[1] for c in cells); maxz = max(c[1] for c in cells)
W, H = maxx - minx + 1, maxz - minz + 1

tiles = []
for (cx, cz) in cells:
    top = top_h.get((cx, cz), 0)
    if top > 2.2:   kind = 3          # tall: blocks sight
    elif top > 0.9: kind = 2          # hard cover
    elif top > 0.35: kind = 1         # low cover
    else: kind = 0
    tiles.append({'x': cx - minx, 'y': cz - minz, 'k': kind,
                  'w': [cx + 0.5, round(floor_h[(cx, cz)], 3), cz + 0.5]})

out = {'source': os.path.basename(SRC), 'grid': [W, H], 'origin': [minx, minz],
       'tiles': tiles, 'textures': textures, 'meshes': meshes, 'nodes': nodes}
json.dump(out, open(os.path.join(OUT, 'play.json'), 'w'), separators=(',', ':'))
kinds = {}
for t in tiles: kinds[t['k']] = kinds.get(t['k'], 0) + 1
print(f'{os.path.basename(SRC)}: grid {W}x{H}  floor tiles {len(tiles)}')
print('  tile kinds (0 open, 1 low, 2 hard, 3 blocks sight):', dict(sorted(kinds.items())))
print(f'  meshes {len(meshes)}  nodes {len(nodes)}  textures {len(textures)}')
print('  play.json', os.path.getsize(os.path.join(OUT, 'play.json')), 'bytes')
