from typing import Optional, Iterable
from datetime import datetime
from collections import namedtuple


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
        'crit_chance',
        'max_one_hit',
        'debuff',
        'damage_share',
        'taken_damage_share',
        'attacks_in_share',
        'total_heals',
        'heal_crit_chance',
        'heal_share',
        'deaths',
        'heal_crit_num',
        'heal_num',
        'crit_num',
        'total_damage_taken',
        'attacks_in_num',
        'total_attacks',
        'hull_attacks',
        'resistance_sum',
        'misses'
        ))

ComputerOverviewRow = namedtuple('ComputerOverviewRow',
        ('name',
        'handle',
        'combat_time',
        'DPS',
        'total_damage',
        'crit_chance',
        'max_one_hit',
        'debuff',
        'damage_share',
        'taken_damage_share',
        'attacks_in_share',
        'total_heals',
        'heal_crit_chance',
        'heal_share',
        'deaths',
        'heal_crit_num',
        'heal_num',
        'crit_num',
        'total_damage_taken',
        'attacks_in_num',
        'total_attacks',
        'hull_attacks',
        'resistance_sum',
        'misses'
        ))


class TreeModel():
    """
    Data model that contains a hierachical table.
    """
    
    def __init__(self, header: tuple[str]):
        self._root = TreeItem(header, None)

class TreeItem():
    """
    Item that contains data and children optionally.
    """

    __slots__ = ('_data', '_parent', '_children')
    
    def __init__(self, data:tuple, parent):
        self._data = data
        self._parent = parent
        self._children = list()

    def __repr__(self):
        return f'<{self.__class__.__name__}: data={self._data}, parent={self._parent}, children={self._children}>'

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
        if self._parent is not None:
            return self._parent._children.index(self)
        return 0
    
    @property
    def column_count(self):
        return len(self._data)
    
    def get_data(self, column:int):
        try:
            return self._data[column]
        except IndexError:
            return None
    @property    
    def parent_item(self):
        return self._parent

class PlayerTableRow():
    '''
    Contains a single row of data
    '''
    __slots__ = ('name', 'handle', 'combat_time', 'DPS', 'total_damage', 'crit_chance', 'max_one_hit', 
            'debuff', 'damage_share', 'taken_damage_share', 'attacks_in_share', 'total_heals', 
            'heal_crit_chance', 'heal_share', 'deaths', 'heal_crit_num', 'heal_num', 'crit_num', 
            'total_damage_taken', 'attacks_in_num', 'total_attacks', 'hull_attacks', 'resistance_sum', 
            'misses', 'DMG_graph_data', 'DPS_graph_data', 'graph_time', 'damage_buffer', 'combat_start',
            'combat_end')
    
    def __init__(self, name:str, handle:str):
        self.name: str = name
        self.handle: str = handle
        self.combat_time: float = 0.0
        self.DPS: float = 0.0
        self.total_damage: float = 0.0
        self.crit_chance: float = 0.0
        self.max_one_hit: float = 0.0
        self.debuff: float = 0.0
        self.damage_share: float = 0.0
        self.taken_damage_share: float = 0.0
        self.attacks_in_share: float = 0.0
        self.total_heals: float = 0.0
        self.heal_crit_chance: float = 0.0
        self.heal_share: float = 0.0
        self.deaths: int = 0

        self.heal_crit_num: int = 0
        self.heal_num: int = 0
        self.crit_num: int = 0
        self.total_damage_taken: float = 0.0
        self.attacks_in_num: int = 0
        self.total_attacks: int = 0
        self.hull_attacks: int = 0
        self.resistance_sum: float = 0.0
        self.misses: int = 0

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
    
    def __getitem__(self, position):
        match position:
            case 0: return self.name
            case 1: return self.handle
            case 2: return self.combat_time
            case 3: return self.DPS
            case 4: return self.total_damage
            case 5: return self.crit_chance
            case 6: return self.max_one_hit
            case 7: return self.debuff
            case 8: return self.damage_share
            case 9: return self.taken_damage_share
            case 10: return self.attacks_in_share
            case 11: return self.total_heals
            case 12: return self.heal_crit_chance
            case 13: return self.heal_share
            case 14: return self.deaths
            case 15: return self.heal_crit_num
            case 16: return self.heal_num
            case 17: return self.crit_num
            case 18: return self.total_damage_taken
            case 19: return self.attacks_in_num
            case 20: return self.total_attacks
            case 21: return self.hull_attacks
            case 22: return self.resistance_sum
            case 23: return self.misses
            case _: raise StopIteration()

