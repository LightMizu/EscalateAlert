import asyncio
import logging

import httpx
from pyrogram import Client, idle

from alertescalation.alerts import BotAlerts
from alertescalation.config import BOT_TOKEN, ALERT_CHAT_ID
from alertescalation.handlers import register_handlers
from alertescalation.monitor import BehaviorMonitor


async def main():
    if bool(BOT_TOKEN) != bool(ALERT_CHAT_ID):
        raise ValueError("Set both BOT_TOKEN and ALERT_CHAT_ID")
    # httpx logs request URLs at INFO, which would expose the bot token.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    monitor = BehaviorMonitor()
    app = Client(
        name="MySession", api_id="2040", api_hash="b18441a1ff607e10a989891a5462e627"
    )
    try:
        async with httpx.AsyncClient(timeout=15) as http_client:
            alerts = BotAlerts(http_client, BOT_TOKEN, ALERT_CHAT_ID) if BOT_TOKEN else None
            if alerts is None:
                logging.getLogger(__name__).warning("Bot alerts disabled: BOT_TOKEN and ALERT_CHAT_ID are unset")
            register_handlers(app, monitor, alerts=alerts)
            async with app:
                await idle()
    finally:
        await monitor.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
