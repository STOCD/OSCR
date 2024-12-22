from datetime import datetime, timedelta
from typing import Generator, Iterable


def to_datetime(date_time: str) -> datetime:
    """
    returns datetime object from combatlog string containing date and time
    """
    date_time_list = date_time.split(':')
    date_time_list += date_time_list.pop().split('.')
    date_time_list = list(map(int, date_time_list))
    date_time_list[0] += 2000
    date_time_list[6] *= 100000
    return datetime(*date_time_list)


def to_microseconds(timedelta: timedelta):
    return ((timedelta.days * (24 * 3600) + timedelta.seconds) * 1000000
            + timedelta.microseconds)


def datetime_to_display(date_time: datetime) -> str:
    """
    Converts datetime object to formatted string.
    """
    return (f'{date_time.year}-{date_time.month:02d}-{date_time.day:02d} {date_time.hour:02d}:'
            f'{date_time.minute:02d}:{date_time.second:02d}')


def get_handle_from_id(id_str: str) -> str:
    """
    returns player handle from id string
    """
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


def bundle[_T](*iterables: Iterable[_T]) -> Generator[_T, None, None]:
    """
    Generator yielding the items of the given iterables in the order they were provided.

    Parameters:
    - :param iterables: iterables to be bundled
    """
    for inner_iterable in iterables:
        for element in inner_iterable:
            yield element
