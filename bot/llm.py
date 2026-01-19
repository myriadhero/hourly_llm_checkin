import json
import logging
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


class NotEventsError(ValueError):
    pass


class UnclearEventError(ValueError):
    pass


def build_system_prompt() -> str:
    return (
        "You extract activity entries from a check-in message. "
        "Return ONLY valid JSON as a LIST of objects (one per activity). Return a list even if only a single event object was extracted. "
        "Each object must include keys: "
        "description (string; what was done, short phrase), "
        "duration_minutes (number > 0; minutes spent), "
        "quadrant (integer 1-4; Eisenhower matrix: Q1 urgent+important, "
        "Q2 important+not urgent, Q3 urgent+not important, Q4 not urgent+not important), "
        "tags (array of strings, optional), "
        "when (string optional literal 'now' OR 'YYYY-MM-DD HH:MM' in 24h format; when the parsed activity happened, PREFER literal 'now' instead of timestamp unless specified). "
        "If quadrant is missing, infer it from the description/urgency/importance. "
        "Infer tags even if the user does not provide them; prefer concise, lowercase tags "
        "like work, health, relationships, focus, distraction, learning, planning. "
        "NOTE: If the message is an attempted check-in but too ambiguous to extract (missing key details or unclear whether it's one or many events), "
        "return a single JSON object (not a list) with keys: error (set to unclearEvent), message "
        "(one sentence prompting the user to clarify the missing specifics). "
        "NOTE: If the user message is clearly not a check-in entry, return a single JSON object (not a list) "
        "with keys: error (set to notEvents), message (one sentence). The message should be "
        "a brief low-effort positive/encouraging (prompt user to think of something they care about) reply if it's a simple acknowledgement like "
        "'thanks', otherwise briefly explain why it couldn't be parsed. "
        "Do not include any extra keys or commentary."
    )


def extract_json(text: str) -> str:
    brace_index = text.find("{")
    bracket_index = text.find("[")
    if brace_index == -1 and bracket_index == -1:
        raise ValueError("LLM response did not include JSON")
    if bracket_index != -1 and (brace_index == -1 or bracket_index < brace_index):
        start = bracket_index
        end = text.rfind("]")
        if end == -1 or end <= start:
            raise ValueError("LLM response did not include JSON array")
        return text[start : end + 1]
    start = brace_index
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
        normalized_tags = [
            part.strip() for part in str(tags).split(",") if part.strip()
        ] or None
    when_value = str(when) if isinstance(when, str) and when.strip() else None
    return ActivityData(
        description=description.strip(),
        duration_minutes=float(duration),
        quadrant=quadrant,
        tags=normalized_tags,
        when=when_value,
    )


def normalize_activities(payload: Any) -> list[ActivityData]:
    if isinstance(payload, dict):
        if payload.get("error") == "notEvents":
            message = payload.get("message")
            raise NotEventsError(
                message
                if isinstance(message, str) and message.strip()
                else "Not a check-in."
            )
        if payload.get("error") == "unclearEvent":
            message = payload.get("message")
            raise UnclearEventError(
                message
                if isinstance(message, str) and message.strip()
                else "Please clarify what you did, how long it took, and the quadrant."
            )
        payloads = [payload]
    elif isinstance(payload, list):
        payloads = payload
    else:
        raise ValueError("LLM response did not include activity list")
    activities: list[ActivityData] = []
    for item in payloads:
        if not isinstance(item, dict):
            raise ValueError("Activity entries must be objects")
        activities.append(normalize_activity(item))
    if not activities:
        raise ValueError("No activities found")
    return activities


def parse_activities_from_text(
    client: Client, model: str, text: str
) -> list[ActivityData]:
    logging.debug("LLM check-in prompt: %s", text)
    chat = client.chat.create(model=model)
    chat.append(system(build_system_prompt()))
    chat.append(user(text))
    response = chat.sample()
    raw = response.content or ""
    logging.debug("LLM check-in response: %s", raw)
    payload = json.loads(extract_json(raw))
    return normalize_activities(payload)
