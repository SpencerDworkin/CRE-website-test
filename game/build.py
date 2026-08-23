#!/usr/bin/env python3
"""Build the playable data for the RAD Soldiers 3D recreation.

Reads the game's own Unity asset bundles and writes everything the browser
needs: the level's meshes and their atlases, and one character mesh + skin per
operative.  Nothing here ships with the code - you point it at your own copy of
the archived client and it rebuilds the data locally.

    python3 build.py --bundles <dir with the extracted asset bundles> --out play

Requires:  pip install UnityPy Pillow
"""
import argparse, json, os, sys

try:
    import UnityPy
except ImportError:
    sys.exit('UnityPy is required:  pip install UnityPy Pillow')

# bundle -> (slot key, preferred texture substring)
OPERATIVES = [
    ('ArchieFletcherOutfits',   'commando', 'Soldier_Light_Rambo_d'),
    ('BigTimeTaschmannOutfits', 'engineer', 'Engineer_d'),
    ('CarlitoGrossoOutfits',    'heavy',    'Engineer_Heavy'),
    ('CommanderMaleOutfits',    'captain',  'Commander'),
    ('CommanderFemaleOutfits',  'medic',    'CommanderF'),
    ('HalloweenOutfits',        'agent',    'Agent'),
]


def parse_obj(text):
    """UnityPy exports meshes as OBJ; unweld it into flat GL arrays."""
    V, T, F = [], [], []
    for line in text.splitlines():
        if line.startswith('v '):
            V.append([float(x) for x in line.split()[1:4]])
        elif line.startswith('vt '):
            T.append([float(x) for x in line.split()[1:3]])
        elif line.startswith('f '):
            idx = []
            for part in line.split()[1:]:
                b = part.split('/')
                vi = int(b[0]) - 1
                ti = int(b[1]) - 1 if len(b) > 1 and b[1] else vi
                idx.append((vi, ti))
            for i in range(1, len(idx) - 1):
                F.append((idx[0], idx[i], idx[i + 1]))
    pos, uv, tri, remap = [], [], [], {}
    for f in F:
        for vi, ti in f:
            k = (vi, ti)
            if k not in remap:
                remap[k] = len(pos) // 3
                v = V[vi] if vi < len(V) else [0, 0, 0]
                t = T[ti] if ti < len(T) else [0, 0]
                pos += [v[0], v[1], v[2]]
                uv += [t[0], t[1]]
            tri.append(remap[k])
    return pos, uv, tri


def build_texture_pool(bundle_dir):
    """Materials point at atlases that live in *other* bundles, so index every
    texture in the set by name and resolve against that."""
    pool = {}
    for f in sorted(os.listdir(bundle_dir)):
        try:
            env = UnityPy.load(os.path.join(bundle_dir, f))
        except Exception:
            continue
        for o in env.objects:
            if o.type.name == 'Texture2D':
                try:
                    pool.setdefault(o.read().m_Name, o)
                except Exception:
                    pass
    return pool


