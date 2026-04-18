from gzip import open as gzip_open
import os
import shutil
from time import time
from typing import Iterable

from .constants import PATCHES


def format_timestamp(timestamp: str) -> str:
    '''
    Formats timestamp. '24:01:13:04:37:45.7' becomes '24-01-13_04:37:45'
    '''
    return timestamp.replace(':', '-', 2).replace(':', '_', 1).split('.')[0]


def extract_bytes(source_path: str, target_path: str, start_pos: int, end_pos: int) -> bool:
    """
    Extracts combat from file at `source_path` by copying bytes from `start_pos` (including) up to
    `end_pos` (not including) to a new file at `target_path`. Returns `True` if successful, returns
    `False` if unsuccessful.

    Parameters:
    - :param source_path: path to source file
    - :param source_path: path to target_file, will overwrite if it already exists
    - :param start_pos: first byte from source file to copy
    - :param end_pos: copies data until this byte, not including it
    """
    try:
        with open(source_path, 'rb') as source_file:
            if source_file.read(2) == b'\x1f\x8b':
                source_file.close()
                source_file = gzip_open(source_path, 'rb')
            source_file.seek(start_pos)
            extracted_bytes = source_file.read(end_pos - start_pos)
        with open(target_path, 'wb') as target_file:
            target_file.write(extracted_bytes)
        return True
    except OSError:
        return False


def compose_logfile(
        source_path: str, target_path: str, intervals: Iterable[tuple[int, int]],
        templog_folder_path: str) -> bool:
    """
    Grabs bytes in given `intervals` from `source_path` and writes them to `target_path`. Returns
    `True` if successful, returns `False` if unsuccessful.

    Parameters:
    - :param source_path: path to source file, must be absolute
    - :param target_path: path to target file, must be absolute, will overwrite if it already exists
    - :param intervals: iterable with start and end position pairs (half-open interval)
    - :param templog_folder_path: path to folder used for temporary logfiles
    """
    tempfile_path = f'{templog_folder_path}\\{int(time())}'
    try:
        with open(source_path, 'rb') as source_file, open(tempfile_path, 'wb') as temp_file:
            if source_file.read(2) == b'\x1f\x8b':
                source_file.close()
                source_file = gzip_open(source_path, 'rb')
            for start_pos, end_pos in intervals:
                source_file.seek(start_pos)
                temp_file.write(source_file.read(end_pos - start_pos))
        shutil.copyfile(tempfile_path, target_path)
        return True
    except OSError:
        return False


def fix_line(line: bytes) -> bytes:
    """
    Removes escaped commas.

    Parameters:
    - :param line: line to fix
    """
    if b'"' in line:
        parts = line.split(b'"')
        if len(parts) % 2 == 1:
            line = b''
            for i in range(1, len(parts), 2):
                line += parts[i - 1] + parts[i].replace(b', ', b' - ').replace(b',', b' ')
            line += parts[-1]
    return line


def repair_logfile(path: str, templog_folder_path: str) -> str:
    """
    Replace bugged combatlog lines. Returns empty string on success, class name of error on failure.

    Parameters:
    - :param path: logfile to repair
    """
    tempfile_path = os.path.join(templog_folder_path, str(int(time())))
    with open(path, 'rb') as log_file, open(tempfile_path, 'wb') as temp_file:
        multiline_buffer = b''
        for line in log_file:
            if line.strip() == b'':
                continue
            if multiline_buffer == b'':
                if b'::' not in line:
                    continue
            else:
                if b'::' in line:
                    multiline_buffer = b''
            for broken_string, fixed_string in PATCHES:
                if broken_string in line:
                    clean_line = line.replace(broken_string, fixed_string)
                    break
            else:
                clean_line = line
            line_parts = (multiline_buffer + clean_line).split(b',')
            if len(line_parts) < 12:
                multiline_buffer += clean_line.replace(b'\r', b'').replace(b'\n', b'')
            else:
                temp_file.write(fix_line(multiline_buffer + clean_line))
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
    if os.path.exists(path) and os.path.isdir(path):
        shutil.rmtree(path)
    os.mkdir(path)
