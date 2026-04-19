"""
MongoDB Atlas async client using Motor.
All collections, indexes, and CRUD operations for the bot.
"""
import motor.motor_asyncio
from datetime import datetime, timezone
from bson import ObjectId
from config import MONGO_URI, DB_NAME

_client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URI)
db = _client[DB_NAME]

# Collections
users_col       = db["users"]
characters_col  = db["characters"]
missions_col    = db["missions"]
pvp_stats_col   = db["pvp_stats"]
events_col      = db["events"]
trades_col      = db["trades"]
coop_rooms_col  = db["coop_rooms"]
shop_col        = db["shop"]


async def init_db():
    """Create all indexes on startup."""
    await users_col.create_index("user_id", unique=True)
    await users_col.create_index([("world", 1), ("level", -1)])
    await users_col.create_index([("world", 1), ("weekly_pvp_score", -1)])
    await users_col.create_index([("world", 1), ("monthly_pvp_score", -1)])
    await characters_col.create_index([("owner_id", 1), ("char_id", 1)])
    await missions_col.create_index([("user_id", 1), ("mission_type", 1)])
    await pvp_stats_col.create_index([("week", 1), ("score", -1)])
    await trades_col.create_index("trade_id")
    await coop_rooms_col.create_index("room_id")


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ── Helpers ────────────────────────────────────────────────────────────────────
def _default_user(user_id: int, username: str, world: str) -> dict:
    now = _now()
    return {
        "user_id":              user_id,
        "username":             username or f"Shinobi#{user_id % 9999}",
        "world":                world,
        "level":                1,
        "xp":                   0,
        "rank":                 "Genin" if world == "naruto" else "Cadet",
        "currencies": {
            "ryo":              500,
            "chakra_crystals":  0,
            "maria_gold":       500,
            "expedition_medals":0,
            "world_gems":       0,
            "scraps":           0,
        },
        "stamina":              100,
        "stamina_regen_at":     now,
        "pity_count":           0,
        "daily_streak":         0,
        "last_daily":           None,
        "free_missions_today":  0,
        "free_missions_date":   now.date().isoformat(),
        "team":                 [],            # list of char_ids (max 4 Naruto, 3 AoT)
        "sensei_id":            None,
        "formation":            "standard",
        "offline_xp_at":        now,
        "weekly_pvp_score":     0,
        "monthly_pvp_score":    0,
        "pvp_wins":             0,
        "pvp_losses":           0,
        "created_at":           now,
        "updated_at":           now,
        "event_progress":       {},
    }


# ── User operations ────────────────────────────────────────────────────────────
async def get_user(user_id: int) -> dict | None:
    return await users_col.find_one({"user_id": user_id})


async def create_user(user_id: int, username: str, world: str) -> dict:
    doc = _default_user(user_id, username, world)
    await users_col.insert_one(doc)
    return doc


async def update_user(user_id: int, updates: dict):
    updates["updated_at"] = _now()
    await users_col.update_one({"user_id": user_id}, {"$set": updates})


async def inc_user(user_id: int, field: str, amount: int | float):
    await users_col.update_one(
        {"user_id": user_id},
        {"$inc": {field: amount}, "$set": {"updated_at": _now()}},
    )


async def add_xp(user_id: int, xp: int) -> dict:
    """Add XP, handle level-up, return updated user."""
    from game.progression import xp_for_level, rank_for_level
    user = await get_user(user_id)
    if not user:
        return {}
    new_xp = user["xp"] + xp
    new_level = user["level"]
    while new_xp >= xp_for_level(new_level + 1) and new_level < 100:
        new_xp -= xp_for_level(new_level + 1)
        new_level += 1
    new_rank = rank_for_level(new_level, user["world"])
    await update_user(user_id, {"xp": new_xp, "level": new_level, "rank": new_rank})
    user["xp"] = new_xp
    user["level"] = new_level
    user["rank"] = new_rank
    return user


# ── Currency operations ────────────────────────────────────────────────────────
async def get_currency(user: dict, currency: str) -> int:
    return user.get("currencies", {}).get(currency, 0)


