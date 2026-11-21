"""camp_strength creep camp count + strength vs the 14 reference ranked maps (external/refmaps/wc3/ref). Ranges = ref min/max."""
import camp_metrics
def ranges(np_):
    return [('camps_per_side',4.0,10.0),('lv_med',11.0,17.5),('lv_max',17,26),('max_creep',5,9),
            ('xp_side',1400 if np_==2 else 850,2950),('n_main',2.0,4.0),('lv_main',5.0,18.0),('lv_natural',11.0,19.5)]
def run(path,I,F):
    m=camp_metrics.metrics(path)
    I.append('camp_strength camps: %d (%.1f/side), camp levels min/med/max %d/%.1f/%d, green/orange/red %.0f/%.0f/%.0f%%, strongest creep L%d, XP/side %d, main %.1f x L%.1f, natural L%.1f, building %.1f x L%.1f, centre %d'%(
        m['camps'],m['camps_per_side'],m['lv_min'],m['lv_med'],m['lv_max'],100*m['green'],100*m['orange'],100*m['red'],m['max_creep'],m['xp_side'],m['n_main'],m['lv_main'],m['lv_natural'],m['n_building'],m['lv_building'],m['n_centre']))
    for k,lo,hi in ranges(m['players']):
        if not lo<=m[k]<=hi: F.append('camp_strength: %s %s outside reference range %s-%s'%(k,m[k],lo,hi))
    if m['n_building']>0 and m['lv_building']<13: F.append('camp_strength: neutral-building guards median L%.1f < reference min 13'%m['lv_building'])
    return m
