# Catalog — Server Module. Everything collectable in Busy Bun, in one place.
# The client gets this through Game.get_state() / Admin.admin_state(), so names, emoji and
# prices live only here. Rules that use it are in Game.py.

RARITY = {
    "common": {"name": "Common", "color": "#7a9a5b", "price": 8, "weight": 60},
    "uncommon": {"name": "Uncommon", "color": "#3d8fd1", "price": 16, "weight": 28},
    "rare": {"name": "Rare", "color": "#9b59d0", "price": 40, "weight": 10},
    "legendary": {"name": "Legendary", "color": "#e3a21a", "price": 0, "weight": 1},  # never sold
}

CATEGORIES = [
    {"key": "meat", "name": "Meats & Seafood", "emoji": "🥩",
     "blurb": "Fillings! Every meat you grab plumps up your bun."},
    {"key": "veg", "name": "Greens & Roots", "emoji": "🥬", "blurb": "Fresh things the neighbours always need."},
    {"key": "pantry", "name": "Pantry", "emoji": "🍯", "blurb": "Sauces, staples and secret treasures."},
]

# key, name, emoji, category, rarity, description[, gold]
_ITEMS = [
    ("pork_belly", "Pork Belly", "🥓", "meat", "common", "Layered and juicy. The heart of a classic bao."),
    ("chicken", "Chicken Thigh", "🍗", "meat", "common", "Tender, golden and always popular."),
    ("char_siu", "Char Siu", "🍖", "meat", "uncommon", "Sticky-sweet barbecue pork from the night market."),
    ("beef", "Beef Brisket", "🥩", "meat", "uncommon", "Slow-braised in star anise until it falls apart."),
    ("shrimp", "Shrimp", "🦐", "meat", "uncommon", "Sweet and springy. Har gow can't happen without it."),
    ("lap_cheong", "Lap Cheong", "🌭", "meat", "uncommon", "Sweet Cantonese sausage, glossy and red."),
    ("fish", "Sea Bass", "🐟", "meat", "common", "Fresh off the morning boats."),
    ("squid", "Squid", "🦑", "meat", "uncommon", "Wiggly, slippery, delicious with salt and pepper."),
    ("crab", "Mud Crab", "🦀", "meat", "rare", "Pinchy! Its roe makes the richest soup dumplings."),
    ("lobster", "Lobster", "🦞", "meat", "rare", "The pride of the harbour. Guarded by gulls."),
    ("wagyu", "Golden Wagyu", "🥩", "meat", "legendary", "Marbled like a sunset. Only served at the Emperor's table.", True),
    ("scallion", "Scallion", "🌿", "veg", "common", "Grandma puts it in everything. Everything."),
    ("garlic", "Garlic", "🧄", "veg", "common", "Keeps vampires and boredom away."),
    ("bok_choy", "Bok Choy", "🥬", "veg", "common", "Crunchy stems, silky leaves."),
    ("mushroom", "Shiitake", "🍄", "veg", "common", "Smoky and savoury. Dried ones are even better."),
    ("chili", "Chili", "🌶️", "veg", "uncommon", "Handle with care. Makes buns brave."),
    ("corn", "Sweet Corn", "🌽", "veg", "common", "Grilled on a stick at every night market."),
    ("carrot", "Carrot", "🥕", "veg", "common", "Cut into little flowers for fancy dishes."),
    ("onion", "Onion", "🧅", "veg", "common", "Makes everyone cry, then makes everyone happy."),
    ("peanut", "Peanuts", "🥜", "veg", "common", "Crushed on top, mixed inside, snacked on the way."),
    ("dragon_chili", "Dragon Pepper", "🌶️", "veg", "legendary", "Grows only on Dragon's Peak. Glows in the dark.", True),
    ("egg", "Egg", "🥚", "pantry", "common", "For custard, for glaze, for everything."),
    ("rice", "Sticky Rice", "🍚", "pantry", "common", "Glutinous, glorious, wrapped in lotus leaves."),
    ("honey", "Honey", "🍯", "pantry", "uncommon", "The secret to a shiny char siu glaze."),
    ("salt", "Sea Salt", "🧂", "pantry", "common", "Harvested from the harbour flats."),
    ("rice_wine", "Rice Wine", "🍶", "pantry", "uncommon", "A splash makes crab sing."),
    ("coconut", "Coconut", "🥥", "pantry", "uncommon", "For custard buns as yellow as the sun."),
    ("phoenix_egg", "Phoenix Egg", "🥚", "pantry", "legendary", "Warm to the touch. Makes the fluffiest dough in the land.", True),
]
ITEMS = {}
for _row in _ITEMS:
    ITEMS[_row[0]] = {"key": _row[0], "name": _row[1], "emoji": _row[2], "cat": _row[3], "rarity": _row[4],
                      "desc": _row[5], "gold": bool(_row[6]) if len(_row) > 6 else False}
