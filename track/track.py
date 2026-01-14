#!/usr/bin/env python3
# /// script
# dependencies = [
#   "SQLAlchemy"
# ]
# ///
"""
Activity Tracker - Log activities with Eisenhower matrix quadrant and tags.
Usage: uv run track.py add --when "2024-01-04 10:30" --duration 45 --quadrant 2 --desc "Deep work on project X" --tags "work,coding,focus"
       uv run track.py add --duration 30 --quadrant 4 --desc "Scrolled Twitter" --tags "distraction,social"
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path

from sqlalchemy import create_engine, Column, Integer, String, DateTime, Float, or_
from sqlalchemy.orm import declarative_base, sessionmaker
from typing import Optional
# Database setup
DB_PATH = Path(__file__).parent / "activities.db"
engine = create_engine(f"sqlite:///{DB_PATH}", echo=False)
Base = declarative_base()
Session = sessionmaker(bind=engine)


class Activity(Base):
    __tablename__ = "activities"

    id = Column(Integer, primary_key=True, autoincrement=True)
    entry_timestamp = Column(DateTime, default=datetime.now, nullable=False)
    activity_timestamp = Column(DateTime, nullable=False)
    duration_minutes = Column(Float, nullable=False)
    quadrant = Column(Integer, nullable=False)  # 1-4 Eisenhower matrix
    description = Column(String, nullable=False)
    tags = Column(String, nullable=True)  # Comma-separated

    def __repr__(self):
        return f"<Activity {self.id}: Q{self.quadrant} {self.duration_minutes}m - {self.description[:30]}>"


# Quadrant descriptions for reference
QUADRANTS = {
    1: "Urgent & Important (Do)",
    2: "Not Urgent & Important (Schedule)",
    3: "Urgent & Not Important (Delegate)",
    4: "Not Urgent & Not Important (Eliminate)",
}


def init_db():
    """Create tables if they don't exist."""
    Base.metadata.create_all(engine)


def add_activity(when: Optional[str], duration: float, quadrant: int, desc: str, tags: Optional[str]):
    """Add a new activity to the database."""
    if quadrant not in QUADRANTS:
        print(f"Error: Quadrant must be 1-4. Got {quadrant}")
        print("  1 = Urgent & Important (Do)")
        print("  2 = Not Urgent & Important (Schedule)")
        print("  3 = Urgent & Not Important (Delegate)")
        print("  4 = Not Urgent & Not Important (Eliminate)")
        sys.exit(1)

    # Parse activity timestamp
    if when:
        try:
            activity_ts = datetime.fromisoformat(when)
        except ValueError:
            # Try common formats
            for fmt in ["%Y-%m-%d %H:%M", "%Y-%m-%d", "%H:%M"]:
                try:
                    activity_ts = datetime.strptime(when, fmt)
                    if fmt == "%H:%M":
                        # Time only - use today's date
                        today = datetime.now().date()
                        activity_ts = datetime.combine(today, activity_ts.time())
                    break
                except ValueError:
                    continue
            else:
                print(f"Error: Could not parse timestamp '{when}'")
                print("Try formats: '2024-01-04 10:30', '2024-01-04', '10:30'")
                sys.exit(1)
    else:
        activity_ts = datetime.now()

    session = Session()
    try:
        activity = Activity(
            activity_timestamp=activity_ts,
            duration_minutes=duration,
            quadrant=quadrant,
            description=desc,
            tags=tags,
        )
        session.add(activity)
        session.commit()

        print(f"✓ Logged: Q{quadrant} | {duration}m | {desc}")
        if tags:
            print(f"  Tags: {tags}")
        print(f"  When: {activity_ts.strftime('%Y-%m-%d %H:%M')}")

    finally:
        session.close()


def format_table(headers: list[str], rows: list[list[str]]) -> str:
    """Return a simple aligned table for terminal output."""
    if not rows:
        return ""
    widths = [len(header) for header in headers]
    for row in rows:
        for idx, cell in enumerate(row):
            widths[idx] = max(widths[idx], len(cell))
    header_line = " | ".join(header.ljust(widths[idx]) for idx, header in enumerate(headers))
    divider = "-+-".join("-" * widths[idx] for idx in range(len(headers)))
    body_lines = [" | ".join(cell.ljust(widths[idx]) for idx, cell in enumerate(row)) for row in rows]
    return "\n".join([header_line, divider, *body_lines])


