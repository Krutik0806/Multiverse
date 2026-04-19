"""
/start and /help handlers.
Fixes:
- safe_edit used everywhere (no crash on photo messages)
- World Switch button added
- Starter character given on registration
- Rich main menu UI
"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler
from database.mongo import get_user, create_user, update_user, add_char_to_user
from handlers.utils import safe_edit, WORLD_HEADER, RANK_BADGE

STARTER_CHARS = {"naruto": "iruka", "aot": "marco"}


async def _give_starter(user_id: int, world: str):
    """Give a starter character and set them as the team."""
    char_id = STARTER_CHARS[world]
    await add_char_to_user(user_id, char_id)
    await update_user(user_id, {"team": [char_id]})


# ── /start ─────────────────────────────────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db_user = await get_user(user.id)

    if db_user:
        world = db_user["world"]
        wh = WORLD_HEADER[world]
        rank = db_user.get("rank", "Genin")
        rb = RANK_BADGE.get(rank, rank)
        lvl = db_user["level"]

        kb = [
            [InlineKeyboardButton("📊 Profile",   callback_data="nav_profile"),
             InlineKeyboardButton("⚔️ Mission",   callback_data="nav_mission"),
             InlineKeyboardButton("🎴 Gacha",     callback_data="nav_gacha")],
            [InlineKeyboardButton("👥 Team",      callback_data="nav_team"),
             InlineKeyboardButton("🏆 PvP",       callback_data="nav_pvp"),
             InlineKeyboardButton("📦 Inventory", callback_data="nav_inventory")],
            [InlineKeyboardButton("🛒 Shop",      callback_data="nav_shop"),
             InlineKeyboardButton("📅 Daily",     callback_data="nav_daily"),
             InlineKeyboardButton("🌐 Lobby",     callback_data="nav_worldlobby")],
            [InlineKeyboardButton("🤝 Trade",     callback_data="nav_trade"),
             InlineKeyboardButton("🎉 Events",    callback_data="nav_events"),
             InlineKeyboardButton("🔄 Switch",    callback_data="switch_world_prompt")],
        ]
        text = (
            f"🌌 *MultiVerse Anime Bot*\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"👤 *{user.first_name}*\n"
            f"🌍 {wh}\n"
            f"⚡ {rb}  │  Level {lvl}\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"_Choose an action below_ ▾"
        )
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
        return

    # New user
    kb = [
        [InlineKeyboardButton("🍃 Naruto World",       callback_data="world_naruto"),
         InlineKeyboardButton("⚔️ Attack on Titan",   callback_data="world_aot")],
    ]
    await update.message.reply_photo(
        photo="https://picsum.photos/seed/multiverse_banner/800/400",
        caption=(
            "🌌 *Welcome to MultiVerse Anime Bot!*\n"
            "━━━━━━━━━━━━━━━━━━━\n\n"
            "Two worlds. Two destinies.\n\n"
            "🍃 *Naruto World*\n"
            "   Earn Ryo • Climb from Genin to Kage\n\n"
            "⚔️ *Attack on Titan World*\n"
            "   Earn Maria Gold • Rise to Commander\n\n"
            "_Choose your world to begin!_"
        ),
        reply_markup=InlineKeyboardMarkup(kb),
        parse_mode="Markdown",
    )


async def world_select_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = update.effective_user
    world = "naruto" if query.data == "world_naruto" else "aot"

    existing = await get_user(user.id)
    if existing:
        await safe_edit(query, "Already registered! Use /start.", None)
        return

    db_user = await create_user(user.id, user.username or user.first_name, world)
    await _give_starter(user.id, world)  # Give starter character + team

    if world == "naruto":
        wh = "🍃 Naruto World"
        starter_name = "Iruka Umino"
        curr_line = "500 🪙 Ryo"
    else:
        wh = "⚔️ Attack on Titan"
        starter_name = "Marco Bott"
        curr_line = "500 💴 Maria Gold"

    kb = [
        [InlineKeyboardButton("⚔️ First Mission!", callback_data="nav_mission"),
         InlineKeyboardButton("📊 My Profile",     callback_data="nav_profile")],
    ]
    await safe_edit(
        query,
        f"🌌 *Welcome to {wh}!*\n"
        f"━━━━━━━━━━━━━━━━━━━\n\n"
        f"✅ Registration complete!\n\n"
        f"🎁 *Starter Package:*\n"
        f"   • {curr_line} (starting currency)\n"
        f"   • {starter_name} added to team\n"
        f"   • 100 Stamina (full)\n\n"
        f"💡 _Tip: Run D-Rank missions to earn more!_",
        InlineKeyboardMarkup(kb),
    )


# ── World Switch ───────────────────────────────────────────────────────────────
async def switch_world_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    user = await get_user(user_id)
    if not user:
        await query.answer("Register first!", show_alert=True)
        return

    cur = user["world"]
    new_w = "aot" if cur == "naruto" else "naruto"

    if new_w == "naruto":
        new_label = "🍃 Naruto World"
        note = "Missions & shop change to Naruto. Earn Ryo."
    else:
        new_label = "⚔️ Attack on Titan"
        note = "Missions & shop change to AoT. Earn Maria Gold."

    kb = [
        [InlineKeyboardButton(f"✅ Switch to {new_label}", callback_data=f"switch_confirm_{new_w}")],
        [InlineKeyboardButton("❌ Cancel", callback_data="nav_main")],
    ]
    await safe_edit(
        query,
        f"🔄 *Switch World?*\n"
        f"━━━━━━━━━━━━━━━━━━━\n\n"
        f"Current: {WORLD_HEADER[cur]}\n"
        f"Switch to: *{new_label}*\n\n"
        f"ℹ️ {note}\n"
        f"Your characters and currencies are *kept*.\n"
        f"Your team will be *cleared* (set a new one after).",
        InlineKeyboardMarkup(kb),
    )


async def switch_confirm_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    new_world = query.data.replace("switch_confirm_", "")

    from game.progression import rank_for_level
    user = await get_user(user_id)
    if not user:
        return

    new_rank = rank_for_level(user["level"], new_world)
    await update_user(user_id, {
        "world": new_world,
        "rank":  new_rank,
        "team":  [],           # clear team (chars from old world don't transfer)
        "sensei_id": None,
    })

    # Give world's starter char if not already owned
    await _give_starter(user_id, new_world)

    wh = WORLD_HEADER[new_world]
    curr = "Ryo" if new_world == "naruto" else "Maria Gold"
    kb = [[InlineKeyboardButton("🔙 Main Menu", callback_data="nav_main")]]
    await safe_edit(
        query,
        f"✅ *Switched to {wh}!*\n\n"
        f"New Rank: {new_rank}\n"
        f"Currency: {curr}\n\n"
        f"Your team was reset. Set up a new team in /team!",
        InlineKeyboardMarkup(kb),
    )


# ── Main menu from nav_main ────────────────────────────────────────────────────
async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = update.effective_user
    user_id = user.id
    db_user = await get_user(user_id)
    world = db_user["world"] if db_user else "naruto"
    wh = WORLD_HEADER[world]
    rank = db_user.get("rank", "?") if db_user else "?"
    lvl = db_user["level"] if db_user else 1

    kb = [
        [InlineKeyboardButton("📊 Profile",   callback_data="nav_profile"),
         InlineKeyboardButton("⚔️ Mission",   callback_data="nav_mission"),
         InlineKeyboardButton("🎴 Gacha",     callback_data="nav_gacha")],
        [InlineKeyboardButton("👥 Team",      callback_data="nav_team"),
         InlineKeyboardButton("🏆 PvP",       callback_data="nav_pvp"),
         InlineKeyboardButton("📦 Inventory", callback_data="nav_inventory")],
        [InlineKeyboardButton("🛒 Shop",      callback_data="nav_shop"),
         InlineKeyboardButton("📅 Daily",     callback_data="nav_daily"),
         InlineKeyboardButton("🌐 Lobby",     callback_data="nav_worldlobby")],
        [InlineKeyboardButton("🤝 Trade",     callback_data="nav_trade"),
         InlineKeyboardButton("🎉 Events",    callback_data="nav_events"),
         InlineKeyboardButton("🔄 Switch",    callback_data="switch_world_prompt")],
    ]
    text = (
        f"🌌 *MultiVerse Anime Bot*\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"👤 {user.first_name}  │  {wh}\n"
        f"⚡ {rank}  │  Level {lvl}\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"_Choose an action_ ▾"
    )
    await safe_edit(query, text, InlineKeyboardMarkup(kb))


# ── Navigation dispatcher ─────────────────────────────────────────────────────
async def nav_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data.replace("nav_", "")

    dispatch = {
        "profile":    ("handlers.profile", "show_profile"),
        "mission":    ("handlers.mission", "show_missions"),
        "gacha":      ("handlers.gacha",   "show_gacha"),
        "team":       ("handlers.team",    "show_team"),
        "pvp":        ("handlers.pvp",     "show_pvp"),
        "inventory":  ("handlers.profile", "show_inventory"),
        "shop":       ("handlers.shop",    "show_shop"),
        "daily":      ("handlers.daily",   "show_daily"),
        "worldlobby": ("handlers.events",  "show_world_lobby"),
        "trade":      ("handlers.trade",   "show_trade"),
        "events":     ("handlers.events",  "show_events"),
        "help":       (None,               None),
        "main":       (None,               None),
    }

    if data == "main":
        await show_main_menu(update, context)
        return
    if data == "help":
        await show_help(update, context)
        return

    entry = dispatch.get(data)
    if entry:
        module_name, func_name = entry
        import importlib
        mod = importlib.import_module(module_name)
        await getattr(mod, func_name)(update, context)


# ── /help ──────────────────────────────────────────────────────────────────────
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = _help_text()
    kb = [[InlineKeyboardButton("🔙 Menu", callback_data="nav_main")]]
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")


async def show_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    kb = [[InlineKeyboardButton("🔙 Menu", callback_data="nav_main")]]
    await safe_edit(query, _help_text(), InlineKeyboardMarkup(kb))


def _help_text() -> str:
    return (
        "❓ *MultiVerse Bot — Commands*\n"
        "━━━━━━━━━━━━━━━━━━━\n\n"
        "/start — Main menu & registration\n"
        "/profile — Your stats & rank\n"
        "/team — Manage your squad\n"
        "/mission — Go on missions\n"
        "/gacha — Pull characters\n"
        "/pvp — Battle other players\n"
        "/inventory — Your characters\n"
        "/shop — Buy items\n"
        "/daily — Claim daily reward\n"
        "/leaderboard — Weekly rankings\n"
        "/trade — Trade characters\n"
        "/coop — Co-op raids\n"
        "/event — Active events\n"
        "/worldlobby — Level 10+ hub\n"
        "/help — This message"
    )


def register(app):
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help",  help_command))
    app.add_handler(CallbackQueryHandler(world_select_callback,  pattern="^world_"))
    app.add_handler(CallbackQueryHandler(nav_callback,           pattern="^nav_"))
    app.add_handler(CallbackQueryHandler(switch_world_prompt,    pattern="^switch_world_prompt$"))
    app.add_handler(CallbackQueryHandler(switch_confirm_callback, pattern="^switch_confirm_"))
