# Levels — Server Module. The level format, its checks, and the built-in journey.
#
# A level's `data` (stored in levels.data, a Simple Object) looks like:
#   {"w": 22, "h": 12,
#    "tiles": ["#####...", ...],              h strings of w tile characters (see Catalog.TILES)
#    "ents": [{"t": "start", "x": 1, "y": 1}, {"t": "exit", ...},
#             {"t": "item", "k": "pork_belly", ...}, {"t": "pickup", "k": "coin", ...},
#             {"t": "pest", "k": "rat", ...}, {"t": "nest", "k": "ant", "r": 4, ...},
#             {"t": "npc", "style": "grandma", "name": "Grandma Bao", "wants": "scallion", "count": 2,
#              "gift": "egg", "gift_count": 1, "say": "...", "thanks": "..."}],
#    "goals": {"meat": 3, "errands": true, "nests": true},   a Rat King ("king" pest) must always be beaten
#    "par": 45,                                              seconds, for the time star
#    "intro": "Grandma needs ..."}
#
# The built-in levels below are drawn as ASCII and converted with from_ascii().
from . import Catalog as C

# ---------------------------------------------------------------- checks

WALKABLE_EXTRA = {"X"}  # crates block walking but can be smashed with a dash


def _neighbours(x, y):
    return ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1))


def check(data):
    """Return (errors, warnings) for a level. Errors stop it being published."""
    errors, warnings = [], []
    try:
        w, h, tiles, ents = int(data["w"]), int(data["h"]), data["tiles"], data.get("ents") or []
    except Exception:
        return ["The level data is damaged (needs w, h, tiles)."], []
    if not (8 <= w <= 64 and 6 <= h <= 48):
        errors.append("Size must be between 8×6 and 64×48 tiles.")
    if len(tiles) != h or any(len(r) != w for r in tiles):
        errors.append("The tile rows don't match the level size.")
        return errors, warnings
    bad = {ch for r in tiles for ch in r if ch not in C.TILE_CHARS}
    if bad:
        errors.append("Unknown tiles: %s" % " ".join(sorted(bad)))
    starts = [e for e in ents if e.get("t") == "start"]
    exits = [e for e in ents if e.get("t") == "exit"]
    if len(starts) != 1:
        errors.append("Place exactly one start (the bun).")
    if len(exits) != 1:
        errors.append("Place exactly one exit steamer.")
    for e in ents:
        if not (0 <= e.get("x", -1) < w and 0 <= e.get("y", -1) < h):
            errors.append("An entity is outside the map.")
            break
    if errors:
        return errors, warnings
    for e in ents:
        if tiles[e["y"]][e["x"]] in C.SOLID and not (e["t"] == "pest" and e.get("k") in C.FLYERS):
            errors.append("%s at %d,%d sits inside a solid tile." % (_label(e), e["x"], e["y"]))
    # Reachability from the start (crates count as open: the bun can smash them).
    sx, sy = starts[0]["x"], starts[0]["y"]
    seen, todo = {(sx, sy)}, [(sx, sy)]
    while todo:
        x, y = todo.pop()
        for nx, ny in _neighbours(x, y):
            if 0 <= nx < w and 0 <= ny < h and (nx, ny) not in seen:
                ch = tiles[ny][nx]
                if ch not in C.SOLID or ch in WALKABLE_EXTRA:
                    seen.add((nx, ny))
                    todo.append((nx, ny))
    for e in ents:
        if e["t"] in ("pest",):
            continue
        if (e["x"], e["y"]) not in seen:
            (errors if e["t"] in ("exit", "npc", "nest") else warnings).append(
                "%s at %d,%d can't be reached from the start." % (_label(e), e["x"], e["y"]))
    # Goals must be possible.
    counts = {}
    for e in ents:
        if e["t"] == "item":
            counts[e.get("k")] = counts.get(e.get("k"), 0) + 1
            if e.get("k") not in C.ITEMS:
                errors.append("Unknown ingredient %r." % e.get("k"))
    goals = data.get("goals") or {}
    meat_total = sum(n for k, n in counts.items() if k in C.MEATS)
    if (goals.get("meat") or 0) > meat_total:
        errors.append("The meat goal is %d but the level only has %d meat." % (goals.get("meat"), meat_total))
    wants = {}
    for e in ents:
        if e["t"] == "npc":
            if e.get("wants") not in C.ITEMS:
                errors.append("%s needs a wanted ingredient." % _label(e))
                continue
            wants[e["wants"]] = wants.get(e["wants"], 0) + max(1, int(e.get("count") or 1))
            if e.get("gift") and e["gift"] not in C.ITEMS:
                errors.append("%s gives an unknown gift." % _label(e))
    for k, n in wants.items():
        if n > counts.get(k, 0):
            errors.append("Errands need %d %s but the level has %d." % (n, C.ITEMS[k]["name"], counts.get(k, 0)))
    if goals.get("errands") and not wants:
        warnings.append("The errands goal is on but there are no neighbours with errands.")
    if goals.get("nests") and not any(e["t"] == "nest" for e in ents):
        warnings.append("The nests goal is on but there are no nests.")
    for e in ents:
        if e["t"] in ("pest", "nest") and e.get("k") not in C.PEST_KEYS:
            errors.append("Unknown pest %r." % e.get("k"))
        if e["t"] == "nest" and e.get("k") in C.BOSSES:
            errors.append("A boss can't come out of a nest.")
        if e["t"] == "pickup" and e.get("k") not in C.PICKUP_KEYS:
            errors.append("Unknown pickup %r." % e.get("k"))
    if not any(e["t"] == "item" for e in ents):
        warnings.append("No ingredients to collect.")
    return errors, warnings


