"""Make worlds 7-16 (100 levels) and write them to server_code/LevelPack.py.

    python -I tools/gen_levels.py          # writes the pack and prints a summary
    python -I tools/gen_levels.py --check  # only checks that the written pack matches what this script makes

Every level is built from rooms on a grid (doors between them, some hidden behind crates), then dressed with the
world's features (counters, rugs, ponds, rivers, hot stoves, ice, conveyors...) and filled with the bun, the
steamer, neighbours, nests, pests, ingredients and bonuses. A level is kept only if it passes Levels.check() and
the stricter checks below (nothing is walled in by a neighbour or a nest, there is always a path that avoids hot
stoves to the oven knob, ...). The same seed always gives the same level, so the pack is reproducible.
Difficulty grows over the 100 levels: bigger maps, more pests, more nests, more mechanics at once.
"""
import pathlib
import random
import sys
import types

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "server_code" / "LevelPack.py"

# Load the real Catalog and Levels modules, with an empty pack so Levels doesn't import the file we're writing.
_pkg = types.ModuleType("bbapp")
_pkg.__path__ = [str(ROOT / "server_code")]
sys.modules["bbapp"] = _pkg
_lp = types.ModuleType("bbapp.LevelPack")
_lp.TERRITORIES, _lp.LEVELS = [], []
sys.modules["bbapp.LevelPack"] = _lp
from bbapp import Catalog as C  # noqa: E402
from bbapp import Levels as L  # noqa: E402

# ---------------------------------------------------------------- words

UNIT = {
    "pork_belly": ("slice of pork belly", "slices of pork belly"), "chicken": ("chicken thigh", "chicken thighs"),
    "char_siu": ("piece of char siu", "pieces of char siu"), "beef": ("chunk of brisket", "chunks of brisket"),
    "shrimp": ("shrimp", "shrimp"), "lap_cheong": ("lap cheong sausage", "lap cheong sausages"),
    "fish": ("sea bass", "sea bass"), "squid": ("squid", "squid"), "crab": ("mud crab", "mud crabs"),
    "lobster": ("lobster", "lobsters"), "scallion": ("scallion", "scallions"), "garlic": ("bulb of garlic", "bulbs of garlic"),
    "bok_choy": ("head of bok choy", "heads of bok choy"), "mushroom": ("shiitake", "shiitakes"), "chili": ("chili", "chilies"),
    "corn": ("ear of sweet corn", "ears of sweet corn"), "carrot": ("carrot", "carrots"), "onion": ("onion", "onions"),
    "peanut": ("bag of peanuts", "bags of peanuts"), "egg": ("egg", "eggs"), "rice": ("bowl of sticky rice", "bowls of sticky rice"),
    "honey": ("jar of honey", "jars of honey"), "salt": ("jar of sea salt", "jars of sea salt"),
    "rice_wine": ("bottle of rice wine", "bottles of rice wine"), "coconut": ("coconut", "coconuts"),
    "duck": ("roast duck", "roast ducks"), "eel": ("river eel", "river eels"), "chestnut": ("bag of chestnuts", "bags of chestnuts"),
    "bamboo": ("bamboo shoot", "bamboo shoots"), "lotus_seed": ("lotus pod", "lotus pods"),
    "noodles": ("bundle of noodles", "bundles of noodles"), "red_bean": ("pot of red bean paste", "pots of red bean paste"),
    "mandarin": ("mandarin", "mandarins"), "matcha": ("tin of matcha", "tins of matcha"),
}


def qty(n, k):
    one, many = UNIT.get(k, (C.ITEMS[k]["name"].lower(), C.ITEMS[k]["name"].lower()))
    if n == 1:
        return ("an " if one[0] in "aeiou" else "a ") + one
    return "%s %s" % ({2: "two", 3: "three", 4: "four"}.get(n, str(n)), many)


SAY = [
    "Could you find me {q}? {flavor}",
    "Oh, little bun! I need {q}. {flavor}",
    "{flavor} Bring me {q} and I'll make it worth your while.",
    "Psst. I need {q}, please. {flavor}",
    "I'm all out! Could you fetch {q}? {flavor}",
    "{flavor} If you spot {q}, they're mine!",
]
THANKS = [
    "Wonderful! Take this, with my thanks.",
    "You're the busiest bun in town! Here you go.",
    "Perfect. This is for you.",
    "Hooray! A little something for your journey.",
    "Just what I needed. Have this!",
    "Grandma raised you well. Take this.",
]
PEST_TIP = {
    "ant": "Ants are slow, but they never come alone.",
    "rat": "Rats sniff you out around corners.",
    "fly": "Flies buzz right over the counters.",
    "roach": "Cockroaches need two bonks.",
    "gull": "Gulls squawk before they swoop. Dash aside!",
    "snail": "Snails leave slime that slows you down.",
    "mould": "Mould blobs split in two when you bonk them.",
    "frog": "Frogs hop at you in big jumps.",
    "weevil": "Weevils charge in straight lines. Let them bump a wall, then bonk them while they're dizzy.",
    "spider": "Spiders hide in the dark and pounce when you get close.",
    "wasp": "Wasps fly over walls and dart at you.",
}

# ---------------------------------------------------------------- the ten new worlds