async def subtract_currency(user_id: int, currency: str, amount: int) -> bool:
    user = await get_user(user_id)
    if not user:
        return False
    current = user["currencies"].get(currency, 0)
    if current < amount:
        return False
    await users_col.update_one(
        {"user_id": user_id},
        {"$inc": {f"currencies.{currency}": -amount}, "$set": {"updated_at": _now()}},
    )
    return True


async def add_currency(user_id: int, currency: str, amount: int):
    await users_col.update_one(
        {"user_id": user_id},
        {"$inc": {f"currencies.{currency}": amount}, "$set": {"updated_at": _now()}},
    )


# ── Stamina ───────────────────────────────────────────────────────────────────
async def get_stamina(user_id: int) -> int:
    user = await get_user(user_id)
    return user["stamina"] if user else 0


async def subtract_stamina(user_id: int, amount: int) -> bool:
    user = await get_user(user_id)
    if not user or user["stamina"] < amount:
        return False
    await users_col.update_one(
        {"user_id": user_id},
        {"$inc": {"stamina": -amount}, "$set": {"updated_at": _now()}},
    )
    return True


async def regen_stamina_all():
    """Called by APScheduler every 30 min — add 5 stamina to all users below cap."""
    from config import MAX_STAMINA, STAMINA_REGEN_AMOUNT
    await users_col.update_many(
        {"stamina": {"$lt": MAX_STAMINA}},
        {"$inc": {"stamina": STAMINA_REGEN_AMOUNT}},
    )
    # Cap at MAX_STAMINA
    await users_col.update_many(
        {"stamina": {"$gt": MAX_STAMINA}},
        {"$set": {"stamina": MAX_STAMINA}},
    )


# ── Character collection ───────────────────────────────────────────────────────
async def get_user_chars(user_id: int) -> list:
    cursor = characters_col.find({"owner_id": user_id}).sort("obtained_at", -1)
    return await cursor.to_list(length=None)


async def get_user_char(user_id: int, char_id: str) -> dict | None:
    return await characters_col.find_one({"owner_id": user_id, "char_id": char_id})


# Alias used by trade.py
async def get_char_by_id(user_id: int, char_id: str) -> dict | None:
    return await get_user_char(user_id, char_id)


async def add_char_to_user(user_id: int, char_id: str) -> dict:
    """Add character or increment duplicate count, handle star upgrades. Returns result dict."""
    existing = await get_user_char(user_id, char_id)
    if existing:
        new_dupes = existing.get("duplicates", 0) + 1
        new_stars = existing.get("stars", 1)
        scraps_gained = 0
        if new_dupes >= 3 and new_stars < 5:
            new_stars += 1
            new_dupes = 0
        else:
            from game.characters import get_char, RARITY_SCRAP_VALUE
            char_data = get_char(char_id)
            if char_data:
                scraps_gained = RARITY_SCRAP_VALUE.get(char_data["rarity"], 1)
        await characters_col.update_one(
            {"owner_id": user_id, "char_id": char_id},
            {"$set": {"duplicates": new_dupes, "stars": new_stars}},
        )
        if scraps_gained > 0:
            await add_currency(user_id, "scraps", scraps_gained)
        return {"is_duplicate": True, "stars": new_stars, "scraps": scraps_gained}
    else:
        doc = {
            "owner_id":    user_id,
            "char_id":     char_id,
            "stars":       1,
            "duplicates":  0,
            "obtained_at": _now(),
        }
        await characters_col.insert_one(doc)
        return {"is_duplicate": False, "stars": 1, "scraps": 0}


# ── Team operations ────────────────────────────────────────────────────────────
async def set_team(user_id: int, team: list[str], sensei_id: str | None):
    await update_user(user_id, {"team": team, "sensei_id": sensei_id})


async def set_formation(user_id: int, formation: str):
    await update_user(user_id, {"formation": formation})


# ── Pity counter ───────────────────────────────────────────────────────────────
async def get_pity(user_id: int) -> int:
    user = await get_user(user_id)
    return user.get("pity_count", 0) if user else 0


