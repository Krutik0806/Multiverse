"""
Mission engine: cooldowns (Redis), stamina, rewards, drop rates.
Rebalanced enemy powers so new players (1 char) can win D/Patrol missions.
Added get_mission_preview() for the confirmation-step UI.
"""
import random
from database.redis_client import redis
from database.mongo import (
    subtract_stamina, add_currency, add_xp,
    add_char_to_user, get_user, use_free_mission,
    increment_event_progress,
)
from game.characters import random_char_by_rarity, get_world_chars
from game.characters import get_char, get_char_stats

# ── REBALANCED enemy powers (drastically reduced so new players can win) ───────
# Old values: D=350, C=600, B=950, A=1400, S=2200
# New values calibrated for a 1-char starter team (~50 power):
MISSION_ENEMY_POWER = {
    "d_rank":         60,    # 1-char Iruka (~50pwr) wins ~45% + min override → 75%
    "c_rank":         180,   # needs 2-3 chars
    "b_rank":         400,   # needs a solid team
    "a_rank":         750,   # needs strong team + formation
    "s_rank":         1300,  # endgame only
    "patrol":         60,
    "recon":          180,
    "titan_hunt":     400,
    "bridge_defense": 750,
    "wall_breach":    1300,
}

# Minimum win chance per rank (floor so beginners always have a shot at D-rank)
MISSION_MIN_WIN = {
    "d_rank": 0.75, "c_rank": 0.55, "b_rank": 0.35,
    "a_rank": 0.20, "s_rank": 0.10,
    "patrol": 0.75, "recon": 0.55, "titan_hunt": 0.35,
    "bridge_defense": 0.20, "wall_breach": 0.10,
}

# ── Mission definitions ────────────────────────────────────────────────────────
MISSIONS = {
    "naruto": {
        "d_rank": {
            "label":       "D-Rank Mission",
            "emoji":       "📜",
            "desc":        "Village chores & low-level tasks.",
            "stamina":     5,
            "cooldown":    300,     # 5 min
            "xp":          50,
            "coin":        100,
            "coin_key":    "ryo",
            "drop_chance": 0.05,
            "min_level":   1,
        },
        "c_rank": {
            "label":       "C-Rank Mission",
            "emoji":       "🗡️",
            "desc":        "Guard duty or low-risk escort.",
            "stamina":     10,
            "cooldown":    900,     # 15 min
            "xp":          100,
            "coin":        200,
            "coin_key":    "ryo",
            "drop_chance": 0.08,
            "min_level":   5,
        },
        "b_rank": {
            "label":       "B-Rank Mission",
            "emoji":       "⚔️",
            "desc":        "Confronting rogue ninja.",
            "stamina":     15,
            "cooldown":    1800,    # 30 min
            "xp":          175,
            "coin":        350,
            "coin_key":    "ryo",
            "drop_chance": 0.12,
            "min_level":   10,
        },
        "a_rank": {
            "label":       "A-Rank Mission",
            "emoji":       "🔥",
            "desc":        "Highly dangerous assassination target.",
            "stamina":     20,
            "cooldown":    3600,    # 1 hr
            "xp":          250,
            "coin":        500,
            "coin_key":    "ryo",
            "drop_chance": 0.18,
            "min_level":   20,
        },
        "s_rank": {
            "label":       "S-Rank Mission",
            "emoji":       "💥",
            "desc":        "Legendary threat — life on the line.",
            "stamina":     30,
            "cooldown":    10800,   # 3 hrs
            "xp":          400,
            "coin":        800,
            "coin_key":    "ryo",
            "drop_chance": 0.25,
            "min_level":   30,
        },
    },
    "aot": {
        "patrol": {
            "label":       "Wall Patrol",
            "emoji":       "🏰",
            "desc":        "Routine wall watch duty.",
            "stamina":     5,
            "cooldown":    300,
            "xp":          50,
            "coin":        100,
            "coin_key":    "maria_gold",
            "drop_chance": 0.05,
            "min_level":   1,
        },
        "recon": {
            "label":       "Recon Mission",
            "emoji":       "🔭",
            "desc":        "Scout titan activity outside the walls.",
            "stamina":     10,
            "cooldown":    900,
            "xp":          100,
            "coin":        200,
            "coin_key":    "maria_gold",
            "drop_chance": 0.08,
            "min_level":   5,
        },
        "titan_hunt": {
            "label":       "Titan Hunt",
            "emoji":       "⚡",
            "desc":        "Track and eliminate roaming titans.",
            "stamina":     15,
            "cooldown":    1800,
            "xp":          175,
            "coin":        350,
            "coin_key":    "maria_gold",
            "drop_chance": 0.12,
            "min_level":   10,
        },
        "bridge_defense": {
            "label":       "Bridge Defense",
            "emoji":       "🌉",
            "desc":        "Protect critical supply routes.",
            "stamina":     20,
            "cooldown":    3600,
            "xp":          250,
            "coin":        500,
            "coin_key":    "maria_gold",
            "drop_chance": 0.18,
            "min_level":   20,
        },
        "wall_breach": {
            "label":       "Wall Breach",
            "emoji":       "💣",
            "desc":        "Repel a colossal titan assault.",
            "stamina":     30,
            "cooldown":    10800,
            "xp":          400,
            "coin":        800,
            "coin_key":    "maria_gold",
            "drop_chance": 0.25,
            "min_level":   30,
        },
    },
}


def get_missions_for_world(world: str) -> dict:
    return MISSIONS.get(world, {})


