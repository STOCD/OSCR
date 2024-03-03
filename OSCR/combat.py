""" This file implements the Combat class """

from collections import deque
from datetime import datetime, timedelta

import numpy

from .datamodels import OverviewTableRow
from .detection import Detection
from .utilities import get_entity_name, get_flags, get_handle_from_id


def check_difficulty_deaths(data, metadata):
    """
    Check deaths against combat metadata
    data: difficulty-based dicitionary in MAP_DIFFICULTY_ENTITY_DEATH_COUNTS
    metadata: Combat metadata from analyze_computers
    returns True on match, otherwise False
    """

    for k, v in data.items():
        meta = metadata.get(k)
        if meta is None:
            # Map is missing some NPC data - it's invalid.
            return False
        if v != meta["deaths"]:
            # Map kill counts don't line up - it's invalid (possible missed kill shot)
            return False
    return True


def check_difficulty_damage(data, metadata):
    """
    Check hull damage taken against combat metadata
    data: difficulty-based dicitionary in MAP_DIFFICULTY_ENTITY_HULL_COUNTS
    metadata: Combat metadata from analyze_computers
    returns True on match, otherwise False
    """

    # I had issues detecting HSA. This really should be lower.
    # Maybe make it per-map?
    var = 0.20

    for k, v in data.items():
        meta = metadata.get(k)
        if meta is None:
            # Map is missing some NPC data - it's invalid.
            return False
        med = numpy.percentile(meta["total_hull_damage_taken"], 50)
        low = v * (1 - var)
        high = v * (1 + var)
        if low > med or high < med:
            # Map damage don't line up - it's invalid (possible over/underkill)
            return False
    return True


