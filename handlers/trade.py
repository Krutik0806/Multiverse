"""
/trade handler — create offer, view incoming/sent trades, accept/reject with MongoDB escrow.
"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from database.mongo import (
    get_user, get_user_chars, get_char_by_id,
    get_pending_trades, get_sent_trades,
    create_trade, get_trade, complete_trade, cancel_trade,
)
from database.redis_client import redis
from game.characters import get_char, rarity_label


async def show_trade(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = update.effective_user.id
    user = await get_user(user_id)

    if not user:
        await query.answer("Register first! /start", show_alert=True)
        return

    pending = await get_pending_trades(user_id)
    sent = await get_sent_trades(user_id)

    kb = [
        [InlineKeyboardButton("📤 New Trade",     callback_data="trade_new"),
         InlineKeyboardButton("📥 Incoming",      callback_data="trade_incoming")],
        [InlineKeyboardButton("📦 Sent Offers",   callback_data="trade_sent"),
         InlineKeyboardButton("🔙 Back",          callback_data="nav_main")],
    ]
    await query.edit_message_text(
        f"🤝 *Trade Hub*\n\n"
        f"📥 Incoming offers: {len(pending)}\n"
        f"📦 Sent offers: {len(sent)}\n\n"
        "_Trade same-world characters only._",
        reply_markup=InlineKeyboardMarkup(kb),
        parse_mode="Markdown",
    )


async def trade_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = await get_user(user_id)
    if not user:
        await update.message.reply_text("Register first! /start")
        return
    pending = await get_pending_trades(user_id)
    kb = [
        [InlineKeyboardButton("📤 New Trade",   callback_data="trade_new"),
         InlineKeyboardButton("📥 Incoming",    callback_data="trade_incoming")],
        [InlineKeyboardButton("📦 Sent",        callback_data="trade_sent"),
         InlineKeyboardButton("🔙 Menu",        callback_data="nav_main")],
    ]
    await update.message.reply_text(
        f"🤝 *Trade Hub*\n📥 {len(pending)} incoming offers",
        reply_markup=InlineKeyboardMarkup(kb),
        parse_mode="Markdown",
    )


# ── Incoming trades ───────────────────────────────────────────────────────────
async def trade_incoming_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    pending = await get_pending_trades(user_id)

    if not pending:
        kb = [[InlineKeyboardButton("🔙 Back", callback_data="nav_trade")]]
        await query.edit_message_text(
            "📥 *No incoming trade offers.*",
            reply_markup=InlineKeyboardMarkup(kb),
            parse_mode="Markdown",
        )
        return

    lines = ["📥 *Incoming Offers:*\n"]
    rows = []
    for i, trade in enumerate(pending[:6]):
        from_char = get_char(trade.get("from_char", ""))
        to_char = get_char(trade.get("to_char", ""))
        from_name = from_char["name"] if from_char else "?"
        to_name = to_char["name"] if to_char else "?"
        tid = trade["trade_id"][:8]
        lines.append(f"{i+1}. They offer *{from_name}* for your *{to_name}*")
        rows.append([
            InlineKeyboardButton(f"✅ Accept #{i+1}", callback_data=f"trade_acc_{trade['trade_id']}"),
            InlineKeyboardButton(f"❌ Reject #{i+1}", callback_data=f"trade_rej_{trade['trade_id']}"),
        ])

    rows.append([InlineKeyboardButton("🔙 Back", callback_data="nav_trade")])
    await query.edit_message_text(
        "\n".join(lines),
        reply_markup=InlineKeyboardMarkup(rows),
        parse_mode="Markdown",
    )


async def trade_accept_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    trade_id = query.data.replace("trade_acc_", "")

    trade = await get_trade(trade_id)
    if not trade or trade["status"] != "pending":
        await query.answer("Trade expired or not found!", show_alert=True)
        return
    if trade["to_user"] != user_id:
        await query.answer("Not your trade!", show_alert=True)
        return

    # Validate both chars still owned
    from_char_owned = await get_char_by_id(trade["from_user"], trade["from_char"])
    to_char_owned = await get_char_by_id(user_id, trade["to_char"])
    if not from_char_owned or not to_char_owned:
        await cancel_trade(trade_id)
        await query.answer("Character no longer available!", show_alert=True)
        return

    # Validate same world
    from_u = await get_user(trade["from_user"])
    to_u = await get_user(user_id)
    if from_u and to_u and from_u["world"] != to_u["world"]:
        await cancel_trade(trade_id)
        await query.answer("Cross-world trade not allowed!", show_alert=True)
        return

    success = await complete_trade(trade_id)
    kb = [[InlineKeyboardButton("🔙 Trade Hub", callback_data="nav_trade")]]
    if success:
        from_char = get_char(trade["from_char"])
        to_char = get_char(trade["to_char"])
        await query.edit_message_text(
            f"✅ *Trade Complete!*\n\n"
            f"You received: *{from_char['name'] if from_char else '?'}*\n"
            f"They received: *{to_char['name'] if to_char else '?'}*",
            reply_markup=InlineKeyboardMarkup(kb),
            parse_mode="Markdown",
        )
    else:
        await query.edit_message_text("❌ Trade failed!", reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")


async def trade_reject_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    trade_id = query.data.replace("trade_rej_", "")
    await cancel_trade(trade_id)
    kb = [[InlineKeyboardButton("🔙 Trade Hub", callback_data="nav_trade")]]
    await query.edit_message_text(
        "❌ *Trade rejected.*",
        reply_markup=InlineKeyboardMarkup(kb),
        parse_mode="Markdown",
    )


# ── Sent trades ───────────────────────────────────────────────────────────────
async def trade_sent_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    sent = await get_sent_trades(user_id)

    if not sent:
        kb = [[InlineKeyboardButton("🔙 Back", callback_data="nav_trade")]]
        await query.edit_message_text(
            "📦 *No pending sent offers.*",
            reply_markup=InlineKeyboardMarkup(kb),
            parse_mode="Markdown",
        )
        return

    lines = ["📦 *Sent Offers:*\n"]
    rows = []
    for i, trade in enumerate(sent[:6]):
        from_char = get_char(trade.get("from_char",""))
        to_char = get_char(trade.get("to_char",""))
        lines.append(f"{i+1}. *{from_char['name'] if from_char else '?'}* → *{to_char['name'] if to_char else '?'}*")
        rows.append([InlineKeyboardButton(
            f"❌ Cancel #{i+1}", callback_data=f"trade_cancel_{trade['trade_id']}"
        )])

    rows.append([InlineKeyboardButton("🔙 Back", callback_data="nav_trade")])
    await query.edit_message_text(
        "\n".join(lines),
        reply_markup=InlineKeyboardMarkup(rows),
        parse_mode="Markdown",
    )


async def trade_cancel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    trade_id = query.data.replace("trade_cancel_", "")
    await cancel_trade(trade_id)
    kb = [[InlineKeyboardButton("🔙 Trade Hub", callback_data="nav_trade")]]
    await query.edit_message_text(
        "✅ *Trade offer cancelled.*",
        reply_markup=InlineKeyboardMarkup(kb),
        parse_mode="Markdown",
    )


# ── New trade flow ─────────────────────────────────────────────────────────────
async def trade_new_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    chars = await get_user_chars(user_id)

    if len(chars) < 2:
        await query.answer("Need 2+ characters to trade!", show_alert=True)
        return

    # Store in Redis session to track step
    import json
    await redis.set_session(user_id, json.dumps({"step": "select_offer"}), ex=300)

    rows = []
    for i, owned in enumerate(chars[:9]):
        cd = get_char(owned["char_id"])
        if cd:
            rows.append(InlineKeyboardButton(cd["name"][:15], callback_data=f"trade_offer_{cd['id']}"))
    chunked = [rows[j:j+3] for j in range(0, len(rows), 3)]
    chunked.append([InlineKeyboardButton("🔙 Back", callback_data="nav_trade")])
    await query.edit_message_text(
        "📤 *New Trade — Step 1/3*\nSelect the character YOU will offer:",
        reply_markup=InlineKeyboardMarkup(chunked),
        parse_mode="Markdown",
    )


async def trade_offer_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    offer_char_id = query.data.replace("trade_offer_", "")

    import json
    sess_raw = await redis.get_session(user_id)
    sess = json.loads(sess_raw) if sess_raw else {}
    sess["offer_char"] = offer_char_id
    sess["step"] = "select_request"
    await redis.set_session(user_id, json.dumps(sess), ex=300)

    await query.edit_message_text(
        "📤 *New Trade — Step 2/3*\n"
        "Reply with the Telegram user ID of the player you want to trade with.\n\n"
        "_Type their Telegram numeric ID:_",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="nav_trade")]]),
        parse_mode="Markdown",
    )


async def trade_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle plain-text inputs for trade partner ID and char selection."""
    user_id = update.effective_user.id
    import json
    sess_raw = await redis.get_session(user_id)
    if not sess_raw:
        return
    sess = json.loads(sess_raw)
    step = sess.get("step")

    if step == "select_request":
        text = update.message.text.strip()
        try:
            partner_id = int(text)
        except ValueError:
            await update.message.reply_text("❌ Invalid user ID. Enter a numeric Telegram ID.")
            return

        partner = await get_user(partner_id)
        if not partner:
            await update.message.reply_text("❌ Player not found or not registered.")
            return

        # World validation
        my_user = await get_user(user_id)
        if my_user["world"] != partner["world"]:
            await update.message.reply_text("❌ Cross-world trades not allowed!")
            await redis.delete_session(user_id)
            return

        sess["partner_id"] = partner_id
        sess["step"] = "select_their_char"
        await redis.set_session(user_id, json.dumps(sess), ex=300)

        # Show partner's chars for selection
        partner_chars = await get_user_chars(partner_id)
        if not partner_chars:
            await update.message.reply_text("❌ This player has no characters to trade.")
            return

        rows = []
        for i, owned in enumerate(partner_chars[:9]):
            cd = get_char(owned["char_id"])
            if cd:
                rows.append(InlineKeyboardButton(cd["name"][:15], callback_data=f"trade_want_{cd['id']}"))
        chunked = [rows[j:j+3] for j in range(0, len(rows), 3)]
        chunked.append([InlineKeyboardButton("❌ Cancel", callback_data="nav_trade")])
        await update.message.reply_text(
            f"📤 *New Trade — Step 3/3*\nSelect the character you want from {partner.get('username','?')}:",
            reply_markup=InlineKeyboardMarkup(chunked),
            parse_mode="Markdown",
        )


