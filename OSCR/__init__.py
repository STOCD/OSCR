__all__ = [
        'cli', 'combat', 'datamodels', 'detection', 'iofunc', 'liveparser', 'main', 'parser',
        'utilities']

TABLE_HEADER = (
    'Combat Time', 'DPS', 'Total Damage', 'Debuff', 'Attacks-in Share',
    'Taken Damage Share', 'Damage Share', 'Max One Hit', 'Crit Chance', 'Deaths', 'Total Heals',
    'Heal Share', 'Heal Crit Chance', 'Total Damage Taken', 'Total Hull Damage Taken',
    'Total Shield Damage Taken', 'Total Attacks', 'Hull Attacks', 'Attacks-in Number',
    'Heal Crit Number', 'Heal Number', 'Crit Number', 'Misses')

TREE_HEADER = (
    '', 'DPS', 'Total Damage', 'Debuff', 'Max One Hit', 'Crit Chance', 'Accuracy', 'Flank Rate',
    'Kills', 'Attacks', 'Misses', 'Critical Hits', 'Flank Hits', 'Shield Damage', 'Shield DPS',
    'Hull Damage', 'Hull DPS', 'Base Damage', 'Base DPS', 'Combat Time', 'Hull Attacks',
    'Shield Attacks')  # , 'Shield Resistance')

HEAL_TREE_HEADER = (
    '', 'HPS', 'Total Heal', 'Hull Heal', 'Hull HPS', 'Shield Heal', 'Shield HPS',
    'Max One Heal', 'Crit Chance', 'Heal Ticks', 'Critical Heals', 'Combat Time', 'Hull Heal Ticks',
    'Shield Heal Ticks')

LIVE_TABLE_HEADER = (
    'DPS', 'Combat Time', 'Debuff', 'Attacks-in', 'HPS', 'Kills', 'Deaths')

from .main import OSCR
from .datamodels import TreeItem
from .iofunc import split_log_by_lines, split_log_by_combat
from .liveparser import LiveParser
