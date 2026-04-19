"""
APScheduler jobs for automated bot tasks:
- Weekly PvP reset (Monday 00:00 UTC) + World Gem awards to Top 10
- Monthly PvP reset (1st of month 00:00 UTC)
- Daily free missions reset (every 00:00 UTC)
- Stamina regeneration (every 30 minutes)
- Offline XP trickle (every 60 minutes)
"""
import logging
from datetime import datetime, timezone
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)


async def job_reset_weekly_pvp(bot):
    """Every Monday 00:00 UTC — award gems to top 10, reset weekly scores."""
    from database.mongo import get_weekly_leaderboard, add_currency, reset_weekly_pvp, get_all_users

    logger.info("🔄 Running weekly PvP reset...")
    GEM_REWARDS = [50, 40, 30, 25, 20, 15, 12, 10, 8, 5]

    for world in ("naruto", "aot"):
        lb = await get_weekly_leaderboard(world, limit=10)
        for i, entry in enumerate(lb):
            if entry.get("weekly_pvp_score", 0) > 0:
                gems = GEM_REWARDS[i] if i < len(GEM_REWARDS) else 3
                await add_currency(entry["user_id"], "world_gems", gems)
                try:
                    await bot.send_message(
                        chat_id=entry["user_id"],
                        text=(
                            f"🏆 *Weekly PvP Results!*\n\n"
                            f"You ranked #{i+1} in {world.title()} World!\n"
                            f"💎 Reward: +{gems} World Gems!"
                        ),
                        parse_mode="Markdown",
                    )
                except Exception:
                    pass

    await reset_weekly_pvp()
    logger.info("✅ Weekly PvP reset complete.")


async def job_reset_monthly_pvp():
    """1st of month 00:00 UTC — reset monthly scores."""
    from database.mongo import reset_monthly_pvp
    logger.info("🔄 Running monthly PvP reset...")
    await reset_monthly_pvp()
    logger.info("✅ Monthly PvP reset complete.")


async def job_reset_daily_free_missions():
    """Every 00:00 UTC — reset free missions count."""
    from database.mongo import reset_free_missions_if_new_day
    logger.info("🔄 Resetting daily free missions...")
    await reset_free_missions_if_new_day()
    logger.info("✅ Daily free missions reset.")


async def job_stamina_regen():
    """Every 30 minutes — add 5 stamina to all users below 100."""
    from database.mongo import regen_stamina_all
    logger.info("💚 Running stamina regeneration...")
    await regen_stamina_all()
    logger.info("✅ Stamina regen complete.")


async def job_offline_xp():
    """Every 60 minutes — award offline XP trickle."""
    from database.mongo import get_all_users, add_xp
    from game.progression import calc_offline_xp
    logger.info("📈 Awarding offline XP...")
    users = await get_all_users()
    xp = calc_offline_xp(1.0)  # 1 XP per hour
    for u in users:
        await add_xp(u["user_id"], xp)
    logger.info(f"✅ Offline XP awarded to {len(users)} users.")


def setup_scheduler(bot) -> AsyncIOScheduler:
    """Create and configure the APScheduler. Returns started scheduler."""
    scheduler = AsyncIOScheduler(timezone="UTC")

    # Weekly PvP reset — every Monday at 00:00 UTC
    scheduler.add_job(
        job_reset_weekly_pvp,
        CronTrigger(day_of_week="mon", hour=0, minute=0, timezone="UTC"),
        args=[bot],
        id="weekly_pvp_reset",
        replace_existing=True,
    )

    # Monthly PvP reset — every 1st at 00:00 UTC
    scheduler.add_job(
        job_reset_monthly_pvp,
        CronTrigger(day=1, hour=0, minute=0, timezone="UTC"),
        id="monthly_pvp_reset",
        replace_existing=True,
    )

    # Daily free mission reset — every day at 00:00 UTC
    scheduler.add_job(
        job_reset_daily_free_missions,
        CronTrigger(hour=0, minute=0, timezone="UTC"),
        id="daily_missions_reset",
        replace_existing=True,
    )

    # Stamina regen — every 30 minutes
    scheduler.add_job(
        job_stamina_regen,
        "interval",
        minutes=30,
        id="stamina_regen",
        replace_existing=True,
    )

    # Offline XP — every 60 minutes
    scheduler.add_job(
        job_offline_xp,
        "interval",
        hours=1,
        id="offline_xp",
        replace_existing=True,
    )

    return scheduler
