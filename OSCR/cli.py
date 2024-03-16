""" OSCR CLI """

import argparse
import cProfile
import os
import pstats

import numpy

import OSCR


def list_combats(parser):
    """List the parsed combats but do not do any analysis"""
    for combat in parser.combats:
        print(
            f"start={combat.start_time} end={combat.end_time} duration={combat.duration} "
            "map={combat.map} difficulty={combat.difficulty}"
        )


def shallow(args, parser):
    """Print the combat summary for each combat"""
    for idx, _ in enumerate(parser.analyzed_combats):
        parser.shallow_combat_analysis(idx)
        combat = parser.active_combat
        print(
            f"start={combat.start_time} end={combat.end_time} duration={combat.duration} map={combat.map} difficulty={combat.difficulty}"
        )

        print("  Players (Damage)")
        for k, v in parser.active_combat.player_dict.items():
            print(f"    {v.name}{v.handle}: damage={v.total_damage:,.0f} dps={v.DPS:,.0f} build={v.build}")

        if args.metadata:
            print("  Computers:")
            for k, v in parser.active_combat.critter_meta.items():
                if v["deaths"] == 0:
                    continue
                perc = numpy.percentile(v["total_hull_damage_taken"], 50)
                print(f"    {k}: count={v['count']} deaths={v['deaths']} hull={perc:.0f}")

        if args.events:
            print(" Events (Players)")
            for k, v in parser.active_combat.player_dict.items():
                print(f"    {v.name}{v.handle}:")
                for event in v.events:
                    print(f"      {event}")


def main():
    """Main"""
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--input")
    parser.add_argument("-l", "--list", action=argparse.BooleanOptionalAction)
    parser.add_argument("-s", "--shallow", action=argparse.BooleanOptionalAction)
    parser.add_argument("-m", "--metadata", action=argparse.BooleanOptionalAction)
    parser.add_argument("-e", "--events", action=argparse.BooleanOptionalAction)
    args = parser.parse_args()

    parser = OSCR.OSCR(args.input)
    parser.analyze_log_file()

    if args.list:
        list_combats(parser)
    if args.shallow or args.metadata:
        shallow(args, parser)


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
