from typing import Optional, Iterable
from datetime import datetime
from collections import namedtuple
from . import TREE_HEADER


LogLine = namedtuple('LogLine', 
        ('timestamp',
        'owner_name', 
        'owner_id', 
        'source_name', 
        'source_id', 
        'target_name', 
        'target_id', 
        'event_name', 
        'event_id', 
        'type', 
        'flags', 
        'magnitude', 
        'magnitude2'))

PlayerOverviewRow = namedtuple('PlayerOverviewRow',
        ('name', 
        'handle', 
        'combat_time', 
        'DPS',
        'total_damage', 
        'debuff', 
        'attacks_in_share', 
        'taken_damage_share', 
        'damage_share', 
        'max_one_hit', 
        'crit_chance', 
        'deaths', 
        'total_heals', 
        'heal_share', 
        'heal_crit_chance', 
        'total_damage_taken', 
        'total_hull_damage_taken',
        'total_shield_damage_taken', 
        'total_attacks', 
        'hull_attacks', 
        'attacks_in_num', 
        'heal_crit_num', 
        'heal_num', 
        'crit_num', 
        'misses'
        ))

class OverviewTableRow():
    '''
    Contains a single row of data
    '''
    __slots__ = ('name', 'handle', 'combat_time', 'DPS', 'total_damage', 'debuff', 'attacks_in_share', 
            'taken_damage_share', 'damage_share', 'max_one_hit', 'crit_chance', 'deaths', 
            'total_heals', 'heal_share', 'heal_crit_chance', 'total_damage_taken', 'total_hull_damage_taken',
            'total_shield_damage_taken', 'total_attacks', 'hull_attacks', 'attacks_in_num', 'heal_crit_num', 
            'heal_num', 'crit_num', 'misses', 'resistance_sum', 'DMG_graph_data', 'DPS_graph_data', 
            'graph_time', 'damage_buffer', 'combat_start', 'combat_end')
    
    def __init__(self, name:str, handle:str):
        self.name: str = name
        self.handle: str = handle
        self.combat_time: float = 0.0
        self.DPS: float = 0.0
        self.total_damage: float = 0.0
        self.debuff: float = 0.0
        self.attacks_in_share: float = 0.0
        self.taken_damage_share: float = 0.0
        self.damage_share: float = 0.0
        self.max_one_hit: float = 0.0
        self.crit_chance: float = 0.0
        self.deaths: int = 0
        self.total_heals: float = 0.0
        self.heal_share: float = 0.0
        self.heal_crit_chance: float = 0.0
        self.total_damage_taken: float = 0.0
        self.total_hull_damage_taken: float = 0.0
        self.total_shield_damage_taken: float = 0.0
        self.total_attacks: int = 0
        self.hull_attacks: int = 0
        self.attacks_in_num: int = 0
        self.heal_crit_num: int = 0
        self.heal_num: int = 0
        self.crit_num: int = 0
        self.misses: int = 0
        
        self.resistance_sum: float = 0.0
        self.DMG_graph_data: list[float] = list()
        self.DPS_graph_data: list[float] = list()
        self.graph_time: list[float] = list()
        self.damage_buffer: float = 0.0
        self.combat_start: datetime = None
        self.combat_end: datetime = None

    def __repr__(self) -> str:
        return f'<{self.__class__.__name__}: {self.name}{self.handle}>'
    
    def __len__(self) -> int:
        return 25
    
    def __getitem__(self, position):
        entries = {
            0: self.name,
            1: self.handle,
            2: self.combat_time,
            3: self.DPS,
            4: self.total_damage,
            5: self.debuff,
            6: self.attacks_in_share,
            7: self.taken_damage_share,
            8: self.damage_share,
            9: self.max_one_hit,
            10: self.crit_chance,
            11: self.deaths,
            12: self.total_heals,
            13: self.heal_share,
            14: self.heal_crit_chance,
            15: self.total_damage_taken,
            16: self.total_hull_damage_taken,
            17: self.total_shield_damage_taken,
            18: self.total_attacks,
            19: self.hull_attacks,
            20: self.attacks_in_num,
            21: self.heal_crit_num,
            22: self.heal_num,
            23: self.crit_num,
            24: self.misses,
        }

        if position >= len(entries):
            raise StopIteration()

        return entries.get(position, 0)

