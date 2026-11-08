from anvil import *

from ._anvil_designer import PostcardTileTemplate
from ... import flows


class PostcardTile(PostcardTileTemplate):
    """Pantry → one of Grandma's postcards: readable once found, sealed (???) before."""

    def __init__(self, **properties):
        super().__init__(**properties)
        t, dn = self.item["t"], self.dom_nodes
        found = bool(t.get("postcard"))
        dn["box"].className = "g-post" + ("" if found else " sealed")
        dn["box"].disabled = not found
        dn["emo"].textContent = "✉️" if found else "❔"
        dn["txt"].textContent = t["name"] if found else "???"
        dn["box"].setAttribute("aria-label", ("Read the postcard from " + t["name"]) if found else "A postcard not found yet")
        dn["box"].addEventListener("click", self._click)

    def _click(self, event):
        flows.postcard(self.item["t"]["key"])
