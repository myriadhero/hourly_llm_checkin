import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional


@dataclass
class BotState:
    chat_id: Optional[int] = None
    last_prompt_at: Optional[datetime] = None
    last_message_id: Optional[int] = None
    pending_checkin: Optional[str] = None
    pending_delete_id: Optional[int] = None


def load_state(path: Path) -> BotState:
    if not path.exists():
        return BotState()
    try:
        raw = json.loads(path.read_text())
    except json.JSONDecodeError:
        return BotState()
    last_prompt_at = None
    if isinstance(raw.get("last_prompt_at"), str):
        try:
            last_prompt_at = datetime.fromisoformat(raw["last_prompt_at"])
        except ValueError:
            last_prompt_at = None
    chat_id = raw.get("chat_id")
    if not isinstance(chat_id, int):
        chat_id = None
    last_message_id = raw.get("last_message_id")
    if not isinstance(last_message_id, int):
        last_message_id = None
    pending_checkin = raw.get("pending_checkin")
    if not isinstance(pending_checkin, str) or not pending_checkin.strip():
        pending_checkin = None
    pending_delete_id = raw.get("pending_delete_id")
    if not isinstance(pending_delete_id, int):
        pending_delete_id = None
    return BotState(
        chat_id=chat_id,
        last_prompt_at=last_prompt_at,
        last_message_id=last_message_id,
        pending_checkin=pending_checkin,
        pending_delete_id=pending_delete_id,
    )


def save_state(path: Path, state: BotState) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "chat_id": state.chat_id,
        "last_prompt_at": state.last_prompt_at.isoformat() if state.last_prompt_at else None,
        "last_message_id": state.last_message_id,
        "pending_checkin": state.pending_checkin,
        "pending_delete_id": state.pending_delete_id,
    }
    temp_path = path.with_suffix(path.suffix + ".tmp")
    temp_path.write_text(json.dumps(payload, indent=2))
    temp_path.replace(path)
