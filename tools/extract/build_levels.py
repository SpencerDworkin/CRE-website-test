import UnityPy, os, collections, json

OUT = 'levels_full'
os.makedirs(OUT, exist_ok=True)
made = []

for fn in sorted(os.listdir('maps')):
    path = os.path.join('maps', fn)
    if not os.path.isfile(path):
        continue
    try:
        env = UnityPy.load(path)
    except Exception:
        continue

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

    go_tr, tr_fa = {}, {}
    for pid, o in objs.items():
        if o.type.name == 'Transform':
            t = tree(pid)
            if not t:
                continue
            go = t.get('m_GameObject', {}).get('m_PathID')
            if go:
                go_tr[go] = pid
            tr_fa[pid] = t.get('m_Father', {}).get('m_PathID')

    grids, tile_by_go, zones, spawns, objectives = {}, {}, {}, {}, []
    for pid, o in objs.items():
        if o.type.name != 'MonoBehaviour':
            continue
        t = tree(pid)
        if not t:
            continue
        go = t.get('m_GameObject', {}).get('m_PathID')
        keys = set(t.keys())
        plain = keys - {'m_GameObject', 'm_Enabled', 'm_Script', 'm_Name'}
        if 'SizeX' in keys and 'SizeY' in keys:
            grids[go] = (t['SizeX'], t['SizeY'])
        elif 'TileIndexX' in keys:
            tile_by_go[go] = t
        elif plain == {'CaptureZone'}:
            zones[go] = t['CaptureZone']
        elif plain == {'Direction', 'Team'}:
            spawns[go] = (t['Team'], t['Direction'])
        elif 'TurnsToCaptureZone' in keys:
            objectives.append((go, t['TurnsToCaptureZone']))
    if not grids:
        continue

    def owner(go_pid):
        tr, n = go_tr.get(go_pid), 0
        while tr and n < 60:
            fa = tr_fa.get(tr)
            if not fa:
                return None
            ft = tree(fa)
            if not ft:
                return None
            fgo = ft.get('m_GameObject', {}).get('m_PathID')
            if fgo in grids:
                return fgo
            tr, n = fa, n + 1
        return None

    go_grid = {go: owner(go) for go in tile_by_go}
    obj_turns = {}
    for go, turns in objectives:
        obj_turns.setdefault(owner(go), []).append(turns)

    per = collections.defaultdict(lambda: {'tiles': [], 'capture': [], 'spawns': []})
    for go, t in tile_by_go.items():
        g = go_grid.get(go)
        if g is None:
            continue
        x, y = t['TileIndexX'], t['TileIndexY']
        per[g]['tiles'].append({
            'x': x, 'y': y, 'h': t['Height'], 'vis': int(t['VisBlocker']),
            'cover': [t['NorthCover'], t['EastCover'], t['SouthCover'], t['WestCover']],
            'solid': [int(t['SolidNorth']), int(t['SolidEast']), int(t['SolidSouth']), int(t['SolidWest'])],
        })
        if go in zones:
            per[g]['capture'].append([x, y])
        if go in spawns:
            team, direction = spawns[go]
            per[g]['spawns'].append({'x': x, 'y': y, 'team': team, 'dir': direction})

    for g, data in per.items():
        sx, sy = grids[g]
        if not data['tiles']:
            continue
        name = f'{fn}__{sx}x{sy}__{g}'
        turns = sorted(set(obj_turns.get(g, [])))
        out = {'source': fn, 'size': [sx, sy], 'turnsToCapture': turns,
               'tiles': data['tiles'], 'capture': data['capture'], 'spawns': data['spawns']}
        json.dump(out, open(os.path.join(OUT, name + '.json'), 'w'))
        made.append((name, sx, sy, len(data['tiles']), len(data['capture']), len(data['spawns']), turns))

made.sort(key=lambda r: r[3])
print(f'{"level":52s} {"grid":>7s} {"tiles":>6s} {"cap":>4s} {"spawn":>6s}  turns')
for name, sx, sy, nt, nc, ns, turns in made:
    print(f'{name[:52]:52s} {sx}x{sy:<4d} {nt:6d} {nc:4d} {ns:6d}  {turns}')
print(f'\ntotal levels: {len(made)}')
print('complete (have capture + spawns):', sum(1 for r in made if r[4] and r[5]))
