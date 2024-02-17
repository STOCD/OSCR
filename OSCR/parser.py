from datetime import timedelta

from .datamodels import Combat, TreeItem, TreeModel, AnalysisTableRow
from . import TREE_HEADER
from .utilities import get_handle_from_id

def analyze_combat(combat: Combat, settings: dict) -> TreeItem:
    """
    Fully analyzes the given combat and returns the root TreeItem from the output model.
    """
    graph_resolution = settings['graph_resolution']
    graph_timedelta = timedelta(seconds=graph_resolution)
    data = TreeModel(TREE_HEADER)
    last_graph_time = combat.log_data[0].timestamp
    graph_points = 1
    for line in combat.log_data:
        # manage entites
        player_attacks = line.owner_id.startswith('P')
        player_attacked = line.target_id.startswith('P')
        attacker = None
        target = None
        crit_flag, miss_flag, flank_flag, kill_flag, shield_break_flag = get_flags(line.flags)

        attacker_id = (line.owner_id,)
        attacker_handle = get_handle_from_id(line.owner_id)
        if attacker_id in data.actor_index:
            attacker = data.actor_index[attacker_id]
        else:
            attacker = data.add_actor(line.owner_name, attacker_handle, attacker_id, player_attacks)
            attacker.data.combat_start = line.timestamp
        attacker.data.combat_end = line.timestamp

        if line.source_name:
            pet_group_id = (line.owner_id, line.source_name)
            if pet_group_id in data.pet_group_index:
                attacker = data.pet_group_index[pet_group_id]
            else:
                attacker = data.add_pet_group(line.source_name, pet_group_id, attacker)

            attacker_id = (line.owner_id, line.source_id)
            if attacker_id in data.pet_index:
                attacker = data.pet_index[attacker_id]
            else:
                attacker = data.add_pet(line.source_id + 
                        get_handle_from_id(line.source_id), attacker_id, attacker)
        
        ability_id = line.event_id
        if ability_id in data.ability_index[attacker_id]:
            ability = data.ability_index[attacker_id][ability_id]
        else:
            ability = data.add_ability(line.event_name, ability_id, attacker, attacker_id)

        ability_target_id = line.target_id
        if ability_target_id in data.target_index[attacker_id][ability_id]:
            ability_target = data.target_index[attacker_id][ability_id][ability_target_id].data
        else:
            ability_target = data.add_target(AnalysisTableRow(line.target_name, 
                    get_handle_from_id(ability_target_id), ability_target_id), ability_target_id, ability, 
                    ability_id, attacker_id)

        # get table data
        if miss_flag:
            ability_target.misses += 1
        if kill_flag:
            ability_target.kills += 1
        if flank_flag:
            ability_target.flank_num += 1
        
        if ((line.type == 'Shield' and line.magnitude < 0 and line.magnitude2 >= 0) 
                        or line.type == 'HitPoints'):
            pass
        else:
            magnitude = abs(line.magnitude)
            magnitude2 = abs(line.magnitude2)
            ability_target.total_damage += magnitude
            ability_target.total_base_damage += magnitude2
            if line.type == 'Shield':
                ability_target.total_shield_damage += magnitude
                ability_target.shield_attacks += 1
            else:
                ability_target.total_hull_damage += magnitude
                if not miss_flag and magnitude != 0 and magnitude2 != 0:
                    ability_target.resistance_sum += magnitude / magnitude2
                    ability_target.hull_attacks += 1
            ability_target.total_attacks += 1
            if crit_flag:
                ability_target.crit_num += 1
            if magnitude > ability_target.max_one_hit:
                ability_target.max_one_hit = magnitude
                
    complete_tree(data)
    return data

def get_flags(flag_str:str) -> tuple[bool]:
    '''
    Returns flags from flag field of log line.

    Return: (critical_hit, miss, flank, kill, shield_break)
    '''
    critical_hit = 'Critical' in flag_str
    miss = 'Miss' in flag_str
    flank = 'Flank' in flag_str
    kill = 'Kill' in flag_str
    shield_break = 'ShieldBreak' in flag_str
    return (critical_hit, miss, flank, kill, shield_break)

