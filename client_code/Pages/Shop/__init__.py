from anvil import *

from ._anvil_designer import ShopTemplate
from ... import bun, router


class Shop(ShopTemplate):
    """#shop: today's market stall (ingredients for coins) and the hat stand (buy, then wear)."""

    def __init__(self, args=(), **properties):
        super().__init__(**properties)
        bun.music("menu")
        if bun.ensure():
            st = bun.st
            p = st["progress"]
            self.dom_nodes["coins"].textContent = str(p["coins"])
            market = p.get("market") or {}
            bought = market.get("bought") or [] if market.get("day") == st["today"] else []
            self.market_panel.items = [{"o": o, "bought": o["id"] in bought, "host": self} for o in st["market"]]
            self.hats_panel.items = [{"h": h, "host": self} for h in st["catalog"]["hats"]]

    def buy(self, offer_id):
        r = bun.act("buy_market", offer_id)
        if r and r.get("ok"):
            bun.sfx("coin")
            it = bun.item(r["report"]["item"])
            bun.toast("%s %s ×%s added to your pantry" % (it["emoji"], it["name"], r["report"]["qty"]))
        router.show()

    def buy_hat(self, key):
        r = bun.act("buy_hat", key)
        if r and r.get("ok"):
            bun.sfx("unlock")
            bun.toast("🎩 New hat: %s!" % bun.hat(key)["name"], "gold")
            badge_toasts(r["report"])
        router.show()

    def wear(self, key):
        bun.act("wear_hat", key)
        router.show()


def badge_toasts(rep):
    for k in (rep or {}).get("new_badges") or []:
        b = bun.badge(k)
        if b:
            bun.toast("%s Badge earned: %s" % (b["emoji"], b["name"]), "gold")