def _calc_win_chance(team_power: float, mission_key: str) -> float:
    """Win chance with floor so beginners always have a real shot."""
    enemy_power = MISSION_ENEMY_POWER.get(mission_key, 350)
    raw = team_power / (team_power + enemy_power) if (team_power + enemy_power) > 0 else 0.5
    floor = MISSION_MIN_WIN.get(mission_key, 0.10)
    return min(0.95, max(floor, raw))


def _calc_team_power(team_ids: list, formation: str, sensei_id: str) -> float:
    """Calculate actual team power from stored team."""
    from game.battle import calc_team_power
    team_chars = [(get_char(cid), 1) for cid in team_ids if get_char(cid)]
    if not team_chars:
        return 0
    return calc_team_power(team_chars, formation, sensei_id)


async def get_mission_preview(user_id: int, mission_key: str) -> dict:
    """
    Returns mission preview info (win chance, cost, rewards) WITHOUT running it.
    Used for the confirmation step UI.
    """
    user = await get_user(user_id)
    if not user:
        return {"error": "Register first! /start"}

    world = user["world"]
    mission_def = MISSIONS[world].get(mission_key)
    if not mission_def:
        return {"error": "Invalid mission!"}

    if user["level"] < mission_def["min_level"]:
        return {"error": f"Need Level {mission_def['min_level']}!"}

    # Cooldown check
    remaining = await redis.get_cooldown(user_id, mission_key)
    if remaining > 0:
        mins, secs = divmod(remaining, 60)
        cd_str = f"{mins}m {secs}s" if mins > 0 else f"{secs}s"
        return {"error": f"On cooldown! Wait {cd_str}"}

    team_power = _calc_team_power(
        user.get("team", []), user.get("formation", "standard"), user.get("sensei_id")
    )
    win_chance = _calc_win_chance(team_power, mission_key)

    # Free mission check
    from config import FREE_MISSIONS_PER_DAY
    from datetime import datetime, timezone
    today = datetime.now(timezone.utc).date().isoformat()
    free_used = user.get("free_missions_today", 0) if user.get("free_missions_date") == today else 0
    is_free = free_used < FREE_MISSIONS_PER_DAY

    return {
        "ok":          True,
        "mission":     mission_def["label"],
        "emoji":       mission_def["emoji"],
        "desc":        mission_def["desc"],
        "win_chance":  int(win_chance * 100),
        "team_power":  int(team_power),
        "enemy_power": MISSION_ENEMY_POWER.get(mission_key, 0),
        "stamina":     mission_def["stamina"],
        "cooldown":    mission_def["cooldown"],
        "xp":          mission_def["xp"],
        "coin":        mission_def["coin"],
        "coin_key":    mission_def["coin_key"],
        "is_free":     is_free,
        "current_stamina": user["stamina"],
    }


async def run_mission(user_id: int, mission_key: str) -> dict:
    """Execute a mission. Returns result dict."""
    user = await get_user(user_id)
    if not user:
        return {"error": "Register first! /start"}

    world = user["world"]
    mission_def = MISSIONS[world].get(mission_key)
    if not mission_def:
        return {"error": "Invalid mission!"}

    if user["level"] < mission_def["min_level"]:
        return {"error": f"Need Level {mission_def['min_level']}!"}

    # Cooldown check
    remaining = await redis.get_cooldown(user_id, mission_key)
    if remaining > 0:
        mins, secs = divmod(remaining, 60)
        cd_str = f"{mins}m {secs}s" if mins > 0 else f"{secs}s"
        return {"error": f"On cooldown! Wait {cd_str}"}

    # Stamina / free missions
    is_free = await use_free_mission(user_id)
    if not is_free:
        if not await subtract_stamina(user_id, mission_def["stamina"]):
            return {"error": f"Not enough stamina! ({user['stamina']}/{mission_def['stamina']} needed)"}

    # Calculate team power & win chance
    team_power = _calc_team_power(
        user.get("team", []), user.get("formation", "standard"), user.get("sensei_id")
    )
    win_chance = _calc_win_chance(team_power, mission_key)

    # Roll
    success = random.random() < win_chance

    # Set cooldown AFTER deducting stamina
    await redis.set_cooldown(user_id, mission_key, mission_def["cooldown"])

    if not success:
        return {
            "success":    False,
            "mission":    mission_def["label"],
            "emoji":      mission_def["emoji"],
            "win_chance": int(win_chance * 100),
            "team_power": int(team_power),
            "is_free":    is_free,
        }

    # Rewards (slight variance)
    xp_gain   = mission_def["xp"]   + random.randint(0, 20)
    coin_gain = mission_def["coin"] + random.randint(0, 50)

    await add_xp(user_id, xp_gain)
    await add_currency(user_id, mission_def["coin_key"], coin_gain)

    # Character drop
    dropped_char = None
    if random.random() < mission_def["drop_chance"]:
        if mission_key in ("d_rank", "patrol"):
            rarity_pool = ["common", "rare"]
        elif mission_key in ("c_rank", "recon", "b_rank", "titan_hunt"):
            rarity_pool = ["common", "rare", "epic"]
        else:
            rarity_pool = ["rare", "epic", "legendary"]
        rarity = random.choice(rarity_pool)
        char = random_char_by_rarity(world, rarity)
        if char:
            await add_char_to_user(user_id, char["id"])
            dropped_char = char

    await increment_event_progress(user_id, "daily_login", 1)

    return {
        "success":      True,
        "mission":      mission_def["label"],
        "emoji":        mission_def["emoji"],
        "win_chance":   int(win_chance * 100),
        "team_power":   int(team_power),
        "xp":           xp_gain,
        "coin":         coin_gain,
        "coin_key":     mission_def["coin_key"],
        "dropped_char": dropped_char,
        "is_free":      is_free,
    }
