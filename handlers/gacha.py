"""
/gacha handler — single pull, 10-pull, pity display. Characters sent as photos.
"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler
from database.mongo import get_user, get_pity
from database.redis_client import redis
from game.gacha_engine import single_pull, ten_pull
from game.characters import rarity_label, RARITY_COLORS
from config import GACHA_SINGLE_COST, GACHA_TEN_COST, PITY_THRESHOLD


RARITY_EMOJI = {
    "common":      "⬜",
    "rare":        "🟦",
    "epic":        "🟪",
    "legendary":   "🟧",
    "world_class": "🌟",
}


async def show_gacha(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = update.effective_user.id
    user = await get_user(user_id)

    if not user:
        await query.answer("Register first! /start", show_alert=True)
        return

    world = user["world"]
    currency = "ryo" if world == "naruto" else "maria_gold"
    curr_sym = "Ryo" if world == "naruto" else "Maria Gold"
    curr_amt = user["currencies"].get(currency, 0)
    pity = await get_pity(user_id)
    pity_bar = "⬛" * (pity // 5) + "░" * (10 - pity // 5)

    kb = [
        [InlineKeyboardButton(f"🎴 Single Pull ({GACHA_SINGLE_COST} {curr_sym})", callback_data="gacha_single")],
        [InlineKeyboardButton(f"🎰 10-Pull ({GACHA_TEN_COST} {curr_sym})",        callback_data="gacha_ten")],
        [InlineKeyboardButton("📊 My Pity",   callback_data="gacha_pity"),
         InlineKeyboardButton("🔙 Back",      callback_data="nav_main")],
    ]
    await query.edit_message_text(
        f"🎴 *Gacha Banner*\n\n"
        f"💰 Balance: {curr_amt:,} {curr_sym}\n"
        f"🎯 Pity: {pity}/{PITY_THRESHOLD} {pity_bar}\n\n"
        f"Rates: 🌟1% • 🟧4% • 🟪10% • 🟦30% • ⬜55%\n"
        f"_10-pull: pos 10 = Rare+ guaranteed_",
        reply_markup=InlineKeyboardMarkup(kb),
        parse_mode="Markdown",
    )


async def gacha_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = await get_user(user_id)
    if not user:
        await update.message.reply_text("Register first! /start")
        return
    world = user["world"]
    currency = "ryo" if world == "naruto" else "maria_gold"
    curr_sym = "Ryo" if world == "naruto" else "Maria Gold"
    curr_amt = user["currencies"].get(currency, 0)
    pity = await get_pity(user_id)
    kb = [
        [InlineKeyboardButton(f"🎴 Single ({GACHA_SINGLE_COST} {curr_sym})", callback_data="gacha_single")],
        [InlineKeyboardButton(f"🎰 10-Pull ({GACHA_TEN_COST} {curr_sym})",   callback_data="gacha_ten")],
        [InlineKeyboardButton("📊 Pity",     callback_data="gacha_pity"),
         InlineKeyboardButton("🔙 Menu",     callback_data="nav_main")],
    ]
    await update.message.reply_text(
        f"🎴 *Gacha Banner*\n💰 {curr_amt:,} {curr_sym} | 🎯 Pity: {pity}/{PITY_THRESHOLD}",
        reply_markup=InlineKeyboardMarkup(kb),
        parse_mode="Markdown",
    )


def _result_caption(result: dict) -> str:
    emoji = RARITY_EMOJI.get(result["rarity"], "⬜")
    pity_tag = " ✨PITY!" if result.get("is_pity") else ""
    dup_tag = f"\n🔩 Duplicate! +{result['scraps']} Scraps" if result["is_duplicate"] else "\n🆕 New character!"
    stars = "⭐" * result.get("stars", 1)
    return (
        f"{emoji} *{result['name']}* {stars}{pity_tag}\n"
        f"{rarity_label(result['rarity'])}{dup_tag}"
    )


async def _send_pull_result(update: Update, context: ContextTypes.DEFAULT_TYPE, result: dict):
    """Send a single pull result as a photo with caption."""
    if "error" in result:
        return result["error"]

    kb = [[
        InlineKeyboardButton("🎴 Pull Again", callback_data="gacha_single"),
        InlineKeyboardButton("🔙 Gacha",     callback_data="nav_gacha"),
    ]]
    caption = _result_caption(result)

    try:
        await context.bot.send_photo(
            chat_id=update.effective_chat.id,
            photo=result["img"],
            caption=caption,
            reply_markup=InlineKeyboardMarkup(kb),
            parse_mode="Markdown",
        )
    except Exception:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=caption,
            reply_markup=InlineKeyboardMarkup(kb),
            parse_mode="Markdown",
        )
    return None


async def gacha_single_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("🎴 Pulling...")
    user_id = update.effective_user.id

    # Rate limit
    if await redis.rate_limit(user_id, "gacha", window=5):
        await query.answer("⏳ Too fast!", show_alert=True)
        return

    result = await single_pull(user_id)
    err = await _send_pull_result(update, context, result)
    if err:
        await query.answer(err, show_alert=True)


async def gacha_ten_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("🎰 Pulling 10...")
    user_id = update.effective_user.id

    if await redis.rate_limit(user_id, "gacha10", window=10):
        await query.answer("⏳ Too fast!", show_alert=True)
        return

    results = await ten_pull(user_id)

    if results and "error" in results[0]:
        await query.answer(results[0]["error"], show_alert=True)
        return

    # Summary text for 10-pull
    summary_lines = ["🎰 *10-Pull Results:*\n"]
    for r in results:
        emoji = RARITY_EMOJI.get(r.get("rarity", "common"), "⬜")
        dup = " (dup)" if r.get("is_duplicate") else " ✨"
        summary_lines.append(f"{emoji} {r.get('name','?')}{dup}")

    # Send the best (highest rarity) result as photo
    rarity_order = ["world_class", "legendary", "epic", "rare", "common"]
    best = min(results, key=lambda r: rarity_order.index(r.get("rarity", "common")))

    kb = [[
        InlineKeyboardButton("🎰 10-Pull Again", callback_data="gacha_ten"),
        InlineKeyboardButton("🔙 Gacha",         callback_data="nav_gacha"),
    ]]
    try:
        await context.bot.send_photo(
            chat_id=update.effective_chat.id,
            photo=best["img"],
            caption="\n".join(summary_lines),
            reply_markup=InlineKeyboardMarkup(kb),
            parse_mode="Markdown",
        )
    except Exception:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="\n".join(summary_lines),
            reply_markup=InlineKeyboardMarkup(kb),
            parse_mode="Markdown",
        )


async def gacha_pity_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    pity = await get_pity(user_id)
    remaining = PITY_THRESHOLD - pity
    bar = "🟧" * (pity // 5) + "░" * (10 - pity // 5)
    kb = [[InlineKeyboardButton("🔙 Gacha", callback_data="nav_gacha")]]
    await query.edit_message_text(
        f"🎯 *Pity Counter*\n\n"
        f"{bar}\n"
        f"Pulls: {pity}/{PITY_THRESHOLD}\n"
        f"Guaranteed Legendary in {remaining} pull(s)!",
        reply_markup=InlineKeyboardMarkup(kb),
        parse_mode="Markdown",
    )


def register(app):
    app.add_handler(CommandHandler("gacha", gacha_command))
    app.add_handler(CallbackQueryHandler(show_gacha,          pattern="^nav_gacha$"))
    app.add_handler(CallbackQueryHandler(gacha_single_callback, pattern="^gacha_single$"))
    app.add_handler(CallbackQueryHandler(gacha_ten_callback,    pattern="^gacha_ten$"))
    app.add_handler(CallbackQueryHandler(gacha_pity_callback,   pattern="^gacha_pity$"))
