import asyncio
import logging
import math
from collections import deque

from pyrogram import Client, filters
from pyrogram.handlers import MessageHandler
from pyrogram.types import Message

from alertescalation.alerts import BotAlerts
from alertescalation.config import (
    ALERT_THRESHOLD,
    ALERT_DROP,
    ALERT_TREND_MESSAGES,
    DEBUG_MODE,
    HISTORY_SIZE,
    USER_ID,
    WEIGHTS,
)
from alertescalation.monitor import BehaviorMonitor


def calculate_score(analysis):
    return sum(getattr(analysis, key) * weight for key, weight in WEIGHTS.items())


def evaluate_trend(scores: deque, score: float):
    previous = scores[-1] if scores else None
    delta = score - previous if previous is not None else None
    window_delta = (
        score - scores[-ALERT_TREND_MESSAGES]
        if len(scores) >= ALERT_TREND_MESSAGES else None
    )
    falling = window_delta is not None and (
        window_delta <= -ALERT_DROP
        or math.isclose(window_delta, -ALERT_DROP, abs_tol=1e-9)
    )
    # A high but falling score reflects old conflict still present in history.
    # Notify on the first high score or renewed growth, not every high reading.
    rising = delta is not None and delta > 1e-9
    first_high = previous is None and score >= ALERT_THRESHOLD
    should_alert = not falling and (first_high or rising)
    scores.append(score)
    return should_alert, delta, window_delta


async def new_message(
    client: Client,
    message: Message,
    monitor: BehaviorMonitor,
    *,
    history: deque,
    lock: asyncio.Lock,
    scores: deque,
    alerts: BotAlerts | None = None,
    debug: bool = DEBUG_MODE,
):
    content = message.text or message.caption
    if not content or message.from_user is None:
        return
    logger = logging.getLogger(__name__)
    try:
        # Serialize each chat while allowing different chats to run concurrently.
        async with lock:
            monitor.add_message(str(message.from_user.id), content, history=history)
            analysis = (
                await monitor.analyze(history=history, min_messages=1)
                if debug
                else await monitor.analyze(history=history)
            )
            if analysis is None:
                return
            score = calculate_score(analysis)
            should_alert, delta, window_delta = evaluate_trend(scores, score)
            if debug:
                logger.info(
                    "Message analysis: chat_id=%s score=%.3f analysis=%s",
                    message.chat.id,
                    score,
                    analysis,
                )
            if should_alert:
                logger.warning(
                    "Escalate detect: chat_id=%s score=%.3f delta=%s window_delta=%s",
                    message.chat.id,
                    score,
                    delta,
                    window_delta,
                )
            if alerts is not None:
                if debug:
                    await alerts.send(
                        message.chat.id, score, analysis=analysis,
                        delta=delta, window_delta=window_delta, is_alert=should_alert,
                    )
                elif should_alert:
                    await alerts.send(message.chat.id, score, delta=delta, window_delta=window_delta)
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        # Avoid logging private message contents or provider response bodies.
        logger.error(
            "Message analysis failed: chat_id=%s error_type=%s",
            message.chat.id,
            type(exc).__name__,
        )


def register_handlers(
    app: Client,
    monitor: BehaviorMonitor,
    *,
    user_id: int | None = USER_ID,
    history_size: int = HISTORY_SIZE,
    alerts: BotAlerts | None = None,
    debug: bool = DEBUG_MODE,
) -> MessageHandler:
    if history_size <= 0:
        raise ValueError("history_size must be positive")
    histories: dict[int, deque] = {}
    locks: dict[int, asyncio.Lock] = {}
    scores: dict[int, deque] = {}

    async def on_message(client: Client, message: Message):
        chat_id = message.chat.id
        # No await between lookup and creation within this event loop.
        if chat_id not in histories:
            histories[chat_id] = deque(maxlen=history_size)
            locks[chat_id] = asyncio.Lock()
            scores[chat_id] = deque(maxlen=ALERT_TREND_MESSAGES)
        await new_message(
            client,
            message,
            monitor,
            history=histories[chat_id],
            lock=locks[chat_id],
            scores=scores[chat_id],
            alerts=alerts,
            debug=debug,
        )

    message_filter = filters.private
    if user_id is not None:
        message_filter &= filters.chat(user_id)
    handler = MessageHandler(on_message, message_filter)
    app.add_handler(handler)
    return handler
