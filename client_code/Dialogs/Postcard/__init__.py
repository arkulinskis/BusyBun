from anvil import *

from ._anvil_designer import PostcardTemplate
from ... import bun


class Postcard(PostcardTemplate):
    """One of Grandma's postcards (found in a territory's level), in handwriting."""

    def __init__(self, tkey=None, **properties):
        super().__init__(**properties)
        t = bun.territory(tkey) or {}
        self.dom_nodes["title"].textContent = "A postcard from " + (t.get("name") or "Grandma")
        self.dom_nodes["stamp"].textContent = t.get("emoji") or "✉️"
        self.dom_nodes["text"].textContent = t.get("postcard") or ""

    def close_click(self, event):
        self.raise_event("x-close-alert", value=None)
