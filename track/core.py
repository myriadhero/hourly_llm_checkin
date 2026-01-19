from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from sqlalchemy import Column, DateTime, Float, Integer, String, create_engine, or_
from sqlalchemy.orm import declarative_base, sessionmaker

DB_PATH = Path(__file__).resolve().parent / "activities.db"
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


QUADRANTS = {
    1: "Urgent & Important (Do)",
    2: "Not Urgent & Important (Schedule)",
    3: "Urgent & Not Important (Delegate)",
    4: "Not Urgent & Not Important (Eliminate)",
}


def init_db() -> None:
    """Create tables if they don't exist."""
    Base.metadata.create_all(engine)


def parse_activity_timestamp(when: Optional[str]) -> datetime:
    if not when:
        return datetime.now()
    try:
        return datetime.fromisoformat(when)
    except ValueError:
        pass
    for fmt in ["%Y-%m-%d %H:%M", "%Y-%m-%d", "%H:%M"]:
        try:
            activity_ts = datetime.strptime(when, fmt)
            if fmt == "%H:%M":
                today = datetime.now().date()
                activity_ts = datetime.combine(today, activity_ts.time())
            return activity_ts
        except ValueError:
            continue
    raise ValueError(
        f"Could not parse timestamp '{when}'. Try formats: '2026-01-04 10:30', '2026-01-04', '10:30'"
    )


def resolve_activity_timestamp(when: Optional[str], duration: float) -> datetime:
    if not when or (isinstance(when, str) and when.strip().lower() == "now"):
        return datetime.now() - timedelta(minutes=duration)
    return parse_activity_timestamp(when)


def add_activity(
    when: Optional[str],
    duration: float,
    quadrant: int,
    desc: str,
    tags: Optional[str],
) -> datetime:
    if quadrant not in QUADRANTS:
        raise ValueError(f"Quadrant must be 1-4. Got {quadrant}")
    activity_ts = resolve_activity_timestamp(when, duration)

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
    return activity_ts


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


def fetch_activities(limit: int, sort_by: str) -> list[Activity]:
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
        return activities
    finally:
        session.close()


def fetch_activity(activity_id: int) -> Optional[Activity]:
    session = Session()
    try:
        activity = (
            session.query(Activity).filter(Activity.id == activity_id).one_or_none()
        )
        if activity:
            session.expunge(activity)
        return activity
    finally:
        session.close()


def delete_activity(activity_id: int) -> bool:
    session = Session()
    try:
        activity = (
            session.query(Activity).filter(Activity.id == activity_id).one_or_none()
        )
        if not activity:
            return False
        session.delete(activity)
        session.commit()
        return True
    finally:
        session.close()


def list_activities(limit: int, sort_by: str) -> None:
    activities = fetch_activities(limit, sort_by)
    render_activities(activities)


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
        print(
            "About to delete: "
            f"ID {activity.id} | {when} | {duration} | Q{activity.quadrant} | {activity.description}"
        )
        confirm = input("Delete this activity? [y/N]: ").strip().lower()
        if confirm not in {"y", "yes"}:
            print("Delete cancelled.")
            return
        session.delete(activity)
        session.commit()
        print(f"Deleted activity ID {activity_id}.")
    finally:
        session.close()
