import json
from dataclasses import dataclass
from typing import Any, Optional

from xai_sdk import Client
from xai_sdk.chat import system, user


@dataclass
class ActivityData:
    description: str
    duration_minutes: float
    quadrant: int
    tags: Optional[list[str]]
    when: Optional[str]


def build_system_prompt() -> str:
    return (
        "You extract a single activity entry from a check-in message. "
        "Return ONLY valid JSON with keys: "
        "description (string), duration_minutes (number), quadrant (integer 1-4), "
        "tags (array of strings, optional), when (string optional in 'YYYY-MM-DD HH:MM' 24h). "
        "Infer tags even if the user does not provide them; prefer concise, lowercase tags "
        "like work, health, relationships, focus, distraction, learning, planning. "
        "Do not include any extra keys or commentary."
    )


def extract_json(text: str) -> str:
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("LLM response did not include JSON object")
    return text[start : end + 1]


def normalize_activity(payload: dict[str, Any]) -> ActivityData:
    description = payload.get("description") or payload.get("desc")
    duration = payload.get("duration_minutes") or payload.get("duration")
    quadrant = payload.get("quadrant")
    tags = payload.get("tags")
    when = payload.get("when")
    if not isinstance(description, str) or not description.strip():
        raise ValueError("Missing description")
    if isinstance(duration, str):
        try:
            duration = float(duration)
        except ValueError:
            duration = None
    if not isinstance(duration, (int, float)) or duration <= 0:
        raise ValueError("Missing duration_minutes")
    if isinstance(quadrant, str):
        try:
            quadrant = int(quadrant)
        except ValueError:
            quadrant = None
    if not isinstance(quadrant, int) or quadrant not in {1, 2, 3, 4}:
        raise ValueError("Missing quadrant")
    if tags is None:
        normalized_tags = None
    elif isinstance(tags, list):
        normalized_tags = [str(tag).strip() for tag in tags if str(tag).strip()]
        if not normalized_tags:
            normalized_tags = None
    else:
        normalized_tags = [part.strip() for part in str(tags).split(",") if part.strip()] or None
    when_value = str(when) if isinstance(when, str) and when.strip() else None
    return ActivityData(
        description=description.strip(),
        duration_minutes=float(duration),
        quadrant=quadrant,
        tags=normalized_tags,
        when=when_value,
    )


def parse_activity_from_text(client: Client, model: str, text: str) -> ActivityData:
    chat = client.chat.create(model=model)
    chat.append(system(build_system_prompt()))
    chat.append(user(text))
    response = chat.sample()
    raw = response.content or ""
    payload = json.loads(extract_json(raw))
    return normalize_activity(payload)
