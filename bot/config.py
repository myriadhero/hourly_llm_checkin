import logging
import os
from dataclasses import dataclass
from datetime import datetime, timezone, tzinfo
from typing import Optional
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


@dataclass
class BotConfig:
    token: str
    xai_api_key: str
    xai_model: str
    timezone_name: Optional[str]
    day_start_hour: int
    day_end_hour: int
    checkin_prompt: str
    chat_id: Optional[int]
    pending_ttl_minutes: int


def parse_int_env(var_name: str, default: int, min_value: int, max_value: int) -> int:
    raw = os.getenv(var_name)
    if raw is None:
        return default
    try:
        value = int(raw)
    except ValueError:
        logging.warning("Invalid %s=%r, using default %s", var_name, raw, default)
        return default
    if value < min_value or value > max_value:
        logging.warning("Out-of-range %s=%r, using default %s", var_name, raw, default)
        return default
    return value


def load_config() -> BotConfig:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError("Missing TELEGRAM_BOT_TOKEN")
    xai_api_key = os.getenv("XAI_API_KEY")
    if not xai_api_key:
        raise RuntimeError("Missing XAI_API_KEY")
    chat_id_raw = os.getenv("TELEGRAM_CHAT_ID")
    chat_id: Optional[int]
    if chat_id_raw:
        try:
            chat_id = int(chat_id_raw)
        except ValueError:
            raise RuntimeError("Invalid TELEGRAM_CHAT_ID; must be an integer") from None
    else:
        chat_id = None
    return BotConfig(
        token=token,
        xai_api_key=xai_api_key,
        xai_model=os.getenv("XAI_MODEL", "grok-4-latest"),
        timezone_name=os.getenv("TIMEZONE"),
        day_start_hour=parse_int_env("DAY_START_HOUR", 9, 0, 23),
        day_end_hour=parse_int_env("DAY_END_HOUR", 18, 0, 23),
        checkin_prompt=os.getenv(
            "CHECKIN_PROMPT",
            "Hourly check-in: what did you do in the last hour? Include duration, quadrant (Q1-4), tags, and why if you can.",
        ),
        chat_id=chat_id,
        pending_ttl_minutes=parse_int_env("CHECKIN_TTL_MINUTES", 120, 10, 720),
    )


def get_timezone(config: BotConfig) -> tzinfo:
    if config.timezone_name:
        try:
            return ZoneInfo(config.timezone_name)
        except ZoneInfoNotFoundError:
            logging.warning(
                "Unknown TIMEZONE %r, using local timezone.", config.timezone_name
            )
    return datetime.now().astimezone().tzinfo or timezone.utc
