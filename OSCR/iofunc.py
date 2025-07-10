from gzip import open as gzip_open
import os
import shutil
from time import time
from typing import Iterable

from .constants import MULTILINE_PATCHES, PATCHES


def format_timestamp(timestamp: str) -> str:
    '''
    Formats timestamp. '24:01:13:04:37:45.7' becomes '24-01-13_04:37:45'
    '''
    return timestamp.replace(':', '-', 2).replace(':', '_', 1).split('.')[0]


def extract_bytes(source_path: str, target_path: str, start_pos: int, end_pos: int):
    """
    Extracts combat from file at `source_path` by copying bytes from `start_pos` (including) up to
    `end_pos` (not including) to a new file at `target_path`

    Parameters:
    - :param source_path: path to source file, must be absolute
    - :param source_path: path to target_file, must be absolute, will overwrite if it already exists
    - :param start_pos: first byte from source file to copy
    - :param end_pos: copies data until this byte, not including it
    """
    if not os.path.isabs(source_path):
        raise AttributeError(f'source_path is not absolute: {source_path}')
    if not os.path.isabs(target_path):
        raise AttributeError(f'target_path is not absolute: {target_path}')
    with open(source_path, 'rb') as source_file:
        if source_file.read(2) == b'\x1f\x8b':
            source_file.close()
            source_file = gzip_open(source_path, 'rb')
        source_file.seek(start_pos)
        extracted_bytes = source_file.read(end_pos - start_pos)
    with open(target_path, 'wb') as target_file:
        target_file.write(extracted_bytes)


def compose_logfile(
            source_path: str, target_path: str, intervals: Iterable[tuple[int, int]],
            templog_folder_path: str):
    """
    Grabs bytes in given `intervals` from `source_path` and writes them to `target_path`.

    Parameters:
    - :param source_path: path to source file, must be absolute
    - :param target_path: path to target file, must be absolute, will overwrite if it already exists
    - :param intervals: iterable with start and end position pairs (half-open interval)
    - :param templog_folder_path: path to folder used for temporary logfiles
    """
    tempfile_path = f'{templog_folder_path}\\{int(time())}'
    with open(source_path, 'rb') as source_file, open(tempfile_path, 'wb') as temp_file:
        if source_file.read(2) == b'\x1f\x8b':
            source_file.close()
            source_file = gzip_open(source_path, 'rb')
        for start_pos, end_pos in intervals:
            source_file.seek(start_pos)
            temp_file.write(source_file.read(end_pos - start_pos))
    shutil.copyfile(tempfile_path, target_path)


def repair_logfile(path: str, templog_folder_path: str) -> str:
    """
    Replace bugged combatlog lines

    Parameters:
    - :param path: logfile to repair
    """
    tempfile_path = f'{templog_folder_path}\\{int(time())}'
    with open(path, 'rb') as log_file, open(tempfile_path, 'wb') as temp_file:
        multiline_progress = 0
        multiline_buffer = b''
        multiline_data = None
        for line in log_file:
            if multiline_progress > 1:
                multiline_progress -= 1
                multiline_buffer += line.strip()
                continue
            elif multiline_progress == 1:
                multiline_progress = 0
                multiline_buffer += line
                temp_file.write(multiline_buffer.replace(multiline_data[0], multiline_data[1]))
                continue
            if line.strip() == b'':
                continue
            for broken_string, fixed_string in PATCHES:
                if broken_string in line:
                    temp_file.write(line.replace(broken_string, fixed_string))
                    break
            else:
                for indentifier, *patch_data in MULTILINE_PATCHES:
                    if indentifier in line:
                        multiline_progress = patch_data[2] - 1
                        multiline_buffer = line.strip()
                        multiline_data = patch_data
                        break
                else:
                    temp_file.write(line)
    try:
        shutil.copyfile(tempfile_path, path)
        res = ''
    except PermissionError:
        res = 'PermissionError'
    return res


def reset_temp_folder(path: str):
    '''
    Deletes and re-creates folder housing temporary log files.
    '''
    if os.path.exists(path):
        if os.path.isdir(path):
            shutil.rmtree(path)
        else:
            raise FileExistsError(f'Expected path to folder, got "{path}"')
    os.mkdir(path)
