import UnityPy, os
os.makedirs('maps', exist_ok=True)
env = UnityPy.load('unity/resources.assets')
n = 0
for o in env.objects:
    if o.type.name != 'TextAsset':
        continue
    d = o.read()
    if d.m_Name.startswith('Theme_'):
        raw = d.m_Script
        b = raw.encode('utf-8', 'surrogateescape') if isinstance(raw, str) else bytes(raw)
        open('maps/' + d.m_Name, 'wb').write(b)
        n += 1
        print(f'{len(b):9d}  {d.m_Name}')
print('skirmish bundles written:', n)
