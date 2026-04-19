"""
main.py — Bot entry point.
- Webhook mode when WEBHOOK_URL is set (production/Render)
- Polling mode locally
- Unified text handler routes to trade or coop based on Redis session state
"""
import asyncio
import logging
import json
from config import BOT_TOKEN, WEBHOOK_URL, PORT

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


async def post_init(application):
    from database.mongo import init_db
    from scheduler.jobs import setup_scheduler
    logger.info("Initializing MongoDB indexes...")
    await init_db()
    logger.info("MongoDB ready.")
    logger.info("Starting APScheduler...")
    scheduler = setup_scheduler(application.bot)
    scheduler.start()
    application.bot_data["scheduler"] = scheduler
    logger.info("Scheduler running. All systems go.")


# ── Unified text handler (routes trade / coop based on Redis session) ──────────
async def unified_text_handler(update, context):
    from database.redis_client import redis
    user_id = update.effective_user.id
    sess_raw = await redis.get_session(user_id)
    if not sess_raw:
        return  # No active session, ignore plain text

    try:
        sess = json.loads(sess_raw)
    except Exception:
        return

    step = sess.get("step", "")

    if step in ("select_request", "select_their_char"):
        from handlers.trade import trade_text_handler
        await trade_text_handler(update, context)
    elif step == "coop_join":
        from handlers.coop import coop_join_text_handler
        await coop_join_text_handler(update, context)


def build_application():
    from telegram import Update
    from telegram.ext import Application, MessageHandler, filters

    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .post_init(post_init)
        .build()
    )

    # ── Register all handlers ──────────────────────────────────────────────────
    from handlers import start, profile, team, mission, gacha, pvp, shop, daily, trade, coop, events
    start.register(app)
    profile.register(app)
    team.register(app)
    mission.register(app)
    gacha.register(app)
    pvp.register(app)
    shop.register(app)
    daily.register(app)
    trade.register(app)
    coop.register(app)
    events.register(app)

    # ── Single unified text handler (lowest priority) ──────────────────────────
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, unified_text_handler),
        group=1,  # Group 1 = runs after group 0 command handlers
    )

    return app


def main():
    app = build_application()

    if WEBHOOK_URL:
        webhook_url = WEBHOOK_URL.rstrip("/")
        full_url = f"{webhook_url}/webhook" if not webhook_url.endswith("/webhook") else webhook_url
        logger.info(f"Starting WEBHOOK mode on port {PORT} → {full_url}")
        app.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path="/webhook",
            webhook_url=full_url,
            drop_pending_updates=True,
        )
    else:
        logger.info("Starting POLLING mode (local dev)")
        app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