def _label(e):
    t = e.get("t")
    if t == "item":
        return C.ITEMS.get(e.get("k"), {}).get("name", "Ingredient")
    if t == "npc":
        return e.get("name") or "Neighbour"
    if t in ("pest", "nest"):
        return ("%s nest" if t == "nest" else "%s") % (e.get("k") or "pest").title()
    return {"start": "The start", "exit": "The exit", "pickup": (e.get("k") or "Pickup").title()}.get(t, t)


def totals(data):
    """What a level holds: item counts, pickups, npcs, nests, crates, bosses (used to check results)."""
    out = {"items": {}, "coins": 0, "chopsticks": 0, "postcard": 0, "npcs": 0, "nests": 0, "crates": 0, "kings": 0,
           "bonuses": 0, "knobs": 0}
    for e in data.get("ents") or []:
        t = e.get("t")
        if t == "item":
            out["items"][e["k"]] = out["items"].get(e["k"], 0) + 1
        elif t == "pickup":
            k = e.get("k")
            if k == "coin":
                out["coins"] += 1
            elif k == "bag":
                out["coins"] += C.BAG_COINS
            elif k in ("chopsticks", "postcard"):
                out[k] += 1
            if k in C.BONUS_KEYS:
                out["bonuses"] += 1
            if k in C.KNOB_KEYS:
                out["knobs"] += 1
        elif t == "npc":
            out["npcs"] += 1
        elif t == "nest":
            out["nests"] += 1
        elif t == "pest" and e.get("k") in C.BOSSES:
            out["kings"] += 1  # "kings" = bosses (the Rat King, the Wasp Queen)
    out["crates"] = sum(r.count("X") for r in data.get("tiles") or [])
    return out


# ---------------------------------------------------------------- ASCII authoring

SYMBOLS = {"@": ("start", None), "E": ("exit", None), "*": ("pickup", "coin"), "+": ("pickup", "heart"),
           "!": ("pickup", "tea"), "$": ("pickup", "chopsticks"), "?": ("pickup", "postcard"),
           "a": ("pest", "ant"), "r": ("pest", "rat"), "f": ("pest", "fly"), "c": ("pest", "roach"),
           "g": ("pest", "gull"), "K": ("pest", "king"),
           "s": ("pest", "snail"), "m": ("pest", "mould"), "j": ("pest", "frog"), "v": ("pest", "weevil"),
           "p": ("pest", "spider"), "w": ("pest", "wasp"), "Q": ("pest", "queen"),
           "M": ("pickup", "magnet"), "B": ("pickup", "bubble"), "&": ("pickup", "bag"), "A": ("pickup", "anise"),
           "Z": ("pickup", "clock"), "k": ("pickup", "knob"), "t": ("pickup", "timer")}


def from_ascii(rows, legend=None, npcs=None, nests=None, nest_kind="ant", goals=None, par=60, intro=""):
    legend, npcs, nests = legend or {}, list(npcs or []), list(nests or [])
    h, w = len(rows), max(len(r) for r in rows)
    if any(len(r) != w for r in rows):
        raise ValueError("ragged rows: %s" % [(i, len(r)) for i, r in enumerate(rows) if len(r) != w])
    grid = [list(r) for r in rows]
    ents = []
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            if ch in C.TILE_CHARS:
                continue
            if ch in SYMBOLS:
                t, k = SYMBOLS[ch]
                e = {"t": t, "x": x, "y": y}
                if k:
                    e["k"] = k
            elif ch.isdigit():
                e = {"t": "item", "k": legend[ch], "x": x, "y": y}
            elif ch == "n":
                e = dict(npcs.pop(0), t="npc", x=x, y=y)
            elif ch == "O":
                spec = nests.pop(0) if nests else {}
                e = {"t": "nest", "k": spec.get("k", nest_kind), "r": spec.get("r", 4), "x": x, "y": y}
            else:
                raise ValueError("unknown symbol %r at %d,%d" % (ch, x, y))
            ents.append(e)
            grid[y][x] = _floor_under(rows, x, y)
    if npcs or nests:
        raise ValueError("unused npcs/nests")
    return {"w": w, "h": h, "tiles": ["".join(r) for r in grid], "ents": ents,
            "goals": goals or {"meat": 0, "errands": False, "nests": False}, "par": par, "intro": intro}


def _floor_under(rows, x, y):
    """The floor an entity stands on: the most common walkable tile around it."""
    seen = {}
    for nx, ny in _neighbours(x, y):
        if 0 <= ny < len(rows) and 0 <= nx < len(rows[ny]):
            ch = rows[ny][nx]
            if ch in (".", ",", "H", "=", "%"):
                seen[ch] = seen.get(ch, 0) + 1
    return max(sorted(seen), key=lambda c: seen[c]) if seen else "."


def npc(style, name, wants, count, gift=None, gift_count=1, say="", thanks=""):
    return {"style": style, "name": name, "wants": wants, "count": count, "gift": gift,
            "gift_count": gift_count if gift else 0, "say": say, "thanks": thanks}


# ---------------------------------------------------------------- the built-in journey