async def increment_pity(user_id: int):
    await users_col.update_one({"user_id": user_id}, {"$inc": {"pity_count": 1}})


async def reset_pity(user_id: int):
    await update_user(user_id, {"pity_count": 0})


# ── PvP operations ─────────────────────────────────────────────────────────────
async def get_pvp_opponents(user_id: int, world: str, limit: int = 10) -> list:
    cursor = users_col.find(
        {"user_id": {"$ne": user_id}, "world": world, "team": {"$ne": []}},
        {"user_id": 1, "username": 1, "level": 1, "team": 1, "formation": 1,
         "sensei_id": 1, "weekly_pvp_score": 1},
    ).sort("weekly_pvp_score", -1).limit(limit)
    return await cursor.to_list(length=limit)


async def update_pvp_score(user_id: int, won: bool, points: int = 10):
    inc = {
        "weekly_pvp_score":  points if won else -2,
        "monthly_pvp_score": points if won else -1,
    }
    if won:
        inc["pvp_wins"] = 1
    else:
        inc["pvp_losses"] = 1
    await users_col.update_one({"user_id": user_id}, {"$inc": inc, "$set": {"updated_at": _now()}})


async def get_weekly_leaderboard(world: str, limit: int = 10) -> list:
    cursor = users_col.find(
        {"world": world},
        {"user_id": 1, "username": 1, "weekly_pvp_score": 1, "rank": 1},
    ).sort("weekly_pvp_score", -1).limit(limit)
    return await cursor.to_list(length=limit)


async def get_monthly_leaderboard(world: str, limit: int = 10) -> list:
    cursor = users_col.find(
        {"world": world},
        {"user_id": 1, "username": 1, "monthly_pvp_score": 1, "rank": 1},
    ).sort("monthly_pvp_score", -1).limit(limit)
    return await cursor.to_list(length=limit)


async def reset_weekly_pvp():
    """Called every Monday 00:00 UTC."""
    # Award top 10 world gems first (handled in scheduler/jobs.py)
    await users_col.update_many({}, {"$set": {"weekly_pvp_score": 0}})


async def reset_monthly_pvp():
    await users_col.update_many({}, {"$set": {"monthly_pvp_score": 0}})


# ── Trade operations ───────────────────────────────────────────────────────────
async def create_trade(from_id: int, to_id: int, from_char: str, to_char: str) -> str:
    trade_id = str(ObjectId())
    doc = {
        "trade_id":   trade_id,
        "from_user":  from_id,
        "to_user":    to_id,
        "from_char":  from_char,
        "to_char":    to_char,
        "status":     "pending",
        "created_at": _now(),
    }
    await trades_col.insert_one(doc)
    return trade_id


async def get_trade(trade_id: str) -> dict | None:
    return await trades_col.find_one({"trade_id": trade_id})


async def get_pending_trades(user_id: int) -> list:
    cursor = trades_col.find({"to_user": user_id, "status": "pending"})
    return await cursor.to_list(length=20)


async def get_sent_trades(user_id: int) -> list:
    cursor = trades_col.find({"from_user": user_id, "status": "pending"})
    return await cursor.to_list(length=20)


async def complete_trade(trade_id: str):
    """Swap character ownership — called after both parties confirm."""
    trade = await get_trade(trade_id)
    if not trade:
        return False
    # Transfer characters
    await characters_col.update_one(
        {"owner_id": trade["from_user"], "char_id": trade["from_char"]},
        {"$set": {"owner_id": trade["to_user"]}},
    )
    await characters_col.update_one(
        {"owner_id": trade["to_user"], "char_id": trade["to_char"]},
        {"$set": {"owner_id": trade["from_user"]}},
    )
    await trades_col.update_one(
        {"trade_id": trade_id},
        {"$set": {"status": "completed", "completed_at": _now()}},
    )
    return True


async def cancel_trade(trade_id: str):
    await trades_col.update_one(
        {"trade_id": trade_id},
        {"$set": {"status": "cancelled"}},
    )


