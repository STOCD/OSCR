""" Combat Detection Methods """

import re

from .datamodels import LogLine


class Detection:
    # TODO: Dynamically load as json?
    MAP_IDENTIFIERS_EXISTENCE = {
        "Space_Borg_Battleship_Raidisode_Sibrian_Elite_Initial": {
            "map": "Infected Space",
            "difficulty": "Elite",
        },
        "Space_Borg_Dreadnought_Raidisode_Sibrian_Final_Boss": {
            "map": "Infected Space",
            "difficulty": None,
        },
        "Mission_Space_Romulan_Colony_Flagship_Lleiset": {
            "map": "Azure Nebula Rescue",
            "difficulty": None,
        },
        "Space_Klingon_Dreadnought_Dsc_Sarcophagus": {
            "map": "Battle At The Binary Stars",
            "difficulty": None,
        },
        "Event_Procyon_5_Queue_Krenim_Dreadnaught_Annorax": {
            "map": "Battle At Procyon V",
            "difficulty": None,
        },
        "Mission_Space_Borg_Queen_Diamond_Brg_Queue_Liberation": {
            "map": "Borg Disconnected",
            "difficulty": None,
        },
        "Mission_Starbase_Mirror_Ds9_Mu_Queue": {
            "map": "Counterpoint",
            "difficulty": None,
        },
        "Space_Crystalline_Entity_2018": {
            "map": "Crystalline Entity",
            "difficulty": None,
        },
        "Event_Ico_Qonos_Space_Herald_Dreadnaught": {
            "map": "Gateway To Grethor",
            "difficulty": None,
        },
        "Mission_Space_Federation_Science_Herald_Sphere": {
            "map": "Herald Sphere",
            "difficulty": None,
        },
        "Msn_Dsc_Priors_System_Tfo_Orbital_Platform_1_Fed_Dsc": {
            "map": "Operation Riposte",
            "difficulty": None,
        },
        "Space_Borg_Dreadnought_R02": {
            "map": "Cure Found",
            "difficulty": None,
        },
        "Space_Klingon_Tos_X3_Battlecruiser": {
            "map": "Days Of Doom",
            "difficulty": None,
        },
        "Msn_Luk_Colony_Dranuur_Queue_System_Upgradeable_Satellite": {
            "map": "Dranuur Gauntlet",
            "difficulty": None,
        },
        "Space_Borg_Dreadnought_Raidisode_Khitomer_Intro_Boss": {
            "map": "Khitomer Space",
            "difficulty": None,
        },
        "Mission_Spire_Space_Voth_Frigate": {
            "map": "Storming The Spire",
            "difficulty": None,
        },
        "Space_Drantzuli_Alpha_Battleship": {
            "map": "Swarm",
            "difficulty": None,
        },
        "Mission_Beta_Lankal_Destructible_Reactor": {
            "map": "To Hell With Honor",
            "difficulty": None,
        },
        "Space_Federation_Dreadnought_Jupiter_Class_Carrier": {
            "map": "Gravity Kills",
            "difficulty": None,
        },
        "Msn_Luk_Hypermass_Queue_System_Tzk_Protomatter_Facility": {
            "map": "Gravity Kills",
            "difficulty": None,
        },
        "Space_Borg_Dreadnought_Hive_Intro": {
            "map": "Hive Space",
            "difficulty": None,
        },
        "Ground_Federation_Capt_Mirror_Runabout_Tfo": {
            "map": "Operation Wolf",
            "difficulty": "Normal",
        },
        "Bluegills_Ground_Boss": {
            "map": "Bug Hunt",
            "difficulty": None,
        },
        "Msn_Edren_Queue_Ground_Gorn_Lt_Tos_Range_Rock": {
            "map": "Miner Instabilities",
            "difficulty": None,
        },
        "Msn_Ground_Capt_Mirror_Janeway_Boss_Unkillable": {
            "map": "Jupiter Station Showdown",
            "difficulty": None,
        },
        "Mission_Event_Tholian_Invasion_Ext_Boss": {
            "map": "Nukara Prime: Transdimensional Tactics",
            "difficulty": None,
        },
        "Space_Borg_Dreadnought_Wolf359": {
            "map": "Battle of Wolf 359",
            "difficulty": None,
        },
    }

    # There's a possibility where there's so much overkill that the entity is
    # detected as an entity of the difficulty higher. This would be more likely to
    # happen on ground maps.
    MAP_DIFFICULTY_ENTITY_HULL_IDENTIFIERS = {
        "Infected Space": {},
        "Hive Space": {},
        "Bug Hunt": {},
        "Miner Instabilities": {},
        "Jupiter Station Showdown": {},
        "Operation Wolf": {},
        "Nukara Prime: Transdimensional Tactics": {},
    }

    @staticmethod
    def detect_line(line: LogLine) -> tuple:
        """
        Do a very shallow map detect based on a log line only
        taking NPCs into consideration.

        return: a tuple in the form of (Map, Difficulty)
        """

        # Note: Doing a string split is slightly faster than using a regex.
        # re.search(r"C\[.* (?P<name>.*)]", line.target_id)

        split = line.target_id.split(" ")
        if len(split) != 2:
            return "Combat", None

        entity = split[1].replace("]", "")
        entry = Detection.MAP_IDENTIFIERS_EXISTENCE.get(entity)
        if entry:
            return entry["map"], entry["difficulty"]

        return "Combat", None