async def trade_want_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    want_char_id = query.data.replace("trade_want_", "")

    import json
    sess_raw = await redis.get_session(user_id)
    if not sess_raw:
        await query.answer("Session expired! Start again.", show_alert=True)
        return
    sess = json.loads(sess_raw)

    partner_id = sess.get("partner_id")
    offer_char_id = sess.get("offer_char")

    if not partner_id or not offer_char_id:
        await query.answer("Session lost! Start again.", show_alert=True)
        return

    trade_id = await create_trade(user_id, partner_id, offer_char_id, want_char_id)
    await redis.delete_session(user_id)

    offer_char = get_char(offer_char_id)
    want_char = get_char(want_char_id)
    kb = [[InlineKeyboardButton("🔙 Trade Hub", callback_data="nav_trade")]]
    await query.edit_message_text(
        f"✅ *Trade offer sent!*\n\n"
        f"You offered: *{offer_char['name'] if offer_char else '?'}*\n"
        f"You want: *{want_char['name'] if want_char else '?'}*\n\n"
        f"Waiting for acceptance...\n_Trade ID: {trade_id[:8]}_",
        reply_markup=InlineKeyboardMarkup(kb),
        parse_mode="Markdown",
    )


def register(app):
    app.add_handler(CommandHandler("trade", trade_command))
    app.add_handler(CallbackQueryHandler(show_trade,           pattern="^nav_trade$"))
    app.add_handler(CallbackQueryHandler(trade_new_callback,   pattern="^trade_new$"))
    app.add_handler(CallbackQueryHandler(trade_offer_callback, pattern="^trade_offer_"))
    app.add_handler(CallbackQueryHandler(trade_want_callback,  pattern="^trade_want_"))
    app.add_handler(CallbackQueryHandler(trade_incoming_callback, pattern="^trade_incoming$"))
    app.add_handler(CallbackQueryHandler(trade_sent_callback,  pattern="^trade_sent$"))
    app.add_handler(CallbackQueryHandler(trade_accept_callback, pattern="^trade_acc_"))
    app.add_handler(CallbackQueryHandler(trade_reject_callback, pattern="^trade_rej_"))
    app.add_handler(CallbackQueryHandler(trade_cancel_callback, pattern="^trade_cancel_"))
    # NOTE: text input handled by unified_text_handler in main.py

