# RAD Squad Tactics

A turn-based squad tactics game for the browser, built as an original tribute to the 2012-era
mobile squad-tactics games whose servers have long since been switched off.

**It is one self-contained HTML file. Open `index.html` and play — no install, no build step, no server.**

---

## What this is (and is not)

This is **not** a copy or a revival of any commercial game. No original code, art, audio, character
likenesses, names, or map data from any shipped title are used here — none of it is public, and it is
not ours to redistribute. What is reproduced is the *design*: the tactical rules that made those games
worth playing, rebuilt from scratch.

Everything in this repository is original work:

- an original roster, with original names, classes and traits
- original maps
- original art, drawn procedurally on a `<canvas>` at runtime (there are no image files at all):
  an isometric board rendered with depth-sorted 3D blocks, and chunky heavy-outlined cartoon
  operatives with segmented health rings at their feet
- original audio, synthesised in the browser with the WebAudio API (there are no sound files either)
- an original rules engine, AI opponent and UI

## The design it recreates

The genre signature these games shared, and what this rebuilds:

| Mechanic | How it works here |
|---|---|
| **Energy as one currency** | Each operative gets a pool per turn and pays for *everything* out of it — 2 per tile moved, 3 through rubble, 4–8 to fire depending on the weapon, 4–6 for abilities. |
| **Unspent energy is return fire** | Whatever an operative does not spend is what they shoot with on the opponent's turn. Move an enemy into their sight line and they take a snap shot — once per turn, at −15 accuracy and 60% damage. Emptying a soldier wins the fight in front of you; leaving them loaded wins the next one. |
| **Three-state directional cover** | Green (full, behind a wall, −40 to the shooter), yellow (half, behind sandbags or a wreck, −20), red (flanked, full accuracy **and +50% damage**). Cover is computed per shot from the attack direction, so moving two tiles sideways is often worth more than a second shot. |
| **King-of-the-hill objective** | Hold the marked zone *uncontested* at the end of a round to score. First to 5 wins. Wiping out the enemy also wins, as does leading on objective score when the round limit expires. |
| **Points-bought squads** | An operative costs exactly what their weapon costs, so a 14-point squad is three lightly-armed bodies or two well-armed ones. Budgets of 14 / 20 / 26 points, 2–5 operatives. |
| **Five classes** | Commando (suppress), Medic (heal), Engineer (build cover), Captain (hand an ally extra energy), Agent (smoke). Each operative also has a trait that bends one rule in their favour. |

## Modes

- **Campaign** — five missions on a difficulty curve, with progress saved to `localStorage`.
- **Skirmish** — pick a budget, build a squad, choose a map, fight a randomly-generated AI squad.
- **Pass & Play** — two players on one device, both squads mirrored for a fair match.

## Controls

Tap an operative to select. Blue tiles are reachable; the darker blue ones cost so much to reach that
there would be no energy left to shoot. Tap a bracketed enemy to fire — hover first for the odds,
the cover state and the damage band. The ability button targets separately.

Keyboard: `Tab` cycles operatives, `Enter` ends the turn, `Esc` cancels ability targeting.

## Project layout

```
index.html                the entire game — markup, styles and engine
tools/artifact-body.sh    strips the HTML wrapper off index.html for embedding elsewhere
```

`index.html` is the whole game and the only file you need — edit it directly. `tools/artifact-body.sh`
exists only to derive an embeddable, wrapper-free copy for hosting the page inside another document.

## Balance

The rules were tuned against automated self-play rather than guesswork:

- **Mirror matches** (identical squads, AI driving both sides, 8 matches across all three maps):
  **4–4**, average 5.1 rounds, with the objective scored in 8 of 8 matches and 3 decided on the hold
  alone. First-mover advantage is compensated by giving the second team +4 energy on the opening round —
  before that compensation the first mover won 7 of 8.
- **Campaign** (AI driving the player's squad at each mission's budget): wins 2 of 5. A human plays
  better than this AI, so the campaign is winnable but not a walkover. Every enemy squad is costed
  at or near the player's own budget — difficulty ramps on composition, not on a points advantage.

## Known limitations

- **Single device only.** The original games were built around asynchronous online multiplayer; there
  is no server here, so head-to-head is hot-seat on one screen.
- The AI is a one-ply heuristic — it scores every reachable tile for cover, exposure, shot quality and
  objective pressure, but it does not look ahead a turn or coordinate between operatives.
- Three maps, ten recruits, seven weapons, five missions. The data tables at the top of the script are
  plain objects; adding more of any of them requires no engine changes.
- No elevation, no destructible terrain, no overwatch cones (return fire is omnidirectional).
