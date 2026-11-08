from anvil import *

from ._anvil_designer import BadgeCardTemplate
from ... import bun

# Badges counted from the status rather than a stat: (status key, target)
COUNTS = {"traveller": ("clears", 50), "century": ("clears", 100), "constellation": ("stars", 200),
          "star_chef": ("stars", 45), "chopstick_master": ("chopsticks", 50), "golden_touch": ("chopsticks", 10)}


class BadgeCard(BadgeCardTemplate):
    """Badges → one badge: earned (and when), or a bar towards it."""

    def __init__(self, **properties):
        super().__init__(**properties)
        b, dn = self.item["b"], self.dom_nodes
        p, s = bun.st["progress"], bun.st["status"]
        when = p["badges"].get(b["key"])
        dn["box"].className = "g-it g-badge still" + ("" if when else " locked")
        dn["emo"].textContent = b["emoji"]
        dn["name"].textContent = b["name"]
        dn["desc"].textContent = b.get("desc") or ""
        dn["when"].hidden = not when
        dn["when"].textContent = "Earned %s" % when if when else ""
        have, at = None, 1
        if not when and b.get("stat"):
            have, at = p["stats"].get(b["stat"]) or 0, b.get("at") or 1
        elif not when and b["key"] in COUNTS:
            k, at = COUNTS[b["key"]]
            have = s.get(k) or 0
        dn["bar"].hidden = dn["prog"].hidden = have is None
        if have is not None:
            dn["fill"].style.width = "%d%%" % min(100, int(round(100.0 * have / max(1, int(at)))))
            dn["prog"].textContent = "%s / %s" % (have, at)
