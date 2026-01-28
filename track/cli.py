import argparse
import sys

from .core import (
    QUADRANTS,
    add_activity,
    init_db,
    list_activities,
    remove_activity,
    search_activities,
)


def print_quadrant_help() -> None:
    print("  1 = Urgent & Important (Do)")
    print("  2 = Not Urgent & Important (Schedule)")
    print("  3 = Urgent & Not Important (Delegate)")
    print("  4 = Not Urgent & Not Important (Eliminate)")


def main() -> None:
    parser = argparse.ArgumentParser(description="Track activities with Eisenhower matrix")
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    add_parser = subparsers.add_parser("add", help="Add a new activity")
    add_parser.add_argument("--when", "-w", help="When the activity happened (default: now)")
    add_parser.add_argument("--duration", "-d", type=float, required=True, help="Duration in minutes")
    add_parser.add_argument("--quadrant", "-q", type=int, required=True, help="Eisenhower quadrant (1-4)")
    add_parser.add_argument("--desc", "-D", required=True, help="Description of the activity")
    add_parser.add_argument("--tags", "-t", help="Comma-separated tags (e.g., 'work,coding,focus')")
    add_parser.add_argument("--why", "-y", help="Optional reason or intent for the activity")

    list_parser = subparsers.add_parser("list", help="List recent activities")
    list_parser.add_argument("--limit", "-l", type=int, default=10, help="Number of activities to show (default: 10)")
    list_parser.add_argument(
        "--sort-by",
        choices=["id", "added", "event"],
        default="id",
        help="Sort by id (ASC), added (entry timestamp DESC), or event (activity timestamp DESC)",
    )

    search_parser = subparsers.add_parser("search", help="Search activities")
    search_parser.add_argument("--tags", "-t", help="Comma-separated tags to match (OR logic)")
    search_parser.add_argument("--desc", "-D", help="Description keywords to match (OR logic)")
    search_parser.add_argument("--quadrant", "-q", type=int, help="Filter by Eisenhower quadrant (1-4)")

    remove_parser = subparsers.add_parser("remove", help="Remove an activity by ID")
    remove_parser.add_argument("--id", type=int, required=True, help="Activity ID to delete")

    args = parser.parse_args()

    init_db()

    try:
        if args.command == "add":
            add_activity(
                args.when, args.duration, args.quadrant, args.desc, args.tags, args.why
            )
        elif args.command == "list":
            list_activities(args.limit, args.sort_by)
        elif args.command == "search":
            search_activities(args.tags, args.desc, args.quadrant)
        elif args.command == "remove":
            remove_activity(args.id)
        else:
            parser.print_help()
    except ValueError as exc:
        print(f"Error: {exc}")
        if args.command == "add" and args.quadrant not in QUADRANTS:
            print_quadrant_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