class Combat:
    """
    Contains a single combat including raw log lines, map and combat information and shallow parse results.
    """

    def __init__(self):
        self.log_data = deque()
        self.map = None
        self.difficulty = None
        self.start_time = None
        self.end_time = None
        self.players = {}
        self.computers = {}
        self.computer_meta = {}

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
        self.analyze_log_data()
        self.analyze_players()
        self.analyze_computers()

    def analyze_log_data(self):
        """ """

        graph_timedelta = timedelta(seconds=self.graph_resolution)
        graph_points = 1
        last_graph_time = self.log_data[0].timestamp

        self.players = {}
        self.computers = {}
        self.computer_meta = {}

        for line in self.log_data:
            # manage entites
            player_attacks = line.owner_id.startswith("P")
            player_attacked = line.target_id.startswith("P")
            if not player_attacks and not player_attacked:
                continue
            attacker = None
            target = None
            crit_flag, miss_flag, kill_flag = get_flags(line.flags)
            if player_attacks:
                if line.owner_id not in self.players:
                    self.players[line.owner_id] = OverviewTableRow(
                        line.owner_name, get_handle_from_id(line.owner_id)
                    )
                    self.players[line.owner_id].combat_start = line.timestamp
                attacker = self.players[line.owner_id]
                attacker.combat_end = line.timestamp
            else:
                if line.owner_id not in self.computers:
                    self.computers[line.owner_id] = OverviewTableRow(
                        line.owner_name, get_handle_from_id(line.owner_id)
                    )
                    self.computers[line.owner_id].combat_start = line.timestamp
                attacker = self.computers[line.owner_id]
                attacker.combat_end = line.timestamp

            if player_attacked:
                if line.target_id not in self.players:
                    self.players[line.target_id] = OverviewTableRow(
                        line.target_name, get_handle_from_id(line.target_id)
                    )
                    self.players[line.target_id].combat_start = line.timestamp
                target = self.players[line.target_id]
                target.combat_end = line.timestamp
            else:
                if line.target_id not in self.computers:
                    self.computers[line.target_id] = OverviewTableRow(
                        line.target_name, get_handle_from_id(line.target_id)
                    )
                    self.computers[line.target_id].combat_start = line.timestamp
                target = self.computers[line.target_id]
                target.combat_end = line.timestamp

            # get table data
            if miss_flag:
                attacker.misses += 1
            if kill_flag:
                target.deaths += 1

            if (
                line.type == "Shield" and line.magnitude < 0 and line.magnitude2 >= 0
            ) or line.type == "HitPoints":
                attacker.total_heals += abs(line.magnitude)
                attacker.heal_num += 1
                if crit_flag:
                    attacker.heal_crit_num += 1
            else:
                magnitude = abs(line.magnitude)
                target.total_damage_taken += magnitude
                if line.type == "Shield":
                    target.total_shield_damage_taken += magnitude
                else:
                    target.total_hull_damage_taken += magnitude
                target.attacks_in_num += 1
                attacker.total_attacks += 1
                attacker.total_damage += magnitude
                attacker.damage_buffer += magnitude
                if crit_flag:
                    attacker.crit_num += 1
                if magnitude > attacker.max_one_hit:
                    attacker.max_one_hit = magnitude
                if not line.type == "Shield" and not miss_flag:
                    if line.magnitude != 0 and line.magnitude2 != 0:
                        attacker.resistance_sum += line.magnitude / line.magnitude2
                        attacker.hull_attacks += 1

        # update graph
        if line.timestamp - last_graph_time >= graph_timedelta:
            for player in self.players.values():
                player.DMG_graph_data.append(player.damage_buffer)
                player.damage_buffer = 0.0
                player.graph_time.append(graph_points * self.graph_resolution)
            graph_points += 1
            last_graph_time = line.timestamp

    def analyze_players(self):
        """
        Analyze players to determine time-based metrics such as DPS.
        """

        for player in self.players.values():
            player.combat_time = (
                player.combat_end - player.combat_start
            ).total_seconds()
            successful_attacks = player.hull_attacks - player.misses
            try:
                player.debuff = player.resistance_sum / successful_attacks * 100
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

            player.graph_time = tuple(map(lambda x: round(x, 1), player.graph_time))
            DPS_data = numpy.array(player.DMG_graph_data, dtype=numpy.float64).cumsum()
            player.DPS_graph_data = tuple(DPS_data / player.graph_time)

    def analyze_computers(self):
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

        if self.map and self.difficulty:
            return

        if self.map == "Combat":
            return

        for entity_id, entity in self.computers.items():
            entity_name = get_entity_name(entity_id)
            self.add_entity_to_computer_meta(entity_name)
            self.computer_meta[entity_name]["count"] += 1
            self.computer_meta[entity_name]["deaths"] += entity.deaths
            self.computer_meta[entity_name]["total_hull_damage_taken"].append(
                entity.total_hull_damage_taken
            )

        data = Detection.MAP_DIFFICULTY_ENTITY_DEATH_COUNTS.get(self.map)
        if data is None:
            self.difficulty = _difficulty
            return

        for difficulty, entry in data.items():
            if check_difficulty_deaths(entry, self.computer_meta):
                _difficulty = difficulty
                break

        data = Detection.MAP_DIFFICULTY_ENTITY_HULL_COUNTS.get(self.map)
        if data is None:
            self.difficulty = _difficulty
            return

        matched = False
        for difficulty, entry in data.items():
            if check_difficulty_damage(entry, self.computer_meta):
                matched = True
                _difficulty = difficulty
                break
        if not matched:
            return

        self.difficulty = _difficulty

    def add_entity_to_computer_meta(self, entity_name):
        """Adds a new entry to the computer metadata"""
        if self.computer_meta.get(entity_name) is None:
            self.computer_meta[entity_name] = {
                "count": 0,
                "deaths": 0,
                "total_hull_damage_taken": [],
            }

    @property
    def duration(self):
        return (self.end_time - self.start_time).total_seconds()

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
            f"<{self.__class__.__name__} - Map: {self.map} - Difficulty: {self.difficulty} - Datetime: "
            f"{self.start_time}>"
        )

    def __gt__(self, other):
        if not isinstance(other, Combat):
            raise TypeError(
                f"Cannot compare {self.__class__.__name__} to {other.__class__.__name__}"
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
