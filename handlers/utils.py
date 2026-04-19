"""
Shared utilities used across handlers.
- safe_edit: edit text or caption without crashing on photo messages
- fmt_num: format large numbers with commas
- power_bar: visual power indicator
"""
from telegram import InlineKeyboardMarkup


async def safe_edit(query, text: str, reply_markup: InlineKeyboardMarkup = None, parse_mode: str = "Markdown"):
    """
    Safely edit a message whether it's text or photo.
    Fallback chain: edit_message_text → edit_message_caption → reply_text (new msg)
    """
    kwargs = {"reply_markup": reply_markup, "parse_mode": parse_mode}
    try:
        await query.edit_message_text(text, **kwargs)
        return
    except Exception:
        pass
    try:
        await query.edit_message_caption(caption=text, **kwargs)
        return
    except Exception:
        pass
    # Last resort: send a new message
    try:
        await query.message.reply_text(text, **kwargs)
    except Exception:
        pass


def fmt(n: int) -> str:
    """Format number with commas: 12345 → 12,345"""
    return f"{int(n):,}"


def power_bar(power: float, max_power: float = 2000, length: int = 8) -> str:
    """Visual bar for team power.  ████████░░"""
    if max_power <= 0:
        return "░" * length
    filled = min(length, int(length * power / max_power))
    return "█" * filled + "░" * (length - filled)


def xp_progress_bar(current: int, needed: int, length: int = 8) -> str:
    if needed <= 0:
        return "█" * length
    filled = min(length, int(length * current / needed))
    return "▰" * filled + "▱" * (length - filled)


def stamina_bar(current: int, maximum: int = 100, length: int = 8) -> str:
    filled = min(length, int(length * current / maximum))
    return "💚" * filled + "🖤" * (length - filled)


RARITY_BADGE = {
    "common":      "◻️ Common",
    "rare":        "🔷 Rare",
    "epic":        "🟣 Epic",
    "legendary":   "🔶 Legendary",
    "world_class": "🌟 World-Class",
}

WORLD_HEADER = {
    "naruto": "🍃 NARUTO WORLD",
    "aot":    "⚔️ ATTACK ON TITAN",
}

RANK_BADGE = {
    "Genin":     "🟢 Genin",
    "Chuunin":   "🔵 Chuunin",
    "Jonin":     "🟣 Jonin",
    "ANBU":      "🔴 ANBU",
    "Kage":      "⭐ Kage",
    "Cadet":     "🟢 Cadet",
    "Scout":     "🔵 Scout",
    "Soldier":   "🟣 Soldier",
    "Captain":   "🔴 Captain",
    "Commander": "⭐ Commander",
}