WORLDS = [
    {"key": "noodle", "name": "Noodle Alley", "emoji": "🍜", "theme": "noodle", "pest": "rat",
     "blurb": "Steam, slurps and sizzling woks. Grab the bonuses!",
     "postcard": "Dear Bao,\nYou freed the Banquet! But the pests ran off to faraway kitchens, so I'm visiting old friends "
                 "along the Noodle Road. Follow my postcards, and always slurp loudly. It's polite here!\nLove, Grandma",
     "pests": [("rat", 3, 0), ("fly", 2, 1), ("ant", 1, 0), ("roach", 1, 5)],
     "meats": ["duck", "pork_belly", "char_siu", "chicken"],
     "others": ["noodles", "chestnut", "scallion", "egg", "bok_choy", "mushroom", "garlic"],
     "features": {"rug": 3, "counter": 3, "plants": 2, "oil": 1, "conveyor": 1, "stoves": 1},
     "bonuses": ["magnet", "bubble", "bag", "tea"],
     "people": [("dumpling", "Uncle Lo Mein"), ("tofu", "Auntie Broth"), ("fortune", "Master Wonton"), ("mooncake", "Mr. Roast"),
                ("sesame", "Little Noodle"), ("eggtart", "Chef Biang")],
     "flavor": ["The dinner rush is coming!", "My wok is getting cold!", "The rats keep pinching my stock.", "Slurp first, talk later!"],
     "names": ["Slurp Street", "The Long Noodle", "Wok This Way", "Broth Bridge", "Bonus Bowl", "Chopstick Corners", "Duck Window",
               "Steam Lanterns", "Night Noodle Rush", "The Grand Slurp"],
     "first": "Welcome to Noodle Alley! Glowing bubbles are bonuses: 🧲 a magnet pulls everything to you, 🛡️ a shield blocks a hit, 💰 a bag holds 5 coins."},
    {"key": "bakery", "name": "Bakery Lane", "emoji": "🥐", "theme": "bakery", "pest": "mould",
     "blurb": "Warm ovens everywhere and mould on the loaves. Find the oven knobs!",
     "postcard": "Bao,\nThe bakers here let me shape the morning buns. Mine were the lumpiest, and the tastiest. "
                 "Remember: when the kitchen gets too hot, turn the knob. Works for ovens AND tempers.\nGrandma",
     "pests": [("mould", 3, 0), ("ant", 2, 0), ("fly", 1, 3), ("rat", 1, 6)],
     "meats": ["pork_belly", "chicken", "lap_cheong", "char_siu"],
     "others": ["red_bean", "egg", "coconut", "honey", "rice", "chestnut"],
     "features": {"counter": 3, "rug": 2, "plants": 2, "stoves": 3, "conveyor": 1},
     "bonuses": ["magnet", "bubble", "bag", "tea"], "knob": "knob",
     "people": [("eggtart", "Baker Tart"), ("mooncake", "Mrs. Crumb"), ("sesame", "Sesame Sue"), ("dumpling", "Proof the Dough"),
                ("grandma", "Granny Flour"), ("fortune", "Fortune Baker")],
     "flavor": ["The ovens are roaring today!", "Mould got into my pantry!", "The bake sale starts soon!", "Mind the hot trays, dear."],
     "names": ["Rising Dough", "The Oven Knob", "Mouldy Mischief", "Crumb Alley", "Sweet Bonus Shop", "Too Many Ovens", "Bake Sale Panic",
               "Pastry Maze", "Proofing Room", "The Great Bake-Off"],
     "first": "Hot stoves block the way. Find the 🎛️ oven knob and touch it: every stove in the level turns off! Mould blobs split in two when bonked."},
    {"key": "garden", "name": "Tea Garden", "emoji": "🍵", "theme": "garden", "pest": "snail",
     "blurb": "Terraces of tea, slow snails and slippery trails.",
     "postcard": "Little one,\nI drank seven cups of tea today and now I can hear colours. The snails here are slow but stubborn. "
                 "So am I. That's why we get along.\nGrandma",
     "pests": [("snail", 3, 0), ("ant", 1, 0), ("fly", 1, 2), ("mould", 1, 4), ("rat", 1, 6)],
     "meats": ["chicken", "shrimp", "pork_belly", "beef"],
     "others": ["matcha", "bamboo", "bok_choy", "mushroom", "mandarin", "egg"],
     "features": {"rug": 3, "plants": 3, "sauce": 2, "counter": 1, "pond": 1},
     "bonuses": ["magnet", "bubble", "bag", "anise"],
     "people": [("tofu", "Tea Master Lin"), ("grandma", "Auntie Oolong"), ("fortune", "Monk Pu'er"), ("sesame", "Little Leaf"),
                ("eggtart", "Miss Jasmine"), ("dumpling", "Farmer Sencha")],
     "flavor": ["The tea is steeping!", "The snails are nibbling my leaves.", "Slowly, slowly, little bun.", "A garden needs patience."],
     "names": ["First Flush", "Slow and Steady", "Star Anise", "Pagoda Path", "Bonus Blossoms", "Snail Trail", "Mossy Steps",
               "The Tea Maze", "Jade Pavilion", "Grand Tea Ceremony"],
     "first": "Snails leave slime that slows you down. Grab a 🌟 Star Anise and for a few seconds everything you touch gets bonked!"},
    {"key": "lake", "name": "Lotus Lake", "emoji": "🪷", "theme": "lake", "pest": "frog",
     "blurb": "Bridges, lily pads and a lot of very loud frogs.",
     "postcard": "Bao,\nI rowed across Lotus Lake at dawn. The frogs sang the whole way, slightly off-key. "
                 "Lotus seeds are for luck. Eat one before every big day.\nGrandma",
     "pests": [("frog", 3, 0), ("fly", 1, 0), ("gull", 1, 2), ("snail", 1, 5)],
     "meats": ["fish", "shrimp", "eel", "squid", "duck"],
     "others": ["lotus_seed", "rice", "bamboo", "salt", "mandarin"],
     "features": {"pond": 3, "plants": 2, "rug": 2, "counter": 1}, "river": 0.85,
     "bonuses": ["magnet", "bubble", "anise", "bag"],
     "people": [("fortune", "Boatman Bo"), ("dumpling", "Fisher Fen"), ("tofu", "Lily the Lotus"), ("mooncake", "Uncle Ripple"),
                ("eggtart", "Captain Puddle"), ("grandma", "Granny Reed")],
     "flavor": ["The frogs won't stop croaking!", "The lake is so pretty today.", "Mind the water, little bun.", "My boat is leaking again."],
     "names": ["Lily Pad Hop", "Ribbit Bridge", "Misty Pier", "Eel Pond", "Lotus Bonus", "Frog Chorus", "The Boathouse",
               "Reed Maze", "Moon Bridge", "Lotus Palace"],
     "first": "Rivers cut the lake into islands. Cross on the bridges, and watch the frogs: they hop at you in big jumps."},
    {"key": "terrace", "name": "Rice Terraces", "emoji": "🌾", "theme": "terrace", "pest": "weevil",
     "blurb": "Golden fields, muddy paddies and charging weevils.",
     "postcard": "Dear Bao,\nEvery grain of rice is somebody's hard work. Never leave any in your bowl! "
                 "The farmers taught me to dance in the mud. I was very bad at it.\nGrandma",
     "pests": [("weevil", 3, 0), ("rat", 2, 0), ("ant", 1, 0), ("frog", 1, 5)],
     "meats": ["beef", "pork_belly", "duck", "chicken"],
     "others": ["rice", "corn", "peanut", "chestnut", "garlic", "onion"],
     "features": {"rug": 3, "sauce": 2, "counter": 1, "plants": 2, "stoves": 1},
     "bonuses": ["magnet", "bubble", "bag", "anise", "tea"], "knob": "timer",
     "people": [("dumpling", "Farmer Fu"), ("grandma", "Granny Paddy"), ("sesame", "Little Sprout"), ("tofu", "Miller Mo"),
                ("fortune", "Scarecrow Sam"), ("mooncake", "Harvest Hua")],
     "flavor": ["The weevils are in the granary!", "Harvest time!", "My boots are stuck in the mud.", "Rice for everyone!"],
     "names": ["Paddy Paths", "Weevil Watch", "Kitchen Timer", "Muddy Steps", "Golden Bonus Fields", "Scarecrow Hill", "Straight Charge",
               "Water Wheel", "Granary Gate", "The Great Harvest"],
     "first": "Weevils are armoured and charge in straight lines. Step aside: when one bumps a wall it gets dizzy, and that's your moment to bonk it!"},
    {"key": "cellar", "name": "Pickle Cellar", "emoji": "🏺", "theme": "cellar", "pest": "spider",
     "blurb": "Dark shelves, old jars and spiders that hide.",
     "postcard": "Bao,\nThe cellar is dark, but every jar down here is a summer kept for winter. "
                 "Your grandfather's plum pickles are on the top shelf. Don't tell anyone.\nGrandma",
     "pests": [("spider", 3, 0), ("rat", 2, 0), ("roach", 2, 3), ("mould", 1, 6)],
     "meats": ["lap_cheong", "beef", "fish", "pork_belly"],
     "others": ["mushroom", "garlic", "salt", "rice_wine", "bamboo", "onion"],
     "features": {"counter": 3, "plants": 3, "rug": 1}, "crates": 2,
     "bonuses": ["magnet", "bubble", "bag", "anise", "clock"],
     "people": [("grandma", "Granny Brine"), ("tofu", "Old Mr. Jar"), ("mooncake", "Uncle Pickle"), ("fortune", "Lantern Lou"),
                ("dumpling", "Barrel Bao"), ("eggtart", "Little Vinegar")],
     "flavor": ["It's so dark down here!", "Something with eight legs just waved at me.", "Mind the jars, dear.", "I've lost my lantern."],
     "names": ["Down the Stairs", "Eight Legs", "Pickle Jars", "Cobweb Corner", "Lantern Bonus", "Barrel Maze", "Fermenting Room",
               "The Deep Shelf", "Spider Nest", "The Last Lantern"],
     "first": "It's dark in the cellar: stay near the lanterns. Spiders hide and pounce when you get close. A ⏳ sand timer stops the clock for a while!"},
    {"key": "orchard", "name": "Honey Orchard", "emoji": "🐝", "theme": "orchard", "pest": "wasp",
     "blurb": "Blossoms, honey and the Wasp Queen's hive.",
     "postcard": "My dear Bao,\nThe orchard smells like honey and sunshine. The bees are lovely. The wasps are not. "
                 "Their queen is very rude. Please have a word with her.\nGrandma",
     "pests": [("wasp", 3, 0), ("fly", 1, 0), ("ant", 1, 0), ("snail", 1, 4), ("weevil", 1, 6)],
     "meats": ["chicken", "char_siu", "duck", "pork_belly"],
     "others": ["honey", "mandarin", "peanut", "coconut", "red_bean"],
     "features": {"rug": 3, "plants": 3, "counter": 1, "sauce": 1, "stoves": 1},
     "bonuses": ["magnet", "bubble", "bag", "anise", "clock"], "boss": {9: ["queen"]},
     "people": [("sesame", "Beekeeper Bee"), ("grandma", "Granny Blossom"), ("eggtart", "Little Honey"), ("tofu", "Orchard Ott"),
                ("fortune", "Professor Pollen"), ("mooncake", "Uncle Nectar")],
     "flavor": ["The wasps keep stealing my honey!", "Mind the stingers, sweetie.", "What a buzzing day!", "The blossoms are out!"],
     "names": ["Blossom Row", "Buzz Off", "Honey Drip", "Beehive Hill", "Sweet Bonus Grove", "Sticky Situation", "Pollen Path",
               "Wasp Watchtower", "Royal Jelly", "The Wasp Queen"],
     "first": "Wasps fly right over walls, hover around you, then dart. Dash through them!"},
    {"key": "frost", "name": "Frozen Pantry", "emoji": "🧊", "theme": "frost", "pest": "mould",
     "blurb": "Icy floors, frosty shelves and slippery business.",
     "postcard": "Bao,\nI got locked in the big freezer for a whole hour. I made a snow-bun. He's called Gerald. "
                 "Wear a scarf, and slide carefully on the ice!\nGrandma",
     "pests": [("mould", 2, 0), ("roach", 2, 0), ("spider", 2, 2), ("snail", 1, 0), ("wasp", 1, 4), ("weevil", 1, 6)],
     "meats": ["shrimp", "fish", "crab", "lobster", "squid"],
     "others": ["egg", "coconut", "matcha", "red_bean", "salt"],
     "features": {"ice": 3, "oil": 2, "counter": 2, "plants": 1, "stoves": 1},
     "bonuses": ["magnet", "bubble", "bag", "anise", "clock"], "knob": "mix",
     "people": [("eggtart", "Chef Sorbet"), ("tofu", "Frosty Tofu"), ("mooncake", "Uncle Popsicle"), ("grandma", "Granny Snow"),
                ("sesame", "Little Sprinkles"), ("dumpling", "Penguin Pete")],
     "flavor": ["Brrr! It's chilly!", "Mind the ice, it's slippery.", "My ice cream is melting!", "Everything here is frozen solid."],
     "names": ["Brain Freeze", "Slip Slide", "Ice Cream Aisle", "Frosty Ovens", "Snowball Bonus", "Freezer Burn", "Glacier Shelves",
               "Penguin Waddle", "Thin Ice", "The Big Chill"],
     "first": "Ice is slippery: you slide and turn slowly. Plan your path, and dash to stop sliding into pests!"},
    {"key": "festival", "name": "Lantern Festival", "emoji": "🎆", "theme": "festival", "pest": "wasp",
     "blurb": "A night of lanterns, firecrackers and the rarest fruit of all.",
     "postcard": "Bao,\nThe sky is full of lanterns and every lantern is a wish. I wished for you to visit. "
                 "The Rat King is back, crashing the party. You know what to do.\nGrandma",
     "pests": [("wasp", 2, 0), ("frog", 2, 0), ("rat", 2, 0), ("weevil", 1, 2), ("spider", 1, 3), ("gull", 1, 5)],
     "meats": ["duck", "char_siu", "lap_cheong", "pork_belly", "chicken"],
     "others": ["red_bean", "lotus_seed", "mandarin", "egg", "honey"],
     "features": {"rug": 2, "plants": 3, "counter": 2, "oil": 1, "conveyor": 1}, "river": 0.35,
     "bonuses": ["magnet", "bubble", "bag", "anise", "clock", "tea"], "boss": {9: ["king"]}, "legend": {7: "moon_peach"},
     "people": [("fortune", "Riddle Master Ren"), ("mooncake", "Auntie Mooncake"), ("sesame", "Little Lantern"), ("grandma", "Granny Glow"),
                ("dumpling", "Lion Dancer Lee"), ("eggtart", "Firework Fay")],
     "flavor": ["The lanterns are beautiful tonight!", "The parade is about to start!", "Happy festival, little bun!", "Have you guessed my riddle?"],
     "names": ["First Lanterns", "Dragon Dance", "Firecracker Alley", "Riddle Walk", "Lucky Bonus Night", "Mooncake Market", "Paper Boats",
               "The Moon Peach", "Lion Dance", "Festival Finale"],
     "first": "The festival is on! It's dark between the lanterns, and every pest you've met so far has come to the party."},
    {"key": "dragon", "name": "Dragon's Kitchen", "emoji": "🐉", "theme": "dragon", "pest": "rat",
     "blurb": "The hottest kitchen in the land. The Great Feast awaits.",
     "postcard": "My brave, busy Bao,\nYou found me! The dragon is just a very old chef who lost his recipe book. "
                 "We found it together, and he's cooking the Great Feast for everyone you helped. Come and eat!\nLove forever, Grandma",
     "pests": [("rat", 2, 0), ("roach", 2, 0), ("wasp", 1, 0), ("weevil", 1, 1), ("spider", 1, 2), ("mould", 1, 3), ("snail", 1, 4), ("frog", 1, 5)],
     "meats": ["beef", "lobster", "crab", "eel", "duck"],
     "others": ["chili", "garlic", "honey", "red_bean", "mandarin"],
     "features": {"stoves": 3, "counter": 2, "sauce": 1, "oil": 1, "plants": 1, "conveyor": 1},
     "bonuses": ["magnet", "bubble", "bag", "anise", "clock", "tea"], "knob": "mix",
     "boss": {4: ["queen"], 9: ["king", "queen"]}, "legend": {6: "dragon_chili", 7: "wagyu", 8: "phoenix_egg"},
     "people": [("grandma", "Grandma Bao"), ("fortune", "Old Chef Long"), ("tofu", "Sous Chef Scale"), ("mooncake", "Uncle Ember"),
                ("dumpling", "Wok Master Wu"), ("eggtart", "Little Flame")],
     "flavor": ["It's SO hot in here!", "The Great Feast needs everything!", "Careful, little bun, the stoves bite.", "We're nearly ready!"],
     "names": ["Dragon's Door", "Fire Breath Hall", "Scale Steps", "Ember Pantry", "The Queen Returns", "Treasure Hoard", "Smoky Maze",
               "Lava Ladles", "The Last Larder", "The Great Feast"],
     "first": "The Dragon's Kitchen is the hottest place in the land. Oven knobs and kitchen timers are your best friends here."},
]

