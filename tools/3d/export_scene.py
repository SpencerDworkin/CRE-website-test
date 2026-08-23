"""Export one real level from the archived client into a scene.json + textures
that a three.js renderer can load: real meshes, real transforms, real textures.
"""
import UnityPy, os, json, sys, math

SRC = sys.argv[1] if len(sys.argv) > 1 else 'maps/Theme_01_Skirmish_09'
OUT = sys.argv[2] if len(sys.argv) > 2 else 'scene'
os.makedirs(OUT + '/tex', exist_ok=True)

# global texture pool: every texture in every bundle, keyed by name, so that
# materials pointing at an external file (the shared 2048 atlases) still resolve
POOL = {}
if os.path.isdir('bundles'):
    for _f in sorted(os.listdir('bundles')):
        try:
            _e = UnityPy.load(os.path.join('bundles', _f))
        except Exception:
            continue
        for _o in _e.objects:
            if _o.type.name == 'Texture2D':
                try:
                    _t = _o.read()
                except Exception:
                    continue
                POOL.setdefault(_t.m_Name, _o)
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

# ---- transforms -------------------------------------------------------
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

def local(t):
    p = t.get('m_LocalPosition', {}); q = t.get('m_LocalRotation', {}); s = t.get('m_LocalScale', {})
    return ([p.get('x',0), p.get('y',0), p.get('z',0)],
            [q.get('x',0), q.get('y',0), q.get('z',0), q.get('w',1)],
            [s.get('x',1), s.get('y',1), s.get('z',1)])

def qmul(a, b):
    ax,ay,az,aw = a; bx,by,bz,bw = b
    return [aw*bx+ax*bw+ay*bz-az*by,
            aw*by-ax*bz+ay*bw+az*bx,
            aw*bz+ax*by-ay*bx+az*bw,
            aw*bw-ax*bx-ay*by-az*bz]

def qrot(q, v):
    x,y,z,w = q; vx,vy,vz = v
    tx = 2*(y*vz - z*vy); ty = 2*(z*vx - x*vz); tz = 2*(x*vy - y*vx)
    return [vx + w*tx + (y*tz - z*ty),
            vy + w*ty + (z*tx - x*tz),
            vz + w*tz + (x*ty - y*tx)]

def world(go_pid):
    """Compose position/rotation/scale up the parent chain."""
    pos, rot, scl = [0,0,0], [0,0,0,1], [1,1,1]
    node = go_tr.get(go_pid); guard = 0
    chain = []
    while node and guard < 64:
        t = tr.get(node)
        if not t:
            break
        chain.append(t)
        node = t.get('m_Father', {}).get('m_PathID')
        guard += 1
    for t in reversed(chain):
        lp, lq, ls = local(t)
        sp = [lp[i]*scl[i] for i in range(3)]
        rp = qrot(rot, sp)
        pos = [pos[i] + rp[i] for i in range(3)]
        rot = qmul(rot, lq)
        scl = [scl[i]*ls[i] for i in range(3)]
    return pos, rot, scl

# ---- textures ---------------------------------------------------------
tex_index, textures = {}, []
def save_tex(obj, key):
    if key in tex_index:
        return tex_index[key]
    try:
        t = obj.read()
        img = t.image
        if img is None:
            return -1
        name = f'{t.m_Name}.png'
        img.save(os.path.join(OUT, 'tex', name))
    except Exception:
        return -1
    tex_index[key] = len(textures)
    textures.append(name)
    return tex_index[key]

def texture_for(mat_pid):
    mt = tree(mat_pid)
    if not mt:
        return -1
    # material names mirror their texture; '_Placeholder' is a build-time suffix
    mname = (mt.get('m_Name') or '').replace('_Placeholder', '')
    if mname in POOL:
        return save_tex(POOL[mname], 'pool:' + mname)
    envs = mt.get('m_SavedProperties', {}).get('m_TexEnvs')
    tex_pid = None
    if isinstance(envs, list):
        for entry in envs:
            try:
                k, v = entry
            except Exception:
                continue
            if k.get('name') == '_MainTex':
                tex_pid = v.get('m_Texture', {}).get('m_PathID')
    elif isinstance(envs, dict):
        v = envs.get('_MainTex')
        if v:
            tex_pid = v.get('m_Texture', {}).get('m_PathID')
    if not tex_pid or tex_pid not in objs:
        return -1
    return save_tex(objs[tex_pid], 'local:%d' % tex_pid)

# ---- meshes -----------------------------------------------------------
def parse_obj(text):
    V, T, F = [], [], []
    for line in text.splitlines():
        if line.startswith('v '):
            V.append([float(x) for x in line.split()[1:4]])
        elif line.startswith('vt '):
            T.append([float(x) for x in line.split()[1:3]])
        elif line.startswith('f '):
            idx = []
            for part in line.split()[1:]:
                bits = part.split('/')
                vi = int(bits[0]) - 1
                ti = int(bits[1]) - 1 if len(bits) > 1 and bits[1] else vi
                idx.append((vi, ti))
            for i in range(1, len(idx) - 1):
                F.append((idx[0], idx[i], idx[i+1]))
    pos, uv, tri = [], [], []
    remap = {}
    for face in F:
        for vi, ti in face:
            k = (vi, ti)
            if k not in remap:
                remap[k] = len(pos) // 3
                v = V[vi] if vi < len(V) else [0,0,0]
                t = T[ti] if ti < len(T) else [0,0]
                pos += [v[0], v[1], v[2]]
                uv += [t[0], t[1]]
            tri.append(remap[k])
    return pos, uv, tri

mesh_index, meshes, nodes = {}, [], []
for pid, o in objs.items():
    if o.type.name != 'MeshFilter':
        continue
    mf = tree(pid)
    if not mf:
        continue
    go = mf.get('m_GameObject', {}).get('m_PathID')
    mesh_pid = mf.get('m_Mesh', {}).get('m_PathID')
    if not mesh_pid or mesh_pid not in objs:
        continue
    # renderer on the same GameObject supplies the material
    tex_i = -1
    for pid2, o2 in objs.items():
        if o2.type.name != 'MeshRenderer':
            continue
        mr = tree(pid2)
        if mr and mr.get('m_GameObject', {}).get('m_PathID') == go:
            mats = mr.get('m_Materials') or []
            if mats:
                tex_i = texture_for(mats[0].get('m_PathID'))
            break
    if mesh_pid not in mesh_index:
        try:
            m = objs[mesh_pid].read()
            pos, uv, tri = parse_obj(m.export())
        except Exception:
            continue
        if not tri:
            continue
        mesh_index[mesh_pid] = len(meshes)
        meshes.append({'name': getattr(m, 'm_Name', 'mesh'), 'pos': pos, 'uv': uv, 'idx': tri})
    p, q, s = world(go)
    nodes.append({'mesh': mesh_index[mesh_pid], 'tex': tex_i, 'p': p, 'q': q, 's': s})

scene = {'source': os.path.basename(SRC), 'textures': textures, 'meshes': meshes, 'nodes': nodes}
json.dump(scene, open(os.path.join(OUT, 'scene.json'), 'w'), separators=(',', ':'))
tris = sum(len(m['idx']) // 3 for m in meshes)
print(f'meshes {len(meshes)}  nodes {len(nodes)}  textures {len(textures)}  triangles {tris:,}')
print('scene.json', os.path.getsize(os.path.join(OUT, 'scene.json')), 'bytes')
