"""
Progression system: XP tables, level caps, rank thresholds.
"""

# XP required to go FROM level N to level N+1
def xp_for_level(level: int) -> int:
    """XP needed to reach the next level from `level`."""
    if level <= 0:
        return 0
    return int(100 * (level ** 1.5))


def total_xp_for_level(level: int) -> int:
    """Cumulative XP to reach `level` from level 1."""
    return sum(xp_for_level(l) for l in range(1, level))


def xp_bar(current_xp: int, level: int, bar_len: int = 10) -> str:
    needed = xp_for_level(level + 1)
    if needed == 0:
        return "█" * bar_len
    filled = int(bar_len * current_xp / needed)
    return "█" * filled + "░" * (bar_len - filled)


# ── Rank thresholds ────────────────────────────────────────────────────────────
NARUTO_RANKS = [
    (1,  "Genin"),
    (11, "Chuunin"),
    (21, "Jonin"),
    (36, "ANBU"),
    (51, "Kage"),
]

AOT_RANKS = [
    (1,  "Cadet"),
    (11, "Scout"),
    (21, "Soldier"),
    (36, "Captain"),
    (51, "Commander"),
]


def rank_for_level(level: int, world: str) -> str:
    ranks = NARUTO_RANKS if world == "naruto" else AOT_RANKS
    current = ranks[0][1]
    for threshold, rank in ranks:
        if level >= threshold:
            current = rank
    return current


def rank_emoji(rank: str) -> str:
    emojis = {
        "Genin": "🟢", "Chuunin": "🔵", "Jonin": "🟣",
        "ANBU": "🔴", "Kage": "⭐",
        "Cadet": "🟢", "Scout": "🔵", "Soldier": "🟣",
        "Captain": "🔴", "Commander": "⭐",
    }
    return emojis.get(rank, "⚪")


def stamina_bar(current: int, maximum: int = 100, bar_len: int = 10) -> str:
    filled = int(bar_len * current / maximum)
    return "💚" * filled + "🖤" * (bar_len - filled)


# ── World Lobby unlock ─────────────────────────────────────────────────────────
WORLD_LOBBY_LEVEL = 10


def can_access_world_lobby(level: int) -> bool:
    return level >= WORLD_LOBBY_LEVEL


# ── Offline XP trickle ─────────────────────────────────────────────────────────
def calc_offline_xp(hours: float) -> int:
    from config import OFFLINE_XP_RATE
    return int(hours * OFFLINE_XP_RATE)