FLYERS = C.FLYERS
CONV = set("RLUD")


class Retry(Exception):
    pass


# ---------------------------------------------------------------- one level

class Gen:
    def __init__(self, world, wi, li, attempt=0):
        self.w, self.wi, self.li = world, wi, li
        self.rng = random.Random("%s-%d-%d" % (world["key"], li, attempt))
        self.diff = (wi * 10 + li) / 99.0
        self.boss = (world.get("boss") or {}).get(li) or []
        self.bonus_round = li == 4 and not self.boss or (world["key"] == "dragon" and li == 5)

    # ---- layout
    def layout(self):
        r, d, li = self.rng, self.diff, self.li
        cols = 3 + (d > 0.3) + (d > 0.7 and li >= 5)
        rows = 2 + (d > 0.35 or li >= 6) + (li == 9 and d > 0.8)
        if li == 0:
            cols, rows = max(3, cols - 1), max(2, rows - 1)
        if self.boss:
            cols, rows = max(cols, 4), max(rows, 3)
        cols, rows = min(cols, 5), min(rows, 4)
        cw = 6 + r.randint(0, 1) + (d > 0.6 and r.random() < 0.5)
        chh = 4 + r.randint(0, 1) + (d > 0.5 and r.random() < 0.6)
        self.cols, self.rows, self.cw, self.chh = cols, rows, cw, chh
        W, H = cols * (cw + 1) + 1, rows * (chh + 1) + 1
        self.W, self.H = W, H
        g = [["#"] * W for _ in range(H)]
        self.cells = {}
        for j in range(rows):
            for i in range(cols):
                x0, y0 = 1 + i * (cw + 1), 1 + j * (chh + 1)
                self.cells[(i, j)] = (x0, y0, x0 + cw - 1, y0 + chh - 1)
                for y in range(y0, y0 + chh):
                    for x in range(x0, x0 + cw):
                        g[y][x] = "."
        self.g = g
        # Merge some neighbours into halls (the boss gets a big arena in the middle).
        parent = {c: c for c in self.cells}

        def find(c):
            while parent[c] != c:
                parent[c] = parent[parent[c]]
                c = parent[c]
            return c
        self.find = find
        self.river_row = None
        if rows >= 2 and r.random() < (self.w.get("river") or 0):
            self.river_row = r.randint(0, rows - 2)  # the wall under room row j becomes water
        merges = []
        if self.boss:
            ci, cj = cols // 2 - 1, rows // 2 - 1
            for a, b in (((ci, cj), (ci + 1, cj)), ((ci, cj + 1), (ci + 1, cj + 1)), ((ci, cj), (ci, cj + 1)), ((ci + 1, cj), (ci + 1, cj + 1))):
                merges.append((a, b))
            self.arena = [(ci, cj), (ci + 1, cj), (ci, cj + 1), (ci + 1, cj + 1)]
            if self.river_row == cj:
                self.river_row = None
        else:
            self.arena = None
            for _ in range(r.randint(0, 1 + (cols * rows > 8))):
                i, j = r.randrange(cols), r.randrange(rows)
                if r.random() < 0.5 and i + 1 < cols:
                    merges.append(((i, j), (i + 1, j)))
                elif j + 1 < rows and j != self.river_row:
                    merges.append(((i, j), (i, j + 1)))
        self.open_walls = []
        for a, b in merges:
            ax0, ay0, ax1, ay1 = self.cells[a]
            if b[0] == a[0] + 1:  # side by side: knock out the wall column
                for y in range(ay0, ay1 + 1):
                    g[y][ax1 + 1] = "."
            else:
                for x in range(ax0, ax1 + 1):
                    g[ay1 + 1][x] = "."
            if a[0] != b[0] and a[1] != b[1]:
                continue
            parent[find(a)] = find(b)
        # In a 2x2 arena the middle pillar goes too.
        if self.arena:
            ax0, ay0, ax1, ay1 = self.cells[self.arena[0]]
            g[ay1 + 1][ax1 + 1] = "."
        if self.river_row is not None:
            y = self.cells[(0, self.river_row)][3] + 1
            for x in range(1, W - 1):
                g[y][x] = "~"
        # Doors: a random spanning tree over the groups, plus a few loops.
        edges = []
        for (i, j) in self.cells:
            if i + 1 < cols:
                edges.append(((i, j), (i + 1, j)))
            if j + 1 < rows:
                edges.append(((i, j), (i, j + 1)))
        r.shuffle(edges)
        tree, extra = [], []
        for a, b in edges:
            if find(a) != find(b):
                parent[find(a)] = find(b)
                tree.append((a, b))
            else:
                extra.append((a, b))
        self.adj = {c: set() for c in self.cells}
        self.doors = set()
        for a, b in tree:
            self.door(a, b, "door")
        loops = [e for e in extra if self.wall_between(*e)]
        for a, b in loops[: int(len(loops) * (0.25 + 0.2 * r.random()))]:
            self.door(a, b, "crate" if r.random() < 0.3 + 0.1 * (self.w.get("crates") or 0) else "door")
        for a, b in merges:
            self.adj[a].add(b)
            self.adj[b].add(a)
        self.tree = tree

    def wall_between(self, a, b):
        ax0, ay0, ax1, ay1 = self.cells[a]
        if b[0] == a[0] + 1:
            return self.g[ay0 + 1][ax1 + 1] in "#~"
        return self.g[ay1 + 1][ax0 + 1] in "#~"

    def door(self, a, b, kind):
        r = self.rng
        ax0, ay0, ax1, ay1 = self.cells[a]
        width = 2 if r.random() < 0.6 else 1
        if b[0] == a[0] + 1:
            y = r.randint(ay0 + 1, ay1 - width)
            spots = [(ax1 + 1, y + k) for k in range(width)]
        else:
            x = r.randint(ax0 + 1, ax1 - width)
            spots = [(x + k, ay1 + 1) for k in range(width)]
        for x, y in spots:
            ch = self.g[y][x]
            self.g[y][x] = "H" if ch == "~" else ("X" if kind == "crate" else ".")
            self.doors.add((x, y))
        self.adj[a].add(b)
        self.adj[b].add(a)
        return spots

    # ---- connectivity helpers
    def walk(self, x, y, blocked=(), hot_ok=True):
        ch = self.g[y][x]
        if (x, y) in blocked:
            return False
        if ch in C.SOLID and ch != "X":
            return False
        if not hot_ok and ch == "^":
            return False
        return True

    def bfs(self, start, blocked=(), hot_ok=True):
        dist = {start: 0}
        todo = [start]
        for p in todo:
            x, y = p
            for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                if 0 <= nx < self.W and 0 <= ny < self.H and (nx, ny) not in dist and self.walk(nx, ny, blocked, hot_ok):
                    dist[(nx, ny)] = dist[p] + 1
                    todo.append((nx, ny))
        return dist

    def all_connected(self):
        cells = [(x, y) for y in range(self.H) for x in range(self.W) if self.walk(x, y)]
        return len(self.bfs(cells[0])) == len(cells)

    def room_of(self, x, y):
        for c, (x0, y0, x1, y1) in self.cells.items():
            if x0 <= x <= x1 and y0 <= y <= y1:
                return c
        return None

    def near_door(self, x, y, d=1):
        return any(abs(x - dx) <= d and abs(y - dy) <= d for dx, dy in self.doors)

    # ---- dressing
    def core(self, c):
        x0, y0, x1, y1 = self.cells[c]
        return x0 + 1, y0 + 1, x1 - 1, y1 - 1

    def rect_in_core(self, c, maxw, maxh):
        r = self.rng
        cx0, cy0, cx1, cy1 = self.core(c)
        w = r.randint(1, max(1, min(maxw, cx1 - cx0)))
        h = r.randint(1, max(1, min(maxh, cy1 - cy0)))
        x = r.randint(cx0, max(cx0, cx1 - w + 1))
        y = r.randint(cy0, max(cy0, cy1 - h + 1))
        return [(x + i, y + k) for k in range(h) for i in range(w)]

    def try_solid(self, spots, ch):
        old = [(x, y, self.g[y][x]) for x, y in spots]
        if any(self.g[y][x] not in ".," or self.near_door(x, y) for x, y in spots):
            return False
        for x, y in spots:
            self.g[y][x] = ch
        if not self.all_connected():
            for x, y, o in old:
                self.g[y][x] = o
            return False
        return True

    def paint(self, spots, ch, over=".,"):
        for x, y in spots:
            if self.g[y][x] in over:
                self.g[y][x] = ch

    def dress(self):
        r, w = self.rng, self.w
        feats = dict(w["features"])
        if self.li < 3:
            feats.pop("conveyor", None)
        if self.li < 5 and w["key"] == "noodle":
            feats.pop("stoves", None)
        keys = list(feats)
        weights = [feats[k] for k in keys]
        self.hot_rooms = []
        knob = w.get("knob")
        if knob == "mix":
            knob = "timer" if (self.li % 2) else "knob"
        self.knob_kind = None
        rooms = list(self.cells)
        if knob and self.li >= (1 if w["key"] == "bakery" else 2) and not self.bonus_round:
            self.knob_kind = knob
        for c in rooms:
            for _ in range(r.randint(1, 3)):
                f = r.choices(keys, weights)[0]
                if f == "rug":
                    self.paint(self.rect_in_core(c, 6, 4) if r.random() < 0.5 else self.room_tiles(c), ",", ".")
                elif f == "counter":
                    self.try_solid(self.rect_in_core(c, 3, 2), "T")
                elif f == "pond":
                    self.try_solid(self.rect_in_core(c, 3, 2), "~")
                elif f == "plants":
                    x0, y0, x1, y1 = self.cells[c]
                    for (x, y) in ((x0, y0), (x1, y0), (x0, y1), (x1, y1)):
                        if r.random() < 0.5:
                            self.try_solid([(x, y)], "P")
                elif f == "stoves":
                    self.paint(self.rect_in_core(c, 3, 2), "^")
                elif f == "oil":
                    self.paint(self.rect_in_core(c, 4, 2), "=")
                elif f == "sauce":
                    self.paint(self.rect_in_core(c, 4, 2), "%")
                elif f == "ice":
                    if r.random() < 0.6:
                        self.paint(self.room_tiles(c), "=")
                    else:
                        self.paint(self.rect_in_core(c, 5, 3), "=")
                elif f == "conveyor" and r.random() < 0.6:
                    cx0, cy0, cx1, cy1 = self.core(c)
                    x0, _, x1, _ = self.cells[c]
                    y = r.randint(cy0, cy1)
                    self.paint([(x, y) for x in range(x0, x1 + 1)], r.choice("RL"), ".,")
        if self.w["theme"] in ("cellar", "festival"):
            # dark worlds need lanterns ('P' tiles light up) in every room
            for c in rooms:
                x0, y0, x1, y1 = self.cells[c]
                for (x, y) in r.sample([(x0, y0), (x1, y0), (x0, y1), (x1, y1)], 2):
                    self.try_solid([(x, y)], "P")

    def room_tiles(self, c):
        x0, y0, x1, y1 = self.cells[c]
        return [(x, y) for y in range(y0, y1 + 1) for x in range(x0, x1 + 1)]

    # ---- people and things
    def free(self, c=None, strict=False, avoid=(), allow_hot=False):
        out = []
        tiles = self.room_tiles(c) if c else [(x, y) for y in range(self.H) for x in range(self.W)]
        for x, y in tiles:
            ch = self.g[y][x]
            if ch in C.SOLID or ch in CONV or (ch == "^" and not allow_hot) or (x, y) in self.taken or (x, y) in self.doors:
                continue
            if (x, y) in avoid:
                continue
            if strict:
                ok = True
                for dx in (-1, 0, 1):
                    for dy in (-1, 0, 1):
                        ch2 = self.g[y + dy][x + dx]
                        if ch2 in C.SOLID or (x + dx, y + dy) in self.blockers or (ch2 == "^" and (dx, dy) != (0, 0)):
                            ok = False
                if not ok or self.near_door(x, y, 1):
                    continue
            out.append((x, y))
        return out

    def put(self, e, spot):
        e["x"], e["y"] = spot
        self.taken.add(spot)
        self.ents.append(e)
        return e

    def place(self):
        r, w, li, d = self.rng, self.w, self.li, self.diff
        self.taken, self.blockers, self.ents = set(), set(), []
        rooms = list(self.cells)
        corners = [(0, 0), (self.cols - 1, 0), (0, self.rows - 1), (self.cols - 1, self.rows - 1)]
        start_room = r.choice(corners)
        spots = self.free(start_room, strict=True) or self.free(start_room)
        if not spots:
            raise Retry("no start")
        start = r.choice(spots)
        self.put({"t": "start"}, start)
        dist = self.bfs(start, hot_ok=False)
        # The hot room(s): a whole room of stoves, switched off by a knob somewhere else.
        cand = [c for c in rooms if c != start_room and (not self.arena or c not in self.arena)]
        if self.knob_kind:
            n_hot = 1 + (li >= 6 and w["key"] in ("bakery", "dragon"))
            r.shuffle(cand)
            for c in cand[:n_hot]:
                x0, y0, x1, y1 = self.cells[c]
                for y in range(y0 + 1, y1):
                    for x in range(x0 + 1, x1):
                        if self.g[y][x] in ".,=%":
                            self.g[y][x] = "^"
                self.hot_rooms.append(c)
        hot_tiles = {(x, y) for c in self.hot_rooms for (x, y) in self.room_tiles(c)}
        dist = self.bfs(start, hot_ok=False)
        far = sorted([s for s in self.free(None, strict=True) if s in dist and s not in hot_tiles], key=lambda s: dist[s])
        if len(far) < 10:
            raise Retry("too cramped")
        # The steamer: somewhere far away.
        exit_spot = r.choice(far[-max(3, len(far) // 8):])
        self.put({"t": "exit"}, exit_spot)
        # Oven knob: reachable without touching a stove; a kitchen timer sits close to its hot room.
        if self.knob_kind:
            hr = self.hot_rooms[0]
            near = [c for c in self.adj[hr] if c not in self.hot_rooms]
            if self.knob_kind == "timer" and near:
                opts = [s for s in self.free(r.choice(near)) if s in dist]
            else:
                opts = [s for s in far[len(far) // 4:] if s in dist and self.room_of(*s) not in self.hot_rooms]
            if not opts:
                raise Retry("no knob spot")
            self.put({"t": "pickup", "k": self.knob_kind}, r.choice(opts))
        # Bosses in the arena.
        if self.boss:
            arena_spots = [s for c in self.arena for s in self.free(c, strict=True)]
            mid = self.cells[self.arena[0]]
            cx, cy = mid[2] + 1, mid[3] + 1
            arena_spots.sort(key=lambda s: abs(s[0] - cx) + abs(s[1] - cy))
            for i, b in enumerate(self.boss):
                self.put({"t": "pest", "k": b}, arena_spots[i * 3])
                self.blockers.add(arena_spots[i * 3])
        # Neighbours with errands.
        n_npc = 1 if li == 0 else 1 + (d > 0.2) + (r.random() < 0.25 + d * 0.5)
        if self.bonus_round:
            n_npc = 1
        others = list(w["others"])
        r.shuffle(others)
        people = list(w["people"])
        r.shuffle(people)
        npcs = []
        mid_spots = [s for s in far[len(far) // 5: len(far) * 4 // 5]]
        for i in range(min(n_npc, 3)):
            spot = self.pick_strict(mid_spots)
            if not spot:
                break
            style, name = people[i]
            wants = others[i % len(others)]
            count = 1 + (r.random() < 0.5 + d * 0.3) + (d > 0.5 and r.random() < 0.4)
            gift = r.choice([m for m in w["meats"]] + [o for o in others if o != wants])
            q = qty(count, wants)
            e = {"t": "npc", "style": style, "name": name, "wants": wants, "count": count, "gift": gift,
                 "gift_count": 1 + (r.random() < 0.4),
                 "say": r.choice(SAY).format(q=q[0].upper() + q[1:] if False else q, flavor=r.choice(w["flavor"])).replace("  ", " "),
                 "thanks": r.choice(THANKS)}
            e["say"] = e["say"][0].upper() + e["say"][1:]
            self.put(e, spot)
            self.blockers.add(spot)
            npcs.append(e)
        # Nests (not in the first levels of a world, never in bonus rounds).
        n_nest = 0
        if li >= 2 and not self.bonus_round:
            n_nest = (li in (2, 5, 7, 8, 9)) * (1 + (d > 0.35) + (d > 0.7 and li >= 8))
        nest_kinds = [k for k, _, m in w["pests"] if m <= li and k not in FLYERS] or ["ant"]
        nest_spots = [s for s in far[len(far) // 3:] if self.room_of(*s) != start_room]
        self.nests = 0
        used_rooms = set()
        for _ in range(n_nest):
            ok = [s for s in nest_spots if self.room_of(*s) not in used_rooms]
            spot = self.pick_strict(ok)
            if not spot:
                break
            used_rooms.add(self.room_of(*spot))
            self.put({"t": "nest", "k": r.choice(nest_kinds), "r": r.choice([3, 4, 4, 5])}, spot)
            self.blockers.add(spot)
            self.nests += 1
        # Ingredients: meat for the goal, what the neighbours want, and a few extras.
        n_meat = 3 + round(3 * d) + r.randint(0, 2)
        if self.bonus_round:
            n_meat = 3 + r.randint(0, 1)
        meats = [r.choice(w["meats"][:2 + (d > 0.3) + (li >= 5)]) for _ in range(n_meat)]
        items = list(meats)
        for e in npcs:
            items += [e["wants"]] * e["count"]
        items += [r.choice(others) for _ in range(r.randint(1, 3))]
        leg = (w.get("legend") or {}).get(li)
        all_free = [s for s in self.free(None) if s in dist or s in hot_tiles]
        hot_free = [s for s in self.free(None, allow_hot=True) if s in hot_tiles]
        r.shuffle(hot_free)
        # spread over the rooms: take spots round-robin by room
        by_room = {}
        for s in all_free:
            if s not in hot_tiles:
                by_room.setdefault(self.room_of(*s), []).append(s)
        for v in by_room.values():
            r.shuffle(v)
        order = [c for c in rooms if c in by_room and c != start_room] + ([start_room] if start_room in by_room else [])
        r.shuffle(order)

        def next_spot(prefer_hot=False):
            if prefer_hot and hot_free:
                while hot_free:
                    s = hot_free.pop()
                    if s not in self.taken:
                        return s
            for _ in range(len(order) * 3):
                c = order[self.rr % len(order)]
                self.rr += 1
                while by_room[c]:
                    s = by_room[c].pop()
                    if s not in self.taken:
                        return s
            raise Retry("out of spots")
        self.rr = 0
        for i, k in enumerate(items):
            self.put({"t": "item", "k": k}, next_spot(prefer_hot=self.hot_rooms and i % 3 == 0))
        if leg:
            self.put({"t": "item", "k": leg}, next_spot(prefer_hot=bool(self.hot_rooms)))
        self.n_meat = n_meat
        # Pests.
        kinds = [(k, wt) for k, wt, m in w["pests"] if m <= li]
        n_pest = 2 + round(8 * d) + li // 2
        if self.bonus_round:
            n_pest = 2 + round(2 * d)
        if self.boss:
            n_pest = max(2, n_pest // 2)
        pest_spots = [s for s in self.free(None) if dist.get(s, 0) >= 7 and s not in hot_tiles]
        r.shuffle(pest_spots)
        for _ in range(n_pest):
            if not pest_spots:
                break
            k = r.choices([k for k, _ in kinds], [wt for _, wt in kinds])[0]
            s = pest_spots.pop()
            if s in self.taken:
                continue
            self.put({"t": "pest", "k": k}, s)
        # Coins, hearts and bonuses.
        n_coin = 4 + round(5 * d) + r.randint(0, 3) + (12 if self.bonus_round else 0)
        for _ in range(n_coin):
            self.put({"t": "pickup", "k": "coin"}, next_spot())
        n_heart = 1 + (n_pest > 6) + (self.nests > 1) + 2 * bool(self.boss)
        for _ in range(n_heart):
            self.put({"t": "pickup", "k": "heart"}, next_spot())
        pool = list(w["bonuses"])
        n_bonus = (5 + r.randint(0, 2)) if self.bonus_round else (1 + r.randint(0, 1) + (d > 0.5))
        for i in range(n_bonus):
            k = "bag" if self.bonus_round and i < 2 else pool[(li + i) % len(pool)] if i < len(pool) else r.choice(pool)
            if self.wi == 0 and li == 0:
                k = ["magnet", "bubble", "bag"][i % 3]
            self.put({"t": "pickup", "k": k}, next_spot())
        # Golden chopsticks, behind crates when there's a secret room; Grandma's postcard in level 7 of every world.
        if li > 0:
            secret = self.secret_spot(start_room)
            self.put({"t": "pickup", "k": "chopsticks"}, secret or next_spot(prefer_hot=bool(self.hot_rooms)))
        if li == 6:
            self.put({"t": "pickup", "k": "postcard"}, next_spot(prefer_hot=bool(self.hot_rooms)))
        self.start, self.npcs = start, npcs

    def pick_strict(self, spots):
        ok = [s for s in self.free(None, strict=True) if s in set(spots)]
        if not ok:
            return None
        return self.rng.choice(ok)

    def secret_spot(self, start_room):
        """A dead-end room whose only door becomes crates; the chopsticks hide inside."""
        leaves = [c for c, n in self.adj.items() if len(n) == 1 and c != start_room and c not in self.hot_rooms and (not self.arena or c not in self.arena)]
        exit_room = next(self.room_of(e["x"], e["y"]) for e in self.ents if e["t"] == "exit")
        leaves = [c for c in leaves if c != exit_room and not any(self.room_of(e["x"], e["y"]) == c and e["t"] in ("npc", "nest", "pickup") and e.get("k") in (None, "knob", "timer") for e in self.ents)]
        if not leaves:
            return None
        c = self.rng.choice(leaves)
        x0, y0, x1, y1 = self.cells[c]
        for (x, y) in self.doors:
            if (x in (x0 - 1, x1 + 1) and y0 <= y <= y1) or (y in (y0 - 1, y1 + 1) and x0 <= x <= x1):
                if self.g[y][x] == ".":
                    self.g[y][x] = "X"
        spots = [s for s in self.free(c) if s not in self.taken]
        return self.rng.choice(spots) if spots else None

    # ---- goals, par, words
    def finish(self):
        w, r, li = self.w, self.rng, self.li
        meat_goal = max(2, self.n_meat - r.randint(0, 2))
        goals = {"meat": meat_goal, "errands": bool(self.npcs), "nests": self.nests > 0}
        data = {"w": self.W, "h": self.H, "tiles": ["".join(row) for row in self.g], "ents": self.ents, "goals": goals,
                "par": self.par(meat_goal), "intro": self.intro(meat_goal)}
        if self.bonus_round:
            data["bonus"] = True
        return data

    def par(self, meat_goal):
        targets = []
        meats = [(e["x"], e["y"]) for e in self.ents if e["t"] == "item" and e["k"] in C.MEATS]
        for e in self.ents:
            if e["t"] == "npc":
                targets.append((e["x"], e["y"]))
                targets += [(i["x"], i["y"]) for i in self.ents if i["t"] == "item" and i["k"] == e["wants"]][: e["count"]]
            elif e["t"] == "nest":
                targets.append((e["x"], e["y"]))
            elif e["t"] == "pickup" and e["k"] in C.KNOB_KEYS:
                targets.append((e["x"], e["y"]))
        targets += meats[:meat_goal]
        pos, total = self.start, 0.0
        blocked = {(e["x"], e["y"]) for e in self.ents if e["t"] in ("npc", "nest")}
        left = list(dict.fromkeys(targets))
        while left:
            dist = self.bfs(pos, blocked - set(left))
            best = min(left, key=lambda s: self.near_dist(dist, s))
            total += self.near_dist(dist, best)
            pos = best if best not in blocked else pos
            left.remove(best)
        exit_e = next(e for e in self.ents if e["t"] == "exit")
        total += self.near_dist(self.bfs(pos, blocked), (exit_e["x"], exit_e["y"]))
        secs = total / 3.3 + 3 * self.nests + len(self.npcs) * 1.5
        secs += sum({"king": 30, "queen": 35}.get(b, 0) for b in self.boss)
        secs = secs * 1.25 + 8
        return int(-(-secs // 5) * 5)

    @staticmethod
    def near_dist(dist, s):
        x, y = s
        best = dist.get(s)
        for n in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if n in dist and (best is None or dist[n] + 1 < best):
                best = dist[n] + 1
        return best if best is not None else 60

    def intro(self, meat_goal):
        w, li = self.w, self.li
        if li == 0:
            return w["first"]
        if self.boss:
            names = " and ".join({"king": "the Rat King", "queen": "the Wasp Queen"}[b] for b in self.boss)
            return "Boss level! %s rule%s this place. Bonk %s until %s give%s up, then hop into the steamer." % (
                names[0].upper() + names[1:], "" if len(self.boss) > 1 else "s", "them" if len(self.boss) > 1 else "the boss",
                "they" if len(self.boss) > 1 else "it", "" if len(self.boss) > 1 else "s")
        if self.bonus_round:
            return "🎁 Bonus round! Coins and bonuses everywhere. Grab as many as you can, fill your bun, and race to the steamer."
        bits = []
        if self.npcs:
            names = [e["name"] for e in self.npcs]
            bits.append("Help " + (", ".join(names[:-1]) + " and " + names[-1] if len(names) > 1 else names[0]))
        bits.append("collect %d meat" % meat_goal)
        if self.nests:
            bits.append("wreck %s" % ("the nest" if self.nests == 1 else "%d nests" % self.nests))
        s = ", ".join(bits[:-1]) + (", then " if len(bits) > 1 else "") + bits[-1] + "."
        s = s[0].upper() + s[1:]
        if self.knob_kind == "timer":
            tip = "A ⏲️ kitchen timer turns the stoves off for 12 seconds. Be quick!"
        elif self.knob_kind == "knob":
            tip = "Find the 🎛️ oven knob to switch the stoves off."
        else:
            new = [k for k, _, m in w["pests"] if m == li]
            tip = PEST_TIP.get(new[0]) if new else PEST_TIP.get([k for k, _, m in w["pests"] if m <= li][li % len([1 for _, _, m in w["pests"] if m <= li])])
        if li == 6:
            tip = "One of Grandma's postcards is hidden here. " + (tip or "")
        return (s + " " + (tip or "")).strip()

    # ---- the stricter checks
    def verify(self, data):
        errors, warnings = L.check(data)
        if errors or warnings:
            raise Retry("check: %s %s" % (errors, warnings))
        blocked = {(e["x"], e["y"]) for e in data["ents"] if e["t"] in ("npc", "nest")}
        start = next((e["x"], e["y"]) for e in data["ents"] if e["t"] == "start")
        safe = self.bfs(start, blocked, hot_ok=False)
        full = self.bfs(start, blocked, hot_ok=True)
        knob = [e for e in data["ents"] if e["t"] == "pickup" and e["k"] in C.KNOB_KEYS]
        reach = full if knob else safe
        if knob and (knob[0]["x"], knob[0]["y"]) not in safe:
            raise Retry("knob behind stoves")
        for e in data["ents"]:
            p = (e["x"], e["y"])
            if e["t"] == "pest":
                continue
            if e["t"] in ("npc", "nest"):
                if not any(n in reach for n in ((p[0] + 1, p[1]), (p[0] - 1, p[1]), (p[0], p[1] + 1), (p[0], p[1] - 1))):
                    raise Retry("walled-in %s" % e["t"])
            elif p not in reach:
                raise Retry("unreachable %s %s" % (e["t"], e.get("k")))
        if not knob:
            # without a knob, nothing important may sit on a stove
            for e in data["ents"]:
                if e["t"] in ("item", "exit") and data["tiles"][e["y"]][e["x"]] == "^":
                    raise Retry("item on a stove")
        return True


def build(world, wi, li):
    last = None
    for attempt in range(200):
        g = Gen(world, wi, li, attempt)
        try:
            g.layout()
            g.dress()
            g.place()
            data = g.finish()
            g.verify(data)
            return data, attempt
        except Retry as e:
            last = e
    raise SystemExit("could not build %s-%d: %s" % (world["key"], li + 1, last))


def make():
    terrs, levels, notes = [], [], []
    for wi, w in enumerate(WORLDS):
        terrs.append({k: w[k] for k in ("key", "name", "emoji", "theme", "pest", "blurb", "postcard")})
        for li in range(10):
            data, attempts = build(w, wi, li)
            levels.append({"key": "%s-%d" % (w["key"], li + 1), "territory": w["key"], "name": w["names"][li], "data": data})
            notes.append((levels[-1]["key"], data["w"], data["h"], sum(1 for e in data["ents"] if e["t"] == "pest"), attempts))
    return terrs, levels, notes


def render(terrs, levels):
    import json
    out = ['# LevelPack — Server Module. Worlds 7-16: 100 levels made by tools/gen_levels.py (do not edit by hand;',
           '# change the generator and run it again). Levels.py adds these to the built-in journey.', '',
           'TERRITORIES = [']
    for t in terrs:
        out.append("    %s," % json.dumps(t, ensure_ascii=False))
    out += [']', '', 'LEVELS = [']
    for lv in levels:
        d = lv["data"]
        out.append('    {"key": %s, "territory": %s, "name": %s, "data": {' % (json.dumps(lv["key"]), json.dumps(lv["territory"]), json.dumps(lv["name"], ensure_ascii=False)))
        out.append('        "w": %d, "h": %d, "par": %d, "goals": %s,' % (d["w"], d["h"], d["par"], json.dumps(d["goals"]).replace("true", "True").replace("false", "False")))
        if d.get("bonus"):
            out.append('        "bonus": True,')
        out.append('        "intro": %s,' % json.dumps(d["intro"], ensure_ascii=False))
        out.append('        "tiles": [')
        for row in d["tiles"]:
            out.append('            "%s",' % row)
        out.append('        ],')
        out.append('        "ents": [')
        for e in d["ents"]:
            out.append('            %s,' % json.dumps(e, ensure_ascii=False, separators=(",", ":")).replace("true", "True").replace("false", "False"))
        out.append('        ]}},')
    out.append(']')
    return "\n".join(out) + "\n"


if __name__ == "__main__":
    terrs, levels, notes = make()
    text = render(terrs, levels)
    if "--check" in sys.argv:
        same = OUT.exists() and OUT.read_text(encoding="utf-8") == text
        print("LevelPack is up to date" if same else "LevelPack differs from the generator: run python -I tools/gen_levels.py")
        sys.exit(0 if same else 1)
    OUT.write_text(text, encoding="utf-8", newline="\n")
    for k, w, h, p, a in notes:
        print("%-12s %2dx%-2d pests %2d  (attempt %d)" % (k, w, h, p, a))
    print("wrote %s (%d levels, %d KB)" % (OUT.relative_to(ROOT), len(levels), len(text.encode()) // 1024))
