"""
/shop handler — world-specific items, daily rotation, World Gem shop.
"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler
from database.mongo import get_user, subtract_currency, add_currency, update_user
from database.mongo import get_shop_items
from config import MAX_STAMINA


async def show_shop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = update.effective_user.id
    user = await get_user(user_id)

    if not user:
        await query.answer("Register first! /start", show_alert=True)
        return

    world = user["world"]
    items = get_shop_items(world)
    c = user["currencies"]
    curr_sym = "Ryo" if world == "naruto" else "Maria Gold"
    curr_amt = c.get("ryo" if world == "naruto" else "maria_gold", 0)

    rows = []
    for item in items:
        rows.append([InlineKeyboardButton(
            f"{item['name'][:12]} — {item['cost']} {curr_sym[:4]}",
            callback_data=f"shop_buy_{item['id']}"
        )])

    rows.append([InlineKeyboardButton("🔙 Back", callback_data="nav_main")])

    shop_name = "🍃 Konoha Shop" if world == "naruto" else "⚔️ Corps Supply"
    await query.edit_message_text(
        f"{shop_name}\n\n💰 Balance: {curr_amt:,} {curr_sym}\n\n"
        "_Select an item to purchase:_",
        reply_markup=InlineKeyboardMarkup(rows),
        parse_mode="Markdown",
    )


async def shop_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = await get_user(user_id)
    if not user:
        await update.message.reply_text("Register first! /start")
        return
    world = user["world"]
    items = get_shop_items(world)
    curr_sym = "Ryo" if world == "naruto" else "Maria Gold"
    curr_amt = user["currencies"].get("ryo" if world == "naruto" else "maria_gold", 0)
    rows = []
    for item in items:
        rows.append([InlineKeyboardButton(
            f"{item['name'][:12]} — {item['cost']}",
            callback_data=f"shop_buy_{item['id']}"
        )])
    rows.append([InlineKeyboardButton("🔙 Main Menu", callback_data="nav_main")])
    shop_name = "🍃 Konoha Shop" if world == "naruto" else "⚔️ Corps Supply"
    await update.message.reply_text(
        f"{shop_name}\n💰 {curr_amt:,} {curr_sym}",
        reply_markup=InlineKeyboardMarkup(rows),
        parse_mode="Markdown",
    )


async def shop_buy_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    item_id = query.data.replace("shop_buy_", "")

    user = await get_user(user_id)
    if not user:
        return

    world = user["world"]
    # Find item in all shop pools
    all_items = get_shop_items(world) + get_shop_items(world, is_world_lobby=True)
    item = next((i for i in all_items if i["id"] == item_id), None)

    if not item:
        await query.answer("Item not found!", show_alert=True)
        return

    # Deduct currency
    if not await subtract_currency(user_id, item["currency"], item["cost"]):
        curr_sym = item["currency"].replace("_", " ").title()
        await query.answer(f"Need {item['cost']} {curr_sym}!", show_alert=True)
        return

    # Apply effect
    effect = item["effect"]
    value = item["value"]
    result_msg = f"✅ Bought *{item['name']}*!\n"

    if effect == "stamina":
        new_stamina = min(MAX_STAMINA, user["stamina"] + value)
        await update_user(user_id, {"stamina": new_stamina})
        result_msg += f"💚 Stamina: +{value} (now {new_stamina})"
    elif effect == "xp_boost":
        from database.mongo import add_xp
        await add_xp(user_id, value)
        result_msg += f"📈 +{value} XP!"
    elif effect == "currency":
        # Convert ryo → chakra crystal or maria_gold → expedition medal
        target_curr = "chakra_crystals" if world == "naruto" else "expedition_medals"
        await add_currency(user_id, target_curr, value)
        result_msg += f"🔷 +{value} premium currency!"
    elif effect == "gacha":
        # Trigger a free pull
        from game.gacha_engine import single_pull
        pull_result = await single_pull(user_id)
        if "error" not in pull_result:
            result_msg += f"🎴 Free pull: {pull_result['name']}!"
        else:
            result_msg += "🎴 Free pull applied!"
    else:
        result_msg += "Effect applied!"

    kb = [
        [InlineKeyboardButton("🛒 Shop Again", callback_data="nav_shop"),
         InlineKeyboardButton("🔙 Back",       callback_data="nav_main")],
    ]
    await query.edit_message_text(result_msg, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")


def register(app):
    app.add_handler(CommandHandler("shop", shop_command))
    app.add_handler(CallbackQueryHandler(show_shop,       pattern="^nav_shop$"))
    app.add_handler(CallbackQueryHandler(shop_buy_callback, pattern="^shop_buy_"))