ITEM_ORDER = [r[0] for r in _ITEMS]
MEATS = {k for k, v in ITEMS.items() if v["cat"] == "meat"}

# Recipes: cook them in the Kitchen. The first time unlocks a permanent perk; cooking again sells the bao.
RECIPES = [
    {"key": "pork_bao", "name": "Grandma's Pork Bao", "emoji": "🥟",
     "needs": {"pork_belly": 3, "scallion": 2, "garlic": 1},
     "perk": "hearty", "perk_name": "Hearty", "perk_desc": "+1 heart in every level."},
    {"key": "char_siu_bao", "name": "Honey Char Siu Bao", "emoji": "🍘",
     "needs": {"char_siu": 3, "honey": 2, "onion": 1},
     "perk": "swift", "perk_name": "Swift", "perk_desc": "Run 12% faster."},
    {"key": "spicy_beef_bao", "name": "Spicy Beef Bao", "emoji": "🌶️",
     "needs": {"beef": 3, "chili": 3, "garlic": 1},
     "perk": "quickdash", "perk_name": "Quick Steam", "perk_desc": "Steam Dash recharges 30% faster."},
    {"key": "har_gow", "name": "Crystal Har Gow", "emoji": "🥟",
     "needs": {"shrimp": 4, "bok_choy": 2, "rice": 1},
     "perk": "magnet", "perk_name": "Sticky Dough", "perk_desc": "Ingredients and coins fly to you from further away."},
    {"key": "chicken_mushroom_bao", "name": "Chicken & Shiitake Bao", "emoji": "🍄",
     "needs": {"chicken": 3, "mushroom": 3, "egg": 1},
     "perk": "shield", "perk_name": "Steam Shield", "perk_desc": "Start every level with a shield that blocks one hit."},
    {"key": "xiao_long_bao", "name": "Crab Soup Dumplings", "emoji": "🥣",
     "needs": {"crab": 2, "pork_belly": 2, "rice_wine": 1},
     "perk": "longdash", "perk_name": "Long Dash", "perk_desc": "Steam Dash goes 40% further."},
    {"key": "lap_cheong_rice", "name": "Lap Cheong Sticky Rice", "emoji": "🍙",
     "needs": {"lap_cheong": 2, "rice": 3, "mushroom": 1},
     "perk": "lucky", "perk_name": "Lucky Bun", "perk_desc": "Bonked pests drop twice the coins."},
    {"key": "custard_bao", "name": "Golden Custard Bao", "emoji": "🌕",
     "needs": {"egg": 3, "coconut": 2, "honey": 1},
     "perk": "revive", "perk_name": "Second Helping", "perk_desc": "Once per level, pop back up with 1 heart."},
    {"key": "seafood_bao", "name": "Harbour Seafood Bao", "emoji": "🦞",
     "needs": {"lobster": 1, "squid": 2, "fish": 2, "salt": 1},
     "perk": "rich", "perk_name": "Big Tipper", "perk_desc": "+50% coins from every level."},
    {"key": "emperor_bao", "name": "Golden Emperor Bao", "emoji": "👑",
     "needs": {"wagyu": 1, "phoenix_egg": 1, "dragon_chili": 1, "honey": 2},
     "perk": "fireproof", "perk_name": "Fireproof", "perk_desc": "Hot stoves can't hurt you. Unlocks the Emperor's Crown.",
     "hat": "crown"},
]
RECIPE_BY_KEY = {r["key"]: r for r in RECIPES}
RECIPE_SELL = 25  # coins for cooking a recipe you already know

