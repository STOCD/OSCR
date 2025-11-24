""" OSCR CLI """

from argparse import ArgumentParser
import cProfile
from datetime import datetime
import os
from pathlib import Path
import pstats

from . import OSCR
from .combat import Combat


OVERVIEW_HEADER = [
    'Player', 'DPS', 'Combat Time', 'Combat Time Share', 'Total Damage', 'Debuff',
    'Attacks-in Share', 'Taken Damage Share', 'Damage Share', 'Deaths']

HELP = """OSCR CLI Usage:
• help, h
    Shows this help message.
• open <file>, o <file>
    Selects file to analyze.
• overview <combat>, ov <combat>
    Analyzes specified combat identified by combat ID and shows
    overview table. Not specifying a combat will analyze the most
    recent combat.
• combats <amount>, c <amount>
    Shows specified amount of combats in selected logfile. Shows
    all combats in selected log file if no argument is given.
• quit, q
    Exits the interactive mode and ends the program."""


def convert_datetime(dt: datetime) -> tuple[str, str]:
    """
    Extracts date and time from datetime object and returns them separately in formatted form.
    """
    return (f'{dt.year}-{dt.month:02d}-{dt.day:02d}',
            f'{dt.hour:02d}:{dt.minute:02d}:{dt.second:02d}')


def format_table(table: list[list[str]], header: list[str], column_alignment: list[str]) -> str:
    """
    Puts table consisting of nested lists into str format for output on the terminal. Truncates
    width of table if it is wider than the current terminal width.

    Parameters:
    - :param table: table to convert; outer list contains rows, each inner list contains the
    columns for that row; each row must be of the same length and match the length of `header`
    - :param header: labels for the column heading
    - :param column_alignment: `r` or `l` to align column content except header right or left,
    respectively; any other value will center-align the content; must match the length of `header`
    """
    column_widths = [len(e) for e in header]
    output = list()
    for row in table:
        for i, item in enumerate(row):
            column_widths[i] = max(column_widths[i], len(str(item)))  # TODO unify type beforehand
    border = '┌'
    for width in column_widths:
        border += '─' * width + '┬'
    border = border[:-1] + '┐'
    output.append(border)
    formatted_row = ''
    for item, width in zip(header, column_widths):
        formatted_row += f'│{item:^{width}}'
    output.append(formatted_row + '│')
    border = '├'
    for width in column_widths:
        border += '─' * width + '┼'
    border = border[:-1] + '┤'
    output.append(border)
    for row in table:
        formatted_row = ''
        for column, item in enumerate(row):
            match column_alignment[column]:
                case 'l':
                    formatted_row += f'│{item:<{column_widths[column]}}'
                case 'r':
                    formatted_row += f'│{item:>{column_widths[column]}}'
                case _:
                    formatted_row += f'│{item:^{column_widths[column]}}'
        output.append(formatted_row + '│')
    border = '└'
    for width in column_widths:
        border += '─' * width + '┴'
    border = border[:-1] + '┘'
    output.append(border)
    width = max(69, os.get_terminal_size().columns - 1)
    if width < len(output[0]):
        return '\n'.join(map(lambda row: row[:width], output))
    else:
        return '\n'.join(output)


def open_logfile(
        parser: OSCR, isolated_combats: list[list], logfile_path: str,
        max_combats: int = 5) -> bool:
    """
    """
    path = Path(logfile_path)
    if not path.exists() or not path.is_file():
        print('The specified logfile does not exist. Please choose a different file.')
        return False
    parser.reset_parser()
    parser.log_path = logfile_path
    raw_combats = parser.isolate_combats(logfile_path, max_combats)
    if len(raw_combats) < 1:
        print('The specified logfile does not contain any combats.')
        return False
    isolated_combats.clear()
    for combat in map(list, raw_combats):
        combat[0] += 1
        isolated_combats.append(combat[:5])
    return True


def get_overview_data(combat: Combat, sort_column: int = 1) -> list[list]:
    """
    """
    player_data = [p for p in combat.players.values()]
    if sort_column != 0:
        sort_column += 1
    player_data.sort(key=lambda row: row[sort_column], reverse=True)
    data = list()
    for player in player_data:
        data.append([
            player.name + player.handle,
            f'{player.DPS:,.2f}',
            f'{player.combat_time:.1f}s',
            f'{player.combat_time_share * 100:.2f}%',
            f'{player.total_damage:,.2f}',
            f'{player.debuff * 100:.2f}%',
            f'{player.attacks_in_share * 100:.2f}%',
            f'{player.taken_damage_share * 100:.2f}%',
            f'{player.damage_share * 100:.2f}%',
            f'{player.deaths}'
        ])
    return data


def interpret_combat_argument(args: list[str], available_count: int) -> int:
    """
    """
    count = 0
    if len(args) > 0:
        try:
            count = int(args[0])
        except ValueError:
            print(
                'Invalid input. If supplied, the argument must be an integer. '
                'Using default value...')
    if count > 0:
        return count
    elif available_count > 0:
        return available_count
    else:
        return count


def get_combats(parser: OSCR, isolated_combats: list[list], max_combats: int = 5) -> bool:
    """
    """
    if parser.log_path == '':
        print('No logfile specified. Please open a logfile first.')
        return False
    else:
        raw_combats = parser.isolate_combats(parser.log_path, max_combats)
        if len(raw_combats) < 1:
            print('The specified logfile does not contain any combats.')
            return False
        for combat in map(list, raw_combats[len(isolated_combats):]):
            combat[0] += 1
            isolated_combats.append(combat[:5])
    return True


