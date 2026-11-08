"""Server tests: the real server modules against the strict in-memory table mock.

    python -I tools/testing/test_server.py      # prints ALL OK at the end
"""
import datetime as dt
import pathlib
import shutil
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
PROJECT = HERE.parents[1]
tmp = pathlib.Path(tempfile.mkdtemp(prefix="bbtest-"))
shutil.copytree(PROJECT / "server_code", tmp / "app")
(tmp / "app" / "__init__.py").write_text("")
sys.path[:0] = [str(HERE / "mock"), str(tmp)]

import anvil.server  # noqa: E402
import anvil.users  # noqa: E402
from anvil.tables import app_tables as T  # noqa: E402
from app import Admin, Catalog as C, Game as G, Levels as L  # noqa: E402

FAILS = []


def ok(cond, msg):
    print(("ok   " if cond else "FAIL ") + msg)
    if not cond:
        FAILS.append(msg)


def raises(fn, exc, msg):
    try:
        fn()
    except exc:
        ok(True, msg)
        return
    except Exception as e:
        ok(False, "%s (raised %r)" % (msg, e))
        return
    ok(False, msg + " (did not raise)")


TODAY = dt.datetime.now(dt.timezone.utc).date().isoformat()
now = dt.datetime.now(dt.timezone.utc)


def user(email, **kw):
    return T.users.add_row(email=email, signed_up=now, enabled=True, **kw)


def win(level_key, extra=None):
    """A perfect result for a level, built from its data (what a real playthrough reports)."""
    row = T.levels.get(key=level_key)
    tot = L.totals(row["data"])
    npcs = [e for e in row["data"]["ents"] if e["t"] == "npc"]
    r = {"time": 10.0, "picked": dict(tot["items"]), "errands": list(range(len(npcs))), "nests": tot["nests"],
         "kings": tot["kings"], "coins": tot["coins"], "pests": 4, "crates": tot["crates"], "damage": 0,
         "chopsticks": tot["chopsticks"] > 0, "postcard": tot["postcard"] > 0, "knobs": tot["knobs"], "bonuses": tot["bonuses"]}
    r.update(extra or {})
    return r


# ---- every built-in level passes its own checks
for lv in L.LEVELS:
    e, w = L.check(lv["data"])
    ok(not e and not w, "level %s checks clean %s %s" % (lv["key"], e, w))
ok(len(L.LEVELS) == 118 and len(L.TERRITORIES) == 16, "118 levels in 16 territories")
ok(all(len([l for l in L.LEVELS if l["territory"] == t["key"]]) == 10 for t in L.TERRITORIES[6:]), "worlds 7-16 have 10 levels each")
ok(len({l["key"] for l in L.LEVELS}) == 118, "level keys are unique")
used_pests = {e["k"] for lv in L.LEVELS for e in lv["data"]["ents"] if e["t"] in ("pest", "nest")}
ok(used_pests >= {"snail", "mould", "frog", "weevil", "spider", "wasp", "queen", "king"}, "every new pest appears in a level")
used_pk = {e["k"] for lv in L.LEVELS for e in lv["data"]["ents"] if e["t"] == "pickup"}
ok(used_pk >= C.BONUS_KEYS | C.KNOB_KEYS, "every bonus and both oven knobs appear in a level (%s)" % sorted(C.BONUS_KEYS | C.KNOB_KEYS - used_pk))
ok(all(sum(1 for lv in L.LEVELS if lv["territory"] == t["key"] and L.totals(lv["data"])["postcard"]) == 1 for t in L.TERRITORIES),
   "one postcard per territory")
ok(sum(1 for lv in L.LEVELS if lv["data"].get("bonus")) == 10, "ten bonus rounds")
import subprocess  # noqa: E402
gen = subprocess.run([sys.executable, "-I", str(PROJECT / "tools" / "gen_levels.py"), "--check"], capture_output=True, text=True)
ok(gen.returncode == 0, "LevelPack.py matches the generator (%s)" % gen.stdout.strip())
ok(len(C.ITEMS) >= 10, "at least 10 ingredient types (%d)" % len(C.ITEMS))

