"""
Complete character roster for both worlds.
60 characters total: 30 Naruto, 30 Attack on Titan.
Images: picsum.photos are used as reliable placeholders.
To use real art, upload images to Cloudinary with the char ID as public_id,
then swap _img() to use _cld() instead of _ph().
"""
import random

CLOUD = "dlvzhfun5"

# Seed map — each character gets a unique consistent picsum photo
_SEED_MAP = {
    "jiraiya": 10, "itachi": 11, "pain": 12, "minato": 13,
    "naruto": 14, "sasuke": 15, "kakashi": 16, "might_guy": 17,
    "orochimaru": 18, "tsunade": 19,
    "sakura": 20, "hinata": 21, "gaara": 22, "rock_lee": 23, "neji": 24,
    "shikamaru": 25, "ino": 26, "choji": 27, "kiba": 28, "shino": 29,
    "tenten": 30, "yamato": 31, "sai": 32, "asuma": 33, "kurenai": 34,
    "iruka": 35, "konohamaru": 36, "ebisu": 37, "genma": 38, "raido": 39,
    "levi": 40, "erwin": 41, "zeke": 42,
    "eren": 43, "mikasa": 44, "reiner": 45, "bertholdt": 46, "annie": 47,
    "armin": 48, "hange": 49, "jean": 50, "pieck": 51, "porco": 52,
    "connie": 53, "sasha": 54, "historia": 55, "ymir": 56, "mike": 57,
    "eld": 58, "petra": 59, "oluo": 60, "falco": 61, "gabi": 62,
    "yelena": 63,
    "marco": 64, "gunther": 65, "daz": 66, "samuel": 67, "thomas": 68, "floch": 69,
}

def _img(char_id: str) -> str:
    """Primary: picsum.photos (always works). Each character gets a unique seed."""
    seed = _SEED_MAP.get(char_id, hash(char_id) % 1000 + 100)
    return f"https://picsum.photos/seed/mv{seed}/400/400"

def _cld(public_id: str) -> str:
    """Cloudinary URL (works once images are uploaded to the Cloudinary account)."""
    return f"https://res.cloudinary.com/{CLOUD}/image/upload/v1/multiverse/{public_id}.jpg"


# ── Rarity constants ───────────────────────────────────────────────────────────
RARITY_ORDER = ["common", "rare", "epic", "legendary", "world_class"]
RARITY_COLORS = {
    "common":      "⬜ Common",
    "rare":        "🟦 Rare",
    "epic":        "🟪 Epic",
    "legendary":   "🟧 Legendary",
    "world_class": "🌟 World-Class",
}
RARITY_SCRAP_VALUE = {
    "common": 1, "rare": 2, "epic": 5, "legendary": 10, "world_class": 20
}
PULL_RATES = {
    "common": 0.55, "rare": 0.30, "epic": 0.10, "legendary": 0.04, "world_class": 0.01
}

