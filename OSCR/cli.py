""" OSCR CLI """

import argparse
import cProfile
import os
import pstats

from . import OSCR
from .datamodels import OverviewTableRow


OVERVIEW_HEADER = (
        'Player', 'DPS', 'Combat Time', 'Combat Time Share', 'Total Damage', 'Debuff',
        'Attacks-in Share', 'Taken Damage Share', 'Damage Share', 'Max One Hit', 'Deaths')


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
            print(f'{os.linesep}'.join(f'name={c.name} count={c.count} deaths={c.deaths}' for c in combat.critters.values()))
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


def main():
    """Main"""
    argparser = argparse.ArgumentParser()
    argparser.add_argument("-i", "--input", default='')
    argparser.add_argument("-c", "--count", type=int, default=1)
    argparser.add_argument("-l", "--list", action=argparse.BooleanOptionalAction)
    argparser.add_argument("-m", "--metadata", action=argparse.BooleanOptionalAction)
    argparser.add_argument("-a", "--analysis", action=argparse.BooleanOptionalAction)
    args = argparser.parse_args()
    if args.input == '':
        print(
                'OSCR CLI Options:\n--input / -i: logfile path (mandatory)\n--list / -l: list all '
                'combats in logfile\n--count / -c: number of combats to analyze (for use with -m '
                'and -a)\n--metadata / -m: shows metadata of combats\n--analysis / -a: show combat '
                'analysis overview')
        return

    parser = OSCR(args.input)

    if args.list:
        list_combats(parser)
    elif args.analysis or args.metadata:
        analyzation(args, parser)


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