TERRITORIES = [
    {"key": "kitchen", "name": "Grandma's Kitchen", "emoji": "🏠", "theme": "kitchen", "pest": "ant",
     "blurb": "Where every bao begins. Ants have found the pantry.",
     "postcard": "Dear Bao,\nThe Pest King has scattered the pages of my Banquet Book across the land. "
                 "Every bao needs a filling, and every journey needs a first step. Bring the family table back together.\n"
                 "Love, Grandma"},
    {"key": "market", "name": "Night Market", "emoji": "🏮", "theme": "market", "pest": "rat",
     "blurb": "Lanterns, sizzling stalls, and far too many rats.",
     "postcard": "Bao,\nAt the night market I learned that honey makes everything shine, "
                 "and that the char siu man always saves the best piece for whoever smiles first.\nGrandma"},
    {"key": "dimsum", "name": "Dim Sum Palace", "emoji": "🥢", "theme": "dimsum", "pest": "roach",
     "blurb": "Trolleys never stop rolling. Roaches never stop crawling.",
     "postcard": "Little one,\nDim sum means 'touch the heart'. Your grandfather and I had our first date here. "
                 "He ate fourteen har gow. I counted.\nGrandma"},
    {"key": "spice", "name": "Spice Mountain", "emoji": "🌶️", "theme": "spice", "pest": "roach",
     "blurb": "Chili terraces and bubbling hotpots. Watch your step.",
     "postcard": "Bao,\nGrandpa proposed to me on top of Dragon's Peak. He sneezed from the peppers the whole time. "
                 "I said yes before he could finish.\nGrandma"},
    {"key": "harbour", "name": "Harbour Docks", "emoji": "⚓", "theme": "harbour", "pest": "gull",
     "blurb": "The sea gives generously. The gulls keep score.",
     "postcard": "Dear Bao,\nThe sea gives generously, but the gulls keep score. Mind your buns, and always tip the fishermen.\n"
                 "Grandma"},
    {"key": "banquet", "name": "Golden Banquet", "emoji": "👑", "theme": "banquet", "pest": "rat",
     "blurb": "The Rat King has taken the Emperor's banquet. Take it back.",
     "postcard": "My brave Bao,\nYou did it. The Banquet Book is whole again, and so is the family table. "
                 "Come home soon. Everyone's hungry.\nGrandma"},
]


def _lv(key, territory, name, rows, **kw):
    return {"key": key, "territory": territory, "name": name, "data": from_ascii(rows, **kw)}