# ── Naruto World Characters ────────────────────────────────────────────────────
NARUTO_CHARACTERS = [
    # World-Class
    {
        "id": "jiraiya",      "name": "Jiraiya",           "world": "naruto",
        "rarity": "world_class", "atk": 99, "def": 85, "spd": 78,
        "ability": "Sage Mode", "ability_effect": "team_atk_bonus", "ability_value": 0.12,
        "img": _img("jiraiya"),
    },
    {
        "id": "itachi",       "name": "Itachi Uchiha",     "world": "naruto",
        "rarity": "world_class", "atk": 97, "def": 82, "spd": 91,
        "ability": "Tsukuyomi", "ability_effect": "enemy_spd_debuff", "ability_value": 0.15,
        "img": _img("itachi"),
    },
    {
        "id": "pain",         "name": "Pain / Nagato",     "world": "naruto",
        "rarity": "world_class", "atk": 96, "def": 88, "spd": 80,
        "ability": "Six Paths", "ability_effect": "team_def_bonus", "ability_value": 0.10,
        "img": _img("pain"),
    },
    {
        "id": "minato",       "name": "Minato Namikaze",   "world": "naruto",
        "rarity": "world_class", "atk": 98, "def": 78, "spd": 99,
        "ability": "Flying Thunder God", "ability_effect": "team_spd_bonus", "ability_value": 0.15,
        "img": _img("minato"),
    },
    # Legendary
    {
        "id": "naruto",       "name": "Naruto Uzumaki",    "world": "naruto",
        "rarity": "legendary", "atk": 95, "def": 70, "spd": 85,
        "ability": "Nine-Tails Boost", "ability_effect": "team_atk_bonus", "ability_value": 0.10,
        "img": _img("naruto"),
    },
    {
        "id": "sasuke",       "name": "Sasuke Uchiha",     "world": "naruto",
        "rarity": "legendary", "atk": 98, "def": 65, "spd": 90,
        "ability": "Chidori Stream", "ability_effect": "enemy_def_debuff", "ability_value": 0.12,
        "img": _img("sasuke"),
    },
    {
        "id": "kakashi",      "name": "Kakashi Hatake",    "world": "naruto",
        "rarity": "legendary", "atk": 92, "def": 80, "spd": 88,
        "ability": "Sharingan Copy", "ability_effect": "team_atk_bonus", "ability_value": 0.08,
        "img": _img("kakashi"),
    },
    {
        "id": "might_guy",    "name": "Might Guy",         "world": "naruto",
        "rarity": "legendary", "atk": 98, "def": 55, "spd": 99,
        "ability": "Eight Gates", "ability_effect": "team_spd_bonus", "ability_value": 0.20,
        "img": _img("might_guy"),
    },
    {
        "id": "orochimaru",   "name": "Orochimaru",        "world": "naruto",
        "rarity": "legendary", "atk": 85, "def": 82, "spd": 88,
        "ability": "Curse Mark", "ability_effect": "enemy_atk_debuff", "ability_value": 0.10,
        "img": _img("orochimaru"),
    },
    {
        "id": "tsunade",      "name": "Tsunade",           "world": "naruto",
        "rarity": "legendary", "atk": 90, "def": 92, "spd": 70,
        "ability": "Mitotic Regen", "ability_effect": "team_def_bonus", "ability_value": 0.15,
        "img": _img("tsunade"),
    },
    # Epic
    {
        "id": "sakura",       "name": "Sakura Haruno",     "world": "naruto",
        "rarity": "epic", "atk": 75, "def": 90, "spd": 70,
        "ability": "Byakugo Seal", "ability_effect": "team_def_bonus", "ability_value": 0.08,
        "img": _img("sakura"),
    },
    {
        "id": "hinata",       "name": "Hinata Hyuga",      "world": "naruto",
        "rarity": "epic", "atk": 68, "def": 78, "spd": 80,
        "ability": "Gentle Fist", "ability_effect": "enemy_def_debuff", "ability_value": 0.08,
        "img": _img("hinata"),
    },
    {
        "id": "gaara",        "name": "Gaara",             "world": "naruto",
        "rarity": "epic", "atk": 60, "def": 95, "spd": 65,
        "ability": "Sand Shield", "ability_effect": "team_def_bonus", "ability_value": 0.12,
        "img": _img("gaara"),
    },
    {
        "id": "rock_lee",     "name": "Rock Lee",          "world": "naruto",
        "rarity": "epic", "atk": 80, "def": 60, "spd": 95,
        "ability": "Primary Lotus", "ability_effect": "team_spd_bonus", "ability_value": 0.10,
        "img": _img("rock_lee"),
    },
    {
        "id": "neji",         "name": "Neji Hyuga",        "world": "naruto",
        "rarity": "epic", "atk": 78, "def": 75, "spd": 82,
        "ability": "64 Palms", "ability_effect": "enemy_spd_debuff", "ability_value": 0.10,
        "img": _img("neji"),
    },
    # Rare
    {
        "id": "shikamaru",    "name": "Shikamaru",         "world": "naruto",
        "rarity": "rare", "atk": 55, "def": 68, "spd": 72,
        "ability": "Shadow Bind", "ability_effect": "enemy_spd_debuff", "ability_value": 0.08,
        "img": _img("shikamaru"),
    },
    {
        "id": "ino",          "name": "Ino Yamanaka",      "world": "naruto",
        "rarity": "rare", "atk": 58, "def": 65, "spd": 75,
        "ability": "Mind Transfer", "ability_effect": "enemy_atk_debuff", "ability_value": 0.06,
        "img": _img("ino"),
    },
    {
        "id": "choji",        "name": "Choji Akimichi",    "world": "naruto",
        "rarity": "rare", "atk": 65, "def": 80, "spd": 55,
        "ability": "Expansion Jutsu", "ability_effect": "team_def_bonus", "ability_value": 0.06,
        "img": _img("choji"),
    },
    {
        "id": "kiba",         "name": "Kiba Inuzuka",      "world": "naruto",
        "rarity": "rare", "atk": 62, "def": 60, "spd": 78,
        "ability": "Fang over Fang", "ability_effect": "team_atk_bonus", "ability_value": 0.06,
        "img": _img("kiba"),
    },
    {
        "id": "shino",        "name": "Shino Aburame",     "world": "naruto",
        "rarity": "rare", "atk": 60, "def": 70, "spd": 68,
        "ability": "Insect Clone", "ability_effect": "enemy_def_debuff", "ability_value": 0.06,
        "img": _img("shino"),
    },
    {
        "id": "tenten",       "name": "Tenten",            "world": "naruto",
        "rarity": "rare", "atk": 65, "def": 62, "spd": 70,
        "ability": "Twin Rising Dragons", "ability_effect": "team_atk_bonus", "ability_value": 0.05,
        "img": _img("tenten"),
    },
    {
        "id": "yamato",       "name": "Yamato",            "world": "naruto",
        "rarity": "rare", "atk": 65, "def": 72, "spd": 68,
        "ability": "Wood Style", "ability_effect": "team_def_bonus", "ability_value": 0.07,
        "img": _img("yamato"),
    },
    {
        "id": "sai",          "name": "Sai",               "world": "naruto",
        "rarity": "rare", "atk": 62, "def": 60, "spd": 75,
        "ability": "Super Beast Scroll", "ability_effect": "team_spd_bonus", "ability_value": 0.06,
        "img": _img("sai"),
    },
    {
        "id": "asuma",        "name": "Asuma Sarutobi",    "world": "naruto",
        "rarity": "rare", "atk": 68, "def": 65, "spd": 70,
        "ability": "Wind Blades", "ability_effect": "team_atk_bonus", "ability_value": 0.06,
        "img": _img("asuma"),
    },
    {
        "id": "kurenai",      "name": "Kurenai Yuhi",      "world": "naruto",
        "rarity": "rare", "atk": 60, "def": 65, "spd": 72,
        "ability": "Genjutsu Weave", "ability_effect": "enemy_atk_debuff", "ability_value": 0.07,
        "img": _img("kurenai"),
    },
    # Common
    {
        "id": "iruka",        "name": "Iruka Umino",       "world": "naruto",
        "rarity": "common", "atk": 45, "def": 55, "spd": 50,
        "ability": "Academy Jutsu", "ability_effect": None, "ability_value": 0,
        "img": _img("iruka"),
    },
    {
        "id": "konohamaru",   "name": "Konohamaru",        "world": "naruto",
        "rarity": "common", "atk": 40, "def": 45, "spd": 55,
        "ability": "Rasengan (Mini)", "ability_effect": None, "ability_value": 0,
        "img": _img("konohamaru"),
    },
    {
        "id": "ebisu",        "name": "Ebisu",             "world": "naruto",
        "rarity": "common", "atk": 38, "def": 50, "spd": 45,
        "ability": "Tutor Stance", "ability_effect": None, "ability_value": 0,
        "img": _img("ebisu"),
    },
    {
        "id": "genma",        "name": "Genma Shiranui",    "world": "naruto",
        "rarity": "common", "atk": 42, "def": 52, "spd": 48,
        "ability": "Senbon Throw", "ability_effect": None, "ability_value": 0,
        "img": _img("genma"),
    },
    {
        "id": "raido",        "name": "Raido Namiashi",    "world": "naruto",
        "rarity": "common", "atk": 40, "def": 50, "spd": 47,
        "ability": "Guard Stance", "ability_effect": None, "ability_value": 0,
        "img": _img("raido"),
    },
]

