from anvil import *

from ._anvil_designer import RecipeCardTemplate
from ... import bun


class RecipeCard(RecipeCardTemplate):
    """Kitchen → one recipe: its perk, each ingredient have/need (green when enough), Cook."""

    def __init__(self, **properties):
        super().__init__(**properties)
        r, dn = self.item["r"], self.dom_nodes
        p = bun.st["progress"]
        cooked = p["cooked"].get(r["key"]) or 0
        dn["box"].className = "g-rec" + (" cooked" if cooked else "")
        dn["emo"].textContent = r["emoji"]
        dn["name"].textContent = r["name"]
        dn["perk"].textContent = ("✓ " if cooked else "🔒 ") + r["perk_name"] + ": " + r["perk_desc"]
        needs = []
        for k, n in r["needs"].items():
            it, have, known = bun.item(k), p["pantry"].get(k) or 0, p["seen"].get(k)
            needs.append({"e": it["emoji"] if known else "❔", "t": "%d/%d" % (have, n), "kind": "g-need" + (" ok" if have >= n else ""),
                          "title": it["name"] if known else "???"})
        self.needs_panel.items = needs
        dn["cooked"].textContent = ("Cooked ×%d" % cooked) if cooked else "Not cooked yet"
        sell = bun.st["catalog"].get("recipe_sell")
        self.cook_button.text = ("Cook again +%s🪙" % sell) if cooked else "Cook! 🔥"
        self.cook_button.role = ["bb-btn", "small"] if cooked else ["bb-btn", "small", "red"]
        self.cook_button.enabled = bun.can_cook(r)

    @handle("cook_button", "click")
    def cook_button_click(self, **event_args):
        self.item["host"].cook(self.item["r"]["key"])
