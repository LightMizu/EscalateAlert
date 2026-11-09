import logging

import httpx

from alertescalation.monitor import Analysis
from alertescalation.config import ALERT_TREND_MESSAGES


class BotAlerts:
    def __init__(self, client: httpx.AsyncClient, token: str, chat_id: str):
        self.client = client
        self.token = token
        self.chat_id = chat_id

    async def send(
        self, source_chat_id: int, score: float, *, analysis: Analysis | None = None,
        delta: float | None = None, window_delta: float | None = None,
        is_alert: bool = True,
    ) -> None:
        text = (
            "Отладка анализа.\n"
            if analysis is not None
            else "Пожалуйста остановите эскалацию диалога.\n"
        ) + f"Чат: {source_chat_id}\nОценка: {score:.3f}"
        if delta is not None:
            text += f"\nДельта: {delta:+.3f}"
        if window_delta is not None:
            text += f"\nДельта за {ALERT_TREND_MESSAGES} сообщ.: {window_delta:+.3f}"
        if analysis is not None:
            text += f"\nАлерт: {'да' if is_alert else 'нет'}"
            text += (
                f"\nHostility: {analysis.hostility:.3f}"
                f"\nImpulsivity: {analysis.impulsivity:.3f}"
                f"\nRepetition: {analysis.repetition:.3f}"
                f"\nMutual escalation: {analysis.mutual_escalation:.3f}"
                f"\nEscalation: {analysis.escalation}"
            )
        try:
            response = await self.client.post(
                f"https://api.telegram.org/bot{self.token}/sendMessage",
                json={
                    "chat_id": self.chat_id,
                    "text": text,
                },
            )
            response.raise_for_status()
            if response.json().get("ok") is not True:
                raise ValueError("Telegram rejected alert")
        except Exception as exc:
            # HTTP exception strings contain the bot token in the request URL.
            logging.getLogger(__name__).error(
                "Bot alert failed: chat_id=%s error_type=%s",
                source_chat_id,
                type(exc).__name__,
            )
