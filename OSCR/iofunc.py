import os
import gzip
from io import TextIOWrapper
from re import sub as re_sub
from datetime import timedelta

from .utilities import to_datetime, logline_to_str

# currently as constant, will be some kind of import from disk or config file eventually
MAP_IDENTIFIERS_EXISTENCE = {
    "Space_Borg_Battleship_Raidisode_Sibrian_Elite_Initial": ("Infected Space", 'Elite'),
    "Space_Borg_Dreadnought_Raidisode_Sibrian_Final_Boss": (
            "Infected Space", None, ("Space_Borg_Battleship_Raidisode_Sibrian_Elite_Initial",)),
    "Mission_Space_Romulan_Colony_Flagship_Lleiset": ("Azure Nebula", ''),
    "Space_Klingon_Dreadnought_Dsc_Sarcophagus": ("Battle At The Binary Stars", ''),
    "Event_Procyon_5_Queue_Krenim_Dreadnaught_Annorax": ("Battle At Procyon V", ''),
    "Mission_Space_Borg_Queen_Diamond_Brg_Queue_Liberation": ("Borg Disconnected", ''),
    "Mission_Starbase_Mirror_Ds9_Mu_Queue": ("Counterpoint", ''),
    "Space_Crystalline_Entity_2018": ("Crystalline Entity", ''),
    "Event_Ico_Qonos_Space_Herald_Dreadnaught": ("Gateway To Grethor", ''),
    "Mission_Space_Federation_Science_Herald_Sphere": ("Herald Sphere", ''),
    "Msn_Dsc_Priors_System_Tfo_Orbital_Platform_1_Fed_Dsc": ("Operation Riposte", ''),
    "Space_Borg_Dreadnought_R02": ("Cure Found", ''),
    "Space_Klingon_Tos_X3_Battlecruiser": ("Days Of Doom", ''),
    "Msn_Luk_Colony_Dranuur_Queue_System_Upgradeable_Satellite": ("Dranuur Gauntlet", ''),
    "Space_Borg_Dreadnought_Raidisode_Khitomer_Intro_Boss": ("Khitomer Space", ''),
    "Mission_Spire_Space_Voth_Frigate": ("Storming The Spire", ''),
    "Space_Drantzuli_Alpha_Battleship": ("Swarm", ''),
    "Mission_Beta_Lankal_Destructible_Reactor": ("To Hell With Honor", ''),
    "Space_Federation_Dreadnought_Jupiter_Class_Carrier": ("Gravity Kills", ''),
    "Msn_Luk_Hypermass_Queue_System_Tzk_Protomatter_Facility": ("Gravity Kills", ''),
    "Space_Borg_Dreadnought_Hive_Intro": ("Hive Space", ''),
    "Mission_Space_Borg_Battleship_Queen_1_0f_2": ("Hive Space", ''),
    "Msn_Kcw_Rura_Penthe_System_Tfo_Dilithium_Hauler": ("Best Served Cold", ''),
    "Ground_Federation_Capt_Mirror_Runabout_Tfo": ("Operation Wolf", ''),
    "Bluegills_Ground_Boss": ("Bug Hunt", ''),
    "Msn_Edren_Queue_Ground_Gorn_Lt_Tos_Range_Rock": ("Miner Instabilities", ''),
    }

# There's a possibility where there's so much overkill that the entity is
# detected as an entity of the difficulty higher. This would be more likely to
# happen on ground maps.
MAP_DIFFICULTY_ENTITY_HULL_IDENTIFIERS = {
    "Infected Space": {
        "Gateway": {
            "Elite": 32000000,
            "Advanced": 6828137,
        },
    },
    "Hive Space": {
        "Borg Queen Octahedron": {
            "Elite": 16040000, # TODO: Need to validate.
            "Advanced": 3414068,
        },
    },
    "Bug Hunt": {
        "Larval Queen": {
            "Elite": 32567,
        },
        "Spawnmother": {
            "Elite": 449432,
        },
    },
    # TODO: Capture Na'kuhl Captain Hull Value (There's only one)
    "Miner Instabilities": {
        "Na'kuhl Captain": {
            "Elite": 20843,
        },
    },
}