LEVELS = [
    # ===================================================== Grandma's Kitchen
    _lv("kitchen-1", "kitchen", "First Errand", [
        "######################",
        "#@.....T..T....,,,,,,#",
        "#......T..T....,,1,,,#",
        "#..0...........,,,,1,#",
        "#......PP......,,,,,,#",
        "#..........n.........#",
        "###TTTT####..####TTT##",
        "#.........#..#.......#",
        "#..0..*...#..#...*...#",
        "#.........#..#..0..E.#",
        "#....*...............#",
        "######################",
    ], legend={"0": "pork_belly", "1": "scallion"},
        npcs=[npc("grandma", "Grandma Bao", "scallion", 2, "egg", 1,
                  "Bao, dear! Fetch me two scallions from the garden rug, would you?",
                  "Perfect! Here, take an egg for later.")],
        goals={"meat": 3, "errands": True, "nests": False}, par=40,
        intro="Use the arrow keys or WASD to roll around. Grab 3 pork belly, help Grandma, then hop into the steamer!"),

    _lv("kitchen-2", "kitchen", "Ants in the Pantry", [
        "##########################",
        "#@....#.....,,,,,.....0..#",
        "#.....#..a..,,,,,..a.....#",
        "#..1..X.....,,2,,........#",
        "#.....#.....,,,,,...TTTT.#",
        "###.###..........*..T..T.#",
        "#.....#####XX#####..T.0T.#",
        "#..*........n.......T..T.#",
        "#.....#####..####...TXXT.#",
        "#..0..#..........a.......#",
        "#.....#.a..1.....##P.P.###",
        "#.TT..#.......$..#.......#",
        "#.TT..X....3.....X...1.E.#",
        "##########################",
    ], legend={"0": "pork_belly", "1": "chicken", "2": "garlic", "3": "egg"},
        npcs=[npc("dumpling", "Uncle Jiaozi", "chicken", 2, "scallion", 2,
                  "Ants ate my lunch! Could you find me two chicken thighs?",
                  "You're a lifesaver, little bun. Have some scallions!")],
        goals={"meat": 4, "errands": True, "nests": False}, par=60,
        intro="Ants! Press SPACE (or the steam button) to Steam Dash. Dash into pests to bonk them, and into crates to smash them."),

    _lv("kitchen-3", "kitchen", "The Nest Under the Sink", [
        "############################",
        "#@...#....^^^^....#........#",
        "#....#....^^^^....#..0..a..#",
        "#..0.#............#........#",
        "#....X....TTTT....###XX###.#",
        "#.........T..T.............#",
        "###.####..T.3T..n...,,,,,,.#",
        "#......#..TT.T......,,O,,,.#",
        "#..2...#............,,,,,,.#",
        "#......##.##.###....,,,,,,.#",
        "#.0........a...#...........#",
        "#####.##########..^^^..##..#",
        "#,,,,,,,,#..........1..#.?.#",
        "#,,O,,,,,#..0...a......#####",
        "#,,,,,,,,X......4....1...E.#",
        "############################",
    ], legend={"0": "pork_belly", "1": "scallion", "2": "garlic", "3": "egg", "4": "mushroom"},
        npcs=[npc("grandma", "Grandma Bao", "scallion", 2, "pork_belly", 2,
                  "The ants are coming from two nests! Bring me two scallions while you're at it.",
                  "My brave bun! Take some pork belly for your filling.")],
        nests=[{"k": "ant", "r": 4}, {"k": "ant", "r": 4}],
        goals={"meat": 4, "errands": True, "nests": True}, par=80,
        intro="Pest nests keep spawning ants. Dash into a nest three times to destroy it and clear the area. Don't touch the hot stoves!"),

    # ===================================================== Night Market
    _lv("market-1", "market", "Lantern Alley", [
        "##############################",
        "#@....TTTTT....TTTTT....TTTT.#",
        "#.....T.0.T....T.6.T....T.0T.#",
        "#.....T...T....T...T....T..T.#",
        "#.....TT.TT....TT.TT....TT.T.#",
        "#..*.........................#",
        "#.,,,,,,,,,,,,,,,,,,,,,,,,,,.#",
        "#.,,n,,,,,r,,,,,,,,,,,,f,,,,.#",
        "#.,,,,,,,,,,,,,,,,,,,,,,,,,,.#",
        "#............................#",
        "#..TTTTTT....=====....TTTTTT.#",
        "#..T.1..T....==0==..*.T.2..T.#",
        "#..TT.TTT....=====....TT1TTT.#",
        "#..........r......$.......P.E#",
        "##############################",
    ], legend={"0": "char_siu", "1": "honey", "2": "onion", "6": "chicken"},
        npcs=[npc("mooncake", "Mr. Char", "honey", 2, "char_siu", 2,
                  "My glaze is all gone! Find me two jars of honey, quick, before the dinner rush.",
                  "Ahh, shiny! Take some char siu, on the house.")],
        goals={"meat": 3, "errands": True, "nests": False}, par=60,
        intro="The night market is buzzing. Rats will chase you when they smell your filling. Oil slicks are slippery!"),

    _lv("market-2", "market", "Stall Rush", [
        "################################",
        "#@...#......^^.....^^......#...#",
        "#....#..TT..^^..3..^^..TT..#.5.#",
        "#....#..TT.........,...TT..#...#",
        "#..0.#.......====.....r....X...#",
        "#....###..f..====..........#####",
        "#......n.....====.......n......#",
        "#.TTT......................TTT.#",
        "#.T6T...,,,,,,,,,,,,,,,,...T7T.#",
        "#.T.T...,,r,,,,,,,,,,,,,...T.T.#",
        "#.......,,,,,,0,,,,,,,,,.......#",
        "#..==...,,,,,,,,,,,,,,f,....==.#",
        "#..==.....4....................#",
        "#.....T.TT..5..TT.TT..4..TT.T..#",
        "#..r..T$.T.....T.0.T.....T.5T.E#",
        "################################",
    ], legend={"0": "char_siu", "3": "chili", "4": "corn", "5": "peanut", "6": "chicken", "7": "lap_cheong"},
        npcs=[npc("sesame", "Auntie Sesame", "peanut", 3, "honey", 2,
                  "I need three bags of peanuts for my sesame balls. The rats got mine!",
                  "Wonderful! Here's some honey, sweetie."),
              npc("fortune", "Lucky Cookie", "corn", 2, "chili", 1,
                  "Psst! Two sweet corns and I'll tell your fortune. And give you a chili.",
                  "Your fortune: 'A great filling awaits you.' Here's your chili!")],
        goals={"meat": 3, "errands": True, "nests": False}, par=75,
        intro="Two neighbours need help before the dinner rush. Flies buzz right over the stalls, so keep moving."),

    _lv("market-3", "market", "Rat Ring", [
        "################################",
        "#@.......#..........#..........#",
        "#........#....0.....#.....3....#",
        "#..TTT...X..........X..........#",
        "#..T1T...#####..#####...TTTT...#",
        "#..T.T.......#..#.......T.0T...#",
        "#......,,,,,,#..#,,,,,,,T..T...#",
        "#####..,,O,,,....,,,O,,,TT.T####",
        "#...#..,,,,,,....,,,,,,,.......#",
        "#.?.#..,,,,,,#..#,,,,,,,..r....#",
        "#...#..,,,,,,#..#,,,,,,,.......#",
        "#...X........#..#..........n...#",
        "#####..####..####..####..#######",
        "#........#.......0..#..........#",
        "#..r.....#..,,,,,,,.#...,,,,,..#",
        "#..6..7..X..,,,O,,,.X...,,3,,..#",
        "#........#..,,,,,,,.#...,,,,,.E#",
        "################################",
    ], legend={"0": "char_siu", "1": "honey", "3": "chili", "6": "chicken", "7": "lap_cheong"},
        npcs=[npc("dumpling", "Chef Wonton", "chili", 2, "lap_cheong", 2,
                  "Three rat nests in my market! While you clear them out, could you grab me two chilies?",
                  "The rats are gone and I have my chilies. Take this sausage!")],
        nests=[{"k": "rat", "r": 4}, {"k": "rat", "r": 4}, {"k": "rat", "r": 4}],
        goals={"meat": 4, "errands": True, "nests": True}, par=100,
        intro="Three rat nests have taken over the market square. Destroy them all to free the Night Market!"),

    # ===================================================== Dim Sum Palace
    _lv("dimsum-1", "dimsum", "Trolley Lanes", [
        "##############################",
        "#@....#..................#...#",
        "#.....#..TTTT....TTTT....#.0.#",
        "#..1..#..T.7T....T0.T....X...#",
        "#.....#..TT.T....T.TT....#####",
        "#.....#......................#",
        "#.RRRRRRRRRRRRRRRRRRRRRRRRRRR#",
        "#............................#",
        "#..,,,,,,,,..n...,,,,,,,,,...#",
        "#..,,0,,,,,......,,,,,c,,,...#",
        "#..,,,,,,,,......,,,,,,,,,...#",
        "#LLLLLLLLLLLLLLLLLLLLLLLLLLLL#",
        "#............................#",
        "#..TT..2..TT...4..TT..1...TT.#",
        "#..TT..0..TT..c...TT...$..TT.E",
        "##############################",
    ], legend={"0": "shrimp", "1": "bok_choy", "2": "rice", "4": "mushroom", "7": "pork_belly"},
        npcs=[npc("dumpling", "Har Gow Harry", "bok_choy", 2, "shrimp", 2,
                  "The trolleys keep rolling and I'm out of bok choy! Two, please!",
                  "Splendid! Some shrimp for your trouble.")],
        goals={"meat": 4, "errands": True, "nests": False}, par=70,
        intro="Trolley lanes push you along. Ride them to go fast, or dash across. Cockroaches take two bonks."),

    _lv("dimsum-2", "dimsum", "The Steamer Stacks", [
        "################################",
        "#@..........#.......#..........#",
        "#..P..P..P..#..P.P..#..P..P..P.#",
        "#...........D.......U..........#",
        "#..P..P..P..D..P0P..U..P..P..P.#",
        "#.....0.....D.......U.....5....#",
        "#..P..P..P..#..f....#..P..P..P.#",
        "#####..######..###..######..####",
        "#......,,,,,,..n.......,,,,,,..#",
        "#..c...,,3,,,...........,,4,,..#",
        "#......,,,,,,........c.,,,,,,..#",
        "####..#####RRRRRRRRRR#####..####",
        "#..........#..........#......$.#",
        "#..0..P....#...6..2...X........#",
        "#.....P..f.#..........#..0...E.#",
        "################################",
    ], legend={"0": "shrimp", "2": "rice", "3": "mushroom", "4": "egg", "5": "coconut", "6": "lap_cheong"},
        npcs=[npc("eggtart", "Little Tart", "egg", 1, "coconut", 1,
                  "I'm making custard but I dropped my egg somewhere in the east hall!",
                  "Yay! Custard time! Here, have a coconut.")],
        goals={"meat": 4, "errands": True, "nests": False}, par=75,
        intro="A maze of steamer stacks. The up and down conveyors are one-way streets!"),

    _lv("dimsum-3", "dimsum", "Palace Kitchens", [
        "##################################",
        "#@.....#.....^^^^^^.....#........#",
        "#......#.....^^^^^^.....#...0....#",
        "#..7...X................X........#",
        "#......#..TTTTTT..TTTTTT#####..###",
        "####.###..T..1.T..T.2..T.........#",
        "#.........TT..TT..TT..TT..,,,,,..#",
        "#..,,,,,.................,,O,,,..#",
        "#..,,O,,..RRRRRRRRRRRRR..,,,,,,..#",
        "#..,,,,,.................,,,,,,..#",
        "#.........LLLLLLLLLLLLL..........#",
        "#####..####............####..#####",
        "#........#...n.....4...#.........#",
        "#..0..c..#.............#..5..c...#",
        "#........X......0......X.........#",
        "####..########..####..######..####",
        "#.?.......$.......0........1...E.#",
        "##################################",
    ], legend={"0": "shrimp", "1": "bok_choy", "2": "rice", "4": "mushroom", "5": "coconut", "7": "pork_belly"},
        npcs=[npc("tofu", "Head Chef Tofu", "mushroom", 1, "rice", 2,
                  "Roaches in MY palace kitchens?! Clear their nests and find me a shiitake.",
                  "The palace is spotless again. Take some sticky rice!")],
        nests=[{"k": "roach", "r": 4}, {"k": "roach", "r": 4}],
        goals={"meat": 4, "errands": True, "nests": True}, par=110,
        intro="Roach nests in the palace kitchens! Clear both to free the Dim Sum Palace."),

    # ===================================================== Spice Mountain
    _lv("spice-1", "spice", "Pepper Fields", [
        "##############################",
        "#@...,,,,,,,,,,..#,,,,,,,,,,,#",
        "#....,,1,,,,1,,..#,,,1,,,,1,,#",
        "#....,,,,,,,,,,..#,,,,,,,,,,,#",
        "#....,,,,a,,,,,....,,,,a,,,,,#",
        "#....PPPPPPP..PPPPPPP..PPPPPP#",
        "#............................#",
        "#..%%%...0.....n......%%%..0.#",
        "#..%%%................%%%....#",
        "#PPPPPP..PPPPPPP..PPPPPPPP..P#",
        "#,,,,,,,,,,,,,,..,,,,,,,,,,,,#",
        "#,,2,,,,c,,,,,,..,,,0,,,,c,,,#",
        "#,,,,,,,,,,,,,,..,,,,,,,,,,,,#",
        "#,,,,3,,,,,,,$,..,,,,,,4,,,,E#",
        "##############################",
    ], legend={"0": "beef", "1": "chili", "2": "garlic", "3": "peanut", "4": "onion"},
        npcs=[npc("sesame", "Farmer Chen", "chili", 3, "beef", 1,
                  "Harvest time! Help me pick three chilies from the terraces.",
                  "Ha! Fresh and fiery. Have some brisket!")],
        goals={"meat": 3, "errands": True, "nests": False}, par=70,
        intro="The chili terraces of Spice Mountain. Sticky sauce slows you down."),

    _lv("spice-2", "spice", "Hotpot Hall", [
        "################################",
        "#@.....#..^^^..#..^^^..#.......#",
        "#......#..^0^..#..^5^..#...1...#",
        "#..2...#..^^^..#..^^^..#.......#",
        "#......#.......#.......X.......#",
        "##X######..f......f....#####.###",
        "#.........%%%%%%%%%%...........#",
        "#..n......%%%%0%%%%%......n....#",
        "#.........%%%%%%%%%%...........#",
        "#####.#######....######..#######",
        "#..^^^...#...c.....#...^^^..0..#",
        "#..^4^...#....3....#...^1^.....#",
        "#..^^^...X.........X...^^^..$..#",
        "#........#....0....#...........#",
        "#..c.....#.........#.........E.#",
        "################################",
    ], legend={"0": "beef", "1": "chili", "2": "garlic", "3": "peanut", "4": "onion", "5": "carrot"},
        npcs=[npc("tofu", "Auntie Mala", "chili", 2, "garlic", 2,
                  "My hotpot isn't spicy enough! Bring me two chilies.",
                  "NOW it's hot! Take some garlic, dear."),
              npc("mooncake", "Uncle Pao", "onion", 1, "beef", 1,
                  "Could you grab me an onion? It's in the hot corner, careful!",
                  "You're braver than me. Here's some brisket.")],
        goals={"meat": 4, "errands": True, "nests": False}, par=90,
        intro="Bubbling hotpots everywhere. Some ingredients sit right in the middle of the heat. Be quick!"),

    _lv("spice-3", "spice", "Dragon's Peak", [
        "##################################",
        "#@...#,,,,,,,,,,#.......#,,,,,,,,#",
        "#....#,,,,O,,,,,#..^^^..#,,9,,,,,#",
        "#....#,,,,,,,,,,#..^0^..#,,,,,,,,#",
        "#..1.X,,,,,,,,,,#..^^^..X,,,,,,,,#",
        "#....#,,,,,,,,,,#.......#####..###",
        "##.###,,,,,,,,,,###..####........#",
        "#........%%%%...........%%%..O...#",
        "#..PPP...%%0%.....n.....%%%......#",
        "#..PPP...%%%%...........%%%..1...#",
        "####..#####..#########..#####..###",
        "#.....#........#.......#.........#",
        "#..c..#..^^^...#...0...#..,,,,,..#",
        "#.....X..^4^...X.......X..,,2,,..#",
        "#.....#..^^^...#.......#..,,,,,..#",
        "###..##########..#####..######..##",
        "#?.......$............c.....0..E.#",
        "##################################",
    ], legend={"0": "beef", "1": "chili", "2": "garlic", "4": "onion", "9": "dragon_chili"},
        npcs=[npc("fortune", "Old Monk Mochi", "chili", 2, "peanut", 3,
                  "Few reach the peak. Bring me two chilies and I'll tell you where the Dragon Pepper grows.",
                  "The Dragon Pepper grows where the wind sleeps, top right. Take these peanuts for the climb.")],
        nests=[{"k": "roach", "r": 5}, {"k": "fly", "r": 4}],
        goals={"meat": 4, "errands": True, "nests": True}, par=120,
        intro="The summit of Spice Mountain. Legends say a Dragon Pepper grows here..."),

    # ===================================================== Harbour Docks
    _lv("harbour-1", "harbour", "Pier Pressure", [
        "##############################",
        "#@...,,,,,,,,,,,,,,,,,,,,,,,,#",
        "#....,,,,,0,,,,,,,,,,,4,,,,,,#",
        "#....,,,,,,,,,,n,,,,,,,,,,,,,#",
        "#.....................g......#",
        "#~~~~..~~~~~~~~..~~~~~~~~..~~#",
        "#~~~~HH~~~~~~~~HH~~~~~~~~HH~~#",
        "#~~~~..~~~~~~~~..~~~~~~~~..~~#",
        "#~~...........1.............~#",
        "#~~..TTT..........TTT...0...~#",
        "#~~..T3T....r.....T5T.......~#",
        "#~~.........................~#",
        "#~~~~~~~~HH~~~~~~~~~HH~~~~~~~#",
        "#$.......HH.....0...HH......E#",
        "##############################",
    ], legend={"0": "fish", "1": "squid", "3": "salt", "4": "shrimp", "5": "rice_wine"},
        npcs=[npc("dumpling", "Fisher Lin", "salt", 1, "fish", 2,
                  "The gulls stole my salt! There's a jar on the middle pier.",
                  "Now I can cure my catch. Have a couple of fish!")],
        goals={"meat": 4, "errands": True, "nests": False}, par=70,
        intro="Bridges cross the water. Seagulls squawk before they swoop, so dash out of the way!"),

    _lv("harbour-2", "harbour", "Gull Island", [
        "################################",
        "#@.....#~~~~~~~~~~~~~~~~~~#....#",
        "#..1...#~~~,,,,,,,,,,,,~~~#..0.#",
        "#......#~~~,,,,,O,,,,,,~~~#....#",
        "#..0...HHH,,,,,,,,,,,,,HHHH..4.#",
        "#......#~~~,,,2,,,,,3,,~~~#....#",
        "#......#~~~,,,,,,,,,,,,~~~#....#",
        "###..###~~~~~~~HH~~~~~~~~~###.##",
        "#..............HH..............#",
        "#..TT..r.......n.......g...TT..#",
        "#..TT......................TT..#",
        "#~~~~~~~~~~HH~~~~~~~~HH~~~~~~~~#",
        "#..........HH........HH........#",
        "#..5....,,,,,,,,,,,,,,,,....0..#",
        "#.......,,,,,,1,,,$,,,,,.......#",
        "#..g....,,,,,,,,,,,,,,,,.....E.#",
        "#..............................#",
        "################################",
    ], legend={"0": "fish", "1": "squid", "2": "crab", "3": "shrimp", "4": "salt", "5": "rice_wine"},
        npcs=[npc("eggtart", "Captain Tart", "squid", 2, "crab", 1,
                  "Ahoy! The gull nest on the island has to go. And I'd love two squid for supper.",
                  "Shiver me sprinkles! Take this crab, matey.")],
        nests=[{"k": "gull", "r": 5}],
        goals={"meat": 5, "errands": True, "nests": True}, par=100,
        intro="A gull nest sits on the island in the middle of the bay. Cross the bridges and knock it down."),

    _lv("harbour-3", "harbour", "Lobster Lighthouse", [
        "##################################",
        "#@...,,,,,,,#~~~~~~~~~~#.........#",
        "#....,,0,,,,#~~~~~~~~~~#...6.....#",
        "#....,,,,,,,HHHHHHHHHHHH.......P.#",
        "#..TT,,,,,,,#~~~~HH~~~~#..PPP....#",
        "#..TT,,,O,,,#~~~~HH~~~~#..P?P..O.#",
        "#....,,,,,,,#~~~~HH~~~~#..P.P....#",
        "####...######~~~~HH~~~~####.###.##",
        "#...............n................#",
        "#..g.....1..............g....2...#",
        "#~~~~~HH~~~~~~~~~~~~~~~~~~~HH~~~~#",
        "#~~~~~HH~~~~~~~~~~~~~~~~~~~HH~~~~#",
        "#.......,,,,,,,,..,,,,,,,,.......#",
        "#..5....,,,0,,,,..,,,,3,,,....r..#",
        "#.......,,,,,,,,..,,,,,,,,.......#",
        "#..T.T.....r.........$....T.T....#",
        "#..T6T....................T0T..E.#",
        "##################################",
    ], legend={"0": "fish", "1": "squid", "2": "crab", "3": "shrimp", "5": "rice_wine", "6": "lobster"},
        npcs=[npc("mooncake", "Keeper Moon", "crab", 1, "lobster", 1,
                  "The lighthouse is overrun by gulls! Bring me a mud crab and I'll share my lobster.",
                  "The light shines again! Here, the finest lobster in the harbour.")],
        nests=[{"k": "gull", "r": 4}, {"k": "rat", "r": 4}],
        goals={"meat": 5, "errands": True, "nests": True}, par=120,
        intro="Light up the harbour again: clear the gull and rat nests around the lighthouse."),

    # ===================================================== Golden Banquet
    _lv("banquet-1", "banquet", "Grand Foyer", [
        "################################",
        "#@......,,,,,,,,,,,,,,,,......$#",
        "#..PP...,,TTT,,,,,,TTT,,...PP..#",
        "#..PP...,,T2T,,,,,,T4T,,...PP..#",
        "#.......,,,,,,,,,,,,,,,,.......#",
        "#...r...,,,,,,,n,,,,,,,,...f...#",
        "#.......,,,,,,,,,,,,,,,,.......#",
        "####=====####......####=====####",
        "#...=====....RRRRRRR...=====...#",
        "#..5=====..............=====.7.#",
        "#.......,,,,,,,,,,,,,,,,.......#",
        "#..c....,,,,,,,0,,,,,,,,....c..#",
        "#.......,,,,,,,,,,,,,,,,.......#",
        "#..TT......^^^....^^^......TT..#",
        "#..TT..7...^^^....^^^...5..TT.E#",
        "################################",
    ], legend={"0": "beef", "2": "honey", "4": "rice_wine", "5": "char_siu", "7": "crab"},
        npcs=[npc("fortune", "Herald Fortuna", "honey", 1, "beef", 2,
                  "Halt! Only guests bearing honey may enter the banquet. ...Oh, you have some? Welcome!",
                  "Welcome, honoured bun. Brisket for the road.")],
        goals={"meat": 4, "errands": True, "nests": False}, par=80,
        intro="The Emperor's banquet hall. Golden floors, slippery oil, and pests in fine clothes."),

    _lv("banquet-2", "banquet", "The Emperor's Kitchen", [
        "##################################",
        "#@.....#....^^^^^^^^....#........#",
        "#......#....^^^^0^^^....#..TTTT..#",
        "#..3...X....^^^^^^^^....X..T9.T..#",
        "#......#................#..TT.T..#",
        "###.####..TTTT....TTTT..#........#",
        "#.........T5.T....T.6T..####..####",
        "#..n......TT.T....T.TT...........#",
        "#....................%%%%%%......#",
        "#..,,,,,,,,..f.......%%%%%%...c..#",
        "#..,,,O,,,,..........%%0%%%......#",
        "#..,,,,,,,,..........%%%%%%......#",
        "####..########UUUU#######..#######",
        "#.......=====.UUUU.=====.........#",
        "#..c....==0==.UUUU.==3==....n....#",
        "#.......=====.UUUU.=====.........#",
        "#..$...........................E.#",
        "##################################",
    ], legend={"0": "beef", "3": "lobster", "5": "rice_wine", "6": "honey", "9": "wagyu"},
        npcs=[npc("tofu", "Sous Chef Dou", "lobster", 1, "honey", 2,
                  "The Emperor wants lobster and the roaches won't leave my kitchen!",
                  "His Majesty will be pleased. Take some honey."),
              npc("grandma", "Head Cook Lao", "honey", 1, "phoenix_egg", 1,
                  "I've heard of you, little bun. Bring me a jar of honey and I'll give you something rare.",
                  "A Phoenix Egg, warm from the coals. Use it well.")],
        nests=[{"k": "roach", "r": 4}],
        goals={"meat": 4, "errands": True, "nests": True}, par=110,
        intro="The Golden Wagyu is kept in the Emperor's private pantry. Find it!"),

    _lv("banquet-3", "banquet", "The Rat King's Feast", [
        "##################################",
        "#@.....#...................#.....#",
        "#..0...#..,,,,,,,,,,,,,,,..#..1..#",
        "#......X..,,,,,,,,,,,,,,,..X.....#",
        "#......#..,,,,,,,,,,,,,,,..#.....#",
        "###..###..,,,,,,,,,,,,,,,..###..##",
        "#.........,,,,,,,K,,,,,,,........#",
        "#..O......,,,,,,,,,,,,,,,......O.#",
        "#.........,,,,,,,,,,,,,,,........#",
        "#..TT.....,,,,,,,,,,,,,,,.....TT.#",
        "#..TT.....,,,,,,,,,,,,,,,.....TT.#",
        "###..###.....................###.#",
        "#......#..^^^.........^^^..#.....#",
        "#..2...#..^5^....n....^4^..#..0..#",
        "#......X..^^^.........^^^..X.....#",
        "#......#...................#.....#",
        "####..########..+..##########..###",
        "#..?........................$....#",
        "#..........0.........0........E..#",
        "##################################",
    ], legend={"0": "beef", "1": "phoenix_egg", "2": "honey", "4": "lobster", "5": "wagyu"},
        npcs=[npc("grandma", "Grandma Bao", "honey", 1, "pork_belly", 3,
                  "Bao! You made it! The Rat King is in the banquet hall. Bring me some honey for courage, then show him who's boss.",
                  "That's my bun. Now go get him!")],
        nests=[{"k": "rat", "r": 4}, {"k": "rat", "r": 4}],
        goals={"meat": 5, "errands": True, "nests": True}, par=150,
        intro="The Rat King sits on the Emperor's banquet table. Bonk him eight times to free the land!"),
]


