from anvil import *
from anvil.js import window

from ._anvil_designer import ResultsTemplate
from ... import bun, state
from ..LevelIntro import board_rows


class Results(ResultsTemplate):
    """The results card after a win (the server's report): stars popping in one by one, time and best, coins with the
    breakdown, ingredients gained (NEW ones marked), territory freed, postcard (read it right here), chopsticks,
    badges, the leaderboard. Closes with "next", "replay", "auth" or "map"."""

    def __init__(self, key=None, report=None, found=0, total=0, prev=None, **properties):
        super().__init__(**properties)
        rep, dn = report or {}, self.dom_nodes
        self._rep, self.key = rep, key
        t, l = bun.find_level(key)
        par = l["data"].get("par") or 60
        dn["where"].textContent = bun.level_label(t, l) + " · " + l["name"]
        dn["title"].textContent = "Order up! 🥟" if rep.get("first_clear") else "Delicious! 🥟"
        dn["lab1"].textContent = "All ingredients (%s/%s)" % (found or 0, total or 0)
        dn["lab2"].textContent = "Under par (%s)" % bun.fmt_time(par)
        dn["time"].textContent = "⏱ " + bun.fmt_time(rep.get("time"))
        dn["best"].textContent = "Best " + bun.fmt_time(rep.get("best"))
        dn["newbest"].hidden = not (rep.get("new_best") and not rep.get("first_clear"))
        dn["coins"].textContent = "+%s 🪙" % rep.get("coins", 0)
        self.coin_panel.items = [{"t": "%s: +%s" % (p[0], p[1]), "kind": "g-coinline"} for p in rep.get("coin_parts") or []]
        new_items = rep.get("new_items") or []
        self.gained_panel.items = [{"e": bun.item(k)["emoji"], "t": "%s ×%s" % (bun.item(k)["name"], n), "new": k in new_items}
                                   for k, n in (rep.get("gained") or {}).items()]
        banners = []
        if rep.get("liberated"):
            tt = bun.territory(rep["liberated"])
            banners.append({"e": "🏮", "t": "%s is free from pests!" % (tt["name"] if tt else "The territory"), "kind": "free"})
        if rep.get("chopsticks"):
            banners.append({"e": "🥢", "t": "Golden chopsticks added to your collection!", "kind": "gold"})
        for b in rep.get("new_badges") or []:
            bb = bun.badge(b)
            if bb:
                banners.append({"e": bb["emoji"], "t": "Badge earned: " + bb["name"], "kind": "badge"})
        self.banners_panel.items = banners
        pc = rep.get("postcard")
        self.post_part.visible = bool(pc)
        dn["postcard"].hidden = True
        if pc:
            tt = bun.territory(pc.get("territory")) or {}
            dn["stamp"].textContent = tt.get("emoji") or "✉️"
            dn["post_text"].textContent = pc.get("text") or tt.get("postcard") or ""
        self.guestbar.visible = bun.st["guest"]
        self.board_panel.items = board_rows(rep.get("leaderboard"), False)
        nxt = None
        for k in rep.get("unlocked") or []:
            nxt = nxt or k
        if not nxt:
            lv = bun.all_levels()
            for i, (tt2, ll) in enumerate(lv):
                if ll["key"] == key and i + 1 < len(lv) and bun.is_unlocked(lv[i + 1][1]["key"]):
                    nxt = lv[i + 1][1]["key"]
        self.next_key = nxt
        self.next_button.visible = bool(nxt)
        bun.sfx("win")

    @handle("", "show")
    def form_show(self, **event_args):
        rec = bun.level_rec(self.key)
        for i in range(3):
            window.setTimeout(self._star_fn(i, rec), 350 + i * 380)
        if self._rep.get("liberated"):
            window.setTimeout(lambda: bun.sfx("clear"), 1600)
        state.focus(self.next_button if self.next_key else self.replay_button)

    def _star_fn(self, i, rec):
        node = self.dom_nodes["star%d" % i]
        got = bool((self._rep.get("stars") or [False] * 3)[i])

        def pop():
            if got:
                node.classList.add("on")
                bun.sfx("star")
            elif rec["stars"][i]:
                node.classList.add("got")
        return pop

    def post_click(self, event):
        bun.sfx("unlock")
        self.dom_nodes["postcard"].hidden = False
        self.dom_nodes["post_btn"].hidden = True

    @handle("next_button", "click")
    def next_button_click(self, **event_args):
        self.raise_event("x-close-alert", value="next")

    @handle("replay_button", "click")
    def replay_button_click(self, **event_args):
        self.raise_event("x-close-alert", value="replay")

    @handle("map_button", "click")
    def map_button_click(self, **event_args):
        self.raise_event("x-close-alert", value="map")

    @handle("auth_button", "click")
    def auth_button_click(self, **event_args):
        self.raise_event("x-close-alert", value="auth")
