from datetime import timedelta

from .datamodels import Combat, TreeItem, TreeModel, AnalysisTableRow, DamageTableRow, HealTableRow, LogLine
from . import TREE_HEADER, HEAL_TREE_HEADER
from .utilities import get_handle_from_id, bundle

def analyze_combat(combat: Combat, settings: dict) -> tuple[TreeModel, ...]:
    """
    Fully analyzes the given combat and returns the root TreeItem from the output model.
    """
    graph_resolution = settings['graph_resolution']
    graph_timedelta = timedelta(seconds=graph_resolution)
    dmg_out_model = TreeModel(TREE_HEADER)
    dmg_in_model = TreeModel(TREE_HEADER)
    heal_out_model = TreeModel(HEAL_TREE_HEADER)
    heal_in_model = TreeModel(HEAL_TREE_HEADER)
    actor_combat_durations = dict()
    last_graph_time = combat.log_data[0].timestamp
    graph_points = 1
    for line in combat.log_data:
        # manage entites
        player_attacks = line.owner_id.startswith('P')
        player_attacked = line.target_id.startswith('P')
        is_shield_line = line.type == 'Shield'
        crit_flag, miss_flag, flank_flag, kill_flag, shield_break_flag = get_flags(line.flags)
        is_heal = ((is_shield_line and line.magnitude < 0 and line.magnitude2 >= 0) 
                or line.type == 'HitPoints')
        
        # Combat Duration
        try:
            actor_combat_durations[line.owner_id][1] = line.timestamp
        except KeyError:
            actor_combat_durations[line.owner_id] = [line.timestamp, line.timestamp]
        try:
            actor_combat_durations[line.source_id][1] = line.timestamp
        except KeyError:
            actor_combat_durations[line.source_id] = [line.timestamp, line.timestamp]
        try:
            actor_combat_durations[line.target_id][1] = line.timestamp
        except KeyError:
            actor_combat_durations[line.target_id] = [line.timestamp, line.timestamp]

        # HEALS
        if is_heal:
            ability_target = get_outgoing_heal_target_row(heal_out_model, line, player_attacks)
            source_ability = get_incoming_target_row(heal_in_model, line, player_attacked, HealTableRow)

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

        # DAMAGE
        else:
            ability_target = get_outgoing_target_row(dmg_out_model, line, player_attacks)
            source_ability = get_incoming_target_row(dmg_in_model, line, player_attacked, DamageTableRow)
        
            # get table data
            if miss_flag:
                ability_target.misses += 1
                source_ability.misses += 1
            if kill_flag:
                ability_target.kills += 1
                source_ability.kills += 1
            if flank_flag:
                ability_target.flank_num += 1
                source_ability.flank_num += 1
            if crit_flag:
                ability_target.crit_num += 1
                source_ability.crit_num += 1
        
            magnitude = abs(line.magnitude)
            magnitude2 = abs(line.magnitude2)
            ability_target.total_damage += magnitude
            ability_target.total_base_damage += magnitude2
            ability_target.total_attacks += 1
            source_ability.total_damage += magnitude
            source_ability.total_base_damage += magnitude2
            source_ability.total_attacks += 1
            if is_shield_line:
                ability_target.total_shield_damage += magnitude
                ability_target.shield_attacks += 1
                source_ability.total_shield_damage += magnitude
                source_ability.shield_attacks += 1
            else:
                ability_target.total_hull_damage += magnitude
                source_ability.total_hull_damage += magnitude
                if not miss_flag and magnitude != 0 and magnitude2 != 0:
                    ability_target.resistance_sum += magnitude / magnitude2
                    source_ability.resistance_sum += magnitude / magnitude2
                ability_target.hull_attacks += 1
                source_ability.hull_attacks += 1
            
            if magnitude > ability_target.max_one_hit:
                ability_target.max_one_hit = magnitude
            if magnitude > source_ability.max_one_hit:
                source_ability.max_one_hit = magnitude
    
    for actor_id, (start_time, end_time) in actor_combat_durations.items():
        actor_combat_durations[actor_id] = round((end_time - start_time).total_seconds(), 1)

    merge_single_lines(dmg_out_model)
    complete_damage_tree(dmg_out_model, actor_combat_durations)
    complete_damage_tree(dmg_in_model, actor_combat_durations)
    complete_heal_tree(heal_out_model, actor_combat_durations)
    complete_heal_tree(heal_in_model, actor_combat_durations)
    return dmg_out_model, dmg_in_model, heal_out_model, heal_in_model