# ── Attack on Titan World Characters ──────────────────────────────────────────
AOT_CHARACTERS = [
    # World-Class
    {
        "id": "levi",         "name": "Levi Ackerman",     "world": "aot",
        "rarity": "world_class", "atk": 99, "def": 75, "spd": 99,
        "ability": "Ackerman Power", "ability_effect": "team_atk_bonus", "ability_value": 0.15,
        "img": _img("levi"),
    },
    {
        "id": "erwin",        "name": "Erwin Smith",       "world": "aot",
        "rarity": "world_class", "atk": 88, "def": 90, "spd": 72,
        "ability": "Commander's Will", "ability_effect": "team_def_bonus", "ability_value": 0.15,
        "img": _img("erwin"),
    },
    {
        "id": "zeke",         "name": "Zeke Yeager",       "world": "aot",
        "rarity": "world_class", "atk": 94, "def": 85, "spd": 82,
        "ability": "Beast Titan Throw", "ability_effect": "enemy_def_debuff", "ability_value": 0.15,
        "img": _img("zeke"),
    },
    # Legendary
    {
        "id": "eren",         "name": "Eren Yeager",       "world": "aot",
        "rarity": "legendary", "atk": 95, "def": 80, "spd": 75,
        "ability": "Attack Titan", "ability_effect": "team_atk_bonus", "ability_value": 0.10,
        "img": _img("eren"),
    },
    {
        "id": "mikasa",       "name": "Mikasa Ackerman",   "world": "aot",
        "rarity": "legendary", "atk": 96, "def": 82, "spd": 90,
        "ability": "Ackerman Reflex", "ability_effect": "team_spd_bonus", "ability_value": 0.12,
        "img": _img("mikasa"),
    },
    {
        "id": "reiner",       "name": "Reiner Braun",      "world": "aot",
        "rarity": "legendary", "atk": 85, "def": 95, "spd": 62,
        "ability": "Armored Titan", "ability_effect": "team_def_bonus", "ability_value": 0.12,
        "img": _img("reiner"),
    },
    {
        "id": "bertholdt",    "name": "Bertholdt Hoover",  "world": "aot",
        "rarity": "legendary", "atk": 98, "def": 60, "spd": 55,
        "ability": "Colossal Steam", "ability_effect": "enemy_spd_debuff", "ability_value": 0.15,
        "img": _img("bertholdt"),
    },
    {
        "id": "annie",        "name": "Annie Leonhart",    "world": "aot",
        "rarity": "legendary", "atk": 92, "def": 88, "spd": 85,
        "ability": "Female Titan Cry", "ability_effect": "enemy_atk_debuff", "ability_value": 0.12,
        "img": _img("annie"),
    },
    # Epic
    {
        "id": "armin",        "name": "Armin Arlert",      "world": "aot",
        "rarity": "epic", "atk": 55, "def": 72, "spd": 78,
        "ability": "Tactical Genius", "ability_effect": "team_atk_bonus", "ability_value": 0.08,
        "img": _img("armin"),
    },
    {
        "id": "hange",        "name": "Hange Zoë",         "world": "aot",
        "rarity": "epic", "atk": 70, "def": 75, "spd": 72,
        "ability": "Titan Research", "ability_effect": "enemy_def_debuff", "ability_value": 0.08,
        "img": _img("hange"),
    },
    {
        "id": "jean",         "name": "Jean Kirstein",     "world": "aot",
        "rarity": "epic", "atk": 68, "def": 70, "spd": 74,
        "ability": "Leadership Call", "ability_effect": "team_def_bonus", "ability_value": 0.07,
        "img": _img("jean"),
    },
    {
        "id": "pieck",        "name": "Pieck Finger",      "world": "aot",
        "rarity": "epic", "atk": 72, "def": 80, "spd": 65,
        "ability": "Cart Titan Supply", "ability_effect": "team_def_bonus", "ability_value": 0.08,
        "img": _img("pieck"),
    },
    {
        "id": "porco",        "name": "Porco Galliard",    "world": "aot",
        "rarity": "epic", "atk": 78, "def": 75, "spd": 68,
        "ability": "Jaw Titan Rend", "ability_effect": "enemy_def_debuff", "ability_value": 0.10,
        "img": _img("porco"),
    },
    # Rare
    {
        "id": "connie",       "name": "Connie Springer",   "world": "aot",
        "rarity": "rare", "atk": 62, "def": 58, "spd": 78,
        "ability": "Quick Maneuver", "ability_effect": "team_spd_bonus", "ability_value": 0.06,
        "img": _img("connie"),
    },
    {
        "id": "sasha",        "name": "Sasha Blouse",      "world": "aot",
        "rarity": "rare", "atk": 65, "def": 55, "spd": 82,
        "ability": "Potato Resolve", "ability_effect": "team_spd_bonus", "ability_value": 0.07,
        "img": _img("sasha"),
    },
    {
        "id": "historia",     "name": "Historia Reiss",    "world": "aot",
        "rarity": "rare", "atk": 58, "def": 72, "spd": 68,
        "ability": "Royal Morale", "ability_effect": "team_def_bonus", "ability_value": 0.06,
        "img": _img("historia"),
    },
    {
        "id": "ymir",         "name": "Ymir",              "world": "aot",
        "rarity": "rare", "atk": 72, "def": 68, "spd": 70,
        "ability": "Jaw Bite", "ability_effect": "enemy_def_debuff", "ability_value": 0.07,
        "img": _img("ymir"),
    },
    {
        "id": "mike",         "name": "Mike Zacharias",    "world": "aot",
        "rarity": "rare", "atk": 70, "def": 68, "spd": 65,
        "ability": "Scent Detection", "ability_effect": "team_atk_bonus", "ability_value": 0.06,
        "img": _img("mike"),
    },
    {
        "id": "eld",          "name": "Eld Jinn",          "world": "aot",
        "rarity": "rare", "atk": 65, "def": 62, "spd": 68,
        "ability": "Corps Veteran", "ability_effect": "team_def_bonus", "ability_value": 0.05,
        "img": _img("eld"),
    },
    {
        "id": "petra",        "name": "Petra Ral",         "world": "aot",
        "rarity": "rare", "atk": 62, "def": 65, "spd": 72,
        "ability": "Elite Scout", "ability_effect": "team_spd_bonus", "ability_value": 0.06,
        "img": _img("petra"),
    },
    {
        "id": "oluo",         "name": "Oluo Bozado",       "world": "aot",
        "rarity": "rare", "atk": 63, "def": 60, "spd": 66,
        "ability": "Tongue Biting Cool", "ability_effect": "team_atk_bonus", "ability_value": 0.05,
        "img": _img("oluo"),
    },
    {
        "id": "falco",        "name": "Falco Grice",       "world": "aot",
        "rarity": "rare", "atk": 60, "def": 65, "spd": 72,
        "ability": "Jaw Wings", "ability_effect": "team_spd_bonus", "ability_value": 0.06,
        "img": _img("falco"),
    },
    {
        "id": "gabi",         "name": "Gabi Braun",        "world": "aot",
        "rarity": "rare", "atk": 65, "def": 58, "spd": 78,
        "ability": "Warrior Cadet", "ability_effect": "team_atk_bonus", "ability_value": 0.06,
        "img": _img("gabi"),
    },
    {
        "id": "yelena",       "name": "Yelena",            "world": "aot",
        "rarity": "rare", "atk": 62, "def": 68, "spd": 65,
        "ability": "Zeke's Devotion", "ability_effect": "team_def_bonus", "ability_value": 0.06,
        "img": _img("yelena"),
    },
    # Common
    {
        "id": "marco",        "name": "Marco Bott",        "world": "aot",
        "rarity": "common", "atk": 48, "def": 52, "spd": 50,
        "ability": "Kind Command", "ability_effect": None, "ability_value": 0,
        "img": _img("marco"),
    },
    {
        "id": "gunther",      "name": "Gunther Schultz",   "world": "aot",
        "rarity": "common", "atk": 50, "def": 55, "spd": 52,
        "ability": "Steady Blade", "ability_effect": None, "ability_value": 0,
        "img": _img("gunther"),
    },
    {
        "id": "daz",          "name": "Daz",               "world": "aot",
        "rarity": "common", "atk": 45, "def": 50, "spd": 48,
        "ability": "Survivor Grit", "ability_effect": None, "ability_value": 0,
        "img": _img("daz"),
    },
    {
        "id": "samuel",       "name": "Samuel",            "world": "aot",
        "rarity": "common", "atk": 42, "def": 48, "spd": 45,
        "ability": "Wall Duty", "ability_effect": None, "ability_value": 0,
        "img": _img("samuel"),
    },
    {
        "id": "thomas",       "name": "Thomas Wagner",     "world": "aot",
        "rarity": "common", "atk": 40, "def": 45, "spd": 44,
        "ability": "Cadet Spirit", "ability_effect": None, "ability_value": 0,
        "img": _img("thomas"),
    },
    {
        "id": "floch",        "name": "Floch Forster",     "world": "aot",
        "rarity": "common", "atk": 48, "def": 50, "spd": 52,
        "ability": "Yeagerist Zeal", "ability_effect": None, "ability_value": 0,
        "img": _img("floch"),
    },
]