# ---- guests: state, seeding
anvil.users.CURRENT[0] = None
s = G.guest_state(None, TODAY)
ok(s["ok"] and len(s["journey"]) == 16, "guest state seeds 16 territories")
ok(s["status"]["unlocked"] == ["kitchen-1"], "only the first level is unlocked")
ok(all(t["postcard"] is None for t in s["journey"]), "postcards are hidden until found")
ok(s["daily_ready"], "daily box ready for a new player")
p = s["progress"]

r = G.guest_finish_level(p, "kitchen-2", win("kitchen-2"), TODAY)
ok(not r["ok"] and "unlocked" in r["error"], "locked level is refused")

bad = win("kitchen-1", {"picked": {"pork_belly": 1, "scallion": 2}})
r = G.guest_finish_level(p, "kitchen-1", bad, TODAY)
ok(not r["ok"] and "meat" in r["error"].lower(), "a win without enough meat is refused")

cheat = win("kitchen-1", {"picked": {"pork_belly": 99, "scallion": 99, "wagyu": 5}, "coins": 9999, "pests": 9999})
r = G.guest_finish_level(p, "kitchen-1", cheat, TODAY)
ok(r["ok"], "kitchen-1 won")
rep = r["report"]
p = r["progress"]
ok(p["pantry"].get("pork_belly") == 3 and "wagyu" not in p["pantry"], "items capped at what the level holds")
ok(p["pantry"].get("scallion", 0) == 0 and p["pantry"].get("egg") == 1, "errand hands over scallions, gift egg arrives")
ok(rep["first_clear"] and rep["stars"] == [True, True, True], "three stars on a perfect run")
ok("kitchen-2" in rep["unlocked"], "kitchen-2 unlocks")
ok("first_bite" in rep["new_badges"] and "flawless" in rep["new_badges"], "first badges earned")
coins1 = p["coins"]
ok(coins1 == 3 + 150 + 5 + 30 + 20, "coins add up (got %d)" % coins1)

r = G.guest_finish_level(p, "kitchen-1", win("kitchen-1", {"time": 999}), TODAY)
ok(r["ok"] and not r["report"]["first_clear"] and r["report"]["new_stars"] == [], "replay: no first-clear bonus")
ok(r["progress"]["levels"]["kitchen-1"]["best"] == 10.0, "best time kept")
p = r["progress"]

# ---- daily box, market, hats, cooking
r = G.guest_claim_daily(p, TODAY)
ok(r["ok"] and sum(r["report"]["items"].values()) == 3, "daily box gives 3 items")
p = r["progress"]
r = G.guest_claim_daily(p, TODAY)
ok(not r["ok"], "daily box only once a day")

offers = G.market_offers(G._client_today(TODAY))
ok(len(offers) == C.MARKET_SIZE and offers == G.market_offers(G._client_today(TODAY)), "market is stable for the day")
p["coins"] = 500
r = G.guest_buy_market(p, offers[0]["id"], TODAY)
ok(r["ok"] and r["progress"]["pantry"].get(offers[0]["item"], 0) >= offers[0]["qty"], "market purchase lands in pantry")
r2 = G.guest_buy_market(r["progress"], offers[0]["id"], TODAY)
ok(not r2["ok"], "each offer once a day")
p = r["progress"]

r = G.guest_buy_hat(p, "toque", TODAY)
ok(r["ok"] and r["progress"]["hat"] == "toque", "bought and wearing the toque")
ok(not G.guest_buy_hat(r["progress"], "crown", TODAY)["ok"], "the crown can't be bought")
p = r["progress"]

p["pantry"].update({"pork_belly": 3, "scallion": 2, "garlic": 1})
r = G.guest_cook(p, "pork_bao", TODAY)
ok(r["ok"] and r["report"]["first"] and "hearty" in r["status"]["perks"], "cooking unlocks a perk")
ok("pork_belly" not in r["progress"]["pantry"], "ingredients used up")
ok(not G.guest_cook(r["progress"], "pork_bao", TODAY)["ok"], "can't cook without ingredients")
p = r["progress"]
p["pantry"].update({"pork_belly": 3, "scallion": 2, "garlic": 1})
c0 = p["coins"]
r = G.guest_cook(p, "pork_bao", TODAY)
ok(r["ok"] and r["progress"]["coins"] == c0 + C.RECIPE_SELL, "cooking again sells the bao")
p = r["progress"]

