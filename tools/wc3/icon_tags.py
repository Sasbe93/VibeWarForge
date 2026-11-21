"""Stock icon tag table for icon_fit. Tags = what the picture SHOWS. 'portrait' = a unit/hero face: never fits a spell."""
CONCEPT = {   # tooltip/name words -> concept tag
 'harpoon':'spear','spear':'spear','javelin':'spear','lance':'spear','hurl':'throw','throw':'throw','fling':'throw','toss':'throw',
 'rope':'rope','tether':'rope','reel':'rope','haul':'rope','pull':'rope','leash':'rope','chain':'rope','bind':'root','pin':'root',
 'ice':'ice','floe':'ice','frost':'ice','glacier':'ice','snow':'ice','freeze':'ice','thaw':'heal','cold':'ice',
 'horn':'horn','sound':'horn','bellow':'shout','roar':'shout','taunt':'shout','shout':'shout',
 'heal':'heal','regain':'heal','restore':'heal','mend':'heal','rejuvenat':'heal','sap':'heal','cleans':'heal',
 'charge':'charge','dash':'charge','ram':'charge','stampede':'charge','herd':'charge','batter':'charge','avalanche':'charge',
 'ward':'shield','shield':'shield','absorb':'shield','armor':'shield','bark':'shield','hide':'shield','skin':'shield',
 'water':'water','sea':'water','brine':'water','tide':'water','wave':'water','oil':'water','slick':'slow','slow':'slow',
 'web':'web','silk':'web','thread':'web','egg':'spider','hatch':'spider','spiderling':'spider','brood':'spider',
 'burrow':'burrow','dig':'burrow','gnaw':'burrow','cave':'burrow','collapse':'quake','stomp':'quake','slam':'quake','split':'quake','earth':'quake',
 'thorn':'thorn','bramble':'thorn','root':'root','entangl':'root','poison':'poison','venom':'poison','toxic':'poison',
 'fire':'fire','cinder':'fire','fel':'fire','burn':'fire','infernal':'fire','hellfire':'fire','bear':'bear','ursoc':'bear','ursine':'bear',
 'drum':'drum','beat':'drum','cadence':'drum','invisib':'stealth','veil':'stealth','smell':'detect','nose':'detect','reveal':'detect',
 'crit':'strike','fury':'strike','bash':'strike','maul':'strike','lash':'whip','whip':'whip','aura':'aura','pulse':'aura','spirit':'spirit','pact':'fire',
}
ICON = {
 'BTNImpale':{'spike','quake','burrow'}, 'BTNGlacier':{'ice','quake'}, 'BTNHornOfCenarius':{'horn'}, 'BTNShockWave':{'charge','quake','wave'},
 'BTNTuskaarNomad':{'portrait'}, 'BTNTuskaarBlack':{'portrait'}, 'BTNTuskaarBrown':{'portrait'}, 'BTNTuskaarGold':{'portrait'},
 'BTNSlowOn':{'slow'}, 'BTNInnerFireOn':{'shield','fire'}, 'BTNRejuvenation':{'heal'}, 'BTNBatteringCharge':{'charge'},
 'BTNOilSlick':{'water','slow','fire'}, 'BTNParasite':{'spider','web','poison'}, 'BTNSpiderling':{'spider'}, 'PASBTNRegenerationAura':{'heal','aura'},
 'BTNFrostArmor':{'ice','shield'}, 'BTNCryptFiendBurrow':{'burrow','spider'}, 'BTNWeb':{'web','root','rope'}, 'PASBTNCorrosiveBreath':{'poison','spider'},
 'BTNEntanglingRoots':{'root','thorn'}, 'BTNWarStomp':{'quake','strike'}, 'PASBTNThickFur':{'shield','bear'}, 'BTNGrizzlyBear':{'bear','spirit'},
 'BTNBanditSpearThrower':{'spear','throw','portrait'}, 'BTNThorns':{'thorn'}, 'BTNScout':{'detect'}, 'BTNStampede':{'charge'},
 'BTNPandaTaunt':{'shout'}, 'PASBTNBash':{'strike'}, 'BTNMoonWell':{'water','heal'}, 'BTNShadowStrike':{'whip','poison','strike'},
 'BTNFire':{'fire'}, 'PASBTNDrum':{'drum','aura'}, 'BTNInfernal':{'fire'}, 'PASBTNInvisibility':{'stealth'}, 'BTNEnvenomedSpear':{'spear','poison'},
 'BTNThornShield':{'thorn','shield'}, 'BTNHardenedSkin':{'shield'}, 'PASBTNCriticalStrike':{'strike'}, 'BTNFireRocks':{'fire'},
 # candidates for proposals
 'BTNEnsnare':{'rope','root','throw'}, 'BTNSpiritLink':{'rope','spirit'}, 'BTNMagicLariet':{'rope','throw'}, 'BTNHeadhunterBerserker':{'spear','throw','portrait'},
 'BTNFrostBolt':{'ice','throw'}, 'BTNBreathOfFrost':{'ice'}, 'BTNCrushingWave':{'water','charge'}, 'BTNLiquidFire':{'fire','throw','water'},
 'BTNSlow':{'slow'}, 'BTNStormBolt':{'throw','strike'}, 'BTNHolyBolt':{'heal'}, 'BTNSpikedBarricades':{'spike'},
}
PROPOSE = {'spear':'BTNEnsnare (rope throw) or a generated icon: barbed harpoon with a trailing rope', 'rope':'BTNMagicLariet (thrown rope) / BTNEnsnare',
           'throw':'BTNLiquidFire (thrown flask) / BTNStormBolt', 'ice':'BTNFrostBolt / BTNBreathOfFrost', 'charge':'BTNStampede / BTNBatteringCharge',
           'shield':'BTNFrostArmor / BTNHardenedSkin', 'heal':'BTNRejuvenation / BTNHolyBolt', 'horn':'BTNHornOfCenarius', 'burrow':'BTNCryptFiendBurrow',
           'quake':'BTNWarStomp', 'water':'BTNCrushingWave', 'whip':'BTNShadowStrike', 'fire':'BTNFire', 'slow':'BTNSlow', 'web':'BTNWeb', 'spider':'BTNSpiderling'}