def export_level(src, out, pool):
    env = UnityPy.load(src)
    objs = {o.path_id: o for o in env.objects}
    cache = {}

    def tree(pid):
        if pid not in cache:
            o = objs.get(pid)
            try:
                cache[pid] = o.read_typetree() if o else None
            except Exception:
                cache[pid] = None
        return cache[pid]

    textures, tex_index = [], {}

    def save_tex(obj, key):
        if key in tex_index:
            return tex_index[key]
        try:
            t = obj.read()
            img = t.image
            if img is None:
                return -1
            img.save(os.path.join(out, 'tex', t.m_Name + '.png'))
        except Exception:
            return -1
        tex_index[key] = len(textures)
        textures.append(t.m_Name + '.png')
        return tex_index[key]

    def texture_for(mat_pid):
        mt = tree(mat_pid)
        if not mt:
            return -1
        name = (mt.get('m_Name') or '').replace('_Placeholder', '')
        if name in pool:
            return save_tex(pool[name], 'pool:' + name)
        envs = mt.get('m_SavedProperties', {}).get('m_TexEnvs')
        tp = None
        if isinstance(envs, list):
            for e in envs:
                try:
                    k, v = e
                except Exception:
                    continue
                if k.get('name') == '_MainTex':
                    tp = v.get('m_Texture', {}).get('m_PathID')
        if tp and tp in objs:
            return save_tex(objs[tp], 'local:%d' % tp)
        return -1

    renderer_by_go = {}
    for pid, o in objs.items():
        if o.type.name == 'MeshRenderer':
            mr = tree(pid)
            if mr:
                renderer_by_go[mr.get('m_GameObject', {}).get('m_PathID')] = mr

    meshes, nodes, mesh_index = [], [], {}
    for pid, o in objs.items():
        if o.type.name != 'MeshFilter':
            continue
        mf = tree(pid)
        if not mf:
            continue
        go = mf.get('m_GameObject', {}).get('m_PathID')
        mp = mf.get('m_Mesh', {}).get('m_PathID')
        if not mp or mp not in objs:
            continue
        tex_i = -1
        mr = renderer_by_go.get(go)
        if mr:
            mats = mr.get('m_Materials') or []
            if mats:
                tex_i = texture_for(mats[0].get('m_PathID'))
        if mp not in mesh_index:
            try:
                pos, uv, tri = parse_obj(objs[mp].read().export())
            except Exception:
                continue
            if not tri:
                continue
            mesh_index[mp] = len(meshes)
            meshes.append({'pos': pos, 'uv': uv, 'idx': tri})
        nodes.append({'mesh': mesh_index[mp], 'tex': tex_i,
                      'p': [0, 0, 0], 'q': [0, 0, 0, 1], 's': [1, 1, 1]})

    data = {'source': os.path.basename(src), 'textures': textures,
            'meshes': meshes, 'nodes': nodes}
    path = os.path.join(out, 'play.json')
    with open(path, 'w') as fh:
        json.dump(data, fh, separators=(',', ':'))
    tris = sum(len(m['idx']) // 3 for m in meshes)
    print(f'level  {os.path.basename(src)}: {len(meshes)} meshes, {tris} triangles, '
          f'{len(textures)} atlases -> play.json ({os.path.getsize(path):,} bytes)')


def export_units(bundle_dir, out):
    units, textures, tex_index = {}, [], {}
    for bundle, slot, hint in OPERATIVES:
        p = os.path.join(bundle_dir, bundle)
        if not os.path.exists(p):
            print('  missing bundle, skipping:', bundle)
            continue
        env = UnityPy.load(p)
        mesh = None
        for o in env.objects:
            if o.type.name != 'Mesh':
                continue
            try:
                m = o.read()
                pos, uv, tri = parse_obj(m.export())
            except Exception:
                continue
            if tri and (mesh is None or len(tri) > len(mesh[2])):
                mesh = (pos, uv, tri, m.m_Name)
        if not mesh:
            print('  no mesh in', bundle)
            continue
        best = None
        for o in env.objects:
            if o.type.name != 'Texture2D':
                continue
            try:
                t = o.read()
            except Exception:
                continue
            score = (2 if hint in t.m_Name else 0) + (1 if t.m_Name.endswith('_d') else 0)
            if best is None or score > best[0]:
                best = (score, t)
        ti = -1
        if best:
            t = best[1]
            if t.m_Name not in tex_index:
                try:
                    t.image.save(os.path.join(out, 'tex', t.m_Name + '.png'))
                    tex_index[t.m_Name] = len(textures)
                    textures.append(t.m_Name + '.png')
                except Exception:
                    pass
            ti = tex_index.get(t.m_Name, -1)
        pos, uv, tri, name = mesh
        units[slot] = {'name': name, 'pos': pos, 'uv': uv, 'idx': tri, 'tex': ti}
        print(f'  {slot:9s} {name[:26]:26s} {len(pos)//3:5d} verts  '
              f'{textures[ti] if ti >= 0 else "no skin"}')
    path = os.path.join(out, 'units.json')
    with open(path, 'w') as fh:
        json.dump({'textures': textures, 'units': units}, fh, separators=(',', ':'))
    print(f'units  {len(units)} operatives -> units.json ({os.path.getsize(path):,} bytes)')


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--bundles', required=True, help='directory holding the asset bundles')
    ap.add_argument('--level', default='Theme_01_Skirmish_09', help='level bundle to play on')
    ap.add_argument('--out', default='play', help='output directory (default: play)')
    a = ap.parse_args()

    src = a.level if os.path.exists(a.level) else os.path.join(a.bundles, a.level)
    if not os.path.exists(src):
        sys.exit('no such level bundle: ' + src)
    os.makedirs(os.path.join(a.out, 'tex'), exist_ok=True)

    print('indexing textures across every bundle…')
    pool = build_texture_pool(a.bundles)
    print(f'  {len(pool)} textures indexed')
    export_level(src, a.out, pool)
    print('exporting operatives…')
    export_units(a.bundles, a.out)
    print('\ndone - now run:  python3 serve.py')


if __name__ == '__main__':
    main()
