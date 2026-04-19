"""
/team handler — view team, add/remove characters, set formation, set sensei.
"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler
from database.mongo import get_user, get_user_chars, set_team, set_formation
from game.characters import get_char, rarity_label, get_char_stats
from game.battle import calc_team_power, FORMATION_MULTIPLIERS

MAX_TEAM = {"naruto": 4, "aot": 3}

FORMATIONS = [
    ("standard",  "⚖️ Standard",  "×1.0"),
    ("offensive", "⚔️ Offensive", "×1.15"),
    ("defensive", "🛡️ Defensive", "×1.10"),
    ("balanced",  "💫 Balanced",  "×1.05"),
]


def _team_text(user: dict, team_chars: list) -> str:
    world = user["world"]
    max_t = MAX_TEAM[world]
    formation = user.get("formation", "standard")
    sensei_id = user.get("sensei_id")
    sensei_char = get_char(sensei_id) if sensei_id else None

    power = calc_team_power([(cd, 1) for cd in team_chars], formation, sensei_id) if team_chars else 0

    lines = [
        f"👥 *Your Team* ({len(team_chars)}/{max_t})\n",
        f"⚖️ Formation: {formation.title()} • Power: {int(power)}\n",
    ]
    if sensei_char:
        lines.append(f"🧑‍🏫 Sensei: {sensei_char['name']} (+{int(sensei_char.get('ability_value',0)*100)}% bonus)")
    for i, cd in enumerate(team_chars, 1):
        atk, deff, spd = get_char_stats(cd, 1)
        lines.append(f"{i}. {cd['name']} | ATK {atk} DEF {deff} SPD {spd}")
    return "\n".join(lines)


async def show_team(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = update.effective_user.id
    user = await get_user(user_id)

    if not user:
        await query.answer("Register first!", show_alert=True)
        return

    team_ids = user.get("team", [])
    team_chars = [get_char(cid) for cid in team_ids if get_char(cid)]

    kb = [
        [InlineKeyboardButton("➕ Add Member",   callback_data="team_add"),
         InlineKeyboardButton("➖ Remove",       callback_data="team_remove")],
        [InlineKeyboardButton("🎖️ Formation",   callback_data="team_formation"),
         InlineKeyboardButton("🧑‍🏫 Sensei",    callback_data="team_sensei")],
        [InlineKeyboardButton("🔙 Back",         callback_data="nav_profile")],
    ]
    await query.edit_message_text(
        _team_text(user, team_chars),
        reply_markup=InlineKeyboardMarkup(kb),
        parse_mode="Markdown",
    )


async def team_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = await get_user(user_id)
    if not user:
        await update.message.reply_text("Register first! /start")
        return
    team_ids = user.get("team", [])
    team_chars = [get_char(cid) for cid in team_ids if get_char(cid)]
    kb = [
        [InlineKeyboardButton("➕ Add Member",  callback_data="team_add"),
         InlineKeyboardButton("➖ Remove",      callback_data="team_remove")],
        [InlineKeyboardButton("🎖️ Formation",  callback_data="team_formation"),
         InlineKeyboardButton("🧑‍🏫 Sensei",   callback_data="team_sensei")],
        [InlineKeyboardButton("🔙 Main Menu",   callback_data="nav_main")],
    ]
    await update.message.reply_text(
        _team_text(user, team_chars),
        reply_markup=InlineKeyboardMarkup(kb),
        parse_mode="Markdown",
    )


# ── Add member — show inventory to pick ──────────────────────────────────────
async def team_add_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    user = await get_user(user_id)
    chars = await get_user_chars(user_id)

    if not chars:
        await query.answer("No characters! Pull via /gacha.", show_alert=True)
        return

    max_t = MAX_TEAM[user["world"]]
    if len(user.get("team", [])) >= max_t:
        await query.answer(f"Team full! Max {max_t} members.", show_alert=True)
        return

    # Show first 9 chars for selection
    rows = []
    for i, owned in enumerate(chars[:9]):
        cd = get_char(owned["char_id"])
        if cd and cd["id"] not in user.get("team", []):
            rows.append(InlineKeyboardButton(cd["name"][:15], callback_data=f"team_pick_{cd['id']}"))
    chunked = [rows[j:j+3] for j in range(0, len(rows), 3)]
    chunked.append([InlineKeyboardButton("🔙 Back", callback_data="nav_team")])
    await query.edit_message_text(
        "👥 *Select a character to add:*",
        reply_markup=InlineKeyboardMarkup(chunked),
        parse_mode="Markdown",
    )


async def team_pick_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    char_id = query.data.split("_")[2]

    user = await get_user(user_id)
    team = user.get("team", [])
    max_t = MAX_TEAM[user["world"]]

    if char_id in team:
        await query.answer("Already in team!", show_alert=True)
        return
    if len(team) >= max_t:
        await query.answer(f"Team full! Max {max_t}.", show_alert=True)
        return

    team.append(char_id)
    await set_team(user_id, team, user.get("sensei_id"))
    cd = get_char(char_id)
    await query.answer(f"✅ {cd['name']} added!")
    await show_team(update, context)


# ── Remove member ─────────────────────────────────────────────────────────────
async def team_remove_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    user = await get_user(user_id)
    team = user.get("team", [])

    if not team:
        await query.answer("Team is empty!", show_alert=True)
        return

    rows = []
    for cid in team:
        cd = get_char(cid)
        if cd:
            rows.append(InlineKeyboardButton(f"❌ {cd['name'][:12]}", callback_data=f"team_rem_{cid}"))
    chunked = [rows[j:j+3] for j in range(0, len(rows), 3)]
    chunked.append([InlineKeyboardButton("🔙 Back", callback_data="nav_team")])
    await query.edit_message_text(
        "👥 *Remove a team member:*",
        reply_markup=InlineKeyboardMarkup(chunked),
        parse_mode="Markdown",
    )


async def team_rem_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    char_id = query.data.split("_")[2]
    user = await get_user(user_id)
    team = [c for c in user.get("team", []) if c != char_id]
    sensei = user.get("sensei_id")
    if sensei == char_id:
        sensei = None
    await set_team(user_id, team, sensei)
    cd = get_char(char_id)
    await query.answer(f"❌ {cd['name']} removed.")
    await show_team(update, context)


# ── Formation ─────────────────────────────────────────────────────────────────
async def team_formation_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    rows = []
    for key, label, mult in FORMATIONS:
        rows.append(InlineKeyboardButton(f"{label} {mult}", callback_data=f"form_set_{key}"))
    chunked = [rows[j:j+2] for j in range(0, len(rows), 2)]
    chunked.append([InlineKeyboardButton("🔙 Back", callback_data="nav_team")])
    await query.edit_message_text(
        "🎖️ *Choose Formation:*\n\nFormation affects total Team Power.",
        reply_markup=InlineKeyboardMarkup(chunked),
        parse_mode="Markdown",
    )


async def form_set_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    formation = query.data.split("_")[2]
    user_id = update.effective_user.id
    await set_formation(user_id, formation)
    await query.answer(f"✅ Formation: {formation.title()}")
    await show_team(update, context)


# ── Sensei selection ──────────────────────────────────────────────────────────
async def team_sensei_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    user = await get_user(user_id)
    team = user.get("team", [])

    if not team:
        await query.answer("Set your team first!", show_alert=True)
        return

    rows = []
    for cid in team:
        cd = get_char(cid)
        if cd:
            ability_label = cd.get("ability", "?")[:10]
            rows.append(InlineKeyboardButton(f"{cd['name'][:12]}", callback_data=f"sens_set_{cid}"))
    rows.append(InlineKeyboardButton("❌ None", callback_data="sens_set_none"))
    chunked = [rows[j:j+3] for j in range(0, len(rows), 3)]
    chunked.append([InlineKeyboardButton("🔙 Back", callback_data="nav_team")])
    await query.edit_message_text(
        "🧑‍🏫 *Choose Sensei/Captain:*\nPassive ability activates for whole team.",
        reply_markup=InlineKeyboardMarkup(chunked),
        parse_mode="Markdown",
    )


async def sens_set_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    sensei_id = query.data.split("_")[2]
    user_id = update.effective_user.id
    user = await get_user(user_id)
    actual_sensei = None if sensei_id == "none" else sensei_id
    await set_team(user_id, user.get("team", []), actual_sensei)
    name = get_char(actual_sensei)["name"] if actual_sensei else "None"
    await query.answer(f"✅ Sensei: {name}")
    await show_team(update, context)


def register(app):
    app.add_handler(CommandHandler("team", team_command))
    app.add_handler(CallbackQueryHandler(show_team,             pattern="^nav_team$"))
    app.add_handler(CallbackQueryHandler(team_add_callback,     pattern="^team_add$"))
    app.add_handler(CallbackQueryHandler(team_pick_callback,    pattern="^team_pick_"))
    app.add_handler(CallbackQueryHandler(team_remove_callback,  pattern="^team_remove$"))
    app.add_handler(CallbackQueryHandler(team_rem_callback,     pattern="^team_rem_"))
    app.add_handler(CallbackQueryHandler(team_formation_callback, pattern="^team_formation$"))
    app.add_handler(CallbackQueryHandler(form_set_callback,     pattern="^form_set_"))
    app.add_handler(CallbackQueryHandler(team_sensei_callback,  pattern="^team_sensei$"))
    app.add_handler(CallbackQueryHandler(sens_set_callback,     pattern="^sens_set_"))
