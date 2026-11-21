"""Quest text helpers (rules survival_quest_text and progress announcements; checked by survival_quest_text.py and
scripted_reason.py progress_unannounced).
  survival_item(name)                       -> "<name> must survive"   (never 'until', 'before', 'must reach')
  survival_rule(names)                      -> "The mission is lost if A or B falls."
  heroic_death_update(item, name, deed)     -> JASS: update + complete the survival item in the death scene
  announce(speaker, name, line, item, text) -> JASS: plain in-game line + quest item update for a progress condition"""
import re
_BAD = re.compile(r'\b(until|till|before|as long as|by the time|reach(?:es)?|while)\b', re.I)
def _clean(s):
    if _BAD.search(s): raise ValueError('quest_text: no end condition or timing in survival texts: %r' % s)
    return s.replace('"', "'")
def survival_item(name): return _clean('%s must survive' % name)
def survival_rule(names):
    n = list(names); s = n[0] if len(n) == 1 else ', '.join(n[:-1]) + ' or ' + n[-1]
    return _clean('The mission is lost if %s falls.' % s)
def heroic_death_update(item, name, deed, ind='    '):
    return '%scall QuestItemSetDescription(%s, "%s")\n%scall QuestItemSetCompleted(%s, true)' % (ind, item, ('%s %s' % (name, deed)).replace('"', "'"), ind, item)
def announce(speaker, name, line, item=None, text=None, ind='    '):
    out = '%scall SR_Announce(%s, "%s", "%s")' % (ind, speaker, name.replace('"', "'"), line.replace('"', "'"))
    if item and text: out += '\n%scall QuestItemSetDescription(%s, "%s")\n%scall FlashQuestDialogButton()' % (ind, item, text.replace('"', "'"), ind)
    return out
