from anvil import *

from ._anvil_designer import RoadNodeTemplate
from ... import bun


class RoadNode(RoadNodeTemplate):
    """Journey → one level on the world's road: its number (or a lock), stars, boss/bonus tag, the bun on the next one.
    BB.layoutRoad positions it (data-level is how the page finds it again after a level)."""

    def __init__(self, **properties):
        super().__init__(**properties)
        t, l, i, dn = self.item["t"], self.item["l"], self.item["i"], self.dom_nodes
        key = l["key"]
        rec, n, unl = bun.level_rec(key), bun.stars_of(key), bun.is_unlocked(key)
        info = bun.level_info(l.get("data") or {})
        self._locked = not unl
        cls = "locked" if not unl else "perfect" if n == 3 else "done" if rec["stars"][0] else ""
        if key == self.item["nxt"]:
            cls += " next"
            bun.put_portrait(dn["me"], 56, bun.st["progress"].get("hat"))
        else:
            dn["me"].hidden = True
        dn["node"].className = "g-node " + cls
        dn["node"].setAttribute("data-level", key)
        dn["btn"].textContent = str(i + 1) if unl else "🔒"
        dn["btn"].setAttribute("aria-label", "Level %d: %s%s, %d of 3 stars" % (i + 1, l["name"], "" if unl else " (locked)", n))
        if info["kings"]:
            dn["tag"].textContent, dn["tag"].title = "👑", "Boss level"
        elif info["bonus"]:
            dn["tag"].textContent, dn["tag"].title = "🎁", "Bonus round"
        else:
            dn["tag"].hidden = True
        dn["chop"].hidden = not (info["chop"] and rec.get("chop"))
        dn["nm"].textContent = l["name"]
        for k, el in enumerate((dn["s0"], dn["s1"], dn["s2"])):
            if rec["stars"][k]:
                el.textContent, el.className = "★", "on"
        dn["btn"].addEventListener("click", self._click)

    def _click(self, event):
        self.item["host"].open_level(self.item["l"]["key"], self._locked)
