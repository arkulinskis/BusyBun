from anvil import *

from ._anvil_designer import HatCardTemplate
from ... import bun, state


class HatCard(HatCardTemplate):
    """Shop → one hat on the stand: the bun wearing it; Wear / Wearing / price / recipe reward."""

    def __init__(self, **properties):
        super().__init__(**properties)
        h, dn = self.item["h"], self.dom_nodes
        p = bun.st["progress"]
        own, wearing = h["key"] in p["hats"], p.get("hat") == h["key"]
        dn["box"].className = "g-it g-hat still" + (" wearing" if wearing else "")
        self.pv.show(h["key"], 96)
        dn["name"].textContent = h["name"]
        dn["desc"].textContent = h.get("desc") or ""
        b = self.hat_button
        self._do = None
        if wearing:
            b.text, b.role, b.enabled = "Wearing", ["bb-btn", "small", "cream"], False
        elif own:
            b.text, b.role, self._do = "Wear", ["bb-btn", "small", "green"], "wear"
        elif h.get("price") is None:
            b.text, b.role, b.enabled = "Recipe reward", ["bb-btn", "small", "cream"], False
        else:
            b.text, self._do = "%s 🪙" % h["price"], "buy"
            b.enabled = p["coins"] >= h["price"]
        state.set_control_attr(b, "aria-label", "%s: %s" % (h["name"], b.text.replace("🪙", "coins")))

    @handle("hat_button", "click")
    def hat_button_click(self, **event_args):
        if self._do == "wear":
            self.item["host"].wear(self.item["h"]["key"])
        elif self._do == "buy":
            self.item["host"].buy_hat(self.item["h"]["key"])
