from anvil import *
import anvil.js
from anvil.js import window

from ._anvil_designer import DailyTemplate
from ... import bun, flows, router

PERK_NAMES = {}  # perk key -> recipe perk name, filled from the catalog on first use


def board_lines(b, guest):
    """Daily Dish board lines for Items/BoardRow: the top 10, you below them if further down, notes."""
    if b and b.get("offline"):
        return [{"rank": None, "name": "📴 Offline: today's board comes back when you're online."}]
    if not b or not b.get("top"):
        return [{"rank": None, "name": "No times yet today. Be the first bun on the board!"}]
    rows = []
    for r in b["top"]:
        rows.append(dict(r, name=r["name"] + (" (you)" if r.get("you") else "")))
    you = b.get("you")
    if you and you.get("rank", 0) > len(b["top"]):
        rows.append(dict(you, name=you["name"] + " (you)", you=True))
    return rows


def perk_names(perks):
    if not PERK_NAMES:
        for r in (bun.st["catalog"] or {}).get("recipes", []):
            PERK_NAMES[r["perk"]] = (r["emoji"], r["perk_name"])
    return [PERK_NAMES.get(p, ("✨", p)) for p in perks]


class Daily(DailyTemplate):
    """#daily: today's Daily Dish. The level (a drawing of it), the twist every bun gets, the goals, the reward, your
    best time today, this week's stamps (no streak to lose), today's top 10 and the time until the next dish."""

    def __init__(self, args=(), **properties):
        super().__init__(**properties)
        self._timer = None
        self._tick = anvil.js.report_exceptions(self._countdown)
        self._ok = bun.ensure()
        self.dish = bun.dish() if self._ok else None
        bun.music("menu")
        self.draw()

    def draw(self):
        dn, d = self.dom_nodes, self.dish
        self.empty_box.visible = d is None
        self.dish_part.visible = d is not None
        if d is None:
            if self._ok:
                dn["empty_text"].textContent = "There's no dish today: the journey has no levels yet."
            return
        t, l, tw = d["t"], d["l"], d["twist"]
        dn["title"].textContent = "🍽️ Daily Dish #%d" % d["no"]
        dn["tier"].textContent = d["tier"]
        dn["where"].textContent = "%s %s · %s" % (t["emoji"], t["name"], bun.level_label(t, l))
        dn["lvname"].textContent = l["name"]
        dn["twist_em"].textContent = tw["emoji"]
        dn["twist_name"].textContent = tw["name"]
        hearts = tw["hearts"] or (4 if "hearty" in tw["perks"] else 3)
        names = ", ".join(n for _e, n in perk_names(tw["perks"])) or "no perks"
        dn["twist_desc"].textContent = "%s Everyone plays with %s and %d heart%s." % (
            tw["desc"], names, hearts, "" if hearts == 1 else "s")
        info = bun.level_info(l["data"])
        self.goals_panel.items = [{"e": e, "t": txt} for e, txt in bun.goals(l["data"], info)]
        sec = bun.item(d["secret"])
        won_today = any(s["today"] and s["done"] for s in bun.dish_week())
        if won_today:
            dn["reward"].textContent = "✅ Today's reward is in your pantry. Play again to beat your time!"
        else:
            dn["reward"].textContent = "First win today: +20 🪙 and a secret ingredient (%s ×%d)." % (
                "???" if not bun.st["progress"]["seen"].get(d["secret"]) else sec["name"], d["qty"])
        b = bun.dish_best()
        if b:
            dn["best"].textContent = "⏱ %s · %s" % (bun.fmt_clock(b["time"]), "❤️" * int(b.get("hearts") or 0) or "❤️")
        else:
            dn["best"].textContent = "Not played yet today."
        self.stamps_panel.items = [{"e": "🍽️" if s["done"] else ("·" if s["future"] else "○"), "t": s["label"],
                                    "kind": "g-chip g-stamp" + (" done" if s["done"] else "") + (" today" if s["today"] else ""),
                                    "title": s["day"] + (" · won" if s["done"] else "")} for s in bun.dish_week()]
        guest = bun.st["guest"]
        self.guestbar.visible = guest
        if guest:
            pend = bun.dish_pending_time()
            dn["guest_text"].textContent = ("Create a free account to put %s on today's board." % bun.fmt_clock(pend)
                                            if pend else "Create a free account to get on today's board.")
        self.board_panel.items = [{"rank": None, "name": "Loading today's board…" if bun.online() else
                                   "📴 Offline: today's board comes back when you're online."}]
        self._countdown()

    def _countdown(self, *args):
        mins = int(window.BB.minutesToMidnight())
        self.dom_nodes["countdown"].textContent = "⏳ Next dish in %dh %02dm" % (mins // 60, mins % 60)
        if self.dish and self.dish["day"] != bun.today():
            router.show()  # midnight passed: tomorrow's dish

    @handle("", "show")
    def form_show(self, **event_args):
        if not self.dish:
            return
        width = min(420, int(window.innerWidth) - 64)
        self.thumb.show(self.dish["l"]["data"], self.dish["t"]["theme"], max(200, width))
        self._timer = window.setInterval(self._tick, 30000)
        b = bun.dish_board()
        if b and b.get("total"):
            self.dom_nodes["board_title"].textContent = "Today's top buns · %d played" % b["total"]
        self.board_panel.items = board_lines(b, bun.st["guest"])

    @handle("", "hide")
    def form_hide(self, **event_args):
        if self._timer is not None:
            window.clearInterval(self._timer)
            self._timer = None

    def leave(self):
        self.form_hide()

    @handle("play_button", "click")
    def play_button_click(self, **event_args):
        router.go("play", "dish")

    @handle("save_button", "click")
    def save_button_click(self, **event_args):
        flows.sign_in("signup")
