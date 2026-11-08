from anvil import *

from ._anvil_designer import BannerTemplate


class Banner(BannerTemplate):
    """A results/cooking banner: {"e": emoji, "t": text, "kind": "free" / "badge" / "gold"}."""

    def __init__(self, **properties):
        super().__init__(**properties)
        i, dn = self.item, self.dom_nodes
        dn["box"].className = "g-banner " + (i.get("kind") or "")
        dn["emo"].textContent = i.get("e") or ""
        dn["txt"].textContent = i.get("t") or ""
