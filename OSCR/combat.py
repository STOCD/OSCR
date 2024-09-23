"""This file implements the Combat class"""

from collections import deque
from datetime import datetime, timedelta

import numpy

from .datamodels import OverviewTableRow
from .detection import Detection
from .utilities import get_entity_name, get_flags, get_handle_from_id


def check_difficulty_deaths(difficulty, data, metadata):
    """
    Check deaths against combat metadata
    data: difficulty-based dicitionary in MAP_DIFFICULTY_ENTITY_DEATH_COUNTS
    metadata: Combat metadata from analyze_critters
    returns True on match, otherwise False
    """

    for k, v in data.items():
        meta = metadata.get(k)
        if meta is None:
            # Map is missing some NPC data - it's invalid.
            return False
        if v > 0:
            valid = v == meta["deaths"]
        else:
            valid = meta["deaths"] != 0
        if not valid:
            return False
    return True


def check_difficulty_damage(difficulty, data, metadata):
    """
    Check hull damage taken against combat metadata
    data: difficulty-based dicitionary in MAP_DIFFICULTY_ENTITY_HULL_COUNTS
    metadata: Combat metadata from analyze_critters
    returns True on match, otherwise False
    """

    # only look at the lower variance.
    var = 0.20

    for k, v in data.items():
        meta = metadata.get(k)
        if meta is None:
            # Map is missing some NPC data - it's invalid.
            return False
        med = numpy.percentile(meta["total_hull_damage_taken"], 50)
        low = v * (1 - var)
        high = v * (1 + var)
        valid = low < med
        if not valid:
            return False
    return True


