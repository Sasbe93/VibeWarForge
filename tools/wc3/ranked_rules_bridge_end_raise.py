"""bridge_end_raise: the ground rises toward both ends of every bridge (approach mound), so the bridge visibly
connects to the ground. FAIL when an end lands flat or sunken (rise <16 wu over the ground 6-9 tiles out), unless the
bridge climbs to another level (ground >=100 wu higher further out). Reference maps: raised ends rise median 47 wu;
many reference bridges still have a flat end - this rule is deliberately stricter. Logic: tools/lib/wc3/bridge_ends.py."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'lib', 'wc3'))
import bridge_ends as BE
def run(path, I, F): BE.run(path, I, F)
if __name__ == '__main__':
    for p in sys.argv[1:]:
        I, F = [], []; run(p, I, F); print(p); [print(' ', x) for x in I + F]