HATS = [
    {"key": "none", "name": "No hat", "price": 0, "desc": "Just a bun being a bun."},
    {"key": "party", "name": "Party Hat", "price": 40, "desc": "Every errand is a celebration."},
    {"key": "toque", "name": "Chef's Toque", "price": 60, "desc": "Very tall. Very serious. Very chef."},
    {"key": "beanie", "name": "Cozy Beanie", "price": 70, "desc": "Keeps the steam in."},
    {"key": "bamboo", "name": "Bamboo Hat", "price": 80, "desc": "Shade for long walks to the market."},
    {"key": "flowers", "name": "Flower Crown", "price": 100, "desc": "Picked from Grandma's garden (she knows)."},
    {"key": "bandana", "name": "Pirate Bandana", "price": 120, "desc": "Arr. Harbour-approved."},
    {"key": "headphones", "name": "Headphones", "price": 150, "desc": "Listening to sizzling sounds."},
    {"key": "wizard", "name": "Wizard Hat", "price": 220, "desc": "Turns flour into magic."},
    {"key": "crown", "name": "Emperor's Crown", "price": None, "desc": "Cook the Golden Emperor Bao to earn it."},
]
HAT_BY_KEY = {h["key"]: h for h in HATS}

# Badges: checked after every action. `stat`/`at` badges compare a stats counter.
BADGES = [
    {"key": "first_bite", "name": "First Bite", "emoji": "🥟", "desc": "Finish your first level."},
    {"key": "meat_lover", "name": "Meat Lover", "emoji": "🍖", "desc": "Collect 60 meats.", "stat": "meat", "at": 60},
    {"key": "pest_control", "name": "Pest Control", "emoji": "🧹", "desc": "Bonk 100 pests.", "stat": "pests", "at": 100},
    {"key": "nest_buster", "name": "Nest Buster", "emoji": "💥", "desc": "Destroy 10 pest nests.", "stat": "nests", "at": 10},
    {"key": "flawless", "name": "Not a Scratch", "emoji": "✨", "desc": "Finish a level without losing a heart.", "stat": "flawless", "at": 1},
    {"key": "speedy", "name": "Speedy Bun", "emoji": "⏱️", "desc": "Beat the par time on 5 levels."},
    {"key": "helper", "name": "Good Neighbour", "emoji": "🤝", "desc": "Complete 25 errands.", "stat": "errands", "at": 25},
    {"key": "collector", "name": "Collector", "emoji": "🧺", "desc": "Discover 20 kinds of ingredient."},
    {"key": "legend_hunter", "name": "Legend Hunter", "emoji": "🌟", "desc": "Find a legendary ingredient."},
    {"key": "chef", "name": "Junior Chef", "emoji": "🍳", "desc": "Cook your first recipe."},
    {"key": "master_chef", "name": "Master Chef", "emoji": "👩‍🍳", "desc": "Cook all 10 recipes."},
    {"key": "fashionista", "name": "Fashion Bun", "emoji": "🎩", "desc": "Own 5 hats."},
    {"key": "golden_touch", "name": "Golden Touch", "emoji": "🥢", "desc": "Find 10 pairs of golden chopsticks."},
    {"key": "pen_pal", "name": "Pen Pal", "emoji": "💌", "desc": "Find all of Grandma's postcards."},
    {"key": "regular", "name": "Market Regular", "emoji": "📦", "desc": "Open the daily market box 7 times.", "stat": "dailies", "at": 7},
    {"key": "liberator", "name": "Liberator", "emoji": "🏮", "desc": "Free every territory from the pests."},
    {"key": "star_chef", "name": "Star Chef", "emoji": "⭐", "desc": "Earn 45 stars."},
    {"key": "king_slayer", "name": "Royal Bonker", "emoji": "🐀", "desc": "Defeat the Rat King.", "stat": "bosses", "at": 1},
]

