from collections import namedtuple

import numpy

LogLine = namedtuple(
    'LogLine',
    (
        'timestamp',
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
        'magnitude2'
    )
)


class CritterMeta:
    """
    Represents one npc type in a combat.
    """

    __slots__ = ('name', 'count', 'deaths', 'hull_values')

    def __init__(self, name: str, initial_count: int = 0, initial_deaths: int = 0, initial_hull_values: list = []):
        """
        Represents one NPC type in a combat

        Parameters:
        - :param name: name of the entity
        - :param initial_count: current count of the entity at time of creation
        - :param initial_hull_values: already determined hull values
        """
        self.name = name
        self.count = initial_count
        self.deaths = initial_deaths
        self.hull_values = initial_hull_values

    def add_critter(self, death: int, hull_value: int):
        """
        Adds an entity to the meta

        Parameters:
        - :param hull_value: amount of hull damage this entity suffered
        """
        self.count += 1
        self.hull_values.append(hull_value)
        self.deaths += death

    def __repr__(self):
        return f'<CritterMeta "Nane: {self.name} Count: {self.count} Deaths: {self.deaths}">'


class DetectionInfo:
    """
    Stores information on the detection process
    """

    __slots__ = (
            'success', 'type', 'identificators', 'target_value', 'retrieved_value', 'step',
            'map', 'difficulty')

    def __init__(
            self, success: bool, type: str = '', identificators: tuple = (), target_value: int = 0,
            retrieved_value: int = 0, step: str = '', map=None, difficulty=None):
        """
        Stores information on the detection process.

        Parameters:
        - :param success: True if this step successfully detected a map
        - :param type: "map"/"difficulty"/"both" depending on what the step detected
        - :param identificators: NPCs that were used to identfy the combat or that the detection \
        failed on
        - :param target_value: value that had to be reached for a successful detection
        - :param retrieved_value: value that was determined from the data
        - :param step: "existence"/"deaths"/"damage" depending on the detection method
        - :param map: detected map
        - :param difficulty: detected difficulty
        """
        self.success = success
        self.type = type
        self.identificators = identificators
        self.target_value = target_value
        self.retrieved_value = retrieved_value
        self.step = step
        self.map = map
        self.difficulty = difficulty

    def __repr__(self):
        return f'<DetectionInfo success={self.success} type={self.type}>'

    def __bool__(self):
        return self.success


class OverviewTableRow:
    '''
    Contains a single row of data
    '''

    __slots__ = (
            'name', 'handle', 'DPS', 'combat_time', 'combat_time_share', 'total_damage', 'debuff',
            'attacks_in_share', 'taken_damage_share', 'damage_share', 'max_one_hit', 'crit_chance',
            'deaths', 'total_heals', 'heal_share', 'heal_crit_chance', 'total_damage_taken',
            'total_hull_damage_taken', 'total_shield_damage_taken', 'total_attacks',
            'hull_attacks', 'attacks_in_num', 'heal_crit_num', 'heal_num', 'crit_num', 'misses',
            'base_damage', 'DMG_graph_data', 'DPS_graph_data', 'graph_time', 'damage_buffer',
            'combat_interval', 'events', 'build')

    def __init__(self, name: str, handle: str):
        self.name: str = name
        self.handle: str = handle
        self.DPS: float = 0.0
        self.combat_time: float = 0.0
        self.combat_time_share: float = 0.0
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

        self.base_damage: float = 0.0
        self.DMG_graph_data: list[float] = list()
        self.DPS_graph_data: list[float] = list()
        self.graph_time: list[float] = list()
        self.damage_buffer: float = 0.0
        self.combat_interval: tuple[float] = None
        self.events: list[str] = list()
        self.build: str = "Unknown"

    def __repr__(self) -> str:
        return f'<{self.__class__.__name__}: {self.name}{self.handle}>'

    def __len__(self) -> int:
        return 26

    def __getitem__(self, position):
        if position >= 26:
            raise IndexError()
        return getattr(self, self.__slots__[position])

    def to_dict(self):
        return {
            "DPS": self.DPS,
            "name": self.name,
            "deaths": self.deaths,
            "debuff": self.debuff,
            "handle": self.handle,
            "misses": self.misses,
            "crit_num": self.crit_num,
            "heal_num": self.heal_num,
            "heal_share": self.heal_share,
            "combat_time": self.combat_time,
            "crit_chance": self.crit_chance,
            "max_one_hit": self.max_one_hit,
            "total_heals": self.total_heals,
            "damage_share": self.damage_share,
            "hull_attacks": self.hull_attacks,
            "total_damage": self.total_damage,
            "heal_crit_num": self.heal_crit_num,
            "total_attacks": self.total_attacks,
            "attacks_in_num": self.attacks_in_num,
            "attacks_in_share": self.attacks_in_share,
            "heal_crit_chance": self.heal_crit_chance,
            "taken_damage_share": self.taken_damage_share,
            "total_damage_taken": self.total_damage_taken,
            "total_hull_damage_taken": self.total_hull_damage_taken,
            "total_shield_damage_taken": self.total_shield_damage_taken,
            "build": self.build,
        }