class AnalysisTableRow():
    """
    Contains a single row of data in the analysis table. Unpacks into: (name, handle, total_damage, 
    max_one_hit, kills, total_attacks, misses, crit_num, flank_num, total_shield_damage, total_hull_damage,
    total_base_damage, combat_time, hull_attacks, shield_attacks)
    """
    __slots__ = ('name', 'handle', 'total_damage', 'max_one_hit', 'kills', 
            'total_attacks', 'misses', 'crit_num', 'flank_num', 'total_shield_damage', 'total_hull_damage',
            'total_base_damage', 'combat_time', 'hull_attacks', 'shield_attacks',
            'id', 'resistance_sum', 'DMG_graph_data', 'DPS_graph_data', 'graph_time', 'damage_buffer',
            'combat_start', 'combat_end')
    
    def __init__(self, name: str, handle: str, id: str):
        """
        Parameters:

        """
        # commented attributes represent additional fields in the final result, but are not required here
        self.name: str = name if name else '*'
        self.handle: str = handle
        # self.DPS: float = 0.0
        self.total_damage: float = 0.0
        # self.debuff: float = 0.0
        self.max_one_hit: float = 0.0
        # self.crit_chance: float = 0.0
        # self.accuracy: float = 0.0
        # self.flank_rate: float = 0.0
        self.kills: int = 0
        self.total_attacks: int = 0
        self.misses: int = 0
        self.crit_num: int = 0
        self.flank_num: int = 0
        self.total_shield_damage: float = 0.0
        # self.shield_DPS: float = 0.0
        self.total_hull_damage: float = 0.0
        # self.hull_DPS: float = 0.0
        self.total_base_damage: float = 0.0
        # self.total_base_DPS: float = 0.0
        self.combat_time: float = 0.0
        self.hull_attacks: int = 0
        self.shield_attacks: int = 0
        
        self.id: str = id
        self.resistance_sum: float = 0.0
        self.DMG_graph_data: list[float] = list()
        self.DPS_graph_data: list[float] = list()
        self.graph_time: list[float] = list()
        self.damage_buffer: float = 0.0
        self.combat_start: datetime = None
        self.combat_end: datetime = None

    def __repr__(self) -> str:
        return f'<{self.__class__.__name__}: {self.name}{self.handle}>'
    
    def __len__(self) -> int:
        return 15
    
    def __getitem__(self, position: int):
        entries = {
            0: self.name,
            1: self.handle,
            2: self.total_damage,
            3: self.max_one_hit,
            4: self.kills,
            5: self.total_attacks,
            6: self.misses,
            7: self.crit_num,
            8: self.flank_num,
            9: self.total_shield_damage,
            10: self.total_hull_damage,
            11: self.total_base_damage,
            12: self.combat_time,
            13: self.hull_attacks,
            14: self.shield_attacks,
        }

        if position >= len(entries):
            raise StopIteration()

        return entries.get(position, 0)

class TreeItem():
    """
    Item that contains data and children optionally.
    """

    __slots__ = ('data', 'parent', '_children')
    
    def __init__(self, data, parent):
        self.data = data
        self.parent = parent
        self._children = list()

    def __repr__(self):
        return f'<{self.__class__.__name__}: data={self.data}>'
    
    def __iter__(self):
        return iter(self.data)

    def get_child(self, row:int):
        try:
            return self._children[row]
        except IndexError:
            return None
    
    def append_child(self, item):
        self._children.append(item)

    @property
    def child_count(self):
        return len(self._children)
    
    @property
    def row(self):
        if self.parent is not None:
            return self.parent._children.index(self)
        return 0
    
    @property
    def column_count(self):
        return len(self.data)
    
    def get_data(self, column:int):
        try:
            return self.data[column]
        except IndexError:
            if column == 0:
                return self.data
            return None

