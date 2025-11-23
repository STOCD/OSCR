""" OSCR CLI """

from argparse import ArgumentParser, BooleanOptionalAction, Namespace
import cProfile
from datetime import datetime
import os
from pathlib import Path
import pstats

from . import OSCR
from .combat import Combat
from .datamodels import OverviewTableRow


OVERVIEW_HEADER = (
        'Player', 'DPS', 'Combat Time', 'Combat Time Share', 'Total Damage', 'Debuff',
        'Attacks-in Share', 'Taken Damage Share', 'Damage Share', 'Max One Hit', 'Deaths')

OVERVIEW_HEADER_2 = [
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


def format_overview_row(row: OverviewTableRow):
    """
    Returns a list of formatted column values from OverviewTableRow
    """
    return (
        row.name + row.handle,
        f'{row.DPS:,.2f}',
        f'{row.combat_time:.1f}s',
        f'{row.combat_time_share * 100:.2f}%',
        f'{row.total_damage:,.2f}',
        f'{row.debuff * 100:.2f}%',
        f'{row.attacks_in_share * 100:.2f}%',
        f'{row.taken_damage_share * 100:.2f}%',
        f'{row.damage_share * 100:.2f}%',
        f'{row.max_one_hit:,.2f}',
        f'{row.deaths}',
    )


def list_combats(parser: OSCR):
    """List the parsed combats but do not do any analysis"""
    combats = parser.isolate_combats(parser.log_path)
    for combat in combats:
        print(f"<{combat[1]} {combat[4] + ' ' if combat[4] else ''}at {combat[2]} {combat[3]}>")
    print("++++++++++++++++++++++++++++++++")


def analyzation(args, parser: OSCR):
    """Print the combat summary for each combat"""
    parser.analyze_log_file(max_combats=args.count)
    for combat in parser.combats:
        print("++++++++++++++++++++++++++++++++")
        print(f"###   {combat.description}   ###")
        if args.metadata:
            print(f"Start Time: {combat.start_time} | End Time: {combat.end_time}")
            print(
                    f"Log Duration: {combat.meta['log_duration']}s | "
                    f"Active Player Time: {combat.meta['player_duration']}s")
            print(f'{os.linesep}'.join(f'name={c.name} count={c.count} deaths={c.deaths}'
                                       for c in combat.critters.values()))
        if args.analysis:
            player_data = [OVERVIEW_HEADER]
            paddings = list(map(len, OVERVIEW_HEADER))
            for player in combat.players.values():
                formatted_row = format_overview_row(player)
                player_data.append(formatted_row)
                paddings = [max(e1, e2) for e1, e2 in zip(paddings, map(len, formatted_row))]
            print("###         Analysis         ###")
            for row in player_data:
                print(' | '.join(f'{el:>{pad}}' for el, pad in zip(row, paddings)))


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


def open_logfile(parser: OSCR, filepath: str) -> list[tuple]:
    """
    Opens specified logfile in OSCR and returns the most recent isolated combats (max 5).
    """
    parser.reset_parser()
    path = Path(filepath)
    parser.log_path = str(path)
    return parser.isolate_combats(path, 5)


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
    if log_path is not None:
        path = Path(log_path)
        if not path.exists() or not path.is_file():
            print('The specified logfile does not exist. Please choose a different file.')
        else:
            raw_combats = open_logfile(parser, path)
            if len(raw_combats) < 1:
                print('The specified logfile does not contain any combats.')
            else:
                isolated_combats = list()
                for combat in map(list, raw_combats):
                    combat[0] += 1
                    isolated_combats.append(combat[:5])
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
                path = Path(''.join(arguments))
                if not path.exists() or not path.is_file():
                    print('The specified logfile does not exist. Please choose a different file.')
                    continue
                raw_combats = open_logfile(parser, path)
                if len(raw_combats) < 1:
                    print('The specified logfile does not contain any combats.')
                    continue
                isolated_combats = list()
                for combat in map(list, raw_combats):
                    combat[0] += 1
                    isolated_combats.append(combat[:5])
                print(format_table(
                    isolated_combats, ['ID', 'Map', 'Date', 'Time', 'Difficulty'],
                    ['r', 'l', 'l', 'l', 'l']))
            case 'combats' | 'c':
                combats_to_show = 1
                default_combat_num = False
                if len(arguments) > 0:
                    try:
                        combats_to_show = int(arguments[0])
                    except ValueError:
                        print('Invalid input. If supplied, the argument must be an integer.')
                        continue
                else:
                    default_combat_num = True
                    if len(isolated_combats) > 0:
                        print(format_table(
                            isolated_combats, ['ID', 'Map', 'Date', 'Time', 'Difficulty'],
                            ['r', 'l', 'l', 'l', 'l']))
                        continue
                if len(isolated_combats) >= combats_to_show:
                    print(format_table(
                        isolated_combats[:combats_to_show],
                        ['ID', 'Map', 'Date', 'Time', 'Difficulty'], ['r', 'l', 'l', 'l', 'l']))
                else:
                    if parser.log_path == '':
                        print('No logfile specified. Please open a logfile first.')
                        continue
                    else:
                        if default_combat_num:
                            combats_to_show = 5
                        raw_combats = parser.isolate_combats(parser.log_path, combats_to_show)
                        if len(raw_combats) < 1:
                            print('The specified logfile does not contain any combats.')
                            continue
                        for combat in map(list, raw_combats[len(isolated_combats):]):
                            combat[0] += 1
                            isolated_combats.append(combat[:5])
                        print(format_table(
                            isolated_combats, ['ID', 'Map', 'Date', 'Time', 'Difficulty'],
                            ['r', 'l', 'l', 'l', 'l']))
            case 'overview' | 'ov':
                combat_to_show = 1
                if len(arguments) > 0:
                    try:
                        combat_to_show = int(arguments[0])
                    except ValueError:
                        print('Invalid input. If supplied, the argument must be an integer.')
                        continue
                combat_to_show -= 1
                if combat_to_show < 0:
                    print('The combat ID must be at least 1.')
                    continue
                if len(parser.combats) > combat_to_show:
                    combat = parser.combats[combat_to_show]
                    data = get_overview_data(combat)
                    formatted_date, formatted_time = convert_datetime(combat.start_time)
                    if combat.difficulty is None:
                        difficulty = ''
                    else:
                        difficulty = f' ({combat.difficulty})'
                    print(f'[{combat_to_show + 1}] -> {combat.map}{difficulty} '
                          f'{formatted_date} {formatted_time}')
                    print(format_table(
                        data, OVERVIEW_HEADER_2,
                        ['l', 'r', 'r', 'r', 'r', 'r', 'r', 'r', 'r', 'r']))
                else:
                    parser.analyze_log_file(max_combats=combat_to_show - len(parser.combats) + 1)
                    isolated_combats = list()
                    for combat in parser.combats:
                        isolated_combats.append([
                            combat.id + 1,
                            combat.map,
                            *convert_datetime(combat.start_time),
                            combat.difficulty if combat.difficulty is not None else ''
                        ])
                    if combat_to_show >= len(parser.combats):
                        print(
                            'The specified combat does not exist in the given logfile. '
                            'Use "combats" to show available combats.')
                        continue
                    combat = parser.combats[combat_to_show]
                    data = get_overview_data(combat)
                    formatted_date, formatted_time = convert_datetime(combat.start_time)
                    if combat.difficulty is None:
                        difficulty = ''
                    else:
                        difficulty = f' ({combat.difficulty})'
                    print(f'[{combat_to_show + 1}] -> {combat.map}{difficulty} '
                          f'{formatted_date} {formatted_time}')
                    print(format_table(
                        data, OVERVIEW_HEADER_2,
                        ['l', 'r', 'r', 'r', 'r', 'r', 'r', 'r', 'r', 'r']))
            case _:
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
        '--overview', '--ov', type=int, required=False, metavar='ID', nargs='?', const=1,
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
        path = Path(args.open)
        if not path.exists() or not path.is_file():
            print('The specified logfile does not exist. Please choose a different file.')
            return
        parser = OSCR()
        isolated_combats = list()
        if args.combats is not None:
            raw_combats = parser.isolate_combats(str(path), args.combats)
            if len(raw_combats) < 1:
                print('The specified logfile does not contain any combats.')
                return
            for combat in map(list, raw_combats):
                combat[0] += 1
                isolated_combats.append(combat[:5])
            if args.overview is None:
                print(format_table(
                    isolated_combats, ['ID', 'Map', 'Date', 'Time', 'Difficulty'],
                    ['r', 'l', 'l', 'l', 'l']))
        if args.overview is not None:
            combat_to_show: int = args.overview - 1
            if combat_to_show < 0:
                print('The combat ID must be at least 1.')
                return
            parser.analyze_log_file(str(path), max_combats=combat_to_show + 1)
            if combat_to_show >= len(parser.combats):
                print(
                    'The specified combat does not exist in the given logfile. '
                    'Use "--combats" to show available combats.')
                return
            if args.combats:
                combats = list()
                for combat in parser.combats:
                    combats.append([
                        combat.id + 1,
                        combat.map,
                        *convert_datetime(combat.start_time),
                        combat.difficulty if combat.difficulty is not None else ''
                    ])
                combats += isolated_combats[combat_to_show:]
                print(format_table(
                    combats[:args.combats],
                    ['ID', 'Map', 'Date', 'Time', 'Difficulty'], ['r', 'l', 'l', 'l', 'l']))
            combat = parser.combats[combat_to_show]
            data = get_overview_data(combat)
            formatted_date, formatted_time = convert_datetime(combat.start_time)
            if combat.difficulty is None:
                difficulty = ''
            else:
                difficulty = f' ({combat.difficulty})'
            print(f'[{combat_to_show + 1}] -> {combat.map}{difficulty} '
                  f'{formatted_date} {formatted_time}')
            print(format_table(
                data, OVERVIEW_HEADER_2,
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
