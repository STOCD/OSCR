TABLE_HEADER = (
    'DPS', 'Combat Time', 'Combat Time Share', 'Total Damage', 'Debuff', 'Attacks-in Share',
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

BANNED_ABILITIES = {
    'Electrical Overload'}

PATCHES = (
    (b'Rehona, Sister of the Qowat Milat', b'Rehona - Sister of the Qowat Milat'),
)

# tuple(string in the first line identifying the issue, text with linebreaks removed, replacement
#       text (replaces text with linebreaks removed), total number of lines the issue spans)
MULTILINE_PATCHES = (
    (b'"Nanite Infection',
     b"Nanite Infection<br>Causes damage to nearby players and Kobayashi Maru",
     b'"Nanite Infection - Causes damage to nearby players and Kobayashi Maru"', 3),
)
