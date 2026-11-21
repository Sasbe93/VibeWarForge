# Ability visuals 
Rule: every new hero ability gets a cast animation and visuals that fit what it does. No channel pose for
instant spells. Targeted damage needs a visible projectile and an impact effect. Checked by tools/check_ability_visuals.py
(exemption: `CHANNEL_OK <AbilId> <reason>` in war3map.j or the Design_Note).

## Base ability
- Use Channel (ANcl) only for spells that are really channeled (Ncl1 follow-through > 0, caster holds still, effect lasts).
- For instant spells, prefer a base with the right behaviour and art: Storm Bolt (AHtb), Shadow Strike (AEsh),
  Acid Bomb (ANab) or Chain Lightning (AOcl) for a missile at a unit; Blizzard, Flame Strike or Rain of Fire for areas;
  Thunder Clap or War Stomp for slams. Then trigger the custom effect on EVENT_UNIT_SPELL_EFFECT.
- If Channel is still used, set aani explicitly and also call SetUnitAnimation in the handler.

## Animation per type
| Type | aani / SetUnitAnimation |
|---|---|
| ranged spell at a unit or point | `spell`, or `spell throw` for throwing models |
| summoning a creature or familiar (owl, hawk) | `spell` (arm raised) or `attack` (a pointing or shooting gesture) |
| melee or physical strike | `attack`, `attack slam` |
| ground slam or nova | `spell slam`, `slam` |
| true channel (lasts n s) | `spell channel`, with follow-through = duration |

## Missiles
- Object-data missiles: set `amat` (missile art), `amsp` (speed) and `amac` (arc) on a missile base such as AHtb or AEsh.
- Dummy-unit projectile (any model): CreateUnit a locust dummy (`Aloc`, no shadow, fly height ~150) at the caster,
  give it the model (custom unit with `umdl` = `units\nightelf\Owl\Owl.mdl` (Scout owl), or
  `Abilities\Weapons\...Missile.mdl`). Move it with a 0.03 s timer toward the target (speed 900–1200, slight arc). On arrival:
  impact effect, damage, then KillUnit or RemoveUnit the dummy. Alternative: the dummy casts a missile ability on the target.
- Example (owl dive strike), done right: owl dummy (`units\nightelf\Owl\Owl.mdl`) dives from the caster to the target. On impact
  `Abilities\Spells\Other\Stun\StunTarget` or `Abilities\Weapons\GryphonRiderMissile`-style burst plus a feather/blood effect, and the stun begins.

## Impact effects
- On the target: AddSpecialEffectTarget(..., "chest"/"origin"), and destroy it right away (DestroyEffect).
- Areas: one effect per impact point (e.g. falling arrows → `Abilities\Weapons\Arrow\ArrowMissile` or Starfall caster art per arrow).
- Healing: Rejuvenation or Heal target art on "origin". It is not a projectile, so a missile is not required.
