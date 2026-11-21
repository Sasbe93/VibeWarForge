"""Generator helpers for the mission-flow rules (library jass_mission_flow.j):
  race(...)          rule race_fairness: computes the hold-back delay from the player's realistic position and refuses an
                     unfair race; returns the JASS for warning line + ping + delayed release
  escort_go(...)     rule escort_orders: one move order for the whole crowd, armed escorts passive, idle-only keeper
  captive(...)       rule captive_puzzle: hint line on approach, release only by a player ability / killing the binding
  ability_use(...)   rule ability_mission_use: the design-note line for a player ability (situation + hook)
  rescue_before(...) rule rescue_order: layout-time test that a rescue lies before the objective it helps with
Checked by race_fairness.py, escort_orders.py, captive_puzzle.py, ability_mission_use.py, rescue_order.py (run_all_checks)."""
import math
BUFFER = {0: 15.0, 1: 10.0, 2: 6.0, 3: 4.0}
def race(release_fn, player_path, hero_speed, enemy_path, enemy_speed, speaker, name, line, x, y, ind='    '):
    """Hold the enemy back (per difficulty, gDiff 0..3) until the player can make it with the buffer. Paths in wu, the
    player path measured from the FARTHEST place the player can be when the race starts (e.g. the last objective)."""
    if not line: raise ValueError('race_fairness: a race needs a warning line and ping')
    ds = []
    for d in range(4):
        ds.append(max(0.0, player_path / hero_speed + BUFFER[d] - enemy_path / enemy_speed))
    return ('%s// RACE: player %.0f wu / %.0f, enemy %.0f wu / %.0f, delays %s\n' % (ind, player_path, hero_speed, enemy_path, enemy_speed, '/'.join('%.0f' % v for v in ds)) +
            '%scall MF_RaceWarn(%s, "%s", "%s", %s, %s)\n' % (ind, speaker, name.replace('"', "'"), line.replace('"', "'"), x, y) +
            '%scall TriggerSleepAction(DS_Scale(%.1f, %.1f, %.1f, %.1f))\n' % (ind, ds[0], ds[1], ds[2], ds[3]) +
            '%scall %s()' % (ind, release_fn))
def escort_go(group, x, y, ind='    '):
    return '%scall MF_EscortGo(%s, %s, %s)' % (ind, group, x, y)
def captive(unit, bind, abil, hint_fn, done_fn, ind='    '):
    """hint_fn: function with the captive's hint line (what binds it, not the solution); done_fn: after the release.
    Both need a trigger each: returns the JASS that creates them and registers the captive."""
    return ('%sset gMFTmpH = CreateTrigger()\n%scall TriggerAddAction(gMFTmpH, function %s)\n' % (ind, ind, hint_fn) +
            '%sset gMFTmpD = CreateTrigger()\n%scall TriggerAddAction(gMFTmpD, function %s)\n' % (ind, ind, done_fn) +
            "%scall MF_CaptiveAdd(%s, %s, '%s', gMFTmpH, gMFTmpD)" % (ind, unit, bind or 'null', abil))
CAPTIVE_GLOBALS = '    trigger gMFTmpH = null\n    trigger gMFTmpD = null\n'
def ability_use(aid, situation, hook, encounter=False):
    if len(situation.split()) < 6: raise ValueError('ability_mission_use: situation for %s too short' % aid)
    return 'ABILITY_USE %s :: %s ; hook %s%s' % (aid, situation, 'encounter ' if encounter else '', hook)
def rescue_before(start, rescue, objective, dist=None, on_way=1.25):
    """True if the rescue lies before the objective it helps with (straight-line fallback when no path function given)."""
    dist = dist or (lambda a, b: math.hypot(a[0] - b[0], a[1] - b[1]))
    d0, a, b = dist(start, rescue), dist(start, objective), dist(objective, rescue)
    return not (a < d0 and a + b <= on_way * d0)
