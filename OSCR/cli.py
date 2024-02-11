""" OSCR CLI """

import argparse

from . import OSCR


def main():
    """Main"""
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--input")
    args = parser.parse_args()

    parser = OSCR(args.input)
    parser.analyze_log_file()

    for idx, _ in enumerate(parser.analyzed_combats):
        parser.shallow_combat_analysis(idx)
        print(f"{parser.active_combat.map}")
        for key, value in parser.active_combat.players.items():
            print(f"  {key}: {value.DPS}")


if __name__ == "__main__":
    main()