# ── Co-op operations ───────────────────────────────────────────────────────────
import random as _random
import string as _string


def _gen_room_id() -> str:
    return "".join(_random.choices(_string.ascii_uppercase + _string.digits, k=6))


RAID_BOSSES = {
    "naruto": [
        {"name": "Madara Uchiha",  "hp": 5000, "atk": 120, "def": 100, "spd": 80},
        {"name": "Kaguya Otsutsuki","hp": 7000,"atk": 140, "def": 120, "spd": 90},
        {"name": "Momoshiki",      "hp": 6000, "atk": 130, "def": 110, "spd": 85},
    ],
    "aot": [
        {"name": "Wall Titan",     "hp": 5000, "atk": 110, "def": 130, "spd": 50},
        {"name": "Rod Reiss Titan","hp": 8000, "atk": 100, "def": 150, "spd": 30},
        {"name": "Founding Titan", "hp": 9000, "atk": 160, "def": 140, "spd": 45},
    ],
}


async def create_coop_room(host_id: int, world: str) -> dict:
    boss = _random.choice(RAID_BOSSES[world])
    doc = {
        "room_id":    _gen_room_id(),
        "host":       host_id,
        "members":    [host_id],
        "world":      world,
        "boss":       boss,
        "boss_hp":    boss["hp"],
        "status":     "waiting",
        "created_at": _now(),
    }
    await coop_rooms_col.insert_one(doc)
    return doc


async def get_coop_room(room_id: str) -> dict | None:
    return await coop_rooms_col.find_one({"room_id": room_id})


async def join_coop_room(room_id: str, user_id: int) -> bool:
    room = await get_coop_room(room_id)
    if not room or room["status"] != "waiting" or len(room["members"]) >= 3:
        return False
    if user_id in room["members"]:
        return False
    await coop_rooms_col.update_one(
        {"room_id": room_id},
        {"$push": {"members": user_id}},
    )
    return True


async def set_coop_status(room_id: str, status: str):
    await coop_rooms_col.update_one({"room_id": room_id}, {"$set": {"status": status}})


# ── Shop operations ────────────────────────────────────────────────────────────
NARUTO_SHOP_ITEMS = [
    {"id": "n_scroll",  "name": "Jutsu Scroll",   "cost": 200,  "currency": "ryo",   "effect": "xp_boost",  "value": 50},
    {"id": "n_potion",  "name": "Chakra Potion",   "cost": 150,  "currency": "ryo",   "effect": "stamina",   "value": 30},
    {"id": "n_ramen",   "name": "Ichiraku Ramen",  "cost": 100,  "currency": "ryo",   "effect": "stamina",   "value": 20},
    {"id": "n_crystal", "name": "Chakra Crystal",  "cost": 1000, "currency": "ryo",   "effect": "currency",  "value": 1},
    {"id": "n_pull",    "name": "Gacha Ticket",    "cost": 500,  "currency": "ryo",   "effect": "gacha",     "value": 1},
]
AOT_SHOP_ITEMS = [
    {"id": "a_gas",     "name": "ODM Gas Can",     "cost": 200,  "currency": "maria_gold", "effect": "stamina",  "value": 30},
    {"id": "a_blade",   "name": "Titan Blade",     "cost": 300,  "currency": "maria_gold", "effect": "xp_boost", "value": 50},
    {"id": "a_ration",  "name": "Corps Ration",    "cost": 100,  "currency": "maria_gold", "effect": "stamina",  "value": 20},
    {"id": "a_medal",   "name": "Exp. Medal",      "cost": 1000, "currency": "maria_gold", "effect": "currency", "value": 1},
    {"id": "a_pull",    "name": "Gacha Ticket",    "cost": 500,  "currency": "maria_gold", "effect": "gacha",    "value": 1},
]
WORLD_SHOP_ITEMS = [
    {"id": "w_gem",     "name": "World Gem",       "cost": 50,   "currency": "world_gems", "effect": "world_gacha", "value": 1},
    {"id": "w_title",   "name": "Elite Title",     "cost": 100,  "currency": "world_gems", "effect": "cosmetic",    "value": 0},
]


