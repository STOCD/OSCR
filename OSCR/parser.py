import numpy
from datetime import datetime

from .combat import Combat
from .constants import HEAL_TREE_HEADER, TREE_HEADER
from .datamodels import (
    AnalysisTableRow, DamageTableRow, HealTableRow, LogLine, TreeItem, TreeModel)
from .utilities import bundle, get_handle_from_id, get_player_handle, to_microseconds


def analyze_combat(combat: Combat) -> Combat:
    """
    Fully analyzes the given combat and returns it.
    """
    combat.damage_out = dmg_out_model = TreeModel(TREE_HEADER)
    combat.damage_in = dmg_in_model = TreeModel(TREE_HEADER)
    combat.heals_out = heal_out_model = TreeModel(HEAL_TREE_HEADER)
    combat.heals_in = heal_in_model = TreeModel(HEAL_TREE_HEADER)
    actor_combat_durations: dict[str, list[datetime]] = dict()
    graph_point_delta = combat.graph_resolution * 1_000_000
    combat_duration_delta = combat.end_time - combat.start_time
    combat_duration_sec = int(combat_duration_delta.total_seconds()) + 1  # round up to full second
    total_graph_points = int(combat_duration_delta.total_seconds() // combat.graph_resolution + 2)
    combat_start = combat.log_data[0].timestamp
    relative_combat_sec = 0
    for line in combat.log_data:
        timestamp = line.timestamp
        player_attacks = line.owner_id.startswith('P')
        player_attacked = line.target_id.startswith('P')
        is_shield_line = line.type == 'Shield'
        crit_flag, miss_flag, flank_flag, kill_flag, _, _ = get_flags(line.flags)
        is_heal = (
                (line.type == 'HitPoints' and line.magnitude < 0)
                or (is_shield_line and line.magnitude < 0 and line.magnitude2 >= 0))

        relative_combat_sec = (timestamp - combat_start).seconds

        # HEALS
        if is_heal:
            target_item, ability_target = get_outgoing_target_row(
                    heal_out_model, line, player_attacks, HealTableRow, combat_duration_sec)
            source_item, source_ability = get_incoming_target_row(
                    heal_in_model, line, player_attacked, HealTableRow, combat_duration_sec)

            if crit_flag:
                ability_target.critical_heals += 1
                source_ability.critical_heals += 1

            magnitude = abs(line.magnitude)
            ability_target.total_heal += magnitude
            ability_target.heal_ticks += 1
            source_ability.total_heal += magnitude
            source_ability.heal_ticks += 1
            if is_shield_line:
                ability_target.shield_heal += magnitude
                ability_target.shield_heal_ticks += 1
                source_ability.shield_heal += magnitude
                source_ability.shield_heal_ticks += 1
            else:
                ability_target.hull_heal += magnitude
                ability_target.hull_heal_ticks += 1
                source_ability.hull_heal += magnitude
                source_ability.hull_heal_ticks += 1

            if magnitude > ability_target.max_one_heal:
                ability_target.max_one_heal = magnitude
            if magnitude > source_ability.max_one_heal:
                source_ability.max_one_heal = magnitude

            target_item.graph_data[relative_combat_sec] += magnitude
            source_item.graph_data[relative_combat_sec] += magnitude

        # DAMAGE
        else:
            target_item, ability_target = get_outgoing_target_row(
                    dmg_out_model, line, player_attacks, DamageTableRow, combat_duration_sec)
            source_item, source_ability = get_incoming_target_row(
                    dmg_in_model, line, player_attacked, DamageTableRow, combat_duration_sec)

            # Combat Duration
            # Heals, damage taken and self-damage don't affect combat time
            if ability_target.name != '*' and line.owner_id != line.target_id:
                try:
                    actor_combat_durations[line.owner_id][1] = timestamp
                except KeyError:
                    actor_combat_durations[line.owner_id] = [timestamp, timestamp]
                if not line.source_id.startswith('P'):
                    try:
                        actor_combat_durations[line.source_id][1] = timestamp
                    except KeyError:
                        actor_combat_durations[line.source_id] = [timestamp, timestamp]

            # get table data
            magnitude = abs(line.magnitude)
            magnitude2 = abs(line.magnitude2)
            ability_target.total_damage += magnitude
            ability_target.total_attacks += 1
            source_ability.total_damage += magnitude
            source_ability.total_attacks += 1
            if is_shield_line:
                ability_target.total_shield_damage += magnitude
                ability_target.shield_attacks += 1
                source_ability.total_shield_damage += magnitude
                source_ability.shield_attacks += 1
            else:
                ability_target.total_hull_damage += magnitude
                source_ability.total_hull_damage += magnitude
                ability_target.hull_attacks += 1
                source_ability.hull_attacks += 1
                ability_target.total_base_damage += magnitude2
                source_ability.total_base_damage += magnitude2

            if magnitude > ability_target.max_one_hit:
                ability_target.max_one_hit = magnitude
            if magnitude > source_ability.max_one_hit:
                source_ability.max_one_hit = magnitude

            target_item.graph_data[relative_combat_sec] += magnitude
            source_item.graph_data[relative_combat_sec] += magnitude

            # overview graph data
            if player_attacks:
                time_idx = int(to_microseconds(timestamp - combat_start) // graph_point_delta)
                try:
                    combat.overview_graphs[get_player_handle(line.owner_id)][time_idx] += magnitude
                except KeyError:
                    combat.overview_graphs[get_player_handle(line.owner_id)] = numpy.zeros(
                            total_graph_points, numpy.float64)
                    combat.overview_graphs[get_player_handle(line.owner_id)][time_idx] += magnitude

            if miss_flag:
                ability_target.misses += 1
                source_ability.misses += 1
            if flank_flag:
                ability_target.flank_num += 1
                source_ability.flank_num += 1
            if crit_flag:
                ability_target.crit_num += 1
                source_ability.crit_num += 1
            if kill_flag:
                ability_target.kills += 1
                source_ability.kills += 1
                if (line.target_name == 'Borg Queen Octahedron'
                        or (line.target_id == '*' and (line.owner_name == 'Borg Queen Octahedron'
                            or line.source_name == 'Borg Queen Octahedron'))):
                    if combat.map_is_hive_space():
                        combat_duration_delta = line.timestamp - combat.log_data[0].timestamp
                        combat.end_time = line.timestamp
                        break  # ignore all lines after the Queen kill line in the Hive Space queue

    combat.meta['log_duration'] = combat_duration_delta.total_seconds()
    overview_graph_intervals: dict[str, tuple] = dict()
    first_player_shot = list()
    last_player_shot = list()
    for actor_id, (start_time, end_time) in actor_combat_durations.items():
        if actor_id.startswith('P'):
            start = int((start_time - combat.start_time).total_seconds() // combat.graph_resolution)
            end = int((end_time - combat.start_time).total_seconds() // combat.graph_resolution + 1)
            overview_graph_intervals[get_player_handle(actor_id)] = (start, end)
            first_player_shot.append(start_time)
            last_player_shot.append(end_time)
        actor_combat_durations[actor_id] = round((end_time - start_time).total_seconds(), 1)
    if len(first_player_shot) > 0 and len(last_player_shot) > 0:
        combat.meta['player_duration'] = (
                max(last_player_shot) - min(first_player_shot)).total_seconds()
    else:
        combat.meta['player_duration'] = 0

    merge_single_lines(dmg_out_model)
    combat_duration = combat_duration_delta.total_seconds()
    complete_damage_tree(dmg_out_model, actor_combat_durations, combat_duration)
    complete_damage_tree(dmg_in_model, actor_combat_durations, combat_duration)
    complete_heal_tree(heal_out_model, actor_combat_durations, combat_duration)
    complete_heal_tree(heal_in_model, actor_combat_durations, combat_duration)
    combat.detect_map()
    combat.create_overview(overview_graph_intervals)
    return combat


def get_outgoing_target_row(
        tree_model: TreeModel, line: LogLine, player_attacks: bool, row_constructor,
        parse_duration: int) -> tuple[TreeItem, DamageTableRow | HealTableRow]:
    """
    Adds the needed parents to the tree model and returns the newly created or already existing
    data row. Also updates combat time of the actor.

    Parameters:
    - :param tree_model: model to work on
    - :param line: log line that contains the ability
    - :param player_attacks: True when player attacks, False otherwise
    - :param parse_duration: seconds between the first and last line of the combat, rounded up

    :return: reference to newly created or existing data row
    """
    attacker_id = (line.owner_id,)
    attacker_handle = get_handle_from_id(line.owner_id)
    if attacker_id in tree_model.actor_index:
        attacker = tree_model.actor_index[attacker_id]
    else:
        attacker = tree_model.add_actor(
                line.owner_name, attacker_handle, attacker_id, DamageTableRow, player_attacks)
        attacker.data.combat_start = line.timestamp
    attacker.data.combat_end = line.timestamp

    if line.source_name:
        pet_group_id = (line.owner_id, line.source_name)
        attacker_id = (line.owner_id, line.source_id)
        if pet_group_id in tree_model.pet_group_index:
            attacker = tree_model.pet_group_index[pet_group_id]
        # if attacking pet already in pet index: logfile is bugged (one pet has more than one
        # entity name); pet group is not created in this case as it would not have any children
        elif attacker_id not in tree_model.pet_index:
            attacker = tree_model.add_pet_group(line.source_name, pet_group_id, attacker)

        if attacker_id in tree_model.pet_index:
            attacker = tree_model.pet_index[attacker_id]
        else:
            attacker = tree_model.add_pet(
                    line.source_name + get_handle_from_id(line.source_id), attacker_id, attacker)

    ability_id = line.event_name
    if ability_id in tree_model.ability_index[attacker_id]:
        ability = tree_model.ability_index[attacker_id][ability_id]
    else:
        ability = tree_model.add_ability(line.event_name, ability_id, attacker, attacker_id)

    ability_target_id = line.target_id
    if ability_target_id in tree_model.target_index[attacker_id][ability_id]:
        ability_target = tree_model.target_index[attacker_id][ability_id][ability_target_id]
    else:
        ability_target = tree_model.add_target(row_constructor(
                line.target_name,
                get_handle_from_id(ability_target_id), ability_target_id), ability_target_id,
                ability, ability_id, attacker_id, parse_duration)

    return ability_target, ability_target.data


def get_incoming_target_row(
        tree_model: TreeModel, line: LogLine, player_attacked: bool,
        row_constructor: AnalysisTableRow,
        parse_duration: int) -> tuple[TreeItem, DamageTableRow | HealTableRow]:
    """
    Adds the needed parents to the tree model and returns the newly created or already existing
    data row. Also updates combat time of the actor.

    Parameters:
    - :param tree_model: model to work on
    - :param line: log line that contains the ability
    - :param player_attacked: True when player is attacked, False otherwise
    - :param row_constructor: a new object returned by this constructor will hold the row data
    - :param parse_duration: seconds between the first and last line of the combat, rounded up

    :return: reference to newly created or existing TreeItem and data row
    """
    target_id = (line.target_id,)
    target_handle = get_handle_from_id(line.target_id)
    if target_id in tree_model.actor_index:
        target = tree_model.actor_index[target_id]
    else:
        target = tree_model.add_actor(
                line.target_name, target_handle, target_id, row_constructor, player_attacked)
        target.data.combat_start = line.timestamp
    target.data.combat_end = line.timestamp

    if line.source_name:
        source_id = line.source_id
        source_name = line.source_name
    else:
        source_id = line.owner_id
        source_name = line.owner_name

    if source_id in tree_model.source_index[target_id]:
        ability_source = tree_model.source_index[target_id][source_id]
    else:
        ability_source = tree_model.add_source_actor(
                (source_name, get_handle_from_id(source_id)), source_id, target, target_id)

    source_ability_id = line.source_id + line.event_id
    if source_ability_id in tree_model.ability_index[target_id][source_id]:
        source_ability = tree_model.ability_index[target_id][source_id][source_ability_id]
    else:
        source_ability = tree_model.add_source_ability(
                row_constructor(line.event_name, '', source_ability_id), source_ability_id,
                ability_source, source_id, target_id, parse_duration)

    return source_ability, source_ability.data


def get_flags(flag_str: str) -> tuple[bool]:
    """
    Returns flags from flag field of log line.

    :return: (critical_hit, miss, flank, kill, shield_break)
    """
    critical_hit = 'Critical' in flag_str
    miss = 'Miss' in flag_str
    flank = 'Flank' in flag_str
    kill = 'Kill' in flag_str
    shield_break = None  # 'ShieldBreak' in flag_str
    no_floater = None  # 'NoFloater' in flag_str
    return (critical_hit, miss, flank, kill, shield_break, no_floater)


def calculate_damage_row_stats(row: DamageTableRow, combat_time: float) -> tuple:
    """
    Calculates combat stats from raw stats taken from the parse, for example DPS from damage and
    combat time.

    Parameters:
    - :param row: contains the raw data of a row
    - :param combat_time: combat time of the parent entity in seconds

    :return: complete row data according to TREE_HEADER (see __init__.py), plus a tuple containing
    name and handle as first element -> ((name, handle), DPS, Total Damage, ...)
    """
    successful_attacks = row.hull_attacks - row.misses
    try:
        dps = row.total_damage / combat_time
        shield_dps = row.total_shield_damage / combat_time
        hull_dps = row.total_hull_damage / combat_time
        base_dps = row.total_base_damage / combat_time
    except ZeroDivisionError:
        dps = 0.0
        shield_dps = 0.0
        hull_dps = 0.0
        base_dps = 0.0
    try:
        debuff = (row.total_damage / row.total_base_damage) - 1
    except ZeroDivisionError:
        debuff = 0.0
    try:
        crit_chance = row.crit_num / successful_attacks
        flank_rate = row.flank_num / successful_attacks
    except ZeroDivisionError:
        crit_chance = 0.0
        flank_rate = 0.0
    try:
        accuracy = successful_attacks / row.hull_attacks
    except ZeroDivisionError:
        accuracy = 0.0
    return ((row.name, row.handle), dps, row.total_damage, debuff, row.max_one_hit, crit_chance,
            accuracy, flank_rate, row.kills, row.total_attacks, row.misses, row.crit_num,
            row.flank_num, row.total_shield_damage, shield_dps, row.total_hull_damage, hull_dps,
            row.total_base_damage, base_dps, combat_time, row.hull_attacks, row.shield_attacks)


def calculate_heal_row_stats(row: HealTableRow, combat_time: float) -> tuple:
    """
    Calculates combat stats from raw stats taken from the parse, for example HPS from Heal and
    combat time.

    Parameters:
    - :param raw_row_data: contains the raw data of a row
    - :param combat_time: combat time of the parent entity in seconds

    :return: complete row data according to HEAL_TREE_HEADER (see constants.py), plus a tuple
    containing name and handle as first element -> ((name, handle), HPS, Total Heal, ...)
    """
    try:
        hps = row.total_heal / combat_time
        shield_hps = row.shield_heal / combat_time
        hull_hps = row.hull_heal / combat_time
    except ZeroDivisionError:
        hps = 0.0
        shield_hps = 0.0
        hull_hps = 0.0
    try:
        crit_chance = row.critical_heals / row.hull_heal_ticks
    except ZeroDivisionError:
        crit_chance = 0.0

    return ((row.name, row.handle), hps, row.total_heal, row.hull_heal, hull_hps, row.shield_heal,
            shield_hps, row.max_one_heal, crit_chance, row.heal_ticks, row.critical_heals,
            combat_time, row.hull_heal_ticks, row.shield_heal_ticks)


def combine_children_damage_stats(item: TreeItem):
    """
    Combines the stats of the children items intelligently. Absolute numbers are summed,
    percentages are averaged.

    Parameters:
    - :param item: item to retrieve children data from; item.data must be string containing the
    ability name
    """
    children_data = tuple(zip(*item._children))
    result_data = [None] * 22
    combat_time = result_data[19] = children_data[19][0]
    if isinstance(item.data, (str, tuple)):
        result_data[0] = item.data
    else:
        result_data[0] = (item.data.name, item.data.handle, item.data.id[0])
    for index in (2, 8, 9, 10, 11, 12, 13, 15, 17, 20, 21):
        result_data[index] = sum(children_data[index])
    result_data[4] = max(children_data[4])  # max_one_hit
    try:
        result_data[1] = result_data[2] / combat_time  # DPS
        result_data[14] = result_data[13] / combat_time  # shield_DPS
        result_data[16] = result_data[15] / combat_time  # hull_DPS
        result_data[18] = result_data[17] / combat_time  # base_DPS
    except ZeroDivisionError:
        result_data[1] = 0.0
        result_data[14] = 0.0
        result_data[16] = 0.0
        result_data[18] = 0.0
    try:
        result_data[3] = (result_data[2] / result_data[17]) - 1  # debuff
    except ZeroDivisionError:
        result_data[3] = 0.0
    successful_attacks = result_data[20] - result_data[10]
    try:
        result_data[5] = result_data[11] / successful_attacks  # crit_chance
        result_data[6] = successful_attacks / result_data[20]  # accuracy
        result_data[7] = result_data[12] / successful_attacks  # flank_rate
    except ZeroDivisionError:
        result_data[5] = 0.0
        result_data[6] = 0.0
        result_data[7] = 0.0
    item.data = tuple(result_data)


def combine_children_heal_stats(item: TreeItem):
    """
    Combines the stats of the children items intelligently. Absolute numbers are summed,
    percentages are averaged.

    Parameters:
    - :param item: item to retrieve children data from; item.data must be string containing the
    ability name
    """
    children_data = tuple(zip(*item._children))
    result_data = [None] * 14
    combat_time = result_data[11] = children_data[11][0]
    if isinstance(item.data, (str, tuple)):
        result_data[0] = item.data
    else:
        result_data[0] = (item.data.name, item.data.handle)
    for index in (2, 3, 5, 9, 10, 12, 13):
        result_data[index] = sum(children_data[index])
    result_data[7] = max(children_data[7])  # max_one_heal
    try:
        result_data[1] = result_data[2] / combat_time  # HPS
        result_data[4] = result_data[3] / combat_time  # hull_HPS
        result_data[6] = result_data[5] / combat_time  # shield_HPS
    except ZeroDivisionError:
        result_data[1] = 0.0
        result_data[4] = 0.0
        result_data[6] = 0.0
    try:
        result_data[8] = result_data[10] / result_data[12]  # critical_heals
    except ZeroDivisionError:
        result_data[8] = 0.0
    item.data = tuple(result_data)


def merge_single_lines(tree_model: TreeModel):
    """
    Eliminates one level of depth if needed by merging lines that only have a single child. For
    example:

    v Quantum Mines
        v Quantum Mine 34
            > Mine Explosion
        v Quantum Mine 25
            > Mine Explosion

    becomes:\n
    v Quantum Mines - Mine Explosion\n
       > Quantum Mine 34\n
       > Quantum Mine 25


    Parameters:
    - :param tree_model: tree model to analyze and improve
    """
    for player in tree_model._player._children:
        new_pet_groups = dict()

        for ability_or_petgroup in player._children:
            if (len(ability_or_petgroup._children) < 1
                    or ability_or_petgroup._children[0].child_count == 0):
                continue

            for pet in reversed(ability_or_petgroup._children):
                if pet.child_count == 1:
                    ability_name = pet._children[0].data
                    if ability_or_petgroup.data == ability_name:
                        new_pet_group_name = ability_name
                    else:
                        new_pet_group_name = f'{ability_or_petgroup.data} – {ability_name}'
                    if new_pet_group_name in new_pet_groups:
                        new_pet_group = new_pet_groups[new_pet_group_name]
                    else:
                        new_pet_group = TreeItem(new_pet_group_name, player)
                        new_pet_groups[new_pet_group_name] = new_pet_group
                    new_pet_group.append_child(pet)
                    ability_or_petgroup._children.remove(pet)
                    pet.parent = new_pet_group
                    pet._children = pet._children[0]._children

                    for target in pet._children:
                        target.parent = pet

            if ability_or_petgroup.child_count == 0:
                ability_or_petgroup.parent._children.remove(ability_or_petgroup)

        for new_pet_group in new_pet_groups.values():
            player.append_child(new_pet_group)


def complete_damage_sub_tree(item: TreeItem, combat_time):
    """
    Recursive function merging data from the bottom up.

    Parameters:
    - :param item: item to complete
    """
    graph_data = list()
    for child in item._children:
        if child.child_count == 0:
            child.data = calculate_damage_row_stats(child.data, combat_time)
        else:
            complete_damage_sub_tree(child, combat_time)
        graph_data.append(child.graph_data)
    combine_children_damage_stats(item)
    item.graph_data = numpy.sum(graph_data, axis=0, dtype=numpy.float64)


def complete_heal_sub_tree(item: TreeItem, combat_time):
    """
    Recursive function merging data from the bottom up.

    Parameters:
    - :param item: item to complete
    """
    graph_data = list()
    for child in item._children:
        if child.child_count == 0:
            child.data = calculate_heal_row_stats(child.data, combat_time)
        else:
            complete_heal_sub_tree(child, combat_time)
        graph_data.append(child.graph_data)
    combine_children_heal_stats(item)
    item.graph_data = numpy.sum(graph_data, axis=0, dtype=numpy.float64)


def complete_damage_tree(
        tree_model: TreeModel, combat_durations: dict, total_combat_duration: float):
    """
    Merges the data from the bottom up to fill all lines.

    Parameters:
    - :param tree_model: tree model to be completed
    - :param combat_durations: combat durations for all actors
    """
    for actor in bundle(tree_model._player._children, tree_model._npc._children):
        current_combat_time = combat_durations.get(actor.data.id[0], total_combat_duration)
        actor.data.combat_time = current_combat_time
        complete_damage_sub_tree(actor, current_combat_time)


def complete_heal_tree(tree_model: TreeModel, combat_durations: dict, total_combat_duration: float):
    """
    Merges the data from the bottom up to fill all lines.

    Parameters:
    - :param tree_model: tree model to be completed
    - :param combat_durations: combat durations for all actors
    """
    for actor in bundle(tree_model._player._children, tree_model._npc._children):
        current_combat_time = combat_durations.get(actor.data.id[0], total_combat_duration)
        actor.data.combat_time = current_combat_time
        complete_heal_sub_tree(actor, current_combat_time)