def produce_overview_data(parser: OSCR, isolated_combats: list[list], combat_id: int) -> list[list]:
    """
    """
    if combat_id >= len(parser.combats):
        parser.analyze_log_file(max_combats=combat_id - len(parser.combats) + 1)
        for id, combat in enumerate(parser.combats):
            combat_summary = [
                combat.id + 1,
                combat.map,
                *convert_datetime(combat.start_time),
                combat.difficulty if combat.difficulty is not None else ''
            ]
            if id < len(isolated_combats):
                isolated_combats[id] = combat_summary
            else:
                isolated_combats.append(combat_summary)
        if combat_id >= len(parser.combats):
            print(
                'The specified combat does not exist in the given logfile. '
                'Use "combats" / "--combats" to show available combats.')
            return []
    combat = parser.combats[combat_id]
    return get_overview_data(combat)


def print_combat_announcer(combat: Combat):
    """
    """
    formatted_date, formatted_time = convert_datetime(combat.start_time)
    if combat.difficulty is None:
        difficulty = ''
    else:
        difficulty = f' ({combat.difficulty})'
    print(f'[{combat.id + 1}] -> {combat.map}{difficulty} '
          f'{formatted_date} {formatted_time}')


def interactive_cli(log_path: str | None = None):
    """
    Executes interactive cli for OSCR.
    """
    parser = OSCR()
    # TODO this needs to be integrated into OSCR, but that requires a rewrite
    isolated_combats = list()
    print(
        '      >>  Open Source Combatlog Reader  <<\n\nWelcome to the interactive CLI of OSCR '
        f'{OSCR.__version__}!\nType "help" for more information, "quit" to quit.')
    if log_path is not None and open_logfile(parser, isolated_combats, log_path):
        print(format_table(
            isolated_combats, ['ID', 'Map', 'Date', 'Time', 'Difficulty'],
            ['r', 'l', 'l', 'l', 'l']))
    while True:
        try:
            message = input('(OSCR) ')
        except EOFError:
            break
        action, *arguments = message.split(' ')
        if ''.join(arguments) == '':
            arguments = []
        match action:
            case 'q' | 'quit':
                break
            case 'h' | 'help':
                print(HELP)
            case 'open' | 'o':
                if open_logfile(parser, isolated_combats, ''.join(arguments)):
                    print(format_table(
                        isolated_combats, ['ID', 'Map', 'Date', 'Time', 'Difficulty'],
                        ['r', 'l', 'l', 'l', 'l']))
            case 'combats' | 'c':
                combats_to_show = interpret_combat_argument(arguments, len(isolated_combats))
                if len(isolated_combats) >= combats_to_show:
                    print(format_table(
                        isolated_combats[:combats_to_show],
                        ['ID', 'Map', 'Date', 'Time', 'Difficulty'], ['r', 'l', 'l', 'l', 'l']))
                else:
                    if get_combats(parser, isolated_combats, combats_to_show):
                        print(format_table(
                            isolated_combats, ['ID', 'Map', 'Date', 'Time', 'Difficulty'],
                            ['r', 'l', 'l', 'l', 'l']))
            case 'overview' | 'ov':
                combat_to_show = interpret_combat_argument(arguments, 1) - 1
                data = produce_overview_data(parser, isolated_combats, combat_to_show)
                print_combat_announcer(parser.combats[combat_to_show])
                print(format_table(
                    data, OVERVIEW_HEADER,
                    ['l', 'r', 'r', 'r', 'r', 'r', 'r', 'r', 'r', 'r']))
            case _:
                print('Invalid command. Enter "help" to see available commands.')
                continue


def main():
    """Main"""
    argparser = ArgumentParser(prog='OSCR', description='CLI for the Open Source Combatlog Reader')
    argparser.add_argument(
        '--open', '-o', type=str, required=False, metavar='PATH', help='Selects file to analyze.')
    argparser.add_argument(
        '--combats', '-c', type=int, required=False, metavar='ID', nargs='?', const=5,
        help='Lists given amount of combats from the selected logfile.')
    argparser.add_argument(
        '--overview', '-ov', type=int, required=False, metavar='ID', nargs='?', const=1,
        help='Shows overview table for given combat.')
    args, _ = argparser.parse_known_args()
    if args.open is None:
        if args.combats is None and args.overview is None:
            interactive_cli()
        else:
            print('Could not perform action: --open [PATH] must be specified')
    elif args.combats is None and args.overview is None:
        interactive_cli(args.open)
    else:
        parser = OSCR()
        isolated_combats = list()
        combats_to_show = 5
        if args.combats is not None and args.combats > 0:
            combats_to_show = args.combats
        if not open_logfile(parser, isolated_combats, args.open, combats_to_show):
            return
        if args.overview is None:
            print(format_table(
                isolated_combats, ['ID', 'Map', 'Date', 'Time', 'Difficulty'],
                ['r', 'l', 'l', 'l', 'l']))
        else:
            combat_to_show: int = args.overview - 1
            if combat_to_show < 0:
                print('The combat ID must be at least 1.')
                return
            data = produce_overview_data(parser, isolated_combats, combat_to_show)
            if args.combats is not None:
                print(format_table(
                    isolated_combats[:combats_to_show],
                    ['ID', 'Map', 'Date', 'Time', 'Difficulty'], ['r', 'l', 'l', 'l', 'l']))
            print_combat_announcer(parser.combats[combat_to_show])
            print(format_table(
                data, OVERVIEW_HEADER,
                ['l', 'r', 'r', 'r', 'r', 'r', 'r', 'r', 'r', 'r']))


if __name__ == "__main__":
    if os.environ.get("CPROFILE"):
        pr = cProfile.Profile()
        pr.enable()

    main()

    if os.environ.get("CPROFILE"):
        pr.disable()
        ps = pstats.Stats(pr).sort_stats("cumtime")
        print("================================")
        ps.print_stats()