class TreeModel():
    """
    Data model that contains a hierachical table.
    """
    
    def __init__(self, header: tuple[str]):
        self.actor_index = dict()
        self.ability_index = dict()
        self.pet_group_index = dict()
        self.pet_index = dict()
        self.target_index = dict()
        self._root = TreeItem(header, None)
        self._player = TreeItem(['Player'] + [''] * (len(TREE_HEADER) - 1), self._root)
        self._npc = TreeItem(['NPC'] + [''] * (len(TREE_HEADER) - 1), self._root)
        self._root.append_child(self._player)
        self._root.append_child(self._npc)

    def __repr__(self) -> str:
        return f'<{self.__class__.__name__} with columns {self._root.data}>'
    
    def add_actor(self, name: str, handle: str, id: str, player: bool = True) -> TreeItem:
        """
        Adds Player or NPC to model.

        Parameters:
        - :param name: name of the player or NPC
        - :param handle: handle of the player or NPC (NPC handle is an id number)
        - :param id: unique id string of the entity for use in index
        - :param player: True when player is added, False when NPC is added

        :return: added actor
        """
        row = AnalysisTableRow(name, handle, id)
        if player:
            actor = TreeItem(row, self._player)
            self._player.append_child(actor)
        else:
            actor = TreeItem(row, self._npc)
            self._npc.append_child(actor)
        self.actor_index[id] = actor
        self.ability_index[id] = dict()
        self.target_index[id] = dict()
        return actor

    def add_ability(self, name: str, ability_id: str, actor: TreeItem, actor_id: str) -> TreeItem:
        """
        Adds ability to model. Ability is inserted as child to the given actor.

        Parameters:
        - :param name: name of the ability
        - :param ability_id: unique id string of the ability for use in index
        - :param actor: actor TreeItem that is the parent of the ability

        :return: added ability
        """
        ability = TreeItem(name, actor)
        actor.append_child(ability)
        self.ability_index[actor_id][ability_id] = ability
        self.target_index[actor_id][ability_id] = dict()
        return ability

    def add_pet_group(self, name: str, pet_id: str, actor: TreeItem) -> TreeItem:
        """
        Adds pet group to model. Pet group is inserted as child to the given actor.

        Parameters:
        - :param name: name of the pet group
        - :param pet_id: unique id string of the pet group for use in index
        - :param actor: actor TreeItem that is the parent of the ability

        :return: added pet group
        """
        pet = TreeItem(name, actor)
        actor.append_child(pet)
        self.pet_group_index[pet_id] = pet
        return pet

    def add_pet(self, name: str, pet_id: str, pet_group: TreeItem) -> TreeItem:
        """
        Adds pet to model. Ability is inserted as child to the given pet_group.

        Parameters:
        - :param name: name of the pet
        - :param pet_id: unique id string of the pet for use in index
        - :param pet_group: pet group TreeItem that is the parent of the ability

        :return: added pet
        """
        pet = TreeItem(name, pet_group)
        pet_group.append_child(pet)
        self.pet_index[pet_id] = pet
        self.ability_index[pet_id] = dict()
        self.target_index[pet_id] = dict()
        return pet

    def add_target(self, data: AnalysisTableRow, target_id: str, ability: TreeItem, ability_id: str,
            actor_id: str) -> AnalysisTableRow:
        """
        Adds target to model. target is inserted as child to the given ability.

        Parameters:
        - :param data: row of data for the target. First entry must be the name of the target
        - :param target_id: unique id string of the target for use in index
        - :param ability: ability TreeItem that is the parent of the target

        :return: added target
        """
        target = TreeItem(data, ability)
        ability.append_child(target)
        self.target_index[actor_id][ability_id][target_id] = target
        return data

# Currently not used; I forgot why I put this here
# class TableRow():
#     '''
#     Contains data of a single row. Can have child rows.
#     '''
#     __slots__ = ('_row_data', '_children')

#     def __init__(self, data:Optional[list] = None, children:Optional[list] = None) -> None:
#         self._row_data = list()
#         self._children = list()
#         if isinstance(data, list):
#             self._row_data = data
#         if isinstance(children, list):
#             self._children = children

#     def __repr__(self) -> str:
#         return f'<{self.__class__.__name__} - {self._row_data} - {len(self._children)} child rows>'
    
#     def __len__(self) -> int:
#         return len(self._row_data)
    
#     def __getitem__(self, index:int):
#         try:
#             return self._row_data[index]
#         except IndexError:
#             raise IndexError
    
#     def __setitem__(self, index:int, value) -> None:
#         self._row_data[index] = value
    
#     @property
#     def children(self):
#         return self._children
    
#     @property
#     def row_data(self):
#         return self
    
#     @row_data.setter
#     def row_data(self, full_row:list):
#         self._row_data = full_row

class Combat():
    '''
    Contains a single combat including raw log lines, map and combat information and shallow parse results.
    '''
    __slots__ = ('log_data', '_map', '_difficulty', 'date_time', 'table', 'graph_data')

    def __init__(self, log_lines:Optional[list[LogLine]] = None) -> None:
        self.log_data = log_lines
        self._map = None
        self._difficulty = None
        self.date_time = None
        self.table = None
        self.graph_data = None

    @property
    def player_dict(self):
        dictionary = dict()
        for player_row in self.table:
            dictionary[f'{player_row[0]}{player_row[1]}'] = PlayerOverviewRow(*player_row)
        return dictionary

    @property
    def map(self) -> str:
        if self._map is None:
            return 'Combat'
        return self._map
    
    @map.setter
    def map(self, map_name):
        self._map = map_name

    @property
    def difficulty(self) -> str:
        if self._difficulty is None:
            return ''
        return self._difficulty
    
    @difficulty.setter
    def difficulty(self, difficulty_name):
        self._difficulty = difficulty_name

    def __repr__(self) -> str:
        return (f'<{self.__class__.__name__} - Map: {self.map} - Difficulty: {self.difficulty} - Datetime: '
                f'{self.date_time}>')
    
    def __gt__(self, other):
        if not isinstance(other, Combat):
            raise TypeError(f'Cannot compare {self.__class__.__name__} to {other.__class__.__name__}')
        if isinstance(self.date_time, datetime) and isinstance(self.date_time, datetime):
            return self.date_time > other.date_time
        if not isinstance(self.date_time, datetime) and isinstance(self.date_time, datetime):
            return False
        if isinstance(self.date_time, datetime) and not isinstance(other.date_time, datetime):
            return True
