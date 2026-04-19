"""
/mission handler — all ranks, confirmation step with win-chance preview.
"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler
from database.mongo import get_user
from database.redis_client import redis
from game.mission_engine import MISSIONS, run_mission, get_mission_preview
from game.characters import rarity_label
from handlers.utils import safe_edit, fmt, power_bar, WORLD_HEADER, RARITY_BADGE
from config import FREE_MISSIONS_PER_DAY

RANK_DIFF = {
    "d_rank": "🟢 Easy",    "patrol":         "🟢 Easy",
    "c_rank": "🔵 Normal",  "recon":          "🔵 Normal",
    "b_rank": "🟡 Hard",    "titan_hunt":     "🟡 Hard",
    "a_rank": "🟠 Extreme", "bridge_defense": "🟠 Extreme",
    "s_rank": "🔴 Legendary","wall_breach":   "🔴 Legendary",
}


async def _mission_menu_text_and_kb(user: dict) -> tuple[str, InlineKeyboardMarkup]:
    world = user["world"]
    missions = MISSIONS[world]
    today_free = user.get("free_missions_today", 0)
    stamina = user["stamina"]
    free_left = max(0, FREE_MISSIONS_PER_DAY - today_free)

    header = WORLD_HEADER[world]
    curr_sym = "Ryo" if world == "naruto" else "Maria Gold"

    if world == "naruto":
        keys  = ["d_rank", "c_rank", "b_rank", "a_rank", "s_rank"]
    else:
        keys  = ["patrol", "recon", "titan_hunt", "bridge_defense", "wall_breach"]

    lines = [
        f"━━━━━━ {header} ━━━━━━",
        f"⚡ {header.split()[1]}  │  💚 Stamina: {stamina}/100  │  🆓 Free: {free_left}/{FREE_MISSIONS_PER_DAY}",
        "",
        "Select a mission rank:",
    ]

    rows = []
    for key in keys:
        m = missions[key]
        diff = RANK_DIFF.get(key, "")
        lv = m["min_level"]
        lv_tag = f" (Lv{lv}+)" if lv > 1 else ""
        rows.append([InlineKeyboardButton(
            f"{m['emoji']} {m['label']}{lv_tag}",
            callback_data=f"miss_{key}"
        )])

    rows.append([InlineKeyboardButton("🔙 Main Menu", callback_data="nav_main")])
    return "\n".join(lines), InlineKeyboardMarkup(rows)


async def show_missions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = update.effective_user.id
    user = await get_user(user_id)
    if not user:
        await query.answer("Register first! /start", show_alert=True)
        return
    text, kb = await _mission_menu_text_and_kb(user)
    await safe_edit(query, text, kb)


async def mission_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = await get_user(user_id)
    if not user:
        await update.message.reply_text("Register first! /start")
        return
    text, kb = await _mission_menu_text_and_kb(user)
    await update.message.reply_text(text, reply_markup=kb, parse_mode="Markdown")


# ── Step 1: Show preview / confirmation ───────────────────────────────────────
async def mission_preview_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id

    mission_key = query.data.replace("miss_", "")
    preview = await get_mission_preview(user_id, mission_key)

    if "error" in preview:
        await query.answer(preview["error"], show_alert=True)
        return

    user = await get_user(user_id)
    world = user["world"]
    curr_sym = "Ryo" if world == "naruto" else "Maria Gold"

    win  = preview["win_chance"]
    free = preview["is_free"]
    stam = preview["stamina"]
    cd   = preview["cooldown"]
    mins = cd // 60

    # Win chance colour
    if win >= 75:
        win_icon = "🟢"
    elif win >= 50:
        win_icon = "🟡"
    elif win >= 30:
        win_icon = "🟠"
    else:
        win_icon = "🔴"

    bar = power_bar(preview["team_power"], 1500)
    free_tag = " 🆓 FREE" if free else f"  (-{stam} Stamina)"

    lines = [
        f"{preview['emoji']} *{preview['mission']}*",
        f"_{preview['desc']}_",
        "",
        f"━━━━━━━━━━━━━━━━━━━",
        f"👊 Your Power:  {fmt(preview['team_power'])}  {bar}",
        f"🐉 Enemy Power: {fmt(preview['enemy_power'])}",
        f"",
        f"{win_icon} Win Chance: *{win}%*",
        f"💚 Cost: {free_tag}",
        f"⏱ Cooldown: {mins} min",
        f"",
        f"📈 Rewards:  +{preview['xp']} XP  |  +{preview['coin']} {curr_sym}",
    ]

    kb = [
        [InlineKeyboardButton("⚔️ GO!", callback_data=f"miss_confirm_{mission_key}"),
         InlineKeyboardButton("🔙 Missions", callback_data="nav_mission")],
    ]
    await safe_edit(query, "\n".join(lines), InlineKeyboardMarkup(kb))


# ── Step 2: Execute mission ───────────────────────────────────────────────────
async def mission_confirm_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("⚔️ Mission started!")
    user_id = update.effective_user.id

    if await redis.rate_limit(user_id, "mission", window=4):
        await query.answer("Too fast! Wait a moment.", show_alert=True)
        return

    mission_key = query.data.replace("miss_confirm_", "")
    result = await run_mission(user_id, mission_key)

    if "error" in result:
        await query.answer(result["error"], show_alert=True)
        return

    user = await get_user(user_id)
    world = user["world"] if user else "naruto"
    curr_sym = "Ryo" if world == "naruto" else "Maria Gold"
    free_tag = " 🆓" if result["is_free"] else ""
    win_pct = result["win_chance"]

    if result["success"]:
        if win_pct >= 75:
            outcome_line = "✅ *Mission Complete!* Easy win."
        elif win_pct >= 50:
            outcome_line = "✅ *Mission Complete!* Close fight!"
        else:
            outcome_line = "✅ *Mission Complete!* Against the odds!"

        lines = [
            f"{result['emoji']} *{result['mission']}*{free_tag}",
            f"",
            outcome_line,
            f"",
            f"━━━━━━━━━━━━━━━━━━━",
            f"📈 XP:    +{result['xp']}",
            f"💴 {curr_sym}: +{fmt(result['coin'])}",
        ]
        if result.get("dropped_char"):
            dc = result["dropped_char"]
            lines.append(f"")
            lines.append(f"🎁 *Character Drop!*")
            lines.append(f"   {RARITY_BADGE.get(dc['rarity'], dc['rarity'])} {dc['name']}")
    else:
        lines = [
            f"{result['emoji']} *{result['mission']}*{free_tag}",
            f"",
            f"❌ *Mission Failed!*",
            f"Win chance was only {win_pct}%.",
            f"",
            f"💡 Tip: Build a stronger team or upgrade star levels!",
        ]

    kb = [
        [InlineKeyboardButton("🔄 Try Again",  callback_data=f"miss_{mission_key}"),
         InlineKeyboardButton("⚔️ Missions",   callback_data="nav_mission")],
        [InlineKeyboardButton("👥 Team",        callback_data="nav_team"),
         InlineKeyboardButton("🔙 Menu",        callback_data="nav_main")],
    ]
    await safe_edit(query, "\n".join(lines), InlineKeyboardMarkup(kb))


def register(app):
    app.add_handler(CommandHandler("mission", mission_command))
    app.add_handler(CallbackQueryHandler(show_missions,          pattern="^nav_mission$"))
    # Preview step (tapping a rank)
    app.add_handler(CallbackQueryHandler(mission_preview_callback,
                                         pattern=r"^miss_(d_rank|c_rank|b_rank|a_rank|s_rank|patrol|recon|titan_hunt|bridge_defense|wall_breach)$"))
    # Confirm step (tapping GO!)
    app.add_handler(CallbackQueryHandler(mission_confirm_callback, pattern="^miss_confirm_"))
