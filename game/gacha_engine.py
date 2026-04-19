"""
Gacha engine: single pull, 10-pull, pity system, duplicate handling.
Pity counter stored in MongoDB; pull logic is purely server-side.
"""
import random
from game.characters import (
    PULL_RATES, RARITY_ORDER, random_char_by_rarity,
    get_chars_by_world_rarity,
)
from database.mongo import (
    get_pity, increment_pity, reset_pity, add_char_to_user,
    subtract_currency, get_user,
)
from config import GACHA_SINGLE_COST, GACHA_TEN_COST, PITY_THRESHOLD


def _roll_rarity(world: str, force_rare_plus: bool = False) -> str:
    """Roll a rarity tier. If force_rare_plus, guaranteed Rare or higher."""
    rates = PULL_RATES.copy()
    if force_rare_plus:
        rates.pop("common", None)
        total = sum(rates.values())
        rates = {k: v / total for k, v in rates.items()}

    roll = random.random()
    cumulative = 0.0
    for rarity in ["world_class", "legendary", "epic", "rare", "common"]:
        cumulative += rates.get(rarity, 0)
        if roll < cumulative:
            return rarity
    return "common"


async def _do_single_pull(user_id: int, world: str, force_legendary: bool = False, force_rare_plus: bool = False) -> dict:
    """Internal single pull. Returns pulled character data dict + metadata."""
    if force_legendary:
        rarity = "legendary"
    elif force_rare_plus:
        rarity = _roll_rarity(world, force_rare_plus=True)
    else:
        rarity = _roll_rarity(world)

    char = random_char_by_rarity(world, rarity)
    if not char:
        # Fallback: pick any character of that world
        from game.characters import get_world_chars
        all_chars = get_world_chars(world)
        char = random.choice(all_chars) if all_chars else None

    if not char:
        return {"error": "No characters available"}

    # Update pity
    if rarity in ("legendary", "world_class"):
        await reset_pity(user_id)
        is_pity = force_legendary
    else:
        await increment_pity(user_id)
        is_pity = False

    # Add to collection
    result = await add_char_to_user(user_id, char["id"])

    return {
        "char_id":       char["id"],
        "name":          char["name"],
        "rarity":        char["rarity"],
        "img":           char["img"],
        "is_duplicate":  result["is_duplicate"],
        "stars":         result["stars"],
        "scraps":        result["scraps"],
        "is_pity":       is_pity,
    }


async def single_pull(user_id: int) -> dict:
    """
    Perform one gacha pull. Deducts currency, checks pity.
    Returns pull result dict or {"error": "..."}.
    """
    user = await get_user(user_id)
    if not user:
        return {"error": "User not found."}

    world = user["world"]
    currency = "ryo" if world == "naruto" else "maria_gold"

    # Deduct cost
    if not await subtract_currency(user_id, currency, GACHA_SINGLE_COST):
        sym = "Ryo" if world == "naruto" else "Maria Gold"
        return {"error": f"Need {GACHA_SINGLE_COST} {sym}!"}

    # Check pity
    pity = await get_pity(user_id)
    force_legendary = pity >= PITY_THRESHOLD

    return await _do_single_pull(user_id, world, force_legendary=force_legendary)


async def ten_pull(user_id: int) -> list[dict]:
    """
    Perform 10 gacha pulls. Position 10 guaranteed Rare+. Pity carried across pulls.
    Returns list of 10 pull result dicts or single {"error": "..."} in a list.
    """
    user = await get_user(user_id)
    if not user:
        return [{"error": "User not found."}]

    world = user["world"]
    currency = "ryo" if world == "naruto" else "maria_gold"

    if not await subtract_currency(user_id, currency, GACHA_TEN_COST):
        sym = "Ryo" if world == "naruto" else "Maria Gold"
        return [{"error": f"Need {GACHA_TEN_COST} {sym}!"}]

    results = []
    for i in range(10):
        pity = await get_pity(user_id)
        force_legendary = pity >= PITY_THRESHOLD
        force_rare_plus = (i == 9)  # Position 10 guaranteed Rare+
        result = await _do_single_pull(
            user_id, world,
            force_legendary=force_legendary,
            force_rare_plus=force_rare_plus and not force_legendary,
        )
        results.append(result)

    return results
