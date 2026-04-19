"""
/event and /worldlobby handlers — active events, World Lobby (Level 10+).
"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler
from database.mongo import (
    get_user, get_event_progress, ACTIVE_EVENTS, add_currency,
    update_user, get_shop_items, subtract_currency,
)
from game.progression import can_access_world_lobby, WORLD_LOBBY_LEVEL
from game.gacha_engine import single_pull
from game.characters import rarity_label
from config import GACHA_SINGLE_COST


# ── Events ─────────────────────────────────────────────────────────────────────
async def show_events(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = update.effective_user.id
    user = await get_user(user_id)

    if not user:
        await query.answer("Register first! /start", show_alert=True)
        return

    world = user["world"]
    lines = ["🎉 *Active Events*\n"]

    rows = []
    for i, event in enumerate(ACTIVE_EVENTS):
        if event["world"] not in ("all", world):
            continue
        prog = await get_event_progress(user_id, event["id"])
        goal = event["goal"]
        pct = min(100, int(prog / goal * 100))
        bar = "🟩" * (pct // 10) + "⬜" * (10 - pct // 10)
        status = "✅ Complete!" if prog >= goal else f"{prog}/{goal}"
        lines.append(f"{event['name']}\n{bar} {status}\n{event['description'][:50]}\n")
        rows.append([InlineKeyboardButton(event["name"][:20], callback_data=f"event_view_{i}")])

    rows.append([InlineKeyboardButton("🔙 Back", callback_data="nav_main")])
    await query.edit_message_text(
        "\n".join(lines),
        reply_markup=InlineKeyboardMarkup(rows),
        parse_mode="Markdown",
    )


async def event_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = await get_user(user_id)
    if not user:
        await update.message.reply_text("Register first! /start")
        return
    world = user["world"]
    lines = ["🎉 *Active Events*\n"]
    rows = []
    for i, event in enumerate(ACTIVE_EVENTS):
        if event["world"] not in ("all", world):
            continue
        prog = await get_event_progress(user_id, event["id"])
        goal = event["goal"]
        status = "✅" if prog >= goal else f"{prog}/{goal}"
        lines.append(f"• {event['name']}: {status}")
        rows.append([InlineKeyboardButton(event["name"][:20], callback_data=f"event_view_{i}")])
    rows.append([InlineKeyboardButton("🔙 Main Menu", callback_data="nav_main")])
    await update.message.reply_text(
        "\n".join(lines),
        reply_markup=InlineKeyboardMarkup(rows),
        parse_mode="Markdown",
    )


async def event_view_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    idx = int(query.data.split("_")[2])

    if idx >= len(ACTIVE_EVENTS):
        await query.answer("Event not found!", show_alert=True)
        return

    event = ACTIVE_EVENTS[idx]
    prog = await get_event_progress(user_id, event["id"])
    goal = event["goal"]
    completed = prog >= goal
    bar_len = 10
    filled = min(bar_len, int(bar_len * prog / goal))
    bar = "🟩" * filled + "⬜" * (bar_len - filled)

    reward_sym = event["reward_currency"].replace("_", " ").title()

    kb = []
    if completed:
        kb.append([InlineKeyboardButton("🎁 Claim Reward", callback_data=f"event_claim_{idx}")])
    kb.append([InlineKeyboardButton("🔙 Events", callback_data="nav_events")])

    await query.edit_message_text(
        f"{event['name']}\n\n"
        f"📋 {event['description']}\n\n"
        f"Progress: {bar} {prog}/{goal}\n"
        f"🎁 Reward: {event['reward_amount']} {reward_sym}\n"
        f"{'✅ COMPLETE! Claim below.' if completed else '🔄 Keep going!'}",
        reply_markup=InlineKeyboardMarkup(kb),
        parse_mode="Markdown",
    )


async def event_claim_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    idx = int(query.data.split("_")[2])

    if idx >= len(ACTIVE_EVENTS):
        return

    event = ACTIVE_EVENTS[idx]
    prog = await get_event_progress(user_id, event["id"])

    if prog < event["goal"]:
        await query.answer("Event not complete yet!", show_alert=True)
        return

    # Check if already claimed (use a flag in event_progress)
    claim_key = f"{event['id']}_claimed"
    user = await get_user(user_id)
    if user.get("event_progress", {}).get(claim_key):
        await query.answer("Already claimed!", show_alert=True)
        return

    await add_currency(user_id, event["reward_currency"], event["reward_amount"])
    await update_user(user_id, {f"event_progress.{claim_key}": True})

    reward_sym = event["reward_currency"].replace("_", " ").title()
    kb = [[InlineKeyboardButton("🔙 Events", callback_data="nav_events")]]
    await query.edit_message_text(
        f"🎉 *Reward Claimed!*\n\n"
        f"{event['name']}\n"
        f"💰 +{event['reward_amount']} {reward_sym}!",
        reply_markup=InlineKeyboardMarkup(kb),
        parse_mode="Markdown",
    )


# ── World Lobby ────────────────────────────────────────────────────────────────
async def show_world_lobby(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = update.effective_user.id
    user = await get_user(user_id)

    if not user:
        await query.answer("Register first! /start", show_alert=True)
        return

    if not can_access_world_lobby(user["level"]):
        await query.answer(
            f"🔒 World Lobby unlocks at Level {WORLD_LOBBY_LEVEL}! (You: Lv.{user['level']})",
            show_alert=True,
        )
        return

    gems = user["currencies"].get("world_gems", 0)
    kb = [
        [InlineKeyboardButton("🌟 World Gacha (5 Gems)", callback_data="wl_gacha")],
        [InlineKeyboardButton("⚔️ Cross-World PvP",      callback_data="wl_pvp")],
        [InlineKeyboardButton("🛒 World Shop",            callback_data="wl_shop")],
        [InlineKeyboardButton("🔙 Back",                  callback_data="nav_main")],
    ]
    await query.edit_message_text(
        f"🌐 *World Lobby*\n\n"
        f"💎 World Gems: {gems}\n\n"
        "Cross-anime PvP, exclusive characters, and World Gem gacha!\n"
        "_Only the strongest shinobi and scouts reach here._",
        reply_markup=InlineKeyboardMarkup(kb),
        parse_mode="Markdown",
    )


async def wl_gacha_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("🌟 Pulling World Gacha...")
    user_id = update.effective_user.id
    user = await get_user(user_id)

    if not user or not can_access_world_lobby(user["level"]):
        await query.answer("Not eligible!", show_alert=True)
        return

    if not await subtract_currency(user_id, "world_gems", 5):
        await query.answer("Need 5 World Gems!", show_alert=True)
        return

    # World gacha: always Rare+ from ALL characters (both worlds combined)
    import random
    from game.characters import ALL_CHARACTERS
    rarities = ["rare", "epic", "legendary", "world_class"]
    weights = [0.50, 0.30, 0.15, 0.05]
    chosen_rarity = random.choices(rarities, weights=weights, k=1)[0]
    pool = [c for c in ALL_CHARACTERS if c["rarity"] == chosen_rarity]
    if not pool:
        pool = ALL_CHARACTERS
    char = random.choice(pool)

    from database.mongo import add_char_to_user
    result = await add_char_to_user(user_id, char["id"])

    from game.characters import rarity_label
    kb = [[
        InlineKeyboardButton("🌟 Pull Again", callback_data="wl_gacha"),
        InlineKeyboardButton("🔙 Lobby",      callback_data="nav_worldlobby"),
    ]]
    caption = (
        f"🌟 *World Gacha Pull!*\n\n"
        f"{rarity_label(char['rarity'])} *{char['name']}*\n"
        f"World: {'🍃 Naruto' if char['world'] == 'naruto' else '⚔️ AoT'}\n"
        f"{'🔩 Duplicate! Scraps added.' if result['is_duplicate'] else '✨ New character!'}"
    )
    try:
        await context.bot.send_photo(
            chat_id=update.effective_chat.id,
            photo=char["img"],
            caption=caption,
            reply_markup=InlineKeyboardMarkup(kb),
            parse_mode="Markdown",
        )
    except Exception:
        await query.edit_message_text(caption, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")


async def wl_pvp_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "⚔️ *Cross-World PvP*\nComing soon! Top ranked play across both worlds.",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="nav_worldlobby")]]),
        parse_mode="Markdown",
    )


async def wl_shop_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    items = get_shop_items("naruto", is_world_lobby=True)
    user_id = update.effective_user.id
    user = await get_user(user_id)
    gems = user["currencies"].get("world_gems", 0) if user else 0
    rows = []
    for item in items:
        rows.append([InlineKeyboardButton(
            f"{item['name'][:12]} — {item['cost']} Gems",
            callback_data=f"shop_buy_{item['id']}"
        )])
    rows.append([InlineKeyboardButton("🔙 Lobby", callback_data="nav_worldlobby")])
    await query.edit_message_text(
        f"🌐 *World Shop*\n💎 {gems} World Gems\n\n_Cross-anime exclusive items:_",
        reply_markup=InlineKeyboardMarkup(rows),
        parse_mode="Markdown",
    )


async def worldlobby_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = await get_user(user_id)
    if not user:
        await update.message.reply_text("Register first! /start")
        return
    if not can_access_world_lobby(user["level"]):
        await update.message.reply_text(
            f"🔒 World Lobby unlocks at Level {WORLD_LOBBY_LEVEL}! (You: Lv.{user['level']})"
        )
        return
    gems = user["currencies"].get("world_gems", 0)
    kb = [
        [InlineKeyboardButton("🌟 World Gacha",    callback_data="wl_gacha")],
        [InlineKeyboardButton("⚔️ Cross-World PvP", callback_data="wl_pvp")],
        [InlineKeyboardButton("🛒 World Shop",      callback_data="wl_shop")],
        [InlineKeyboardButton("🔙 Main Menu",       callback_data="nav_main")],
    ]
    await update.message.reply_text(
        f"🌐 *World Lobby*\n💎 {gems} World Gems",
        reply_markup=InlineKeyboardMarkup(kb),
        parse_mode="Markdown",
    )


def register(app):
    app.add_handler(CommandHandler("event",      event_command))
    app.add_handler(CommandHandler("worldlobby", worldlobby_command))
    app.add_handler(CallbackQueryHandler(show_events,         pattern="^nav_events$"))
    app.add_handler(CallbackQueryHandler(event_view_callback, pattern="^event_view_"))
    app.add_handler(CallbackQueryHandler(event_claim_callback, pattern="^event_claim_"))
    app.add_handler(CallbackQueryHandler(show_world_lobby,    pattern="^nav_worldlobby$"))
    app.add_handler(CallbackQueryHandler(wl_gacha_callback,   pattern="^wl_gacha$"))
    app.add_handler(CallbackQueryHandler(wl_pvp_callback,     pattern="^wl_pvp$"))
    app.add_handler(CallbackQueryHandler(wl_shop_callback,    pattern="^wl_shop$"))