class AnalysisTableRow():
    """
    Superclass for damage and heal table rows
    """
    def __repr__(self) -> str:
        return f'<{self.__class__.__name__}: {self.name}{self.handle}>'


class DamageTableRow(AnalysisTableRow):
    """
    Contains a single row of data in the analysis table.
    """

    __slots__ = (
            'name', 'handle', 'total_damage', 'max_one_hit', 'kills', 'total_attacks', 'misses',
            'crit_num', 'flank_num', 'total_shield_damage', 'total_hull_damage',
            'total_base_damage', 'combat_time', 'hull_attacks', 'shield_attacks' 'id',
            'combat_start', 'combat_end')

    def __init__(self, name: str, handle: str, id: str):
        """
        Parameters:
        - :param name: name of the entity
        - :param handle: handle of the entity
        - :param id: id of the entity
        """
        # commented attributes represent additional fields in the final result, that are not
        # required here
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
        self.combat_start: float = None
        self.combat_end: float = None


class HealTableRow(AnalysisTableRow):
    """
    Contains a single row of data in the analysis table.
    """
    __slots__ = (
            'name', 'handle', 'total_heal', 'hull_heal', 'shield_heal', 'max_one_heal',
            'heal_ticks', 'critical_heals', 'combat_time', 'hull_heal_ticks', 'shield_heal_ticks',
            'id', 'combat_start', 'combat_end')

    def __init__(self, name: str, handle: str, id: str):
        """
        Parameters:
        - :param name: name of the entity
        - :param handle: handle of the entity
        - :param id: id of the entity
        """

        # commented attributes represent additional fields in the final result, that are not
        # required here
        self.name: str = name if name else '*'
        self.handle: str = handle
        # self.HPS: float = 0.0
        self.total_heal: float = 0.0
        self.hull_heal: float = 0.0
        # self.hull_HPS: float = 0.0
        self.shield_heal: float = 0.0
        # self.shield_HPS: float = 0.0
        self.max_one_heal: float = 0.0
        # self.crit_chance: float = 0.0
        self.heal_ticks: int = 0
        self.critical_heals: int = 0
        self.combat_time: float = 0.0
        self.hull_heal_ticks: int = 0
        self.shield_heal_ticks: int = 0

        self.id: str = id
        self.combat_start: float = None
        self.combat_end: float = None


