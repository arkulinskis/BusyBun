from anvil import *

from ._anvil_designer import KitchenTemplate
from ... import bun, flows, router


class Kitchen(KitchenTemplate):
    """#kitchen: every recipe with what it needs from the pantry. The first cook teaches its perk for good; cooking
    it again sells the bao for coins."""

    def __init__(self, args=(), **properties):
        super().__init__(**properties)
        bun.music("menu")
        if bun.ensure():
            sell = bun.st["catalog"].get("recipe_sell")
            self.dom_nodes["lead"].textContent = (
                "Cook recipes from your pantry. The first time you cook one, you learn its perk forever. "
                "Cooking it again sells the bao for %s 🪙." % sell)
            self.recipes_panel.items = [{"r": r, "host": self} for r in bun.st["catalog"]["recipes"]]

    def cook(self, key):
        from ...Dialogs.Cook import Cook
        bun.sfx("cook")
        d = Cook(key=key)
        flows.dialog(d, closable=False)
        if d.done:
            router.show()
