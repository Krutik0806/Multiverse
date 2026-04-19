"""
/profile and /inventory handlers — rich card-style UI.
"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler
from database.mongo import get_user, get_user_chars
from game.characters import get_char, rarity_label, get_char_stats
from game.progression import xp_for_level
from game.battle import calc_team_power
from handlers.utils import safe_edit, fmt, power_bar, stamina_bar, xp_progress_bar, WORLD_HEADER, RANK_BADGE, RARITY_BADGE

CHARS_PER_PAGE = 6


def _build_profile_card(user: dict, team_power: float) -> str:
    world = user["world"]
    c = user["currencies"]
    wh = WORLD_HEADER[world]
    rank = user.get("rank", "?")
    rb = RANK_BADGE.get(rank, rank)
    lvl = user["level"]
    xp = user["xp"]
    xp_need = xp_for_level(lvl + 1)
    xp_bar = xp_progress_bar(xp, xp_need)
    stam = user["stamina"]
    s_bar = stamina_bar(stam)
    pw_bar = power_bar(team_power, 2000)

    if world == "naruto":
        curr1 = f"🪙 Ryo:           {fmt(c.get('ryo', 0))}"
        curr2 = f"🔷 Chakra Crystals: {fmt(c.get('chakra_crystals', 0))}"
    else:
        curr1 = f"💴 Maria Gold:    {fmt(c.get('maria_gold', 0))}"
        curr2 = f"🏅 Exp. Medals:   {fmt(c.get('expedition_medals', 0))}"

    pvp_w = user.get("pvp_wins", 0)
    pvp_l = user.get("pvp_losses", 0)
    streak = user.get("daily_streak", 0)
    weekly = user.get("weekly_pvp_score", 0)

    return (
        f"━━━━━ {wh} ━━━━━\n"
        f"👤 *{user['username']}*\n"
        f"⚡ {rb}  │  Level {lvl}\n"
        f"\n"
        f"📈 XP  {xp_bar}  {fmt(xp)}/{fmt(xp_need)}\n"
        f"💚 Stamina  {s_bar}  {stam}/100\n"
        f"\n"
        f"━━━━━ Currencies ━━━━━\n"
        f"{curr1}\n"
        f"{curr2}\n"
        f"💎 World Gems:    {fmt(c.get('world_gems', 0))}\n"
        f"🔩 Scraps:        {fmt(c.get('scraps', 0))}\n"
        f"\n"
        f"━━━━━ Combat ━━━━━\n"
        f"⚔️ Team Power  {pw_bar}  {fmt(team_power)}\n"
        f"🏆 PvP  {pvp_w}W / {pvp_l}L  │  Score: {weekly}\n"
        f"🔥 Daily Streak: {streak} days"
    )


async def show_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = update.effective_user.id
    user = await get_user(user_id)
    if not user:
        await query.answer("Register first! /start", show_alert=True)
        return

    team_chars = [(get_char(cid), 1) for cid in user.get("team", []) if get_char(cid)]
    team_power = calc_team_power(team_chars, user.get("formation", "standard"), user.get("sensei_id")) if team_chars else 0

    kb = [
        [InlineKeyboardButton("📦 Inventory", callback_data="nav_inventory"),
         InlineKeyboardButton("👥 Team",      callback_data="nav_team"),
         InlineKeyboardButton("📅 Daily",     callback_data="nav_daily")],
        [InlineKeyboardButton("🔙 Main Menu", callback_data="nav_main")],
    ]
    await safe_edit(query, _build_profile_card(user, team_power), InlineKeyboardMarkup(kb))


async def profile_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = await get_user(user_id)
    if not user:
        await update.message.reply_text("Register first! /start")
        return
    team_chars = [(get_char(cid), 1) for cid in user.get("team", []) if get_char(cid)]
    team_power = calc_team_power(team_chars, user.get("formation", "standard"), user.get("sensei_id")) if team_chars else 0
    kb = [
        [InlineKeyboardButton("📦 Inventory", callback_data="nav_inventory"),
         InlineKeyboardButton("👥 Team",      callback_data="nav_team")],
        [InlineKeyboardButton("🔙 Main Menu", callback_data="nav_main")],
    ]
    await update.message.reply_text(
        _build_profile_card(user, team_power),
        reply_markup=InlineKeyboardMarkup(kb),
        parse_mode="Markdown",
    )


# ── Inventory ──────────────────────────────────────────────────────────────────
async def show_inventory(update: Update, context: ContextTypes.DEFAULT_TYPE, page: int = 0):
    query = update.callback_query
    user_id = update.effective_user.id
    chars = await get_user_chars(user_id)
    user  = await get_user(user_id)
    world = user["world"] if user else "naruto"

    if not chars:
        kb = [[InlineKeyboardButton("🎴 Pull Gacha", callback_data="nav_gacha"),
               InlineKeyboardButton("🔙 Back",       callback_data="nav_profile")]]
        await safe_edit(
            query,
            "📦 *Inventory is empty!*\n\nPull characters via 🎴 Gacha to fill it.",
            InlineKeyboardMarkup(kb),
        )
        return

    total = len(chars)
    pages = (total - 1) // CHARS_PER_PAGE + 1
    page = max(0, min(page, pages - 1))
    start = page * CHARS_PER_PAGE
    page_chars = chars[start:start + CHARS_PER_PAGE]

    lines = [
        f"━━━━━ 📦 Inventory ━━━━━",
        f"Total: {total} characters  │  Page {page + 1}/{pages}",
        "",
    ]
    for i, owned in enumerate(page_chars, start=1):
        cd = get_char(owned["char_id"])
        if not cd:
            continue
        stars = "⭐" * owned.get("stars", 1)
        badge = RARITY_BADGE.get(cd["rarity"], cd["rarity"])
        lines.append(f"{start + i}. {badge} *{cd['name']}* {stars}")

    # Character view buttons
    char_buttons = []
    for i, owned in enumerate(page_chars):
        cd = get_char(owned["char_id"])
        if cd:
            char_buttons.append(InlineKeyboardButton(
                cd["name"][:15], callback_data=f"inv_c_{start + i}"
            ))
    kb = [char_buttons[j:j+3] for j in range(0, len(char_buttons), 3)]

    # Navigation
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("◀ Prev", callback_data=f"inv_p_{page - 1}"))
    if start + CHARS_PER_PAGE < total:
        nav.append(InlineKeyboardButton("Next ▶", callback_data=f"inv_p_{page + 1}"))
    if nav:
        kb.append(nav)
    kb.append([InlineKeyboardButton("🔙 Profile", callback_data="nav_profile")])

    await safe_edit(query, "\n".join(lines), InlineKeyboardMarkup(kb))


async def inventory_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data.startswith("inv_p_"):
        page = int(data.split("_")[2])
        await show_inventory(update, context, page=page)

    elif data.startswith("inv_c_"):
        idx = int(data.split("_")[2])
        user_id = update.effective_user.id
        chars = await get_user_chars(user_id)
        if idx >= len(chars):
            await query.answer("Not found!", show_alert=True)
            return
        owned = chars[idx]
        cd = get_char(owned["char_id"])
        if not cd:
            await query.answer("Data error!", show_alert=True)
            return

        stars = owned.get("stars", 1)
        atk, def_, spd = get_char_stats(cd, stars)
        star_str = "⭐" * stars
        dupes_to_next = 3 - owned.get("duplicates", 0)
        badge = RARITY_BADGE.get(cd["rarity"], cd["rarity"])

        caption = (
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"{badge} *{cd['name']}* {star_str}\n"
            f"━━━━━━━━━━━━━━━━━━━\n\n"
            f"⚔️ ATK: *{atk}*  │  🛡️ DEF: *{def_}*  │  💨 SPD: *{spd}*\n\n"
            f"✨ *{cd['ability']}*\n\n"
            f"{'🔩 Dupes to next ⭐: ' + str(dupes_to_next) if stars < 5 else '🌟 MAX STARS!'}"
        )
        kb = [[InlineKeyboardButton("🔙 Inventory", callback_data=f"inv_p_{idx // CHARS_PER_PAGE}")]]

        try:
            await context.bot.send_photo(
                chat_id=update.effective_chat.id,
                photo=cd["img"],
                caption=caption,
                reply_markup=InlineKeyboardMarkup(kb),
                parse_mode="Markdown",
            )
        except Exception:
            await safe_edit(query, caption, InlineKeyboardMarkup(kb))


async def inventory_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chars = await get_user_chars(user_id)
    if not chars:
        await update.message.reply_text("📦 Inventory empty! Pull with /gacha first.")
        return
    total = len(chars)
    page_chars = chars[:CHARS_PER_PAGE]
    lines = [f"━━━━━ 📦 Inventory ({total} chars) ━━━━━\n"]
    for i, owned in enumerate(page_chars, 1):
        cd = get_char(owned["char_id"])
        if cd:
            badge = RARITY_BADGE.get(cd["rarity"], cd["rarity"])
            stars = "⭐" * owned.get("stars", 1)
            lines.append(f"{i}. {badge} *{cd['name']}* {stars}")
    char_buttons = [InlineKeyboardButton(
        get_char(o["char_id"])["name"][:14] if get_char(o["char_id"]) else "?",
        callback_data=f"inv_c_{i}"
    ) for i, o in enumerate(page_chars) if get_char(o["char_id"])]
    kb = [char_buttons[j:j+3] for j in range(0, len(char_buttons), 3)]
    if total > CHARS_PER_PAGE:
        kb.append([InlineKeyboardButton("Next ▶", callback_data="inv_p_1")])
    kb.append([InlineKeyboardButton("🔙 Main Menu", callback_data="nav_main")])
    await update.message.reply_text(
        "\n".join(lines), reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown"
    )


def register(app):
    app.add_handler(CommandHandler("profile",   profile_command))
    app.add_handler(CommandHandler("inventory", inventory_command))
    app.add_handler(CallbackQueryHandler(show_profile,       pattern="^nav_profile$"))
    app.add_handler(CallbackQueryHandler(inventory_callback, pattern="^inv_"))