ALL_CHARACTERS = NARUTO_CHARACTERS + AOT_CHARACTERS

# ── Lookup helpers ─────────────────────────────────────────────────────────────
_CHAR_BY_ID = {c["id"]: c for c in ALL_CHARACTERS}
_NARUTO_BY_RARITY = {}
_AOT_BY_RARITY = {}
for _c in NARUTO_CHARACTERS:
    _NARUTO_BY_RARITY.setdefault(_c["rarity"], []).append(_c)
for _c in AOT_CHARACTERS:
    _AOT_BY_RARITY.setdefault(_c["rarity"], []).append(_c)


def get_char(char_id: str) -> dict | None:
    return _CHAR_BY_ID.get(char_id)


def get_chars_by_world_rarity(world: str, rarity: str) -> list:
    pool = _NARUTO_BY_RARITY if world == "naruto" else _AOT_BY_RARITY
    return pool.get(rarity, [])


def random_char_by_rarity(world: str, rarity: str) -> dict | None:
    pool = get_chars_by_world_rarity(world, rarity)
    return random.choice(pool) if pool else None


def get_world_chars(world: str) -> list:
    return NARUTO_CHARACTERS if world == "naruto" else AOT_CHARACTERS


def star_multiplier(stars: int) -> float:
    """Returns stat multiplier for a given star level (1-5)."""
    return 1.0 + (stars - 1) * 0.20


def get_char_stats(char: dict, stars: int = 1) -> tuple[int, int, int]:
    """Return (ATK, DEF, SPD) with star multiplier applied."""
    mult = star_multiplier(stars)
    return (
        int(char["atk"] * mult),
        int(char["def"] * mult),
        int(char["spd"] * mult),
    )


def rarity_label(rarity: str) -> str:
    return RARITY_COLORS.get(rarity, rarity.title())
