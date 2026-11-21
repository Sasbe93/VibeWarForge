"""market_stock (ranked): a Marketplace (nmrk) only sells what Blizzard.j allows: InitNeutralBuildings -> after 120 s, every 30 s one
random item of a type/level that was enabled by UpdateStockAvailability, which is called only by UnitDropItem (WE creep drop code).
FAIL: nmrk on the map but no creep drop goes through UnitDropItem/UpdateStockAvailability (market stays empty all game),
or InitBlizzard missing. FAIL: a shop (ngme/ngad/nmer...) with custom stock removed. Refs: 29/67 have nmrk, 67/67 ngme, all 67 use UnitDropItem."""
import sys,re
sys.path.insert(0,'tools/wc3')
from w3parse import MPQ
def script(path):
    m=MPQ(open(path,'rb').read())
    for k in ('war3map.j','scripts\\war3map.j','war3map.lua'):
        try:
            j=m.read(k)
            if j: return j.decode('latin1')
        except Exception: pass
    return ''
def run(path,I,F):
    j=script(path); mk=len(re.findall(r"['\"]nmrk['\"]",j)); sh=len(re.findall(r"['\"](ngme|ngad|nmer)['\"]",j))
    drop='UnitDropItem' in j or 'UpdateStockAvailability' in j; ib='InitBlizzard' in j
    I.append('market_stock markets %d, shops %d, drops via UnitDropItem/UpdateStockAvailability %s, InitBlizzard %s'%(mk,sh,drop,ib))
    if mk and not drop: F.append('market_stock: Marketplace without stock source - creep drops use CreateItem, not UnitDropItem/UpdateStockAvailability (market stays empty)')
    if (mk or sh) and not ib: F.append('market_stock: InitBlizzard missing - neutral shops/market stock never initialised')
if __name__=='__main__':
    for p in sys.argv[1:]:
        I=[];F=[]; run(p,I,F); print(p.split('/')[-1],I,F)
