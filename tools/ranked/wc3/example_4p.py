"""(4) Example Glades 4P - WC3 2v2/FFA melee, 128x128 (112x112 playable) Ashenvale, 90-degree rotational symmetry (Twisted-Meadows style)."""
import sys; sys.path.insert(0,'tools/ranked/wc3'); from wc3melee import *
m=Melee(128,'rot4',651,'Example Glades 4P',4,'2-4 player melee (FFA or 2v2). 112x112 playable, 90-degree rotational symmetry. Each side: main, natural, 3 creep camps; shared middle with tavern.')
# P1 = south-west corner; rot4 copies to SE, NE, NW
m.disc((24,24),11)                        # main
m.disc((22,54),8)                         # natural
m.disc((64,64),11)                        # centre (tavern)
m.lane([(24,24),(36,36),(64,64)],4.2)     # main -> centre (diagonal)
m.lane([(24,24),(22,40),(22,54)],3.6)     # main -> natural
m.lane([(24,24),(44,20),(64,22)],3.6)     # main -> edge road toward the next corner (its rot4 image meets here)
m.lane([(22,54),(40,56),(64,64)],3.2)     # natural -> centre
m.disc((36,36),5.5); m.disc((44,20),5); m.disc((40,56),5); m.disc((64,22),6)
m.start((25,25),(-5,4))
m.expo((17,55),12500,'nat')
m.camp((36,37),['nwlg','nwlt','nwlt'],1)              # 8 first creep
m.camp((44,21),['ngnb','ngns','ngno'],1)              # 7 road creep
m.camp((23,50),['nogm','nogr','nogr','nmrm'],2)       # 14 natural guard
m.camp((41,57),['nfrb','nfrl','nfrs'],3)              # 14 centre-approach camp
m.camp((64,24),['nftk','nftb','nftr'],2)              # 12 edge camp between neighbours
m.add('ngme',(27,58),NP)
m.units.append(dict(id='ntav',x=0.0,y=0.0,a=270,o=NP,gold=0,tag='',side=0))
out='output/ranked/WC3_4p_Example_Glades_4P.w3x'
print(m.build(out))
