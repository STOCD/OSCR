""" Combat Detection Methods """

from .datamodels import LogLine
from .utilities import get_entity_name


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

    # Detect maps based on # of entities
    MAP_DIFFICULTY_ENTITY_DEATH_COUNTS = {
        "Infected Space": {
            "Advanced": {
                "Space_Borg_Battleship_Raidisode": 5,
                "Space_Borg_Cruiser_Raidisode": 6,
                "Mission_Borgraid1_Transwarp_02": 1,
                "Space_Borg_Dreadnought_Raidisode_Sibrian_Final_Boss": 1,
            },
            "Elite": {
                "Space_Borg_Battleship_Raidisode_Sibrian_Elite_Initial": 2,
                "Space_Borg_Dreadnought_Raidisode_Sibrian_Initial_Boss": 1,
                "Space_Borg_Cruiser_Raidisode_Sibrian_Elite_Initial": 4,
                "Space_Borg_Battleship_Raidisode": 2,
                "Mission_Borgraid1_Transwarp_02": 1,
            },
        },
        "Hive Space": {
            "Advanced": {
                "Mission_Space_Borg_Queen_Diamond": 1,
                "Mission_Space_Borg_Battleship_Queen_2_0f_2": 1,
                "Mission_Space_Borg_Battleship_Queen_1_0f_2": 1,
            },
            "Elite": {
                "Mission_Space_Borg_Queen_Diamond": 1,
                "Mission_Space_Borg_Battleship_Queen_2_0f_2": 1,
                "Mission_Space_Borg_Battleship_Queen_1_0f_2": 1,
            },
        },
        "Bug Hunt": {
            "Elite": {
                "Msn_Dlt_Bluegill_Hunt_Queue_Ground_Ens": 3,
                "Bluegills_Ground_Cdr": 26,
                "Bluegills_Ground_Capt": 1,
                "Bluegills_Ground_Boss": 1,
            },
        },
        "Jupiter Station Showdown": {
            "Elite": {
                "Msn_Assimilated_Fed_Odyssey_Ground_Borg_Ens_Melee": 27,
                "Msn_Assimilated_Fed_Odyssey_Ground_Borg_Lt_Range": 17,
                "Msn_Assimilated_Fed_Odyssey_Ground_Borg_Cdr_Melee": 2,
            }
        },
        "Miner Instabilities": {
            "Elite": {
                "Ground_Nakuhl_Capt_Range_Male": 1,
            }
        },
        "Nukara Prime: Transdimensional Tactics": {
            "Elite": {
                "Mission_Event_Tholian_Invasion_Ext_Boss": 1,
            },
        },
        "Battle of Wolf 359": {
            "Elite": {
                "Space_Borg_Cruiser_Wolf359": 3,
            }
        },
    }

    # Detect maps based on # hull damage taken.
    MAP_DIFFICULTY_ENTITY_HULL_COUNTS = {
        "Hive Space": {
            "Advanced": {
                "Space_Borg_Cruiser_Hive_Intro1": 461582,
                "Space_Borg_Cruiser_Hive_Intro2": 461582,
                "Space_Borg_Battleship_Hive_Intro": 576977,
                "Space_Borg_Dreadnought_Hive_Intro": 1707034,
            },
            "Elite": {
                "Space_Borg_Cruiser_Hive_Intro1": 2165239,
                "Space_Borg_Cruiser_Hive_Intro2": 2165239,
                "Space_Borg_Battleship_Hive_Intro": 2706549,
                "Space_Borg_Dreadnought_Hive_Intro": 8007542,
            },
        },
        "Jupiter Station Showdown": {
            "Elite": {
                "Msn_Assimilated_Fed_Odyssey_Ground_Borg_Ens_Melee": 2605,
                "Msn_Assimilated_Fed_Odyssey_Ground_Borg_Lt_Range": 3439,
            }
        },
        "Bug Hunt": {
            # It's very easy to overkill on ground.
            "Elite": {
                # "Bluegills_Ground_Cdr": 9444,
                # "Bluegills_Ground_Ens": 3191,
                # "Bluegills_Ground_Lt": 4986,
                # "Bluegills_Ground_Capt": 32567,
                "Bluegills_Ground_Boss": 449432,
            }
        },
        "Miner Instabilities": {
            # It's very easy to overkill on ground.
            "Elite": {
                "Ground_Romulan_Tos_Cdr_Range": 6513,
                # "Ground_Romulan_Tos_Lt_Range": 3439,
                # "Ground_Romulan_Tos_Ens_Range": 2605,
                # "Ground_Nakuhl_Cdr_Range_Male": 6513,
                # "Ground_Nakuhl_Cdr_Range_Female": 6513,
                # "Ground_Nakuhl_Lt_Range_Male": 3439,
                # "Ground_Nakuhl_Lt_Range_Female": 3439,
                # "Ground_Nakuhl_Ens_Melee": 2605,
                # "Ground_Nakuhl_Ens_Range": 2605,
                "Ground_Nakuhl_Capt_Range_Male": 20843,
            }
        },
        "Nukara Prime: Transdimensional Tactics": {
            "Elite": {
                "Mission_Event_Tholian_Invasion_Ext_Boss_Portal": 0,
            }
        },
        "Battle of Wolf 359": {
            "Elite": {
                "Space_Borg_Turret_Medium_Plasma_Torpedo_Wolf359": 2081960,
                "Space_Borg_Turret_Medium_Plasma_Beam_Wolf359": 2081960,
                "Space_Borg_Turret_Medium_Tractor_Beam_Wolf359": 2081960,
                "Space_Borg_Wolf359_Escape_Pod_Tractor_Beam": 2081960,  # Assumption
                "Space_Borg_Frigate_Wolf359": 2081960,
                "Space_Borg_Cruiser_Wolf359": 0,
            }
        },
    }

    BUILD_DETECTION_ABILITIES = {
        # DEW
        "Surgical Strikes III": "Surgical Strikes",
        "Reroute Reserves to Weapons": "Reroute Reserves to Weapons",
        "Exceed Rated Limits": "Exceed Rated Limits",
        "Rapid Fire III": "Cannons: Rapid Fire",
        "Scatter Volley III": "Cannons: Scatter Volley",
        "Overload III": "Beams: Overload",
        "Fire at Will III": "Beams: Fire At Will",
        # Kinetic
        "Isolytic Tear": "Kinetic",
        # EPG
        "Electrified Anomalies": "Exotic",
        "Deteriorating Secondary Deflector": "Exotic",
        "Gravity Well III": "Exotic",
        # Support
        "Greater Than The Sum": "Support",
        # Lower Rank abilities that may be commonly used.
        "Rapid Fire II": "Cannons: Rapid Fire",
        "Scatter Volley II": "Cannons: Scatter Volley",
        "Fire at Will II": "Beams: Fire At Will",
        # Classify these last
        "Thalaron Pulse": "Thalaron Pulse",
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

        entity = get_entity_name(line.target_id)
        if entity is None:
            return "Combat", None

        entry = Detection.MAP_IDENTIFIERS_EXISTENCE.get(entity)
        if entry:
            return entry["map"], entry["difficulty"]

        return "Combat", None
