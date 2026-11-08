from anvil import *

from ._anvil_designer import WorldCardTemplate
from ... import bun


class WorldCard(WorldCardTemplate):
    """Journey → the world picker: one world with its number, emoji, levels done and stars."""

    def __init__(self, **properties):
        super().__init__(**properties)
        t, i, dn = self.item["t"], self.item["i"], self.dom_nodes
        s = bun.st["status"]
        done = len([l for l in t["levels"] if bun.level_rec(l["key"])["stars"][0]])
        stars = sum(bun.stars_of(l["key"]) for l in t["levels"])
        locked = not any(bun.is_unlocked(l["key"]) for l in t["levels"])
        cls = "g-world th-" + t["theme"]
        cls += " dark" if t["theme"] in bun.DARK_THEMES else ""
        cls += " sel" if t["key"] == bun.st["world"] else ""
        cls += " cur" if t["key"] == self.item["next_world"] else ""
        cls += " free" if t["key"] in s["cleared"] else ""
        cls += " locked" if locked else ""
        dn["btn"].className = cls
        dn["btn"].setAttribute("aria-label", "World %d: %s, %d of %d levels%s" % (
            i + 1, t["name"], done, len(t["levels"]), ", locked" if locked else ""))
        dn["btn"].setAttribute("aria-pressed", "true" if t["key"] == bun.st["world"] else "false")
        dn["num"].textContent = str(i + 1)
        dn["emo"].textContent = t["emoji"]
        dn["name"].textContent = t["name"]
        dn["meta"].textContent = "%d/%d · ⭐%d" % (done, len(t["levels"]), stars)
        dn["fill"].style.width = "%d%%" % int(round(100.0 * done / max(1, len(t["levels"]))))
        dn["btn"].addEventListener("click", self._click)

    def _click(self, event):
        self.item["host"].pick_world(self.item["t"]["key"])
