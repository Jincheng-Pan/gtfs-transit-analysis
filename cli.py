"""Command-line interface."""
from __future__ import annotations

import argparse

from .analysis import analyse_feed, export_route_od
from .compare import compare_od_times


def main() -> None:
    parser = argparse.ArgumentParser(description="GTFS transit service analysis toolkit")
    sub = parser.add_subparsers(dest="command", required=True)

    p_analyse = sub.add_parser("analyse", help="Analyse a GTFS feed")
    p_analyse.add_argument("--gtfs", required=True, help="Path to GTFS folder")
    p_analyse.add_argument("--output", default="results/route_service_analysis.csv", help="Output CSV path")

    p_od = sub.add_parser("route-od", help="Export representative route stop-pair travel times")
    p_od.add_argument("--gtfs", required=True, help="Path to GTFS folder")
    p_od.add_argument("--route", required=True, help="route_short_name, e.g. 125")
    p_od.add_argument("--direction", default=None, help="Optional direction_id, e.g. 0 or 1")
    p_od.add_argument("--output", required=True, help="Output CSV path")

    p_cmp = sub.add_parser("compare-od", help="Compare two OD travel-time CSVs")
    p_cmp.add_argument("--old", required=True, help="Old OD CSV")
    p_cmp.add_argument("--new", required=True, help="New OD CSV")
    p_cmp.add_argument("--output", required=True, help="Output comparison CSV")

    args = parser.parse_args()

    if args.command == "analyse":
        df = analyse_feed(args.gtfs, args.output)
        print(f"Saved {len(df)} rows to {args.output}")
    elif args.command == "route-od":
        df = export_route_od(args.gtfs, args.route, args.direction, args.output)
        print(f"Saved {len(df)} OD pairs to {args.output}")
    elif args.command == "compare-od":
        df = compare_od_times(args.old, args.new, args.output)
        print(f"Saved {len(df)} compared OD pairs to {args.output}")


if __name__ == "__main__":
    main()
