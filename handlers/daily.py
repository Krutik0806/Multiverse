"""
/daily reward handler — streak tracking, milestone bonuses.
"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler
from database.mongo import get_user, claim_daily
from game.progression import stamina_bar


async def show_daily(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = update.effective_user.id
    user = await get_user(user_id)

    if not user:
        await query.answer("Register first! /start", show_alert=True)
        return

    world = user["world"]
    streak = user.get("daily_streak", 0)
    currency = "ryo" if world == "naruto" else "maria_gold"
    curr_sym = "Ryo" if world == "naruto" else "Maria Gold"
    next_7 = 7 - (streak % 7) if streak % 7 != 0 else 7
    next_30 = 30 - (streak % 30) if streak % 30 != 0 else 30

    kb = [
        [InlineKeyboardButton("🌅 Claim Daily!", callback_data="daily_claim")],
        [InlineKeyboardButton("🔙 Back", callback_data="nav_main")],
    ]
    await query.edit_message_text(
        f"📅 *Daily Rewards*\n\n"
        f"🔥 Current Streak: {streak} days\n"
        f"📈 Base reward: {200 + streak * 10} {curr_sym}\n"
        f"🎁 Day 7 milestone in: {next_7} days (+700)\n"
        f"💎 Day 30 milestone in: {next_30} days (+2000)\n\n"
        "_Claim once per day. Miss a day, streak resets!_",
        reply_markup=InlineKeyboardMarkup(kb),
        parse_mode="Markdown",
    )


async def daily_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = await get_user(user_id)
    if not user:
        await update.message.reply_text("Register first! /start")
        return
    world = user["world"]
    streak = user.get("daily_streak", 0)
    curr_sym = "Ryo" if world == "naruto" else "Maria Gold"
    kb = [
        [InlineKeyboardButton("🌅 Claim Daily!", callback_data="daily_claim")],
        [InlineKeyboardButton("🔙 Main Menu",    callback_data="nav_main")],
    ]
    await update.message.reply_text(
        f"📅 *Daily Rewards* — Streak: {streak} days\nBase: {200 + streak * 10} {curr_sym}",
        reply_markup=InlineKeyboardMarkup(kb),
        parse_mode="Markdown",
    )


async def daily_claim_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    result = await claim_daily(user_id)

    kb = [[InlineKeyboardButton("🔙 Back", callback_data="nav_main")]]

    if result is None:
        await query.edit_message_text(
            "📅 *Already claimed today!*\nCome back tomorrow to keep your streak!",
            reply_markup=InlineKeyboardMarkup(kb),
            parse_mode="Markdown",
        )
        return

    curr_sym = "Ryo" if result["currency"] == "ryo" else "Maria Gold"
    bonus_line = f"\n🎉 *Milestone bonus!* +{result['amount'] - 200 - result['streak']*10}" if result.get("bonus") else ""
    await query.edit_message_text(
        f"🌅 *Daily Claimed!*\n\n"
        f"💰 +{result['amount']:,} {curr_sym}\n"
        f"🔥 Streak: {result['streak']} days!{bonus_line}\n\n"
        "_See you tomorrow!_",
        reply_markup=InlineKeyboardMarkup(kb),
        parse_mode="Markdown",
    )


def register(app):
    app.add_handler(CommandHandler("daily", daily_command))
    app.add_handler(CallbackQueryHandler(show_daily,         pattern="^nav_daily$"))
    app.add_handler(CallbackQueryHandler(daily_claim_callback, pattern="^daily_claim$"))
