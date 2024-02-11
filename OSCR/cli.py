""" OSCR CLI """

import argparse

from . import OSCR


def summary(parser):
    """Print the combat summary for each combat"""
    for idx, _ in enumerate(parser.analyzed_combats):
        parser.shallow_combat_analysis(idx)
        print(f"{parser.active_combat.map}")
        for k, v in parser.active_combat.players.items():
            print(f"  {v.name}{v.handle}: {v.total_damage:,.0f} ({v.DPS:,.0f} DPS)")


def main():
    """Main"""
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--input")
    parser.add_argument("-s", "--summary", action=argparse.BooleanOptionalAction)
    args = parser.parse_args()

    parser = OSCR(args.input)
    parser.analyze_log_file()

    if args.summary:
        summary(parser)


if __name__ == "__main__":
    main()