class ComputerTableRow():
    '''
    Contains a single row of data
    '''
    __slots__ = ('name', 'handle', 'combat_time', 'DPS', 'total_damage', 'crit_chance', 'max_one_hit', 
            'debuff', 'damage_share', 'taken_damage_share', 'attacks_in_share', 'total_heals', 
            'heal_crit_chance', 'heal_share', 'deaths', 'heal_crit_num', 'heal_num', 'crit_num', 
            'total_damage_taken', 'attacks_in_num', 'total_attacks', 'hull_attacks', 'resistance_sum', 
            'misses', 'DMG_graph_data', 'DPS_graph_data', 'graph_time', 'damage_buffer', 'combat_start',
            'combat_end')
    
    def __init__(self, handle:str, name:str):
        self.name: str = name
        self.handle: str = handle
        self.combat_time: float = 0.0
        self.DPS: float = 0.0
        self.total_damage: float = 0.0
        self.crit_chance: float = 0.0
        self.max_one_hit: float = 0.0
        self.debuff: float = 0.0
        self.damage_share: float = 0.0
        self.taken_damage_share: float = 0.0
        self.attacks_in_share: float = 0.0
        self.total_heals: float = 0.0
        self.heal_crit_chance: float = 0.0
        self.heal_share: float = 0.0
        self.deaths: int = 0

        self.heal_crit_num: int = 0
        self.heal_num: int = 0
        self.crit_num: int = 0
        self.total_damage_taken: float = 0.0
        self.attacks_in_num: int = 0
        self.total_attacks: int = 0
        self.hull_attacks: int = 0
        self.resistance_sum: float = 0.0
        self.misses: int = 0

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
    
    def __getitem__(self, position):
        match position:
            case 0: return self.name
            case 1: return self.handle
            case 2: return self.combat_time
            case 3: return self.DPS
            case 4: return self.total_damage
            case 5: return self.crit_chance
            case 6: return self.max_one_hit
            case 7: return self.debuff
            case 8: return self.damage_share
            case 9: return self.taken_damage_share
            case 10: return self.attacks_in_share
            case 11: return self.total_heals
            case 12: return self.heal_crit_chance
            case 13: return self.heal_share
            case 14: return self.deaths
            case 15: return self.heal_crit_num
            case 16: return self.heal_num
            case 17: return self.crit_num
            case 18: return self.total_damage_taken
            case 19: return self.attacks_in_num
            case 20: return self.total_attacks
            case 21: return self.hull_attacks
            case 22: return self.resistance_sum
            case 23: return self.misses
            case _: raise StopIteration()


class TableRow():
    '''
    Contains data of a single row. Can have child rows.
    '''
    __slots__ = ('_row_data', '_children')

    def __init__(self, data:Optional[list] = None, children:Optional[list] = None) -> None:
        self._row_data = list()
        self._children = list()
        if isinstance(data, list):
            self._row_data = data
        if isinstance(children, list):
            self._children = children

    def __repr__(self) -> str:
        return f'<{self.__class__.__name__} - {self._row_data} - {len(self._children)} child rows>'
    
    def __len__(self) -> int:
        return len(self._row_data)
    
    def __getitem__(self, index:int):
        try:
            return self._row_data[index]
        except IndexError:
            raise IndexError
    
    def __setitem__(self, index:int, value) -> None:
        self._row_data[index] = value
    
    @property
    def children(self):
        return self._children
    
    @property
    def row_data(self):
        return self
    
    @row_data.setter
    def row_data(self, full_row:list):
        self._row_data = full_row

class Combat():
    '''
    Contains a single combat including raw log lines, map and combat information and shallow parse results.
    '''
    __slots__ = ('log_data', '_map', '_difficulty', 'date_time', 'table', 'graph_data', 'computer_table', 'computer_graph_data')

    def __init__(self, log_lines:Optional[list[LogLine]] = None) -> None:
        self.log_data = log_lines
        self._map = None
        self._difficulty = None
        self.date_time = None
        self.table = None
        self.graph_data = None
        self.computer_table = None
        self.computer_graph_data = None

    @property
    def player_dict(self):
        dictionary = dict()
        for player_row in self.table:
            dictionary[f'{player_row[0]}{player_row[1]}'] = PlayerOverviewRow(*player_row)
        return dictionary

    @property
    def computer_dict(self):
        dictionary = dict()
        for computer_row in self.computer_table:
            dictionary[f'{computer_row[0]}{computer_row[1]}'] = ComputerOverviewRow(*computer_row)
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
            return 'Normal'
        return self._difficulty
    
    @difficulty.setter
    def difficulty(self, difficulty_name):
        self._difficulty = difficulty_name

    def __repr__(self) -> str:
        return f'<{self.__class__.__name__} - Map: {self.map} - Difficulty: {self.difficulty} - Datetime: {self.date_time}>'
    
    def __gt__(self, other):
        if not isinstance(other, Combat):
            raise TypeError(f'Cannot compare {self.__class__.__name__} to {other.__class__.__name__}')
        if isinstance(self.date_time, datetime) and isinstance(self.date_time, datetime):
            return self.date_time > other.date_time
        if not isinstance(self.date_time, datetime) and isinstance(self.date_time, datetime):
            return False
        if isinstance(self.date_time, datetime) and not isinstance(other.date_time, datetime):
            return True