# ---- normalize drops junk from a browser
junk = {"coins": -5, "pantry": {"pork_belly": "7", "fake": 3}, "hats": ["toque", "fake", "toque"], "hat": "fake",
        "levels": {"kitchen-1": {"stars": [1, 0], "best": "x"}}, "stats": {"meat": "lots"}}
n = G.normalize(junk)
ok(n["coins"] == 0 and n["pantry"] == {"pork_belly": 7} and n["hats"] == ["none", "toque"] and n["hat"] == "none",
   "normalize cleans junk")
ok(n["levels"]["kitchen-1"]["stars"] == [True, False, False] and n["levels"]["kitchen-1"]["best"] is None, "normalize fixes levels")

# ---- full journey as a signed-in player
ana = user("ana@example.com")
anvil.users.CURRENT[0] = ana
s = G.get_state(TODAY)
ok(s["ok"] and s["me"]["name"] == "ana" and not s["me"]["is_admin"], "signed-in state")
r = G.import_guest(p, TODAY)
ok(r["progress"]["levels"].get("kitchen-1"), "guest progress imported into an empty account")
ok(G.import_guest(G.new_progress(), TODAY)["progress"]["levels"].get("kitchen-1"), "import never overwrites real progress")

postcards = 0
for lv in L.LEVELS:
    r = G.finish_level(lv["key"], win(lv["key"]), TODAY)
    if not r["ok"]:
        ok(False, "finish %s: %s" % (lv["key"], r["error"]))
        break
    postcards += 1 if r["report"]["postcard"] else 0
ok(r["ok"], "won every level in order")
st = r["status"]
ok(len(st["cleared"]) == 16 and st["stars"] == 354, "all territories liberated, 354 stars")
ok(st["clears"] == 118 and st["levels_max"] == 118, "118 levels cleared")
ok(postcards == 16 and all(t["postcard"] for t in G.get_state(TODAY)["journey"]), "16 postcards found and readable")
ok(r["report"]["liberated"] == "dragon", "last win liberates the Dragon's Kitchen")
bd = r["progress"]["badges"]
ok(all(b in bd for b in ("traveller", "century", "constellation", "chopstick_master", "hive_breaker", "snacker", "oven_mitts")),
   "the new badges are earned (%s)" % sorted(set(b["key"] for b in C.BADGES) - set(bd)))
b = r["progress"]["badges"]
for k in ("liberator", "star_chef", "pen_pal", "king_slayer", "legend_hunter", "speedy"):
    ok(k in b, "badge " + k)
ok(st["chopsticks"] == st["chopsticks_max"] and st["chopsticks_max"] >= 15, "golden chopsticks counted (%d)" % st["chopsticks_max"])
board = G.leaderboard("kitchen-1")
ok(board["total"] == 1 and board["top"][0]["you"], "leaderboard has ana")
ok(T.levels.get(key="kitchen-1")["clears"] >= 1, "clears counted")

# Every recipe can be cooked from what the journey gives (plus replays).
prog = r["progress"]
for rec in C.RECIPES:
    for k in rec["needs"]:
        ok(any(k in L.totals(lv["data"])["items"] or any(e.get("gift") == k for e in lv["data"]["ents"]) for lv in L.LEVELS),
           "recipe %s: %s is findable" % (rec["key"], k))

ok(G.set_name("  Bun   Master ", TODAY)["me"]["name"] == "Bun Master", "name cleaned")
ok(not G.set_name("x", TODAY)["ok"], "short name refused")

# ---- admin
raises(lambda: Admin.admin_state(), anvil.server.PermissionDenied, "non-admins can't open the editor")
boss = user("arkulinskis@gmail.com")
anvil.users.CURRENT[0] = boss
ok(Admin.admin_whoami()["is_admin"], "the owner's email is an admin")
a = Admin.admin_state()
ok(len(a["territories"]) == 16 and sum(len(t["levels"]) for t in a["territories"]) == 118, "admin sees everything")
d = L.from_ascii(["##########", "#@..0...E#", "#........#", "#........#", "#........#", "##########"], legend={"0": "beef"},
                 goals={"meat": 1, "errands": False, "nests": False}, par=20)
