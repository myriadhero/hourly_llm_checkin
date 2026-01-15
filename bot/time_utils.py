from datetime import datetime, timedelta


def is_daytime(now: datetime, start_hour: int, end_hour: int) -> bool:
    if start_hour == end_hour:
        return True
    if start_hour < end_hour:
        return start_hour <= now.hour < end_hour
    return now.hour >= start_hour or now.hour < end_hour


def seconds_until_next_hour(now: datetime) -> float:
    next_hour = (now + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
    return max((next_hour - now).total_seconds(), 0)
