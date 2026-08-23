/* Measure a tactical grid off a level's geometry.
 *
 * The archive never bound a Skirmish art level to a gameplay grid - the scene
 * that placed one against the other was not in the shipped client - so the
 * board is measured off the art. Every triangle is rasterised onto a
 * quarter-tile lattice; a tile is stand-able when its middle is clear, and
 * cover comes from the height of whatever sits on the boundary between two
 * tiles, which is the same per-edge cover model the original used.
 */

const S = 4;                       // lattice cells per tile
const STEP = 1 / S;
const HEAD = 2.6;                  // canopies and awnings above this do not obstruct
const CLEAR = 0.35;                // taller than this counts as cover
const STEP_OVER = 0.95;            // ...but you can still walk over it up to here
const OFF = 1024;

export const DIRS = [[0,-1],[1,0],[0,1],[-1,0]];        // N E S W
export const dirIx = (dx, dy) => dx ? (dx > 0 ? 1 : 3) : (dy > 0 ? 2 : 0);
const coverOf = h => h < CLEAR ? 0 : h < 1.5 ? 1 : h < 2.4 ? 2 : 3;

export function buildGrid(L) {
  const OOBTEX = L.textures.indexOf('T_OOB_FADE_02_d.png');
  const key = (sx, sz) => (sx + OFF) * 4096 + (sz + OFF);
  const top = new Map(), floor = new Map(), oob = new Set();

  function deposit(sx, sz, y, tex) {
    const k = key(sx, sz);
    if (y <= HEAD) { const t = top.get(k); if (t === undefined || y > t) top.set(k, y); }
    if (y < 0.5) {
      const f = floor.get(k);
      if (f === undefined || y < f) floor.set(k, y);
      if (tex === OOBTEX) oob.add(k);
    }
  }
  const SI = v => Math.floor(v * S);

  for (const n of L.nodes) {
    const m = L.meshes[n.mesh], P = m.pos, I = m.idx;
    for (let t = 0; t < I.length; t += 3) {
      const a = I[t]*3, b = I[t+1]*3, c = I[t+2]*3;
      const ax=P[a],ay=P[a+1],az=P[a+2], bx=P[b],by=P[b+1],bz=P[b+2], cx=P[c],cy=P[c+1],cz=P[c+2];
      deposit(SI(ax),SI(az),ay,n.tex); deposit(SI(bx),SI(bz),by,n.tex); deposit(SI(cx),SI(cz),cy,n.tex);
      const x0=SI(Math.min(ax,bx,cx)), x1=SI(Math.max(ax,bx,cx));
      const z0=SI(Math.min(az,bz,cz)), z1=SI(Math.max(az,bz,cz));
      if ((x1-x0+1)*(z1-z0+1) <= 1) continue;
      const d = (bz-cz)*(ax-cx) + (cx-bx)*(az-cz);
      if (Math.abs(d) < 1e-9) continue;
      for (let ix=x0; ix<=x1; ix++) for (let iz=z0; iz<=z1; iz++) {
        const px=(ix+0.5)*STEP, pz=(iz+0.5)*STEP;
        const w1=((bz-cz)*(px-cx)+(cx-bx)*(pz-cz))/d;
        const w2=((cz-az)*(px-cx)+(ax-cx)*(pz-cz))/d;
        const w3=1-w1-w2;
        if (w1<-.001||w2<-.001||w3<-.001) continue;
        deposit(ix, iz, w1*ay+w2*by+w3*cy, n.tex);
      }
    }
  }

  const H = (sx, sz) => { const v = top.get(key(sx, sz)); return v === undefined ? -99 : v; };

  let minx=1e9,maxx=-1e9,minz=1e9,maxz=-1e9;
  for (const k of top.keys()) {
    const sx = Math.floor(k / 4096) - OFF, sz = (k % 4096) - OFF;
    const x = Math.floor(sx / S), z = Math.floor(sz / S);
    if (x<minx) minx=x; if (x>maxx) maxx=x;
    if (z<minz) minz=z; if (z>maxz) maxz=z;
  }
  const W = maxx-minx+1, GH = maxz-minz+1;

  const cells = new Map();
  for (let x = minx; x <= maxx; x++) for (let z = minz; z <= maxz; z++) {
    const bx = x*S, bz = z*S;
    let ground = 0, fl = null, ob = 0;
    for (let i=0;i<S;i++) for (let j=0;j<S;j++) {
      const f = floor.get(key(bx+i, bz+j));
      if (f !== undefined) { ground++; if (fl === null || f < fl) fl = f; }
      if (oob.has(key(bx+i, bz+j))) ob++;
    }
    if (!ground) continue;
    let mid = -99;                                    // the middle has to be clear to stand on
    for (let i=1;i<3;i++) for (let j=1;j<3;j++) mid = Math.max(mid, H(bx+i, bz+j));
    cells.set(x+','+z, { gx: x, gz: z, x: x-minx, y: z-minz,
                         floor: fl === null ? 0 : fl, oob: ob > 4, stand: mid < STEP_OVER });
  }

  function edgeH(t, dx, dz) {                         // tallest thing straddling the boundary
    const bx = t.gx*S, bz = t.gz*S;
    let h = -99;
    if (dx) {
      const i = dx > 0 ? S-1 : 0, ni = dx > 0 ? S : -1;
      for (let j=0;j<S;j++) h = Math.max(h, H(bx+i, bz+j), H(bx+ni, bz+j));
    } else {
      const j = dz > 0 ? S-1 : 0, nj = dz > 0 ? S : -1;
      for (let i=0;i<S;i++) h = Math.max(h, H(bx+i, bz+j), H(bx+i, bz+nj));
    }
    return h;
  }

  for (const t of cells.values()) {
    t.c = []; t.p = 0;
    DIRS.forEach(([dx, dz], i) => {
      const n = cells.get((t.gx+dx)+','+(t.gz+dz));
      const h = edgeH(t, dx, dz);
      t.c.push(coverOf(h));
      if (h < STEP_OVER && n && n.stand && !n.oob && Math.abs(n.floor - t.floor) < 0.8) t.p |= 1 << i;
    });
  }

  /* the arena is the largest region you can actually walk around in - here that
     is the garden interior, with the ring road outside it a separate island */
  const seen = new Set(), comps = [];
  for (const t of cells.values()) {
    if (!t.stand || t.oob || seen.has(t)) continue;
    const st = [t]; seen.add(t); const c = [];
    while (st.length) {
      const cu = st.pop(); c.push(cu);
      DIRS.forEach(([dx, dz], i) => {
        if (!(cu.p & (1 << i))) return;
        const n = cells.get((cu.gx+dx)+','+(cu.gz+dz));
        if (n && !seen.has(n)) { seen.add(n); st.push(n); }
      });
    }
    comps.push(c);
  }
  comps.sort((a, b) => b.length - a.length);
  const arena = new Set(comps[0] || []);

  const tiles = [...cells.values()].map(t => ({
    x: t.x, y: t.y, w: [t.gx + 0.5, t.floor, t.gz + 0.5],
    c: t.c, p: t.p, a: arena.has(t) ? 1 : 0,
  }));
  return { grid: [W, GH], origin: [minx, minz], tiles, arena: arena.size };
}
