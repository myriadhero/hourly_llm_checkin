import asyncio
import logging
from datetime import datetime, timedelta
from pathlib import Path

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
from xai_sdk import Client

import track

from .config import BotConfig
from .llm import ActivityData, parse_activity_from_text
from .state import BotState, save_state
from .time_utils import is_daytime, seconds_until_next_hour

HOUR_SECONDS = 60 * 60


def should_process_checkin(now: datetime, state: BotState, ttl_minutes: int) -> bool:
    if not state.last_prompt_at:
        return False
    last_prompt_at = state.last_prompt_at
    if last_prompt_at.tzinfo is None and now.tzinfo is not None:
        last_prompt_at = last_prompt_at.replace(tzinfo=now.tzinfo)
    return now - last_prompt_at <= timedelta(minutes=ttl_minutes)


def render_activity_summary(activity: ActivityData, activity_ts: datetime | None = None) -> str:
    tags = ", ".join(activity.tags) if activity.tags else "none"
    if activity_ts is not None:
        when = activity_ts.strftime("%Y-%m-%d %H:%M")
    else:
        when = activity.when or "now"
    return f"Logged: Q{activity.quadrant} | {activity.duration_minutes:g}m | {activity.description} | tags: {tags} | when: {when}"


def format_activity_list(activities: list[track.Activity]) -> str:
    if not activities:
        return "No activities found."
    lines: list[str] = []
    for activity in activities:
        when = activity.activity_timestamp.strftime("%Y-%m-%d %H:%M")
        duration = f"{activity.duration_minutes:g}m"
        tags = f" | tags: {activity.tags}" if activity.tags else ""
        lines.append(
            f"- {when} | {duration} | Q{activity.quadrant} | {activity.description}{tags}"
        )
    return "\n".join(lines)


async def send_checkin(context: ContextTypes.DEFAULT_TYPE, force: bool = False) -> bool:
    config: BotConfig = context.application.bot_data["config"]
    state: BotState = context.application.bot_data["state"]
    tzinfo = context.application.bot_data["timezone"]
    state_path: Path = context.application.bot_data["state_path"]
    now = datetime.now(tzinfo)
    if not force and not is_daytime(now, config.day_start_hour, config.day_end_hour):
        return False
    chat_id = config.chat_id or state.chat_id
    if not chat_id:
        logging.info("No chat_id yet; run /start to register.")
        return False
    await context.bot.send_message(chat_id=chat_id, text=config.checkin_prompt)
    state.last_prompt_at = now
    save_state(state_path, state)
    return True


async def handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    config: BotConfig = context.application.bot_data["config"]
    state: BotState = context.application.bot_data["state"]
    state_path: Path = context.application.bot_data["state_path"]
    chat_id = update.effective_chat.id if update.effective_chat else None
    if chat_id is None:
        return
    if config.chat_id and chat_id != config.chat_id:
        await update.message.reply_text("This bot is configured for a different chat.")
        return
    state.chat_id = chat_id
    save_state(state_path, state)
    await update.message.reply_text(
        "Check-ins are active. I'll ping you hourly during daytime. "
        "You can also send /checkin to prompt now."
    )


async def handle_checkin_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    config: BotConfig = context.application.bot_data["config"]
    state: BotState = context.application.bot_data["state"]
    state_path: Path = context.application.bot_data["state_path"]
    chat_id = update.effective_chat.id if update.effective_chat else None
    if chat_id is not None and not config.chat_id and state.chat_id is None:
        state.chat_id = chat_id
        save_state(state_path, state)
    sent = await send_checkin(context, force=True)
    if update.message:
        if sent:
            await update.message.reply_text("Prompt sent.")
        else:
            await update.message.reply_text("No chat is registered yet. Send /start first.")


async def handle_list_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    config: BotConfig = context.application.bot_data["config"]
    state: BotState = context.application.bot_data["state"]
    state_path: Path = context.application.bot_data["state_path"]
    chat_id = update.effective_chat.id if update.effective_chat else None
    if chat_id is None:
        return
    if config.chat_id and chat_id != config.chat_id:
        await update.message.reply_text("This bot is configured for a different chat.")
        return
    if not config.chat_id and state.chat_id is None:
        state.chat_id = chat_id
        save_state(state_path, state)
    limit = 10
    if context.args:
        try:
            limit = int(context.args[0])
        except ValueError:
            await update.message.reply_text("Usage: /list [number_of_events]")
            return
    limit = max(1, min(limit, 50))
    try:
        activities = await asyncio.to_thread(track.fetch_activities, limit, "event")
    except Exception as exc:
        logging.exception("Failed to list activities: %s", exc)
        await update.message.reply_text("Listing failed. Check logs for details.")
        return
    output = format_activity_list(activities)
    if len(output) > 4000:
        output = output[:4000].rstrip() + "\n...truncated"
    await update.message.reply_text(output)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.message.text:
        return
    config: BotConfig = context.application.bot_data["config"]
    state: BotState = context.application.bot_data["state"]
    tzinfo = context.application.bot_data["timezone"]
    state_path: Path = context.application.bot_data["state_path"]
    chat_id = update.effective_chat.id if update.effective_chat else None
    if chat_id is None:
        return
    if config.chat_id and chat_id != config.chat_id:
        return
    if not should_process_checkin(datetime.now(tzinfo), state, config.pending_ttl_minutes):
        await update.message.reply_text(
            "I didn't ask for a check-in yet. Send /checkin to log one now."
        )
        return
    text = update.message.text
    client: Client = context.application.bot_data["xai_client"]
    try:
        activity = await asyncio.to_thread(parse_activity_from_text, client, config.xai_model, text)
    except Exception as exc:
        logging.exception("Failed to parse check-in: %s", exc)
        await update.message.reply_text(
            "I couldn't parse that. Please include what you did, how long, and a quadrant (Q1-4)."
        )
        return
    tags = ",".join(activity.tags) if activity.tags else None
    try:
        activity_ts = await asyncio.to_thread(
            track.add_activity,
            activity.when,
            activity.duration_minutes,
            activity.quadrant,
            activity.description,
            tags,
        )
    except Exception as exc:
        logging.exception("Failed to log activity: %s", exc)
        await update.message.reply_text("I parsed it, but logging failed. Check logs for details.")
        return
    state.last_prompt_at = None
    save_state(state_path, state)
    await update.message.reply_text(render_activity_summary(activity, activity_ts))


async def on_startup(application: Application) -> None:
    tzinfo = application.bot_data["timezone"]
    delay = seconds_until_next_hour(datetime.now(tzinfo))
    application.job_queue.run_repeating(send_checkin, interval=HOUR_SECONDS, first=delay)


def create_application(
    config: BotConfig,
    state: BotState,
    state_path: Path,
    tzinfo,
    xai_client: Client,
) -> Application:
    application = Application.builder().token(config.token).post_init(on_startup).build()
    application.bot_data["config"] = config
    application.bot_data["state"] = state
    application.bot_data["state_path"] = state_path
    application.bot_data["timezone"] = tzinfo
    application.bot_data["xai_client"] = xai_client

    application.add_handler(CommandHandler("start", handle_start))
    application.add_handler(CommandHandler("checkin", handle_checkin_command))
    application.add_handler(CommandHandler("list", handle_list_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    return application
