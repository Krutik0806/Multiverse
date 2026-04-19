"""
Battle formula engine — team power, win chance, PvP damage.
"""
from game.characters import get_char, get_char_stats

FORMATION_MULTIPLIERS = {
    "standard":  1.00,
    "offensive": 1.15,
    "defensive": 1.10,
    "balanced":  1.05,
}

MISSION_ENEMY_POWER = {
    # Naruto
    "d_rank":   350,
    "c_rank":   600,
    "b_rank":   950,
    "a_rank":   1400,
    "s_rank":   2200,
    # AoT (mapped to same keys internally)
    "patrol":         350,
    "recon":          600,
    "titan_hunt":     950,
    "bridge_defense": 1400,
    "wall_breach":    2200,
}


def calc_char_power(char_data: dict, stars: int = 1) -> float:
    atk, def_, spd = get_char_stats(char_data, stars)
    return atk * 0.40 + def_ * 0.35 + spd * 0.25


def calc_team_power(team_chars: list[tuple[dict, int]], formation: str = "standard", sensei_id: str = None) -> float:
    """
    team_chars: list of (char_data_dict, stars) tuples
    Returns total team power with formation multiplier and sensei bonus.
    """
    base_power = sum(calc_char_power(c, s) for c, s in team_chars)
    mult = FORMATION_MULTIPLIERS.get(formation, 1.0)

    # Sensei ability bonus
    if sensei_id:
        sensei_data = get_char(sensei_id)
        if sensei_data and sensei_data.get("ability_effect") == "team_atk_bonus":
            # Sensei adds their value to the multiplier on top of formation
            mult += sensei_data.get("ability_value", 0)

    return base_power * mult


def calc_win_chance(team_power: float, enemy_power: float) -> float:
    """Returns win probability 5–95%."""
    raw = team_power / (team_power + enemy_power) if (team_power + enemy_power) > 0 else 0.5
    return min(0.95, max(0.05, raw))


def pvp_round_damage(attacker_atk: int, defender_def: int, attacker_spd: int) -> float:
    return max(1, (attacker_atk * 1.2 - defender_def) + (attacker_spd / 2))


def simulate_pvp(team1_chars: list[tuple[dict, int]], form1: str, sensei1: str,
                 team2_chars: list[tuple[dict, int]], form2: str, sensei2: str) -> dict:
    """
    Full auto-battle simulation. Returns winner (1 or 2) and battle log.
    """
    import random

    p1 = calc_team_power(team1_chars, form1, sensei1)
    p2 = calc_team_power(team2_chars, form2, sensei2)

    hp1 = p1 * 10
    hp2 = p2 * 10

    # Aggregate stats for damage calc
    def agg(chars):
        if not chars:
            return 0, 0, 0
        total_a = sum(get_char_stats(c, s)[0] for c, s in chars)
        total_d = sum(get_char_stats(c, s)[1] for c, s in chars)
        total_s = sum(get_char_stats(c, s)[2] for c, s in chars)
        n = len(chars)
        return total_a // n, total_d // n, total_s // n

    a1, d1, s1 = agg(team1_chars)
    a2, d2, s2 = agg(team2_chars)

    log = []
    turn = 0
    while hp1 > 0 and hp2 > 0 and turn < 20:
        turn += 1
        dmg_to_2 = pvp_round_damage(a1, d2, s1) * random.uniform(0.85, 1.15)
        dmg_to_1 = pvp_round_damage(a2, d1, s2) * random.uniform(0.85, 1.15)
        hp2 -= dmg_to_2
        hp1 -= dmg_to_1
        log.append(f"⚔️ Turn {turn}: You dealt {int(dmg_to_2)} • Took {int(dmg_to_1)}")
        if len(log) >= 5:
            break

    winner = 1 if hp1 > hp2 else 2
    return {"winner": winner, "log": log, "team1_hp": max(0, int(hp1)), "team2_hp": max(0, int(hp2))}
