"""(2) Example Glade 2P - WC3 1v1 melee, 96x96 (80x80 playable) Ashenvale, 180-degree rotation. Echo-Isles/Concealed-Hill-size."""
import sys; sys.path.insert(0,'tools/ranked/wc3'); from wc3melee import *
m=Melee(96,'rot2',650,'Example Glade 2P',2,'1v1 melee. 80x80 playable, 180-degree rotational symmetry. Each side: main, natural, far expansion, 4 creep camps. Tavern in the centre.')
# clearings and lanes (cell coords, P1 = south-west)
m.disc((22,22),11)                      # main
m.disc((19,52),8); m.disc((54,19),8) # natural (north) and far expansion (east)
m.disc((48,48),10)                      # centre (tavern)
m.lane([(22,22),(32,33),(48,48)],4.2)    # main -> centre
m.lane([(22,22),(20,40),(19,52)],3.6)    # main -> natural
m.lane([(22,22),(38,17),(54,19)],3.6)    # main -> far expansion
m.lane([(19,52),(32,62),(41,77)],3.4)    # natural -> enemy far expansion (flank route)
m.lane([(32,62),(48,48)],3.0)            # flank -> centre
m.disc((32,33),5.5); m.disc((38,17),5); m.disc((32,62),6); m.disc((40,30),4)
# objects
m.start((23,23),(-5,4))                  # start location + main mine (12500)
m.expo((15,53),12500,'nat'); m.expo((55,15),10000,'far')
m.add('ntav',(48,48),NP) if False else None
m.camp((32,34),['nwlg','nwlt','nwlt'],1)               # 8  : first creep near main
m.camp((39,18),['ngnb','ngns','ngno'],1)               # 7  : second creep on the far-expo road
m.camp((21,48),['nogm','nogr','nogr','nmrm'],2)        # 14 : natural guard
m.camp((54,23),['nftk','nftb','nftr','nftr'],2)        # 14 : far expansion guard
m.camp((33,63),['nfrb','nfrl','nfrs'],3)               # 14 : flank camp (drop level 3)
m.add('ngme',(24,57),NP); m.add('ngad',(59,22),NP)
out='output/ranked/WC3_2p_Example_Glade_2P.w3x'
# tavern exactly on the centre (self-symmetric): add once
m.units.append(dict(id='ntav',x=0.0,y=0.0,a=270,o=NP,gold=0,tag='',side=0))
print(m.build(out))
