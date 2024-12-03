from datetime import datetime, timedelta
from re import search as re_search
from typing import Generator, Iterable

PLAYER_HANDLE_REGEX = '^P\\[.+?@.+?(?P<handle>@.+?)\\]$'
COMPUTER_HANDLE_REGEX = '^C\\[(?P<handle>\\d+).+?\\]$'


def to_datetime(date_time: str) -> datetime:
    '''
    returns datetime object from combatlog string containing date and time
    '''
    date_time_list = date_time.split(':')
    date_time_list += date_time_list.pop().split('.')
    date_time_list = list(map(int, date_time_list))
    date_time_list[0] += 2000
    date_time_list[6] *= 100000
    return datetime(*date_time_list)


def to_microseconds(timedelta: timedelta):
    return ((timedelta.days * (24 * 3600) + timedelta.seconds) * 1000000
            + timedelta.microseconds)


def datetime_to_str(date_time: datetime) -> str:
    '''
    Converts datetime object to str timestamp. Truncates microseconds to tenth of seconds.
    '''
    return (f'{str(date_time.year)[-2:]}:{date_time.month:02d}:{date_time.day:02d}:'
            f'{date_time.hour:02d}:{date_time.minute:02d}:{date_time.second:02d}.'
            f'{str(date_time.microsecond)[0]}')


def datetime_to_display(date_time: datetime) -> str:
    '''
    Converts datetime object to formatted string.
    '''
    return (f'{date_time.year}-{date_time.month:02d}-{date_time.day:02d} {date_time.hour:02d}:'
            f'{date_time.minute:02d}:{date_time.second:02d}')


def logline_to_str(line) -> str:
    '''
    Converts LogLine to str or returns str if argument is str.
    '''
    if isinstance(line, str):
        return line.strip() + '\n'

    timestamp = datetime_to_str(line.timestamp)
    return f'{timestamp}::{",".join(line[1:11])},{line[11]},{line[12]}\n'


def get_handle_from_id(id_str: str) -> str:
    '''
    returns player handle from id string
    '''
    if id_str.startswith('P'):
        _, _, handle_part = id_str.rpartition('@')
        return '@' + handle_part[:-1]
    elif id_str.startswith('C'):
        handle_part, _ = id_str.split(' ', maxsplit=1)
        # the space enables consistent concatenation behaviour between players and NPCs
        return f' {handle_part[2:]}'
    else:
        return ''


def get_player_handle(id_str: str) -> str:
    """
    returns player handle from id string
    """
    _, _, handle_part = id_str.rpartition('@')
    return '@' + handle_part[:-1]


def get_entity_name(entity_id: str) -> str:
    """
    Returns the entity name matching an entity id.
    """
    split = entity_id.split(" ")
    if len(split) != 2:
        return None
    return split[1].replace("]", "")


def get_flags(flag_str: str) -> tuple[bool]:
    """
    Returns flags from flag field of log line.

    :return: (critical_hit, miss, kill)
    """
    critical_hit = "Critical" in flag_str
    miss = "Miss" in flag_str
    kill = "Kill" in flag_str
    return (critical_hit, miss, kill)


def reversed_index(length: int) -> Generator[int, None, None]:
    '''
    Generator that yields the indices for an iterable with given length in reversed order.

    Parameters:
    - :param length: length of the iterable
    '''
    counter = length
    while counter > 0:
        counter -= 1
        yield counter


def bundle[_T](*iterables: Iterable[_T]) -> Generator[_T, None, None]:
    """
    Generator yielding the items of the given iterables in the order they were provided.

    Parameters:
    - :param iterables: iterables to be bundled
    """
    for inner_iterable in iterables:
        for element in inner_iterable:
            yield element
