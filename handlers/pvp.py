"""
/pvp and /leaderboard handlers — auto-battle, weekly/monthly leaderboard.
"""
import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler
from database.mongo import (
    get_user, get_pvp_opponents, update_pvp_score,
    get_weekly_leaderboard, get_monthly_leaderboard,
    add_currency, increment_event_progress,
)
from database.redis_client import redis
from game.characters import get_char, get_char_stats
from game.battle import simulate_pvp, calc_team_power


async def show_pvp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = update.effective_user.id
    user = await get_user(user_id)

    if not user:
        await query.answer("Register first! /start", show_alert=True)
        return

    world = user["world"]
    c = user["currencies"]
    weekly = user.get("weekly_pvp_score", 0)
    world_label = "🍃 Naruto" if world == "naruto" else "⚔️ AoT"

    kb = [
        [InlineKeyboardButton("⚔️ Fight Now!", callback_data="pvp_fight")],
        [InlineKeyboardButton("📊 Weekly LB",  callback_data="pvp_lb_week"),
         InlineKeyboardButton("📅 Monthly LB", callback_data="pvp_lb_month")],
        [InlineKeyboardButton("🔙 Back",        callback_data="nav_main")],
    ]
    await query.edit_message_text(
        f"🏆 *PvP Arena* — {world_label}\n\n"
        f"Your W/L: {user['pvp_wins']}W / {user['pvp_losses']}L\n"
        f"⚡ Weekly Score: {weekly} pts\n\n"
        "_Win = +10 pts | Loss = -2 pts_\n"
        "_Top 10 weekly get World Gems!_",
        reply_markup=InlineKeyboardMarkup(kb),
        parse_mode="Markdown",
    )


async def pvp_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = await get_user(user_id)
    if not user:
        await update.message.reply_text("Register first! /start")
        return
    world = user["world"]
    kb = [
        [InlineKeyboardButton("⚔️ Fight Now!",  callback_data="pvp_fight")],
        [InlineKeyboardButton("📊 Weekly LB",   callback_data="pvp_lb_week"),
         InlineKeyboardButton("📅 Monthly LB",  callback_data="pvp_lb_month")],
        [InlineKeyboardButton("🔙 Main Menu",   callback_data="nav_main")],
    ]
    await update.message.reply_text(
        f"🏆 *PvP Arena*\nW/L: {user['pvp_wins']}W/{user['pvp_losses']}L | Score: {user.get('weekly_pvp_score',0)}",
        reply_markup=InlineKeyboardMarkup(kb),
        parse_mode="Markdown",
    )


async def pvp_fight_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("⚔️ Searching for opponent...")
    user_id = update.effective_user.id

    # Rate limit: 10-second window
    if await redis.rate_limit(user_id, "pvp", window=10):
        await query.answer("⏳ PvP cooldown! Wait a moment.", show_alert=True)
        return

    user = await get_user(user_id)
    if not user:
        return

    world = user["world"]
    team_ids = user.get("team", [])

    if not team_ids:
        await query.answer("Set your team first! /team", show_alert=True)
        return

    # Build player's team
    team1_chars = [(get_char(cid), 1) for cid in team_ids if get_char(cid)]

    # Find opponent
    opponents = await get_pvp_opponents(user_id, world, limit=20)
    if not opponents:
        # No real opponents — fight AI
        opp_name = "AI Shinobi" if world == "naruto" else "AI Scout"
        opp_power = calc_team_power(team1_chars, user.get("formation","standard")) * random.uniform(0.7, 1.3)
        from game.characters import get_world_chars
        world_chars = get_world_chars(world)
        fake_team = [(random.choice(world_chars), 1) for _ in range(3)]
        result = simulate_pvp(
            team1_chars, user.get("formation","standard"), user.get("sensei_id"),
            fake_team, "standard", None,
        )
        opp_name_display = opp_name
    else:
        opp = random.choice(opponents)
        opp_name_display = opp.get("username", "Opponent")
        opp_team_ids = opp.get("team", [])
        opp_team_chars = [(get_char(cid), 1) for cid in opp_team_ids if get_char(cid)]
        if not opp_team_chars:
            from game.characters import get_world_chars
            fake_team = [(random.choice(get_world_chars(world)), 1) for _ in range(3)]
            opp_team_chars = fake_team
        result = simulate_pvp(
            team1_chars, user.get("formation","standard"), user.get("sensei_id"),
            opp_team_chars, opp.get("formation","standard"), opp.get("sensei_id"),
        )
        opp = opp  # referenced below

    won = result["winner"] == 1
    await update_pvp_score(user_id, won=won)
    if won and isinstance(opp_name_display, str) and opponents:
        await update_pvp_score(opponents[0]["user_id"] if opponents else user_id, won=False)

    # Track event progress
    if won:
        await increment_event_progress(user_id, "chunin_exams")

    result_emoji = "🏆 Victory!" if won else "💔 Defeat!"
    pts = "+10 pts" if won else "-2 pts"

    log_text = "\n".join(result["log"][:3])
    kb = [
        [InlineKeyboardButton("⚔️ Fight Again", callback_data="pvp_fight"),
         InlineKeyboardButton("📊 Leaderboard", callback_data="pvp_lb_week")],
        [InlineKeyboardButton("🔙 Back",         callback_data="nav_pvp")],
    ]
    await query.edit_message_text(
        f"⚔️ *PvP Battle vs {opp_name_display}*\n\n"
        f"{log_text}\n\n"
        f"{result_emoji} {pts}\n"
        f"Your HP: {result['team1_hp']} | Opp HP: {result['team2_hp']}",
        reply_markup=InlineKeyboardMarkup(kb),
        parse_mode="Markdown",
    )


