from anvil import *

from ._anvil_designer import DishResultsTemplate
from ... import bun, state

SHARE_URL = "https://busybun.com/#daily"


class DishResults(DishResultsTemplate):
    """After a Daily Dish win: the time, hearts left, the basket, where it ranks today ("You'd be #7 of 52 today"),
    the first win's reward (coins + the secret ingredient), Share (a spoiler-free card for friends) and Play again.
    Signed in, the run goes on today's board here (offline it waits on the device). Closes with "replay", "auth" or
    "daily"."""

    def __init__(self, dish=None, report=None, result=None, found=0, total=0, **properties):
        super().__init__(**properties)
        d, rep, dn = dish or {}, report or {}, self.dom_nodes
        self._d, self._rep, self._result = d, rep, result or {}
        tw = d.get("twist") or {}
        self._max = tw.get("hearts") or (4 if "hearty" in (tw.get("perks") or []) else 3)
        left = max(0, min(self._max, int(rep.get("hearts") or 0)))
        self._hearts = "❤️" * left + "🖤" * (self._max - left)
        self._basket = "🧺 %s/%s" % (found or 0, total or 0)
        dn["where"].textContent = "🍽️ Daily Dish #%s · %s" % (d.get("no"), d.get("tier") or "")
        dn["twist_em"].textContent = tw.get("emoji") or ""
        dn["twist_name"].textContent = tw.get("name") or ""
        dn["time"].textContent = "⏱ " + bun.fmt_clock(rep.get("time"))
        dn["hearts"].textContent = self._hearts
        dn["basket"].textContent = self._basket
        dn["newbest"].hidden = not (rep.get("new_best") and not rep.get("first"))
        if rep.get("first"):
            dn["coins"].textContent = "+%s 🪙" % rep.get("coins", 0)
            new_items = rep.get("new_items") or []
            self.gained_panel.items = [{"e": bun.item(k)["emoji"], "t": "Secret ingredient: %s ×%s" % (bun.item(k)["name"], n),
                                        "new": k in new_items} for k, n in (rep.get("gained") or {}).items()]
            dn["again"].textContent = "Today's stamp is in! Come back tomorrow for a new dish."
        else:
            dn["coins"].textContent = ""
            self.gained_panel.items = []
            dn["again"].textContent = "Today's reward is already yours. Every run can still beat your best time."
        banners = []
        for b in rep.get("new_badges") or []:
            bb = bun.badge(b)
            if bb:
                banners.append({"e": bb["emoji"], "t": "Badge earned: " + bb["name"], "kind": "badge"})
        self.banners_panel.items = banners
        self.guestbar.visible = bun.st["guest"]
        dn["guest_text"].textContent = "Create a free account to put %s on today's board." % bun.fmt_clock(rep.get("time"))
        bun.sfx("win")

    @handle("", "show")
    def form_show(self, **event_args):
        state.focus(self.share_button)
        dn, rep = self.dom_nodes, self._rep
        if not bun.online():
            dn["rank"].textContent = "📴 Offline: your time goes on today's board when you're back online."
            return
        if bun.st["guest"]:
            b = bun.dish_board(rep.get("time"))
            if b.get("offline"):
                dn["rank"].textContent = "📴 Offline: today's board comes back when you're online."
            elif b.get("rank_if"):
                dn["rank"].textContent = "You'd be #%d of %d today!" % (b["rank_if"], (b.get("total") or 0) + 1)
            return
        r = bun.dish_submit_now(self._d.get("level"), self._result, rep)
        if r is None:
            dn["rank"].textContent = "📴 Your time goes on today's board when you're back online."
        elif not r.get("ok"):
            dn["rank"].textContent = r.get("error") or "This time couldn't go on the board."
        else:
            you, total = r.get("you") or {}, r.get("total") or 0
            if r.get("kept"):
                dn["rank"].textContent = "Your best today stays #%s of %d. This run would be #%s." % (
                    you.get("rank", "?"), total, r.get("rank_if") or "?")
            else:
                dn["rank"].textContent = "You're #%s of %d today!" % (you.get("rank", "?"), total)

    def share_text(self):
        tw = self._d.get("twist") or {}
        return "Busy Bun Daily Dish #%s 🥟\n%s %s\n⏱ %s %s %s\n%s" % (
            self._d.get("no"), tw.get("emoji") or "", tw.get("name") or "", bun.fmt_clock(self._rep.get("time")),
            self._hearts, self._basket, SHARE_URL)

    @handle("share_button", "click")
    def share_button_click(self, **event_args):
        bun.share(self.share_text())

    @handle("replay_button", "click")
    def replay_button_click(self, **event_args):
        self.raise_event("x-close-alert", value="replay")

    @handle("back_button", "click")
    def back_button_click(self, **event_args):
        self.raise_event("x-close-alert", value="daily")

    @handle("auth_button", "click")
    def auth_button_click(self, **event_args):
        self.raise_event("x-close-alert", value="auth")
