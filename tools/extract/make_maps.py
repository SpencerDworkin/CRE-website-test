"""Build each map from a left half and mirror it, so both sides get identical
ground. Hand-counting rows produced maps that quietly favoured one team."""
SWAP = {'A': 'B', 'B': 'A'}

def mirror(half):
    return half + ''.join(SWAP.get(c, c) for c in reversed(half))

def build(halves, name):
    rows = [mirror(h) for h in halves]
    w = {len(r) for r in rows}
    assert len(w) == 1, f'{name}: ragged rows {w}'
    for r in rows:
        rev = ''.join(SWAP.get(c, c) for c in reversed(r))
        assert r == rev, f'{name}: row not symmetric: {r}'
    a = sum(r.count('A') for r in rows)
    b = sum(r.count('B') for r in rows)
    assert a == b, f'{name}: spawn imbalance {a} vs {b}'
    obj = sum(r.count('*') for r in rows)
    print(f'{name:22s} {len(rows[0])}x{len(rows)}  spawns {a}v{b}  objective {obj}')
    return rows

GARDENS = build([
    '#HH#HHHH#',
    'HAA,,,Lrr',
    'HAA,,,,,,',
    'H,HHH,,ff',
    '#,,,,,f**',
    'HLS,,r,f*',
    'HLS,,r,f*',
    '#,,,,,f**',
    'H,,fff,,,',
    'HAA,,,,,,',
    'HAA,,,Lrr',
    '#HH#HHHH#',
], 'Fountain Gardens')

SCRAP = build([
    '##########',
    '#AA~~~cc~~',
    '#AA~~~~~~~',
    '#~~~#~~~~~',
    '#~c~#~2~**',
    '#~~~x~2~**',
    '#~~~x~2~**',
    '#~c~#~2~**',
    '#~~~#~~~~~',
    '#AA~~~~~~~',
    '#AA~~~cc~~',
    '##########',
], 'Scrapyard Sunday')

CARPARK = build([
    '#########',
    '#AAAAAAAA',
    '#..c..r..',
    '#.###..22',
    '#..2....*',
    '#L.2.c.**',
    '#L.2.c.**',
    '#..2....*',
    '#.###..22',
    '#..c..r..',
    '#BBBBBBBB',
    '#########',
], 'Multi-Storey Mayhem')

# carpark spawns run along the top and bottom, so mirroring flips them - restore
CARPARK[1] = '#' + 'A' * 16 + '#'
CARPARK[10] = '#' + 'B' * 16 + '#'
assert len(CARPARK[1]) == 18 and len(CARPARK[10]) == 18

def emit(rows):
    return '\n'.join(f"      '{r}'," for r in rows).rstrip(',')

blocks = {
    'gardens': ("Fountain Gardens", 5,
                'Municipal park bounded by hedge. Flowerbeds, railings and statues around the green.',
                "{top:'#cdc4ae',left:'#7d7361',right:'#a29881'}", GARDENS),
    'scrap':   ("Scrapyard Sunday", 5,
                'Open dirt yard stacked with crates and wrecks. Long firing lanes, raised loading bays.',
                "{top:'#c9a86c',left:'#7a5a30',right:'#a07440'}", SCRAP),
    'carpark': ("Multi-Storey Mayhem", 6,
                'Split-level concrete deck. Railings along the drops, nowhere to hide crossing the middle.',
                "{top:'#cfd3da',left:'#767c88',right:'#9aa0ac'}", CARPARK),
}

out = ['const MAPS = [']
for mid, (name, turns, blurb, wall, rows) in blocks.items():
    out.append(f"  {{ id:'{mid}', name:'{name}', turns:{turns},")
    out.append(f"    blurb:'{blurb}',")
    out.append(f"    wall:{wall},")
    out.append("    rows:[")
    out.append(emit(rows))
    out.append("      ] },")
out.append('];')
open('maps_block.js', 'w').write('\n'.join(out) + '\n')
print('\nwrote maps_block.js')