def format_timestamp(timestamp:str) -> str:
    '''
    Formats timestamp. '24:01:13:04:37:45.7' becomes '24-01-13_04:37:45'
    '''
    return timestamp.replace(':', '-', 2).replace(':', '_', 1).split('.')[0]

def is_gz_file(filepath):
    with open(filepath, 'rb') as test_f:
        return test_f.read(2) == b'\x1f\x8b'

def get_lines(log_path:str) -> list:
    '''
    Returns a list of lines parsed from the log file.
    This function is aware that the file being passed in could be gzipped.
    '''
    lines_list = list()

    if is_gz_file(log_path):
        with gzip.open(log_path, 'rt', encoding='utf-8') as file:
            lines_list = file.readlines()
    else:
        with open(log_path, 'r', encoding='utf-8') as file:
            lines_list = file.readlines()

    return lines_list

def get_combat_log_data(log_path:str):
    if not (os.path.exists(log_path) and os.path.isfile(log_path)):
        raise FileNotFoundError(f'Invalid Path: {log_path}')
    if os.path.getsize(log_path) > 125 * 1024 * 1024:
        raise FileExistsError(f'File at {log_path} is too large. Use get_massive_log_data(...) instead')
    lines_list = get_lines(log_path)
    if len(lines_list) < 1 or not lines_list[0].strip():
        raise TypeError('File must contain at least one not-empty line')
    if not '::' in lines_list[0] or not ',' in lines_list[0]:
        raise TypeError("First line invalid. First line may not be empty and must contain '::' and ','.")
    return lines_list

def get_massive_log_data(log_path:str, temp_folder_path:str, combat_distance:int = 100) -> tuple[list, list]:
    '''
    Get log lines from massive combatlog file. Return the latest about 480000 lines of the log as well
    as paths to temporary files containing the remaining lines.
    '''
    absolute_target_path = os.path.abspath(temp_folder_path)
    if not (os.path.exists(log_path) and os.path.isfile(log_path)):
        raise FileNotFoundError(f'Invalid Log Path: {log_path}')
    if not (os.path.exists(absolute_target_path) and os.path.isdir(absolute_target_path)):
        raise FileNotFoundError(f'Invalid or not existing target path: {absolute_target_path}')
    splitted_log_paths = split_log_by_lines(log_path, temp_folder_path, combat_distance=combat_distance)
    with open(splitted_log_paths[-1], 'r', encoding='utf-8') as file:
        lines_list = file.readlines()
    return (lines_list, splitted_log_paths)

def split_log_by_lines(log_path:str, target_path:str, approx_lines_per_file:int = 480000, 
        combat_distance:int = 100) -> list:
    '''
    Splits the combat at log_path into multiple files saved in the directory at target_path and 
    returns the paths to the files.
    '''
    def save_partial_log(directory_path:str, filename:str, lines:list, filepath_list:list) -> str:
        start_time = format_timestamp(lines[0].split('::')[0])
        end_time = format_timestamp(lines[-1].split('::')[0])
        new_filename = sanitize_file_name(f'[{start_time}--{end_time}]{filename}')
        new_path = f'{directory_path}\\{new_filename}'
        try:
            save_log(new_path, lines)
        except FileExistsError:
            new_path += sanitize_file_name(f'{new_path}(2).log')
            try:
                save_log(new_path, lines)
            except FileExistsError:
                return
        filepath_list.append(new_path)

    absolute_target_path = os.path.abspath(target_path)
    if not (os.path.exists(log_path) and os.path.isfile(log_path)):
        raise FileNotFoundError(f'Invalid Log Path: {log_path}')
    if not (os.path.exists(absolute_target_path) and os.path.isdir(absolute_target_path)):
        raise FileNotFoundError(f'Invalid or not existing target path: {absolute_target_path}')
    combat_delta = timedelta(seconds=combat_distance)
    filepaths = list()
    current_lines = list()
    original_filename = os.path.basename(log_path)
    with open(log_path, 'r', encoding='utf-8') as log_file:
        # outer loop: executes once per generated file
        while True:
            current_lines, consumed = read_lines(log_file, approx_lines_per_file, current_lines)
            if consumed:
                save_partial_log(absolute_target_path, original_filename, current_lines, filepaths)
                return filepaths
            last_log_time = to_datetime(current_lines[-1].split('::')[0])
            # inner loop: finds the end of the combat
            while True:
                line = log_file.readline()
                if not line:
                    save_partial_log(absolute_target_path, original_filename, current_lines, filepaths)
                    return filepaths
                log_time = to_datetime(line.split('::')[0])
                if log_time - last_log_time > combat_delta:
                    save_partial_log(absolute_target_path, original_filename, current_lines, filepaths)
                    current_lines = [line]
                    break
                current_lines.append(line)            
        