PESTS = [
    {"key": "ant", "name": "Ant", "hp": 1, "desc": "Wanders about. Slow, but there are always more."},
    {"key": "rat", "name": "Rat", "hp": 1, "desc": "Sniffs you out and chases you around walls."},
    {"key": "fly", "name": "Fly", "hp": 1, "desc": "Buzzes over walls and counters."},
    {"key": "roach", "name": "Cockroach", "hp": 2, "desc": "Fast and armoured. Takes two bonks."},
    {"key": "gull", "name": "Seagull", "hp": 2, "desc": "Squawks, then swoops at you in a straight line."},
    {"key": "king", "name": "Rat King", "hp": 8, "desc": "Boss. Charges, summons rats. Must be defeated."},
]
PEST_KEYS = {p["key"] for p in PESTS}

NPC_STYLES = [
    {"key": "grandma", "name": "Grandma Bao"},
    {"key": "dumpling", "name": "Dumpling"},
    {"key": "tofu", "name": "Tofu"},
    {"key": "eggtart", "name": "Egg Tart"},
    {"key": "mooncake", "name": "Mooncake"},
    {"key": "sesame", "name": "Sesame Ball"},
    {"key": "fortune", "name": "Fortune Cookie"},
]
NPC_STYLE_KEYS = {s["key"] for s in NPC_STYLES}

THEMES = [
    {"key": "kitchen", "name": "Home kitchen"},
    {"key": "market", "name": "Night market"},
    {"key": "dimsum", "name": "Dim sum palace"},
    {"key": "spice", "name": "Spice mountain"},
    {"key": "harbour", "name": "Harbour docks"},
    {"key": "banquet", "name": "Golden banquet"},
]
THEME_KEYS = {t["key"] for t in THEMES}

# Map tiles. solid = blocks walking. Entities are kept separately (see Levels.py).
TILES = [
    {"ch": ".", "name": "Floor", "solid": False},
    {"ch": ",", "name": "Rug / grass", "solid": False},
    {"ch": "#", "name": "Wall", "solid": True},
    {"ch": "T", "name": "Counter", "solid": True},
    {"ch": "P", "name": "Plant", "solid": True},
    {"ch": "X", "name": "Crate (dash to break)", "solid": True, "breakable": True},
    {"ch": "~", "name": "Water", "solid": True},
    {"ch": "H", "name": "Bridge", "solid": False},
    {"ch": "^", "name": "Hot stove (hurts)", "solid": False},
    {"ch": "=", "name": "Oil slick (slippery)", "solid": False},
    {"ch": "%", "name": "Sticky sauce (slow)", "solid": False},
    {"ch": "R", "name": "Conveyor →", "solid": False},
    {"ch": "L", "name": "Conveyor ←", "solid": False},
    {"ch": "U", "name": "Conveyor ↑", "solid": False},
    {"ch": "D", "name": "Conveyor ↓", "solid": False},
]
TILE_CHARS = {t["ch"] for t in TILES}
SOLID = {t["ch"] for t in TILES if t["solid"]}

# Simple entities (no settings). Items, NPCs, pests and nests have their own kinds.
PICKUPS = [
    {"key": "coin", "name": "Steam Coin", "emoji": "🪙"},
    {"key": "heart", "name": "Heart Bun", "emoji": "❤️"},
    {"key": "tea", "name": "Jasmine Tea (speed)", "emoji": "🍵"},
    {"key": "chopsticks", "name": "Golden Chopsticks", "emoji": "🥢"},
    {"key": "postcard", "name": "Grandma's Postcard", "emoji": "💌"},
]

COINS = {"errand": 5, "first_clear": 20, "star": 10, "pest": 1, "crate": 1, "boss": 15, "nest": 3}
DAILY = {"coins": 15, "streak_bonus": 5, "streak_cap": 7, "items": 3}
MARKET_SIZE = 4


def public():
    """The catalog as the client sees it."""
    return {
        "rarity": RARITY, "categories": CATEGORIES, "items": [ITEMS[k] for k in ITEM_ORDER],
        "recipes": RECIPES, "recipe_sell": RECIPE_SELL, "hats": HATS, "badges": BADGES, "pests": PESTS,
        "npc_styles": NPC_STYLES, "themes": THEMES, "tiles": TILES, "pickups": PICKUPS, "coins": COINS,
    }
