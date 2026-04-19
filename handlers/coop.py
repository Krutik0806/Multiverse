"""
/coop handler — create rooms, join rooms, fight raid boss co-operatively.
"""
import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler
from database.mongo import (
    get_user, get_user_chars, create_coop_room, get_coop_room,
    join_coop_room, set_coop_status, add_xp, add_currency,
    add_char_to_user, increment_event_progress,
)
from database.redis_client import redis
from game.characters import get_char, get_char_stats, random_char_by_rarity
from game.battle import calc_team_power


async def show_coop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = update.effective_user.id
    user = await get_user(user_id)

    if not user:
        await query.answer("Register first! /start", show_alert=True)
        return

    kb = [
        [InlineKeyboardButton("🏠 Create Room",  callback_data="coop_create"),
         InlineKeyboardButton("🚪 Join Room",    callback_data="coop_join_prompt")],
        [InlineKeyboardButton("🔙 Back",          callback_data="nav_main")],
    ]
    await query.edit_message_text(
        "🤝 *Co-op Raid*\n\n"
        "🏠 Create a room and invite 1-2 friends.\n"
        "🚪 Join a friend's room with their Room ID.\n"
        "⚔️ Fight powerful Raid Bosses together!\n\n"
        "_Better drops than solo missions!_",
        reply_markup=InlineKeyboardMarkup(kb),
        parse_mode="Markdown",
    )


async def coop_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = await get_user(user_id)
    if not user:
        await update.message.reply_text("Register first! /start")
        return
    kb = [
        [InlineKeyboardButton("🏠 Create Room", callback_data="coop_create"),
         InlineKeyboardButton("🚪 Join Room",   callback_data="coop_join_prompt")],
        [InlineKeyboardButton("🔙 Main Menu",   callback_data="nav_main")],
    ]
    await update.message.reply_text(
        "🤝 *Co-op Raid* — Invite friends & fight Raid Bosses!",
        reply_markup=InlineKeyboardMarkup(kb),
        parse_mode="Markdown",
    )


async def coop_create_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    user = await get_user(user_id)

    if not user.get("team"):
        await query.answer("Set your team first! /team", show_alert=True)
        return

    room = await create_coop_room(user_id, user["world"])
    boss = room["boss"]

    kb = [
        [InlineKeyboardButton("⚔️ Start Raid!", callback_data=f"coop_fight_{room['room_id']}")],
        [InlineKeyboardButton("🔙 Co-op",       callback_data="nav_coop")],
    ]
    await query.edit_message_text(
        f"🏠 *Room Created!*\n\n"
        f"📋 Room ID: `{room['room_id']}`\n"
        f"👥 Members: 1/3\n"
        f"🐉 Boss: *{boss['name']}*\n"
        f"❤️ Boss HP: {boss['hp']:,}\n\n"
        f"Share your Room ID with friends! They can join with /coop.\n"
        "_Start the raid anytime!_",
        reply_markup=InlineKeyboardMarkup(kb),
        parse_mode="Markdown",
    )


async def coop_join_prompt_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id

    import json
    await redis.set_session(user_id, json.dumps({"step": "coop_join"}), ex=120)

    kb = [[InlineKeyboardButton("❌ Cancel", callback_data="nav_coop")]]
    await query.edit_message_text(
        "🚪 *Join Co-op Room*\n\nType the 6-character Room ID:",
        reply_markup=InlineKeyboardMarkup(kb),
        parse_mode="Markdown",
    )


async def coop_join_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    import json
    sess_raw = await redis.get_session(user_id)
    if not sess_raw:
        return
    sess = json.loads(sess_raw)
    if sess.get("step") != "coop_join":
        return

    room_id = update.message.text.strip().upper()
    room = await get_coop_room(room_id)

    if not room:
        await update.message.reply_text(f"❌ Room `{room_id}` not found!")
        return

    # World check
    user = await get_user(user_id)
    if user["world"] != room["world"]:
        await update.message.reply_text("❌ Wrong world! You can't join this room.")
        return

    success = await join_coop_room(room_id, user_id)
    await redis.delete_session(user_id)

    if not success:
        await update.message.reply_text("❌ Room is full or already started!")
        return

    room = await get_coop_room(room_id)
    boss = room["boss"]
    kb = [
        [InlineKeyboardButton("⚔️ Fight!", callback_data=f"coop_fight_{room_id}"),
         InlineKeyboardButton("🔙 Co-op", callback_data="nav_coop")],
    ]
    await update.message.reply_text(
        f"✅ *Joined Room {room_id}!*\n\n"
        f"👥 Members: {len(room['members'])}/3\n"
        f"🐉 Boss: *{boss['name']}* (HP: {boss['hp']:,})\n\n"
        "Ready to fight!",
        reply_markup=InlineKeyboardMarkup(kb),
        parse_mode="Markdown",
    )