async def pvp_lb_week_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    user = await get_user(user_id)
    if not user:
        return

    lb = await get_weekly_leaderboard(user["world"], limit=10)
    lines = ["🏆 *Weekly PvP Leaderboard*\n"]
    medals = ["🥇","🥈","🥉","4️⃣","5️⃣","6️⃣","7️⃣","8️⃣","9️⃣","🔟"]
    for i, entry in enumerate(lb):
        medal = medals[i] if i < len(medals) else f"{i+1}."
        lines.append(f"{medal} {entry.get('username','?')} — {entry.get('weekly_pvp_score',0)} pts")

    kb = [
        [InlineKeyboardButton("📅 Monthly",   callback_data="pvp_lb_month"),
         InlineKeyboardButton("🔙 Back",      callback_data="nav_pvp")],
    ]
    await query.edit_message_text(
        "\n".join(lines) or "No players yet!",
        reply_markup=InlineKeyboardMarkup(kb),
        parse_mode="Markdown",
    )


async def pvp_lb_month_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    user = await get_user(user_id)
    if not user:
        return

    lb = await get_monthly_leaderboard(user["world"], limit=10)
    lines = ["📅 *Monthly PvP Leaderboard*\n"]
    medals = ["🥇","🥈","🥉","4️⃣","5️⃣","6️⃣","7️⃣","8️⃣","9️⃣","🔟"]
    for i, entry in enumerate(lb):
        medal = medals[i] if i < len(medals) else f"{i+1}."
        lines.append(f"{medal} {entry.get('username','?')} — {entry.get('monthly_pvp_score',0)} pts")

    kb = [
        [InlineKeyboardButton("📊 Weekly",  callback_data="pvp_lb_week"),
         InlineKeyboardButton("🔙 Back",    callback_data="nav_pvp")],
    ]
    await query.edit_message_text(
        "\n".join(lines) or "No players yet!",
        reply_markup=InlineKeyboardMarkup(kb),
        parse_mode="Markdown",
    )


async def leaderboard_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = await get_user(user_id)
    if not user:
        await update.message.reply_text("Register first! /start")
        return
    lb = await get_weekly_leaderboard(user["world"], limit=10)
    lines = ["🏆 *Weekly PvP Leaderboard*\n"]
    medals = ["🥇","🥈","🥉","4️⃣","5️⃣","6️⃣","7️⃣","8️⃣","9️⃣","🔟"]
    for i, entry in enumerate(lb):
        medal = medals[i] if i < len(medals) else f"{i+1}."
        lines.append(f"{medal} {entry.get('username','?')} — {entry.get('weekly_pvp_score',0)}")
    kb = [[InlineKeyboardButton("🔙 Main Menu", callback_data="nav_main")]]
    await update.message.reply_text(
        "\n".join(lines) or "No players yet!",
        reply_markup=InlineKeyboardMarkup(kb),
        parse_mode="Markdown",
    )


def register(app):
    app.add_handler(CommandHandler("pvp",         pvp_command))
    app.add_handler(CommandHandler("leaderboard", leaderboard_command))
    app.add_handler(CallbackQueryHandler(show_pvp,           pattern="^nav_pvp$"))
    app.add_handler(CallbackQueryHandler(pvp_fight_callback, pattern="^pvp_fight$"))
    app.add_handler(CallbackQueryHandler(pvp_lb_week_callback,  pattern="^pvp_lb_week$"))
    app.add_handler(CallbackQueryHandler(pvp_lb_month_callback, pattern="^pvp_lb_month$"))
