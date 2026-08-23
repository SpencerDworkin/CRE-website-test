# RAD Soldiers — 3D recreation

A playable rebuild of the 2012 Splash Damage mobile tactics game, rendered with
the game's own level and character art and a re-implementation of its turn
rules.

Nothing in this folder contains any game content. You point the build script at
your own copy of the archived client and it extracts what the browser needs.

## Build and run

```
pip install UnityPy Pillow
python3 build.py --bundles /path/to/asset/bundles
python3 serve.py
```

`build.py` writes `play/play.json`, `play/units.json` and `play/tex/*.png`.
`serve.py` serves the folder and opens the game. The page is an ES module and
fetches its data, so it has to come off a server — opening `game.html` straight
off disk will not work in any browser.

`--level` picks which level bundle to play on; it defaults to
`Theme_01_Skirmish_09`, the memorial garden. Any `Theme_*_Skirmish_*` bundle
works — the tactical grid is measured off whatever geometry it finds.

## Controls

| | |
|---|---|
| click an operative | select |
| click a blue tile | move there |
| hover an enemy | shot readout — hit chance, damage, cover |
| click an enemy | fire |
| `A` / `D` or arrows | rotate the camera |
| `+` / `-` | zoom |
| `Enter` or End turn | end your turn |

## How it plays

Hold the objective — the ground around the memorial — for three rounds, or wipe
out the other squad. Sixteen rounds, then it goes on objective score.

Each operative spends AP to move (1 per tile) and to shoot. **AP you don't
spend is AP you keep**: anyone with enough left to fire will take a reaction
shot at an enemy that moves through their line of fire, at reduced accuracy and
damage. Moving across open ground in front of a squad that has held its AP is
how you lose people.

Cover is read off the edge between two tiles, not off the tile itself, so it
matters which side a shot comes from. Low cover (a kerb, a flowerbed) costs the
shooter 20 accuracy, hard cover (a hedge, a bench) 35, a wall 55 — and anything
from hard cover upward blocks line of sight entirely. A target with **no** cover
on the side you are shooting from is flanked, and takes 50% more damage. Most
of the tactical game is manoeuvring for that.

Both squads field the same four stat lines, so a match is decided by ground and
dice rather than by the roster. Spawns are matched on walking distance to the
objective — the garden is a hedge maze and one flank has a much clearer run than
the other, which otherwise handed that side the match.

## Balance, and how it was measured

Tuned against self-play, not guesswork: `game.html` exposes `window.__game`, and
the harness drives the same AI on both sides for a batch of matches inside one
page load.

Over 40 mirror matches the side that moves first won 24. Matches run about
8–9 rounds. Getting there took three passes:

- The first roster had one squad 30% ahead on health alone — it won 6 of 6.
  Hence the identical stat lines.
- Spawns picked by straight-line distance put one squad 2 tiles from the
  objective after its first turn and the other 11 away. Hence the walking-distance
  match.
- The AI scored its approach on straight-line distance too, so it would sit at
  4 tiles from the objective for ten rounds, unable to see that the railings meant
  a 15-step walk. It now scores on the same walking distance.
- Weapon damage started at roughly double what it is now: every match was over by
  round 6 with both squads dead and the objective never contested.

One thing the numbers say plainly: left to itself the AI fights it out to a wipe,
so all 40 matches were decided by elimination rather than on the hold. The hold
condition is there for a player who defends ground instead of trading shots.

## Where the numbers come from

The original balance data was served from Splash Damage's Fireteam backend, not
shipped in the client — every one of the 4,048 MonoBehaviours in the archive was
read looking for it and it is not there. The *schema* survives in the decompiled
client, so the shape of the rules is known: AP economy, per-edge cover, reaction
fire from held AP, flanking, accuracy falloff past a weapon's optimal range,
sniper penalty at close quarters. **The numbers in this build are mine**, tuned
by simulation, not recovered.

## How the board is built

The archive does not bind a Skirmish art level to a gameplay grid — the scene
that placed one against the other was never in the client, and pairing the
shipped grids against the art measures out at 0.29 open-clear, i.e. no better
than chance. So the grid is measured off the art instead: every triangle in the
level is rasterised onto a quarter-tile lattice, a tile is stand-able when its
middle is clear, and cover comes from the height of whatever sits on the
boundary between two tiles. The playable arena is then the largest region you
can actually walk around in, which comes out as the garden interior with the
ring road outside it correctly excluded.

## Credits

RAD Soldiers is © Splash Damage. This is a fan recreation for a game whose
servers were shut down; the art and models are the original game's and are
extracted locally from your own copy. Rendering is [three.js](https://threejs.org)
(MIT).