async def coop_fight_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("⚔️ Raiding...")
    user_id = update.effective_user.id
    room_id = query.data.replace("coop_fight_", "")

    room = await get_coop_room(room_id)
    if not room or room["status"] == "completed":
        await query.answer("Room not found or already done!", show_alert=True)
        return

    if room["host"] != user_id and user_id not in room["members"]:
        await query.answer("Not in this room!", show_alert=True)
        return

    await set_coop_status(room_id, "fighting")

    boss = room["boss"]
    boss_hp = room.get("boss_hp", boss["hp"])
    members = room["members"]

    # Calculate combined team power
    total_power = 0
    for mid in members:
        u = await get_user(mid)
        if u and u.get("team"):
            team_chars = [(get_char(cid), 1) for cid in u["team"] if get_char(cid)]
            total_power += calc_team_power(team_chars, u.get("formation","standard"), u.get("sensei_id"))

    if total_power <= 0:
        total_power = 500 * len(members)  # fallback

    # Co-op gets +30% power bonus vs solo
    total_power *= 1.30

    # Battle simulation
    boss_power = boss["atk"] * 0.40 + boss["def"] * 0.35 + boss["spd"] * 0.25
    win_chance = min(0.90, max(0.20, total_power / (total_power + boss_power * 100)))
    success = random.random() < win_chance

    await set_coop_status(room_id, "completed")

    # Distribute rewards to all members
    xp_reward = 300 if success else 100
    coin_rewards = 600 if success else 150

    lines = [f"🏆 *Co-op Raid vs {boss['name']}*\n"]
    lines.append(f"👥 Team Power: {int(total_power)}\n")

    if success:
        lines.append("✅ *VICTORY!* The Raid Boss is defeated!\n")
    else:
        lines.append("❌ *Defeat.* The boss was too strong!\n")

    for mid in members:
        u = await get_user(mid)
        if u:
            world = u["world"]
            currency = "ryo" if world == "naruto" else "maria_gold"
            await add_xp(mid, xp_reward)
            await add_currency(mid, currency, coin_rewards)
            # Co-op drop (better rates)
            if success and random.random() < 0.25:
                rarity = random.choice(["rare", "epic", "legendary"])
                dropped = random_char_by_rarity(world, rarity)
                if dropped:
                    await add_char_to_user(mid, dropped["id"])
            await increment_event_progress(mid, "wall_breach_defense")

    lines.append(f"📈 Each member: +{xp_reward} XP, +{coin_rewards} gold!")
    if success:
        lines.append("🎁 Chance for Rare+ drops distributed!")

    kb = [
        [InlineKeyboardButton("🔙 Co-op",   callback_data="nav_coop"),
         InlineKeyboardButton("📊 Profile", callback_data="nav_profile")],
    ]
    await query.edit_message_text(
        "\n".join(lines),
        reply_markup=InlineKeyboardMarkup(kb),
        parse_mode="Markdown",
    )


async def nav_coop_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await show_coop(update, context)


def register(app):
    app.add_handler(CommandHandler("coop", coop_command))
    app.add_handler(CallbackQueryHandler(show_coop,              pattern="^nav_coop$"))
    app.add_handler(CallbackQueryHandler(coop_create_callback,   pattern="^coop_create$"))
    app.add_handler(CallbackQueryHandler(coop_join_prompt_callback, pattern="^coop_join_prompt$"))
    app.add_handler(CallbackQueryHandler(coop_fight_callback,    pattern="^coop_fight_"))
    # NOTE: text input handled by unified_text_handler in main.py

