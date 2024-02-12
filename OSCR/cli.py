""" OSCR CLI """

import argparse

import OSCR

def summary(parser):
    """Print the combat summary for each combat"""
    for idx, _ in enumerate(parser.analyzed_combats):
        parser.shallow_combat_analysis(idx)
        print(f"{parser.active_combat.map} - {parser.active_combat.difficulty}")

        print(f"  Players (Damage)")
        for k, v in parser.active_combat.player_dict.items():
            print(f"    {v.name}{v.handle}: {v.total_damage:,.0f} ({v.DPS:,.0f} DPS)")

        print(f"  NPCs (Damage Taken)")
        for k, v in parser.active_combat.computer_dict.items():
            print(f"    {v.name} - {v.handle}: tot={v.total_damage_taken:,.0f} hull={v.total_hull_damage_taken:,.0f} shield={v.total_shield_damage_taken:,.0f}")

def main():
    """Main"""
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--input")
    parser.add_argument("-s", "--summary", action=argparse.BooleanOptionalAction)
    args = parser.parse_args()

    parser = OSCR.OSCR(args.input)
    parser.analyze_log_file()

    if args.summary:
        summary(parser)


if __name__ == "__main__":
    main()