r = Admin.save_level({"territory": "kitchen", "name": "Tiny Test", "data": d, "published": True})
key = r["saved"]
ok(r["ok"] and not r["errors"], "new level saved")
kl = [l for l in r["territories"][0]["levels"]]
ok(kl[-1]["key"] == key and kl[-1]["published"], "appended to the kitchen, published")
d2 = dict(d, ents=[e for e in d["ents"] if e["t"] != "exit"])
r = Admin.save_level({"key": key, "territory": "kitchen", "name": "Tiny Test", "data": d2, "published": True})
lvl = [l for l in r["territories"][0]["levels"] if l["key"] == key][0]
ok(r["errors"] and not lvl["published"] and r["note"], "a broken level is kept as a draft")
r = Admin.move_level(key, -1)
ok(r["territories"][0]["levels"][-2]["key"] == key, "level moved up")
r = Admin.save_level({"key": key, "territory": "market", "name": "Moved", "data": d, "published": True})
ok(any(l["key"] == key for l in r["territories"][1]["levels"]), "level moved to another territory")
anvil.users.CURRENT[0] = ana
s = G.get_state(TODAY)
ok(key in [l["key"] for l in s["journey"][1]["levels"]], "players see the new level")
anvil.users.CURRENT[0] = boss
r = Admin.save_territory({"name": "Noodle Bar", "emoji": "🍜", "theme": "market", "pest": "fly", "blurb": "Slurp."})
nk = r["territories"][-1]["key"]
ok(r["territories"][-1]["name"] == "Noodle Bar", "territory added")
r = Admin.delete_territory("kitchen")
ok(r["ok"] is False, "can't delete a territory with levels")
r = Admin.delete_territory(nk)
ok(all(t["key"] != nk for t in r["territories"]), "empty territory deleted")
row = T.levels.get(key="kitchen-1")
row["data"] = d
Admin.restore_level("kitchen-1")
ok(T.levels.get(key="kitchen-1")["data"]["w"] == 22, "built-in level restored")
r = Admin.delete_level(key)
ok(all(l["key"] != key for t in r["territories"] for l in t["levels"]), "level deleted")
T.levels.get(key="spice-2").delete()
ok(Admin.restore_defaults()["note"].startswith("Restored 1"), "deleted built-in level restored")
pl = Admin.list_players()
ok(pl["ok"] and any(x["email"] == "ana@example.com" and x["stars"] == 354 for x in pl["players"]), "players list")
ok(Admin.set_admin("ana@example.com", True)["ok"] and T.users.get(email="ana@example.com")["is_admin"], "made ana an admin")
ok(not Admin.set_admin("arkulinskis@gmail.com", False)["ok"], "can't remove own admin")
cd = Admin.clean_data({"w": 10, "h": 3, "tiles": ["#@#", "zz"], "ents": [{"t": "evil", "x": 1, "y": 1},
                                                                          {"t": "npc", "x": 1, "y": 1, "style": "x"}]})
ok(len(cd["tiles"]) == 3 and all(len(t) == 10 for t in cd["tiles"]) and cd["ents"][0]["style"] == "dumpling",
   "clean_data pads tiles and drops unknown entities")

# ---- version 2 levels: hearts, and the upgrade of unedited live levels
ok(sum(1 for lv in L.LEVELS[:18] for e in lv["data"]["ents"] if e["t"] == "pickup" and e["k"] == "heart") == 24, "24 hearts placed in the first 18 levels")
for lv in L.LEVELS:
    e2, w2 = L.check(lv["data"])
    ok(not e2 and not w2, "v2 level %s still checks clean" % lv["key"])
r1, r2 = T.levels.get(key="market-1"), T.levels.get(key="market-2")
r1["data"] = [x for x in L.LEVELS if x["key"] == "market-1"][0]["v1"]                  # as shipped in version 1
r2["data"] = dict([x for x in L.LEVELS if x["key"] == "market-2"][0]["v1"], par=99)    # edited by the admin
ok(G.upgrade_builtins() == 1, "one unedited level upgraded")
ok(any(e.get("k") == "heart" for e in T.levels.get(key="market-1")["data"]["ents"] if e["t"] == "pickup"), "it now has a heart")
ok(T.levels.get(key="market-2")["data"]["par"] == 99, "the edited level was left alone")
ok(G.upgrade_builtins() == 0, "upgrading twice does nothing")