def get_outgoing_target_row(tree_model: TreeModel, line: LogLine, player_attacks: bool) -> DamageTableRow:
    '''
    Adds the needed parents to the tree model and returns the newly created or already existing data row.
    Also updates combat time of the actor.

    Parameters:
    - :param tree_model: model to work on
    - :param line: log line that contains the ability
    - :param player_attacks: True when player attacks, False otherwise

    :return: reference to newly created or existing data row
    '''
    attacker_id = (line.owner_id,)
    attacker_handle = get_handle_from_id(line.owner_id)
    if attacker_id in tree_model.actor_index:
        attacker = tree_model.actor_index[attacker_id]
    else:
        attacker = tree_model.add_actor(line.owner_name, attacker_handle, attacker_id, 
                DamageTableRow, player_attacks)
        attacker.data.combat_start = line.timestamp
    attacker.data.combat_end = line.timestamp

    if line.source_name:
        pet_group_id = (line.owner_id, line.source_name)
        if pet_group_id in tree_model.pet_group_index:
            attacker = tree_model.pet_group_index[pet_group_id]
        else:
            attacker = tree_model.add_pet_group(line.source_name, pet_group_id, attacker)

        attacker_id = (line.owner_id, line.source_id)
        if attacker_id in tree_model.pet_index:
            attacker = tree_model.pet_index[attacker_id]
        else:
            attacker = tree_model.add_pet(line.source_name + 
                    get_handle_from_id(line.source_id), attacker_id, attacker)
    
    ability_id = line.event_name
    if ability_id in tree_model.ability_index[attacker_id]:
        ability = tree_model.ability_index[attacker_id][ability_id]
    else:
        ability = tree_model.add_ability(line.event_name, ability_id, attacker, attacker_id)

    ability_target_id = line.target_id
    if ability_target_id in tree_model.target_index[attacker_id][ability_id]:
        ability_target = tree_model.target_index[attacker_id][ability_id][ability_target_id].data
    else:
        ability_target = tree_model.add_target(DamageTableRow(line.target_name, 
                get_handle_from_id(ability_target_id), ability_target_id), ability_target_id, ability, 
                ability_id, attacker_id)
        
    return ability_target

def get_outgoing_heal_target_row(tree_model: TreeModel, line: LogLine, player_attacks: bool) -> HealTableRow:
    '''
    Adds the needed parents to the tree model and returns the newly created or already existing data row.
    Also updates combat time of the actor.

    Parameters:
    - :param tree_model: model to work on
    - :param line: log line that contains the ability
    - :param player_attacks: True when player attacks, False otherwise

    :return: reference to newly created or existing data row
    '''
    if line.source_name:
        attacker_name = line.source_name
        attacker_id = (line.source_id,)
        attacker_handle = get_handle_from_id(line.source_id)
    else:
        attacker_name = line.owner_name
        attacker_id = (line.owner_id,)
        attacker_handle = get_handle_from_id(line.owner_id)
    if attacker_id in tree_model.actor_index:
        attacker = tree_model.actor_index[attacker_id]
    else:
        attacker = tree_model.add_actor(attacker_name, attacker_handle, attacker_id, 
                HealTableRow, player_attacks)
        attacker.data.combat_start = line.timestamp
    attacker.data.combat_end = line.timestamp

    ability_id = line.event_name
    if ability_id in tree_model.ability_index[attacker_id]:
        ability = tree_model.ability_index[attacker_id][ability_id]
    else:
        ability = tree_model.add_ability(line.event_name, ability_id, attacker, attacker_id)

    ability_target_id = line.target_id
    if ability_target_id in tree_model.target_index[attacker_id][ability_id]:
        ability_target = tree_model.target_index[attacker_id][ability_id][ability_target_id].data
    else:
        ability_target = tree_model.add_target(HealTableRow(line.target_name, 
                get_handle_from_id(ability_target_id), ability_target_id), ability_target_id, ability, 
                ability_id, attacker_id)
        
    return ability_target

def get_incoming_target_row(tree_model: TreeModel, line: LogLine, player_attacked: bool,
        row_constructor: AnalysisTableRow) -> AnalysisTableRow:
    '''
    Adds the needed parents to the tree model and returns the newly created or already existing data row.
    Also updates combat time of the actor.

    Parameters:
    - :param tree_model: model to work on
    - :param line: log line that contains the ability
    - :param player_attacked: True when player is attacked, False otherwise
    - :param row_constructor: a new object returned by this constructor will hold the row data

    :return: reference to newly created or existing data row
    '''
    target_id = (line.target_id,)
    target_handle = get_handle_from_id(line.target_id)
    if target_id in tree_model.actor_index:
        target = tree_model.actor_index[target_id]
    else:
        target = tree_model.add_actor(line.target_name, target_handle, target_id, row_constructor, 
                player_attacked)
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
        ability_source = tree_model.add_source_actor((source_name, get_handle_from_id(source_id)), source_id, 
                target, target_id)

    source_ability_id = line.source_id + line.event_id
    if source_ability_id in tree_model.ability_index[target_id][source_id]:
        source_ability = tree_model.ability_index[target_id][source_id][source_ability_id].data
    else:
        source_ability = tree_model.add_source_ability(row_constructor(line.event_name, '', 
                source_ability_id), source_ability_id, ability_source, source_id, target_id)
        
    return source_ability

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

