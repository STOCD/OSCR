__all__ = ['baseparser', 'datamodels', 'iofunc', 'main', 'utilities']

TABLE_HEADER = ('Combat Time', 'DPS', 'Total Damage', 'Debuff', 'Attacks-in Share', 'Taken Damage Share', 
        'Damage Share', 'Max One Hit', 'Crit Chance', 'Deaths', 'Total Heals', 'Heal Share', 
        'Heal Crit Chance', 'Total Damage Taken', 'Total Hull Damage Taken', 'Total Shield Damage Taken',
        'Total Attacks', 'Hull Attacks', 'Attacks-in Number', 'Heal Crit Number', 'Heal Number', 
        'Crit Number', 'Misses')

TREE_HEADER = ('', 'DPS', 'Total Damage', 'Debuff', 'Max One Hit', 'Crit Chance', 'Accuracy', 'Flank Rate', 
        'Kills', 'Attacks', 'Misses', 'Critical Hits', 'Flank Hits', 'Shield Damage', 'Shield DPS',
        'Hull Damage', 'Hull DPS', 'Base Damage', 'Base DPS', 'Combat Time', 'Hull Attacks', 
        'Shield Attacks') #, 'Hull Resistance', 'Shield Resistance')

from .main import OSCR
from .datamodels import TreeItem