def get_shop_items(world: str, is_world_lobby: bool = False) -> list:
    if is_world_lobby:
        return WORLD_SHOP_ITEMS
    return NARUTO_SHOP_ITEMS if world == "naruto" else AOT_SHOP_ITEMS


# ── Daily reward ───────────────────────────────────────────────────────────────
async def claim_daily(user_id: int) -> dict | None:
    """Returns reward dict if successful, None if already claimed today."""
    from datetime import timedelta
    user = await get_user(user_id)
    if not user:
        return None

    today = _now().date()
    today_str = today.isoformat()

    if user.get("last_daily") == today_str:
        return None  # Already claimed

    last_str = user.get("last_daily")
    streak = user.get("daily_streak", 0)

    if last_str:
        yesterday = (today - timedelta(days=1)).isoformat()
        if last_str == yesterday:
            streak += 1   # Consecutive day → extend streak
        else:
            streak = 1    # Missed a day → reset
    else:
        streak = 1        # First ever claim

    world = user["world"]
    currency = "ryo" if world == "naruto" else "maria_gold"
    base = 200
    bonus = 0
    if streak % 30 == 0:
        bonus = 2000
    elif streak % 7 == 0:
        bonus = 700
    total = base + bonus + (streak * 10)

    await add_currency(user_id, currency, total)
    await update_user(user_id, {"last_daily": today_str, "daily_streak": streak})
    return {"currency": currency, "amount": total, "streak": streak, "bonus": bonus > 0, "bonus_amount": bonus}


# ── Mission tracking ───────────────────────────────────────────────────────────
async def reset_free_missions_if_new_day():
    today = _now().date().isoformat()
    await users_col.update_many(
        {"free_missions_date": {"$ne": today}},
        {"$set": {"free_missions_today": 0, "free_missions_date": today}},
    )


async def use_free_mission(user_id: int) -> bool:
    """Returns True and decrements free missions if available."""
    user = await get_user(user_id)
    if not user:
        return False
    today = _now().date().isoformat()
    if user.get("free_missions_date") != today:
        await update_user(user_id, {"free_missions_today": 0, "free_missions_date": today})
        user["free_missions_today"] = 0
    from config import FREE_MISSIONS_PER_DAY
    if user["free_missions_today"] >= FREE_MISSIONS_PER_DAY:
        return False
    await inc_user(user_id, "free_missions_today", 1)
    return True


# ── Events ─────────────────────────────────────────────────────────────────────
ACTIVE_EVENTS = [
    {
        "id": "chunin_exams",
        "name": "🥷 Chunin Exams",
        "world": "naruto",
        "description": "Monthly Naruto PvP tournament! Win 10 PvP battles to earn Chakra Crystals.",
        "goal": 10,
        "reward_currency": "chakra_crystals",
        "reward_amount": 20,
    },
    {
        "id": "wall_breach_defense",
        "name": "🏰 Wall Breach Defense",
        "world": "aot",
        "description": "Server-wide AoT co-op raid! Participate in 5 co-op raids.",
        "goal": 5,
        "reward_currency": "expedition_medals",
        "reward_amount": 20,
    },
    {
        "id": "daily_login",
        "name": "📅 Daily Login Streak",
        "world": "all",
        "description": "Log in every day! Reach Day 7 for a bonus.",
        "goal": 7,
        "reward_currency": "world_gems",
        "reward_amount": 5,
    },
]


async def get_event_progress(user_id: int, event_id: str) -> int:
    user = await get_user(user_id)
    if not user:
        return 0
    return user.get("event_progress", {}).get(event_id, 0)


async def increment_event_progress(user_id: int, event_id: str, amount: int = 1):
    await users_col.update_one(
        {"user_id": user_id},
        {"$inc": {f"event_progress.{event_id}": amount}},
    )


async def get_all_users() -> list:
    cursor = users_col.find({}, {"user_id": 1, "weekly_pvp_score": 1, "world": 1})
    return await cursor.to_list(length=None)