def calculate_row_stats(raw_row_data: AnalysisTableRow, combat_time: float) -> tuple:
    '''
    Calculates combat stats from raw stats taken from the parse, for example DPS from damage and combat time.

    Parameters:
    - :param raw_row_data: contains the raw data of a row
    - :param combat_time: combat time of the parent entity in seconds

    :return: complete row data according to TREE_HEADER (see __init__.py), plus a tuple containing name and 
    handle as first element -> ((name, handle), DPS, Total Damage, ...)
    '''
    (name, handle, total_damage, max_one_hit, kills, total_attacks, misses, crit_num, flank_num, 
    total_shield_damage, total_hull_damage, total_base_damage, _, hull_attacks, shield_attacks) = raw_row_data
    successful_attacks = hull_attacks - misses
    try:
        dps = total_damage / combat_time
        shield_dps = total_shield_damage / combat_time
        hull_dps = total_hull_damage / combat_time
        base_dps = total_base_damage / combat_time
    except ZeroDivisionError:
        dps = 0.0
        shield_dps = 0.0
        hull_dps = 0.0
        base_dps = 0.0
    try:
        debuff = (raw_row_data.resistance_sum / successful_attacks) - 1
    except ZeroDivisionError:
        debuff = 0.0
    try:
        crit_chance = crit_num / successful_attacks
    except ZeroDivisionError:
        crit_chance = 0.0
    try:
        accuracy = successful_attacks / hull_attacks
    except ZeroDivisionError:
        accuracy = 0.0
    try:
        flank_rate = flank_num / successful_attacks
    except ZeroDivisionError:
        flank_rate = 0.0
    return ((name, handle), dps, total_damage, debuff, max_one_hit, crit_chance, accuracy, flank_rate,
            kills, total_attacks, misses, crit_num, flank_num, total_shield_damage, shield_dps, 
            total_hull_damage, hull_dps, total_base_damage, base_dps, combat_time, hull_attacks, 
            shield_attacks)

def combine_children_stats(item: TreeItem) -> tuple:
    '''
    Combines the stats of the children items intelligently. Absolute numbers are summed, percentages are
    averaged.

    Parameters:
    - :param item: item to retrieve children data from; item.data must be string containing the ability name

    :return: row data according to TREE_HEADER (see __init__.py), plus the name of the ability as 
    first element -> (name, DPS, Total Damage, ...)
    '''
    for index, column in enumerate(zip(*item._children)):
        if index == 0:
            if isinstance(item.data, str):
                combined_data = [item.data]
            else:
                combined_data = [(item.data.name, item.data.handle)]
            continue
        if index in (3, 5, 6, 7):
            combined_data.append(sum(column) / len(column))
        elif index == 4:
            combined_data.append(max(column))
        elif index == 19:
            combined_data.append(column[0])
        else:
            combined_data.append(sum(column))
    return tuple(combined_data)

def complete_tree(tree_model: TreeModel) -> TreeModel:
    '''
    Merges the data from the bottom up to fill all lines.

    Parameters:
    - :param tree_model: tree model to be completed

    :return: completed tree model
    '''
    combat_times = dict()
    for actor_id, actor in tree_model.actor_index.items():
        current_combat_time = round((actor.data.combat_end - actor.data.combat_start).total_seconds(), 1)
        actor.data.combat_time = current_combat_time
        combat_times[actor_id[0]] = current_combat_time

    for actor_id, actor_subdict in tree_model.target_index.items():
        current_combat_time = combat_times[actor_id[0]]
        for ability_subdict in actor_subdict.values():
            for target in ability_subdict.values():
                target.data = calculate_row_stats(target.data, current_combat_time)

        for ability in tree_model.ability_index[actor_id].values():
            ability.data = combine_children_stats(ability)

    for pet in tree_model.pet_index.values():
        pet.data = combine_children_stats(pet)

    for pet_group in tree_model.pet_group_index.values():
        pet_group.data = combine_children_stats(pet_group)

    for actor in tree_model.actor_index.values():
        actor.data = combine_children_stats(actor)