class Combat:
    """
    Contains a single combat including raw log lines, map and combat information and shallow parse
    results.
    """

    def __init__(self, graph_resolution=0.2):
        self.log_data = deque()
        self.map = None
        self.difficulty = None
        self.start_time = None
        self.end_time = None
        self.players = {}
        self.critters = {}
        self.critter_meta = {}
        self.graph_resolution = graph_resolution

    def analyze_last_line(self):
        """Analyze the last line and try and detect the map and difficulty"""

        if (
            self.map is not None
            and self.map != "Combat"
            and self.difficulty is not None
        ):
            return

        _map, _difficulty = Detection.detect_line(self.log_data[0])

        if self.map is None or self.map == "Combat":
            self.map = _map

        if self.difficulty is None:
            self.difficulty = _difficulty

    def analyze_shallow(self, graph_resolution=0.2):
        """
        Do a shallow combat analysis
        The goal of the shallow combat analysis is to get as much data
        as we can in a single iteration of the log data. This includes building
        damage over time graphs so that the log does not need to be iterated
        over again.
        """

        self.graph_resolution = graph_resolution
        self.analyze_players()
        self.analyze_critters()

    def analyze_players(self):
        """
        Analyze players to determine time-based metrics such as DPS.
        """

        total_damage = 0
        total_damage_taken = 0
        total_attacks = 0
        total_heals = 0

        # Filter out players with no combat time.
        players = {}
        for key, player in self.players.items():
            if player.combat_interval is not None and player.events is not None:
                players[key] = player
        self.players = players

        for player in self.players.values():
            total_damage += player.total_damage
            total_damage_taken += player.total_damage_taken
            total_attacks += player.attacks_in_num
            total_heals += player.total_heals

        for player in self.players.values():
            player.combat_time = player.combat_interval[1] - \
                player.combat_interval[0]
            successful_attacks = player.hull_attacks - player.misses

            try:
                player.debuff = (player.total_damage /
                                 player.base_damage - 1) * 100
            except ZeroDivisionError:
                player.debuff = 0.0
            try:
                player.DPS = player.total_damage / player.combat_time
            except ZeroDivisionError:
                player.DPS = 0.0
            if successful_attacks > 0:
                player.crit_chance = player.crit_num / successful_attacks * 100
            else:
                player.crit_chance = 0
            try:
                player.heal_crit_chance = player.heal_crit_num / player.heal_num * 100
            except ZeroDivisionError:
                player.heal_crit_chance = 0.0

            try:
                player.damage_share = player.total_damage / total_damage * 100
            except ZeroDivisionError:
                player.damage_share = 0.0
            try:
                player.taken_damage_share = (
                    player.total_damage_taken / total_damage_taken * 100
                )
            except ZeroDivisionError:
                player.taken_damage_share = 0.0
            try:
                player.attacks_in_share = player.attacks_in_num / total_attacks * 100
            except ZeroDivisionError:
                player.attacks_in_share = 0.0
            try:
                player.heal_share = player.total_heals / total_heals * 100
            except ZeroDivisionError:
                player.heal_share = 0.0

            for k, v in Detection.BUILD_DETECTION_ABILITIES.items():
                for event in player.events:
                    if k in event:
                        player.build = v
                        break

            player.graph_time = tuple(
                map(lambda x: round(x, 1), player.graph_time))
            DPS_data = numpy.array(player.DMG_graph_data,
                                   dtype=numpy.float64).cumsum()
            player.DPS_graph_data = tuple(DPS_data / player.graph_time)

    def analyze_critters(self):
        """
        Analyze map entities Computers to determine:
            - The map type
            - The difficulty of the map

        If new results are obtained, this overrides the values previously set
        if detect_line() was called during the creation of the Combat object.

        The algorithm starts broad and then narrows in if additional detections
        are necessary. The order in which they are processed:
            - Entity Counts
            - Entity Hull Damage Taken

        On maps such as Infected Space Entity Hull Damage Taken
        (and later steps) do not need to be provided if Entity Counts is
        sufficient in determinning map valididty.

        Assumes that map and difficulty have already been set with detect_line.
        """

        _difficulty = self.difficulty

        if self.map and self.difficulty != "Any":
            return

        if self.map == "Combat":
            return

        for entity_id, entity in self.critters.items():
            entity_name = get_entity_name(entity_id)
            self.add_entity_to_critter_meta(entity_name)
            self.critter_meta[entity_name]["count"] += 1
            self.critter_meta[entity_name]["deaths"] += entity.deaths
            total_hull_damage_taken = self.critter_meta[entity_name][
                "total_hull_damage_taken"
            ]
            total_hull_damage_taken.append(entity.total_hull_damage_taken)

        # Death Detection
        data = Detection.MAP_DIFFICULTY_ENTITY_DEATH_COUNTS.get(self.map)
        if data is None:
            self.difficulty = _difficulty
            return

        matched = False
        for difficulty, entry in data.items():
            if check_difficulty_deaths(difficulty, entry, self.critter_meta):
                matched = True
                _difficulty = difficulty
            else:
                continue

        if not matched:
            return

        # Hull Detection
        data = Detection.MAP_DIFFICULTY_ENTITY_HULL_COUNTS.get(self.map)
        if data is None:
            self.difficulty = _difficulty
            return

        matched = False
        for difficulty, entry in data.items():
            if check_difficulty_damage(difficulty, entry, self.critter_meta):
                matched = True
                _difficulty = difficulty
            else:
                continue

        if not matched:
            return

        self.difficulty = _difficulty

    def add_entity_to_critter_meta(self, entity_name):
        """Adds a new entry to the critter metadata"""
        if self.critter_meta.get(entity_name) is None:
            self.critter_meta[entity_name] = {
                "count": 0,
                "deaths": 0,
                "total_hull_damage_taken": [],
            }

    @property
    def duration(self):
        return self.end_time - self.start_time

    @property
    def date_time(self):
        """Returns the end time - for compatibility with previous versions"""
        return self.end_time

    @property
    def player_dict(self):
        """Returns the list of players - for compatibility with previous versions"""
        return self.players

    def __repr__(self) -> str:
        return (
            f"<{self.__class__.__name__} - Map: {self.map} - Difficulty: {self.difficulty} - "
            f"Datetime: {self.start_time}>"
        )

    def __gt__(self, other):
        if not isinstance(other, Combat):
            raise TypeError(
                f"Cannot compare {self.__class__.__name__} to {
                    other.__class__.__name__}"
            )
        if isinstance(self.date_time, datetime) and isinstance(
            self.date_time, datetime
        ):
            return self.date_time > other.date_time
        if not isinstance(self.date_time, datetime) and isinstance(
            self.date_time, datetime
        ):
            return False
        if isinstance(self.date_time, datetime) and not isinstance(
            other.date_time, datetime
        ):
            return True
