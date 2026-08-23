# RAD Soldiers — what the shipped client actually contains

Notes from examining the preserved 2012 Splash Damage / Warchest game, to establish how it
really worked rather than inferring mechanics from reviews and screenshots.

**No game content is stored in this repository.** These are notes and the scripts that
reproduce the extraction. Run them against your own copy of the archived client
(`archive.org/details/rad-soldiers`); the extracted data is Splash Damage's, not ours.

## Sources examined

| Archive file | MD5 verified | What it is |
|---|---|---|
| `rad-soldiers-assembly-csharp-decompiled.zip` | — | 1,583 decompiled C# files |
| `rad-soldiers-unity3d-unpacked-quickbms.zip` | `242381b6…0ec03` ✓ | the Unity 4.2 build, 17 files |
| `rad-soldiers.zip` | `c5236530…d67a3` ✓ | the Chrome App, 100 entries |

Obfuscation renamed library internals to CJK identifiers, but **the game classes kept their
real names** — `WeaponGameplayData`, `GameTileComponent`, `CoverMap` and ~525 others are
fully readable.

## Platform

The Chrome build is **NaCl** (`unity_nacl_files_3.x.x/{i686,x86_64}/unity.nexe`), not Unity
Web Player. Chrome removed Native Client, so the original client cannot run in any current
browser.

## Mechanics, from the real code

### Tiles — `GameTileComponent`

```
SolidNorth / SolidEast / SolidSouth / SolidWest     movement blocking, per edge
NorthCover / EastCover / SouthCover / WestCover     cover, per edge
VisBlocker                                          line-of-sight blocking, per tile
Height                                              elevation
TileIndexX / TileIndexY
```

Cover is **per edge, not per tile** — a wall belongs to the boundary between two tiles, so
what matters is the edge a shot crosses, not what occupies a neighbouring square.

`CoverMap` packs cover at **2 bits per tile** and computes it *relative to a source tile*,
confirming four cover states and directionality. Measured across all extracted levels
(23,624 edges): `0` → 20,445, `1` → 444, `2` → 648, `3` → 2,087.

Which integer means half vs. full vs. solid is inferred from frequency and not yet proven
from code — the cover resolution logic still needs reading.

### Weapons — `WeaponGameplayData`

```
RequiredActionPoints   AllowsReturnFire     SquadPoints (default 3)
MinRange / MaxRange    ShotsPerAttack       MaxUses
MinDamage              DamageSpread         Accuracy      CritChance
WeaponDamageFallOffCurve    (AnimationCurve over distance / MaxRange)
SplashRange / LineRange / WeaponSplashDamageFallOffCurve
KnockbackDistance / KnockbackRange          TwoStageAttack
```

### Abilities — `AbilityGameplayData`

```
RequiredAP  MaxUses  MinRange/MaxRange  Radius  Duration  APFraction
HealAmount  CanHealSelf  TickDamage  MaxHealth  ActionPoints
DamageBonus  DamageReduction  DamageModifier   MaxOpFirePerTurn
ThermalVisionRange   MaxDeployables   BuffType
```

### Global balance — `GenericGameplayData`

```
ReturnFireDamageScale      CriticalHitDamageScale
SquadPointsTierEntries     PlayFirstTurnImmediately
PlayerLevels / XPRewards   MatchRatings
```

Return fire and critical hits are scaled by dedicated tunables — the mechanics are real and
first-class, confirming that unspent AP driving return fire was the game's core idea.

## The balance numbers are gone

Every constant hangs off `VersionedGameData` (`WeaponData[]`, `AbilityData[]`, `GenericData`,
`RatingModifiers`, `XPLevels`, plus `int Version` and `IgnoreGameValidation`) — a
ScriptableObject **downloaded from the Fireteam backend at runtime** so balance could be
tuned live.

Scanning every shipped file — 4,048 MonoBehaviours across 17 asset files and 9 nested
`UnityWeb` bundles, **zero type-tree read failures** — finds no `VersionedGameData` asset.
The values were never in the client. With `tactics-warchest.live.wws.fireteam.net` offline
they are lost unless someone archived a payload.

The *schema* is fully known; only the numbers are missing.

## Levels — recovered

`Theme_01_Levels_Gameplay`, `Theme_01_Levels_Gameplay_DLC1` and `Theme_02_Levels_Gameplay_DLC1`
hold the gameplay grids, separate from the multi-megabyte art bundles.

15 grids, 14 complete with objectives. Sizes 14×16 to 32×26. Elevation is used heavily —
heights span −24 to +10. `TurnsToCaptureZone` is **5**, with some maps at **6**.

Capture zones and spawn points are components on the tile GameObjects themselves (100% of
them), so both map to exact tile coordinates. Spawns carry team and facing.

## Reproducing

```
pip install UnityPy
python3 dump_maps.py        # pull Theme_* bundles out of resources.assets
python3 build_levels.py     # -> levels_full/*.json, one per grid
python3 render_map.py maps/Theme_01_Levels_Gameplay   # ASCII view
```

Run from a directory containing `unity/` (the unpacked build). Verified against UnityPy
1.25.3 and Unity 4.2.0 assets.
