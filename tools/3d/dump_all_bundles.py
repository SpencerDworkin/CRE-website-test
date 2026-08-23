import UnityPy, os

os.makedirs('bundles', exist_ok=True)
env = UnityPy.load('unity/resources.assets')
n = 0
for o in env.objects:
    if o.type.name != 'TextAsset':
        continue
    d = o.read()
    raw = d.m_Script
    b = raw.encode('utf-8', 'surrogateescape') if isinstance(raw, str) else bytes(raw)
    if b[:9] != b'UnityWeb\x00' and b[:8] != b'UnityRaw' and b[:7] != b'UnityFS':
        continue
    open('bundles/' + d.m_Name, 'wb').write(b)
    n += 1
print('asset bundles extracted:', n)

# global pool of every texture, keyed by name
pool = {}
for f in sorted(os.listdir('bundles')):
    p = os.path.join('bundles', f)
    try:
        e = UnityPy.load(p)
    except Exception:
        continue
    for o in e.objects:
        if o.type.name != 'Texture2D':
            continue
        try:
            t = o.read()
        except Exception:
            continue
        pool.setdefault(t.m_Name, (f, o.path_id, t.m_Width, t.m_Height))
print('distinct texture names across bundles:', len(pool))
for n2 in sorted(pool, key=lambda k: -(pool[k][2] * pool[k][3]))[:22]:
    f, pid, w, h = pool[n2]
    print(f'  {w:5d}x{h:<5d} {n2[:44]:44s} [{f}]')