class TreeItem():
    """
    Item that contains data and children optionally.
    """

    def __init__(self, data: AnalysisTableRow | tuple, parent, parse_duration: int = 0):
        """
        Parameters:
        - :param data: row data
        - :param parent: TreeItem that is the parent of this item
        - :param parse_duration: seconds between the first and last line of the combat, rounded up
        """
        self.data = data
        self.graph_data = numpy.zeros(parse_duration, numpy.float64)
        self.parent: TreeItem = parent
        self._children: list[TreeItem] = list()

    def __repr__(self):
        return f'<{self.__class__.__name__}: data={self.data}>'

    def __iter__(self):
        return iter(self.data)

    def get_child(self, row: int):
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

    def get_data(self, column: int):
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
        self.ability_index: dict[tuple, dict[str, TreeItem]] = dict()
        self.pet_group_index = dict()
        self.pet_index = dict()
        self.target_index = dict()
        self.source_index = dict()
        self._root = TreeItem(header, None)
        self._player = TreeItem(['Player'] + [''] * (len(header) - 1), self._root)
        self._npc = TreeItem(['NPC'] + [''] * (len(header) - 1), self._root)
        self._root.append_child(self._player)
        self._root.append_child(self._npc)

    def __repr__(self) -> str:
        return f'<{self.__class__.__name__} with columns {self._root.data}>'

    def add_actor(
            self, name: str, handle: str, id: str, row_constructor: AnalysisTableRow,
            player: bool = True) -> TreeItem:
        """
        Adds Player or NPC to model.

        Parameters:
        - :param name: name of the player or NPC
        - :param handle: handle of the player or NPC (NPC handle is an id number)
        - :param id: unique id string of the entity for use in index
        - :param row_constructor: a new object returned by this constructor will hold the row data
        - :param player: True when player is added, False when NPC is added

        :return: added actor
        """
        row = row_constructor(name, handle, id)
        if player:
            actor = TreeItem(row, self._player)
            self._player.append_child(actor)
        else:
            actor = TreeItem(row, self._npc)
            self._npc.append_child(actor)
        self.actor_index[id] = actor
        self.ability_index[id] = dict()
        self.target_index[id] = dict()
        self.source_index[id] = dict()
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

    def add_target(
            self, data: AnalysisTableRow, target_id: str, ability: TreeItem, ability_id: str,
            actor_id: str, parse_duration: int) -> TreeItem:
        """
        Adds target to model. target is inserted as child to the given ability.

        Parameters:
        - :param data: row of data for the target. First entry must be the name of the target
        - :param target_id: unique id string of the target for use in index
        - :param ability: ability TreeItem that is the parent of the target
        - :param parse_duration: seconds between the first and last line of the combat, rounded up

        :return: added target
        """
        target = TreeItem(data, ability, parse_duration)
        ability.append_child(target)
        self.target_index[actor_id][ability_id][target_id] = target
        return target

    def add_source_actor(
            self, name: tuple[str], source_id: str, actor: TreeItem, actor_id: str) -> TreeItem:
        """
        Adds source actor to model. Source actor is inserted as child to the given actor. Used for
        incoming damage / heal table.

        Parameters:
        - :param name: name of the source
        - :param source_id: unique id string of the source for use in index
        - :param actor: actor TreeItem that is the parent of the ability

        :return: added source
        """
        source = TreeItem(name, actor)
        actor.append_child(source)
        self.source_index[actor_id][source_id] = source
        self.ability_index[actor_id][source_id] = dict()
        return source

    def add_source_ability(
            self, data: AnalysisTableRow, ability_id: str, source: TreeItem, source_id: str,
            actor_id: str, parse_duration: int) -> TreeItem:
        """
        Adds ability to model. Ability is inserted as child to the given source. Used for incoming
        damage / heal table

        Parameters:
        - :param data: row of data for the target. First entry must be the name of the target
        - :param ability_id: unique id string of the target for use in index
        - :param ability: ability TreeItem that is the parent of the target
        - :param parse_duration: seconds between the first and last line of the combat, rounded up

        :return: added target
        """
        ability = TreeItem(data, source, parse_duration)
        source.append_child(ability)
        self.ability_index[actor_id][source_id][ability_id] = ability
        return ability
