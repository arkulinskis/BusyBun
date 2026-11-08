from anvil import *

from ._anvil_designer import OfferCardTemplate
from ... import bun, state


class OfferCard(OfferCardTemplate):
    """Shop → one market-stall offer: an ingredient, how many, the price (sold out once bought today)."""

    def __init__(self, **properties):
        super().__init__(**properties)
        o, dn = self.item["o"], self.dom_nodes
        i = bun.item(o["item"])
        rar = bun.rarity(i["rarity"])
        dn["box"].className = "g-it still r-" + i["rarity"]
        dn["cnt"].textContent = "×%s" % o["qty"]
        dn["emo"].textContent = i["emoji"]
        dn["name"].textContent = i["name"]
        dn["rar"].textContent = rar["name"]
        dn["rar"].className = "g-rar rar-" + i["rarity"]
        done = self.item["bought"]
        self.buy_button.text = "Sold out" if done else "%s 🪙" % o["price"]
        self.buy_button.role = ["bb-btn", "small", "cream"] if done else ["bb-btn", "small"]
        self.buy_button.enabled = not done and bun.st["progress"]["coins"] >= o["price"]
        state.set_control_attr(self.buy_button, "aria-label", "Sold out" if done else "Buy %s %s for %s coins" % (o["qty"], i["name"], o["price"]))

    @handle("buy_button", "click")
    def buy_button_click(self, **event_args):
        self.item["host"].buy(self.item["o"]["id"])