# ---- feedback
anvil.users.CURRENT[0] = None
ok(not G.submit_feedback("bug", "hi")["ok"], "too-short feedback refused")
ok(G.submit_feedback("bug", "The roach hurt me while I was dashing!", "", {"level": "dimsum-1", "screen": "play", "junk": None})["ok"],
   "guest sends a bug report")
bo = user("bo@example.com", display_name="Bo")
anvil.users.CURRENT[0] = bo
ok(G.submit_feedback("idea", "More hats please, maybe a dragon hat.", None, {"x": 1})["ok"], "player sends an idea")
for i in range(10):
    last = G.submit_feedback("other", "spam message %d" % i)
ok(not last["ok"], "rate limit kicks in")
raises(lambda: Admin.list_feedback(), anvil.server.PermissionDenied, "players can't read feedback")
anvil.users.CURRENT[0] = boss
fb = Admin.list_feedback()
ok(fb["ok"] and fb["counts"]["new"] >= 2, "admin sees the feedback")
bug = [x for x in fb["items"] if x["kind"] == "bug"][0]
ok(bug["name"] == "Guest" and bug["context"].get("level") == "dimsum-1" and "junk" not in bug["context"], "guest report with its game info")
idea = [x for x in fb["items"] if x["kind"] == "idea"][0]
ok(idea["email"] == "bo@example.com" and idea["name"] == "Bo", "player name and email filled in")
r = Admin.set_feedback_status(bug["id"], "done", "new")
ok(all(x["id"] != bug["id"] for x in r["items"]) and r["counts"]["done"] == 1, "marked done, filtered out of New")
r = Admin.delete_feedback(idea["id"])
ok(all(x["id"] != idea["id"] for x in r["items"]), "feedback deleted")
ok("feedback_new" in Admin.admin_state()["stats"], "admin state counts new feedback")

# ---- worlds 7-16 reach an app that was seeded with only the first 6 territories
new_keys = [t["key"] for t in L.TERRITORIES[6:]]
for row in list(T.levels.search()):
    if row["territory"] is not None and row["territory"]["key"] in new_keys:
        row.delete()
for row in list(T.territories.search()):
    if row["key"] in new_keys:
        row.delete()
T.levels.get(key="spice-3").delete()  # an admin deleted an old built-in on purpose
ok(len(T.territories.search()) == 6, "simulated an older install with 6 territories")
G._UPGRADED[0] = False
G.ensure_seeded()
ok(len(T.territories.search()) == 16 and len(T.levels.search(territory=T.territories.get(key="dragon"))) == 10,
   "the new worlds and their levels are added on the next load")
ok(T.levels.get(key="spice-3") is None, "a deliberately deleted old level stays deleted")
ok(T.territories.get(key="noodle")["position"] == 6.0, "new worlds come after the first six")
G._UPGRADED[0] = False
G.ensure_seeded()
ok(len(T.levels.search()) == 117, "seeding twice adds nothing")

# ---- bonuses, knobs and coin bags are capped by what a level holds
bag_lv = next(lv for lv in L.LEVELS if any(e["t"] == "pickup" and e["k"] == "bag" for e in lv["data"]["ents"]))
tb = L.totals(bag_lv["data"])
ok(tb["coins"] >= C.BAG_COINS and tb["bonuses"] >= 1, "a coin bag counts as 5 coins and a bonus")
ok(L.totals(next(lv for lv in L.LEVELS if lv["key"] == "dragon-10")["data"])["kings"] == 2, "the final level has two bosses")
q = G.new_progress()
q["levels"] = {lv["key"]: {"stars": [True, False, False], "best": None, "chop": False, "clears": 1} for lv in L.LEVELS}
jr = G.journey()
q2, rep = G.apply_finish(G.normalize(q), G._level_row(bag_lv["key"], jr), jr, win(bag_lv["key"], {"knobs": 999, "bonuses": 999}), dt.date.today())
ok(q2["stats"]["bonuses"] == tb["bonuses"] and q2["stats"]["knobs"] <= 3 * tb["knobs"], "bonus and knob stats are capped")
raises(lambda: G.apply_finish(G.normalize(q), G._level_row("dragon-10", jr), jr, win("dragon-10", {"kings": 1}), dt.date.today()),
       G.GameError, "both bosses must be beaten")

print("\nALL OK" if not FAILS else "\n%d FAILED" % len(FAILS))
sys.exit(1 if FAILS else 0)