def calculate_damage_row_stats(raw_row_data: DamageTableRow, combat_time: float) -> tuple:
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

def calculate_heal_row_stats(raw_row_data: HealTableRow, combat_time: float) -> tuple:
    '''
    Calculates combat stats from raw stats taken from the parse, for example HPS from Heal and combat time.

    Parameters:
    - :param raw_row_data: contains the raw data of a row
    - :param combat_time: combat time of the parent entity in seconds

    :return: complete row data according to HEAL_TREE_HEADER (see __init__.py), plus a tuple containing name 
    and handle as first element -> ((name, handle), HPS, Total Heal, ...)
    '''
    (name, handle, total_heal, hull_heal, shield_heal, max_one_heal, heal_ticks, critical_heals, _, 
            hull_heal_ticks, shield_heal_ticks) = raw_row_data
    try:
        hps = total_heal / combat_time
        shield_hps = shield_heal / combat_time
        hull_hps = hull_heal / combat_time
    except ZeroDivisionError:
        hps = 0.0
        shield_hps = 0.0
        hull_hps = 0.0
    try:
        crit_chance = critical_heals / heal_ticks
    except ZeroDivisionError:
        crit_chance = 0.0

    return ((name, handle), hps, total_heal, hull_heal, hull_hps, shield_heal, shield_hps, max_one_heal, 
            crit_chance, heal_ticks, critical_heals, combat_time, hull_heal_ticks, shield_heal_ticks)

def combine_children_damage_stats(item: TreeItem) -> tuple:
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
            if isinstance(item.data, (str, tuple)):
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

def combine_children_heal_stats(item: TreeItem) -> tuple:
    '''
    Combines the stats of the children items intelligently. Absolute numbers are summed, percentages are
    averaged.

    Parameters:
    - :param item: item to retrieve children data from; item.data must be string containing the ability name

    :return: row data according to HEAL_TREE_HEADER (see __init__.py), plus the name of the ability as 
    first element -> (name, HPS, Total Heal, ...)
    '''
    for index, column in enumerate(zip(*item._children)):
        if index == 0:
            if isinstance(item.data, (str, tuple)):
                combined_data = [item.data]
            else:
                combined_data = [(item.data.name, item.data.handle)]
            continue
        if index == 8:
            combined_data.append(sum(column) / len(column))
        elif index == 7:
            combined_data.append(max(column))
        elif index == 11:
            combined_data.append(column[0])
        else:
            combined_data.append(sum(column))
    return tuple(combined_data)

def merge_single_lines(tree_model: TreeModel):
    '''
    Eliminates one level of depth if needed by merging lines that only have a single child. For example:

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
    '''
    for player in tree_model._player._children:
        new_pet_groups = dict()

        for ability_or_petgroup in player._children:
            if ability_or_petgroup._children[0].child_count == 0:
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
    '''
    Recursive function merging data from the bottom up.

    Parameters:
    - :param item: item to complete
    '''
    for child in item._children:
        if child.child_count == 0:
            child.data = calculate_damage_row_stats(child.data, combat_time)
        else:
            complete_damage_sub_tree(child, combat_time)
    item.data = combine_children_damage_stats(item)

def complete_heal_sub_tree(item: TreeItem, combat_time):
    '''
    Recursive function merging data from the bottom up.

    Parameters:
    - :param item: item to complete
    '''
    for child in item._children:
        if child.child_count == 0:
            child.data = calculate_heal_row_stats(child.data, combat_time)
        else:
            complete_heal_sub_tree(child, combat_time)
    item.data = combine_children_heal_stats(item)

def complete_damage_tree(tree_model: TreeModel, combat_durations: dict):
    '''
    Merges the data from the bottom up to fill all lines.

    Parameters:
    - :param tree_model: tree model to be completed
    - :param combat_durations: combat durations for all actors
    '''
    for actor in bundle(tree_model._player._children, tree_model._npc._children):
        current_combat_time = combat_durations[actor.data.id[0]]
        actor.data.combat_time = current_combat_time
        complete_damage_sub_tree(actor, current_combat_time)

def complete_heal_tree(tree_model: TreeModel, combat_durations: dict):
    '''
    Merges the data from the bottom up to fill all lines.

    Parameters:
    - :param tree_model: tree model to be completed
    - :param combat_durations: combat durations for all actors
    '''
    for actor in bundle(tree_model._player._children, tree_model._npc._children):
        current_combat_time = combat_durations[actor.data.id[0]]
        actor.data.combat_time = current_combat_time
        complete_heal_sub_tree(actor, current_combat_time)