def render_activities(activities: list[Activity]) -> None:
    if not activities:
        print("No activities found.")
        return
    headers = ["ID", "When", "Duration", "Q", "Description", "Tags"]
    rows: list[list[str]] = []
    for activity in activities:
        when = activity.activity_timestamp.strftime("%Y-%m-%d %H:%M")
        duration = f"{activity.duration_minutes:g}m"
        rows.append(
            [
                str(activity.id),
                when,
                duration,
                str(activity.quadrant),
                activity.description,
                activity.tags or "",
            ]
        )
    print(format_table(headers, rows))


def list_activities(limit: int, sort_by: str) -> None:
    session = Session()
    try:
        if sort_by == "added":
            query = session.query(Activity).order_by(Activity.entry_timestamp.desc())
            activities = query.limit(limit).all()
        elif sort_by == "event":
            query = session.query(Activity).order_by(Activity.activity_timestamp.desc())
            activities = query.limit(limit).all()
        else:
            query = session.query(Activity).order_by(Activity.id.desc())
            activities = list(reversed(query.limit(limit).all()))
        render_activities(activities)
    finally:
        session.close()


def search_activities(tags: Optional[str], desc: Optional[str], quadrant: Optional[int]) -> None:
    session = Session()
    try:
        filters = []
        if tags:
            tag_terms = [term.strip() for term in tags.split(",") if term.strip()]
            if tag_terms:
                filters.extend(Activity.tags.like(f"%{term}%") for term in tag_terms)
        if desc:
            desc_terms = [term.strip() for term in desc.split() if term.strip()]
            if desc_terms:
                filters.extend(Activity.description.like(f"%{term}%") for term in desc_terms)

        query = session.query(Activity)
        if quadrant is not None:
            query = query.filter(Activity.quadrant == quadrant)
        if filters:
            query = query.filter(or_(*filters))

        activities = query.order_by(Activity.activity_timestamp.desc()).all()
        render_activities(activities)
    finally:
        session.close()


def remove_activity(activity_id: int) -> None:
    session = Session()
    try:
        activity = session.query(Activity).filter(Activity.id == activity_id).one_or_none()
        if not activity:
            print(f"No activity found with ID {activity_id}.")
            return
        when = activity.activity_timestamp.strftime("%Y-%m-%d %H:%M")
        duration = f"{activity.duration_minutes:g}m"
        print(f"About to delete: ID {activity.id} | {when} | {duration} | Q{activity.quadrant} | {activity.description}")
        confirm = input("Delete this activity? [y/N]: ").strip().lower()
        if confirm not in {"y", "yes"}:
            print("Delete cancelled.")
            return
        session.delete(activity)
        session.commit()
        print(f"Deleted activity ID {activity_id}.")
    finally:
        session.close()


def main():
    parser = argparse.ArgumentParser(description="Track activities with Eisenhower matrix")
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Add command
    add_parser = subparsers.add_parser("add", help="Add a new activity")
    add_parser.add_argument("--when", "-w", help="When the activity happened (default: now)")
    add_parser.add_argument("--duration", "-d", type=float, required=True, help="Duration in minutes")
    add_parser.add_argument("--quadrant", "-q", type=int, required=True, help="Eisenhower quadrant (1-4)")
    add_parser.add_argument("--desc", "-D", required=True, help="Description of the activity")
    add_parser.add_argument("--tags", "-t", help="Comma-separated tags (e.g., 'work,coding,focus')")

    # List command
    list_parser = subparsers.add_parser("list", help="List recent activities")
    list_parser.add_argument("--limit", "-l", type=int, default=10, help="Number of activities to show (default: 10)")
    list_parser.add_argument(
        "--sort-by",
        choices=["id", "added", "event"],
        default="id",
        help="Sort by id (ASC), added (entry timestamp DESC), or event (activity timestamp DESC)",
    )

    # Search command
    search_parser = subparsers.add_parser("search", help="Search activities")
    search_parser.add_argument("--tags", "-t", help="Comma-separated tags to match (OR logic)")
    search_parser.add_argument("--desc", "-D", help="Description keywords to match (OR logic)")
    search_parser.add_argument("--quadrant", "-q", type=int, help="Filter by Eisenhower quadrant (1-4)")

    # Remove command
    remove_parser = subparsers.add_parser("remove", help="Remove an activity by ID")
    remove_parser.add_argument("--id", type=int, required=True, help="Activity ID to delete")

    args = parser.parse_args()

    init_db()

    if args.command == "add":
        add_activity(args.when, args.duration, args.quadrant, args.desc, args.tags)
    elif args.command == "list":
        list_activities(args.limit, args.sort_by)
    elif args.command == "search":
        search_activities(args.tags, args.desc, args.quadrant)
    elif args.command == "remove":
        remove_activity(args.id)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