# ---------------------------------------------------------------- version 2 (2026-10-26)
# Health hearts in every level with pests (before, only the Rat King's level had one).
# Each built-in keeps its version-1 data in "v1", so Game.upgrade_builtins() can update live levels
# that nobody has edited, and leave levels edited in the builder alone.
HEARTS_V2 = {
    "kitchen-2": [(13, 5)], "kitchen-3": [(16, 9), (21, 13)],
    "market-1": [(15, 9)], "market-2": [(13, 9)], "market-3": [(15, 10), (22, 13)],
    "dimsum-1": [(18, 12)], "dimsum-2": [(12, 10)], "dimsum-3": [(17, 11), (24, 13)],
    "spice-1": [(16, 7)], "spice-2": [(6, 4)], "spice-3": [(16, 9), (24, 12)],
    "harbour-1": [(16, 7)], "harbour-2": [(12, 9)], "harbour-3": [(18, 9), (24, 12)],
    "banquet-1": [(15, 7), (22, 10)], "banquet-2": [(13, 10), (24, 13)],
}
for _lv in LEVELS:
    _lv["v1"] = {k: (list(v) if isinstance(v, list) else (dict(v) if isinstance(v, dict) else v)) for k, v in _lv["data"].items()}
    _lv["v1"]["ents"] = [dict(e) for e in _lv["data"]["ents"]]
    for _x, _y in HEARTS_V2.get(_lv["key"], []):
        _lv["data"]["ents"].append({"t": "pickup", "k": "heart", "x": _x, "y": _y})


# ---------------------------------------------------------------- worlds 7-16 (2026-10-29)
# 100 more levels, made by tools/gen_levels.py (which checks each one) and kept as plain data in LevelPack.
from . import LevelPack as _pack  # noqa: E402
TERRITORIES = TERRITORIES + _pack.TERRITORIES
LEVELS = LEVELS + _pack.LEVELS


def canon(d):
    """A comparable form of level data (Anvil may hand back 3.0 where we stored 3)."""
    if isinstance(d, dict):
        return {k: canon(v) for k, v in d.items()}
    if isinstance(d, list):
        return [canon(v) for v in d]
    if isinstance(d, float) and d.is_integer():
        return int(d)
    return d