def read_lines(file:TextIOWrapper, num:int, input_list=None) -> tuple[list, bool]:
    '''
    Read num lines from file and return them along with a boolean value indicating whether the end of the
    file was reached during the read process.
    '''
    if input_list is None:
        lines = list()
    else:
        lines = input_list
    end_of_file = False
    for _ in range(num):
        line = file.readline()
        if not line:
            end_of_file = True
            break
        lines.append(line)
    return (lines, end_of_file)

def save_log(path:str, lines:list):
    '''
    Saves lines to new file if file doesn't exist yet. Lines may be of type str or LogLine.
    '''
    if os.path.exists(path):
        raise FileExistsError(f'File "{path}" already exists.')
    with open(path, 'w', encoding='utf-8') as file:
        for line in map(logline_to_str, lines):
            file.write(line)

def reset_temp_folder(path:str):
    '''
    Deletes and re-creates folder housing temporary log files.
    '''
    if os.path.exists(path):
        if os.path.isdir(path):
            os.rmdir(path)
        else:
            raise FileExistsError(f'Expected path to folder, got "{path}"')
    os.mkdir(path)
        


def sanitize_file_name(txt, chr_set='extended') -> str:
    """Converts txt to a valid filename.

    Parameters:
    - :param txt: The path to convert.
    - :param chr_set: 
        - 'printable':    Any printable character except those disallowed on Windows/*nix.
        - 'extended':     'printable' + extended ASCII character codes 128-255
        - 'universal':    For almost *any* file system.
    """
    FILLER = '-'
    MAX_LEN = 255  # Maximum length of filename is 255 bytes in Windows and some *nix flavors.

    # Step 1: Remove excluded characters.
    BLACK_LIST = set(chr(127) + r'<>:"/\|?*')
    white_lists = {
        'universal': {'-.0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz'},
        'printable': {chr(x) for x in range(32, 127)} - BLACK_LIST,     # 0-32, 127 are unprintable,
        'extended' : {chr(x) for x in range(32, 256)} - BLACK_LIST,
    }
    white_list = white_lists[chr_set]
    result = ''.join(x if x in white_list else FILLER for x in txt)

    # Step 2: Device names, '.', and '..' are invalid filenames in Windows.
    DEVICE_NAMES = ('CON', 'PRN', 'AUX', 'NUL', 'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7',
            'COM8', 'COM9', 'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9', 'CONIN$',
            'CONOUT$', '..', '.')
    if '.' in txt:
        name, _, ext = result.rpartition('.')
        ext = f'.{ext}'
    else:
        name = result
        ext = ''
    if name in DEVICE_NAMES:
        result = f'-{result}-{ext}'

    # Step 3: Truncate long files while preserving the file extension.
    if len(result) > MAX_LEN:
        result = result[:MAX_LEN - len(ext)] + ext

    # Step 4: Windows does not allow filenames to end with '.' or ' ' or begin with ' '.
    result = re_sub(r"[. ]$", FILLER, result)
    result = re_sub(r"^ ", FILLER, result)

    return result
