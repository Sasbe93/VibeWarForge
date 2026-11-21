"""Generator helpers for rule scripted_reason (JASS snippets for mission build scripts; library jass_scripted_reason.j).
  pursue(group, leader)                    pursuers chase the leader (re-targeted every 2 s), never idle at a fixed point
  halt(group, stop_cause, shown)           a scripted halt / leash / return: stop_cause and shown are REQUIRED
  wait_cue(unit, name, line, x, y)         a companion that waits says so, is marked and the spot is pinged
Checked by tools/wc3/scripted_reason.py (run_all_checks)."""
def pursue(group, leader='gHero', ind='    '):
    return '%scall SR_Pursue(%s, %s)' % (ind, group, leader)
def halt(group, stop_cause, shown, ind='    '):
    if not stop_cause or not shown:
        raise ValueError('scripted_reason: a scripted halt needs a visible stop_cause (collapse, flood, barrier, leader order) and how it is shown')
    return '%s// STOP_CAUSE: %s :: %s\n%scall SR_Halt(%s, "%s")' % (ind, stop_cause, shown, ind, group, stop_cause.replace('"', "'"))
def wait_cue(unit, name, line, x, y, ind='    '):
    if not line: raise ValueError('scripted_reason: a companion wait needs a cue line')
    return '%scall SR_WaitCue(%s, "%s", "%s", %s, %s)' % (ind, unit, name.replace('"', "'"), line.replace('"', "'"), x, y)
