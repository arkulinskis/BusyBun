from anvil import *
from anvil.js import window

from ._anvil_designer import CookTemplate
from ... import bun, state


class Cook(CookTemplate):
    """Cooking a recipe: the steaming pot for at least a second while the server cooks, then the result (a new perk the
    first time, coins after that, a hat reward, badges). self.done = it was cooked."""

    def __init__(self, key=None, **properties):
        super().__init__(**properties)
        self.key, self.done = key, False
        self._r = bun.recipe(key)
        self.dom_nodes["cooking_title"].textContent = "Cooking %s…" % self._r["name"]
        self.done_part.visible = False

    @handle("", "show")
    def form_show(self, **event_args):
        t0 = window.Date.now()
        res = bun.act("cook", self.key)
        if not res or not res.get("ok"):
            self.raise_event("x-close-alert", value=None)
            return
        self.done = True
        window.setTimeout(lambda: self._show(res["report"]), max(0, 1100 - (window.Date.now() - t0)))

    def _show(self, rep):
        r, dn = self._r, self.dom_nodes
        self.cooking_part.visible, self.done_part.visible = False, True
        dn["emo"].textContent = r["emoji"]
        dn["name"].textContent = r["name"] + "!"
        self.perk_part.visible = bool(rep.get("first"))
        dn["perk_name"].textContent = r["perk_name"]
        dn["perk_desc"].textContent = r["perk_desc"]
        dn["sold"].textContent = "" if rep.get("first") else "Sold to a hungry neighbour for +%s 🪙" % rep.get("coins", 0)
        dn["sold"].hidden = bool(rep.get("first"))
        banners = []
        if rep.get("hat"):
            banners.append({"e": "👑", "t": "You earned the %s! Wear it from the Shop." % bun.hat(rep["hat"])["name"], "kind": "gold"})
        for k in rep.get("new_badges") or []:
            b = bun.badge(k)
            if b:
                banners.append({"e": b["emoji"], "t": "Badge earned: " + b["name"], "kind": "badge"})
        self.banners_panel.items = banners
        bun.sfx("clear" if rep.get("first") else "coin")
        state.focus(self.ok_button)

    @handle("ok_button", "click")
    def ok_button_click(self, **event_args):
        self.raise_event("x-close-alert", value=True)
