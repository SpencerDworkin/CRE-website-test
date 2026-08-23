import UnityPy, sys, collections, json

env = UnityPy.load(sys.argv[1])

# index every object in the bundle by path_id
objs = {}
for o in env.objects:
    objs[o.path_id] = o

tt_cache = {}
def tree(pid):
    if pid in tt_cache:
        return tt_cache[pid]
    o = objs.get(pid)
    if o is None:
        return None
    try:
        t = o.read_typetree()
    except Exception:
        t = None
    tt_cache[pid] = t
    return t

# GameObject path_id -> its Transform path_id, and Transform -> father
go_transform = {}
transform_father = {}
for pid, o in objs.items():
    if o.type.name == 'Transform':
        t = tree(pid)
        if not t:
            continue
        go = t.get('m_GameObject', {}).get('m_PathID')
        fa = t.get('m_Father', {}).get('m_PathID')
        if go:
            go_transform[go] = pid
        transform_father[pid] = fa

grids = {}   # GameObject pid -> (SizeX, SizeY)
tiles = []   # (owner GameObject pid, tile dict)
for pid, o in objs.items():
    if o.type.name != 'MonoBehaviour':
        continue
    t = tree(pid)
    if not t:
        continue
    if 'SizeX' in t and 'SizeY' in t:
        grids[t['m_GameObject']['m_PathID']] = (t['SizeX'], t['SizeY'])
    elif 'TileIndexX' in t:
        tiles.append((t['m_GameObject']['m_PathID'], t))

def owner_grid(go_pid):
    seen = 0
    tr = go_transform.get(go_pid)
    while tr and seen < 40:
        fa = transform_father.get(tr)
        if not fa:
            return None
        ft = tree(fa)
        if not ft:
            return None
        fgo = ft.get('m_GameObject', {}).get('m_PathID')
        if fgo in grids:
            return fgo
        tr = fa
        seen += 1
    return None

buckets = collections.defaultdict(list)
for go_pid, t in tiles:
    g = owner_grid(go_pid)
    buckets[g].append(t)

print('grids:', {str(k): v for k, v in grids.items()})
for g, ts in buckets.items():
    if g is None:
        print('unassigned tiles:', len(ts)); continue
    sx, sy = grids[g]
    print(f'\n=== grid {g}  {sx}x{sy}  tiles={len(ts)} ===')
    json.dump({'size': [sx, sy], 'tiles': ts}, open(f'maps/grid_{g}.json', 'w'))
    cells = {(t['TileIndexX'], t['TileIndexY']): t for t in ts}
    heights = collections.Counter(t['Height'] for t in ts)
    covers = collections.Counter()
    for t in ts:
        for e in ('WestCover', 'EastCover', 'NorthCover', 'SouthCover'):
            covers[t[e]] += 1
    print('height histogram:', dict(sorted(heights.items())))
    print('cover-value histogram (per edge):', dict(sorted(covers.items())))
    print('VisBlocker tiles:', sum(1 for t in ts if t['VisBlocker']))
    for y in range(sy):
        row = ''
        for x in range(sx):
            t = cells.get((x, y))
            if t is None:
                row += ' '
            elif t['VisBlocker']:
                row += '#'
            elif max(t['WestCover'], t['EastCover'], t['NorthCover'], t['SouthCover']) >= 2:
                row += 'H'
            elif max(t['WestCover'], t['EastCover'], t['NorthCover'], t['SouthCover']) == 1:
                row += 'o'
            elif t['Height']:
                row += str(min(9, t['Height']))
            else:
                row += '.'
        print(row)
    break
