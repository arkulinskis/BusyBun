from anvil import *

from ._anvil_designer import ShellTemplate
from ... import bun, flows, state


class Shell(ShellTemplate):
    """The hub around Journey, Pantry, Kitchen, Shop and Badges: the player bar, the five tabs (a bottom tab bar on
    phones), the page and the footer. Anvil keeps ONE Shell while the tabs change, so everything here is drawn in
    refresh(page), which router.show() calls after every page change."""

    def __init__(self, **properties):
        super().__init__(**properties)
        bun.listen(self.refresh_net)

    def refresh(self, page):
        for name, el in (("journey", self.tab_journey), ("pantry", self.tab_pantry), ("kitchen", self.tab_kitchen),
                         ("shop", self.tab_shop), ("badges", self.tab_badges)):
            el.classes["on"] = name == page
            state.set_attr(el, "aria-current", "page" if name == page else None)
        self.refresh_top()

    def refresh_top(self):
        st = bun.st
        if not st["loaded"]:
            return
        p, s, me = st["progress"], st["status"], st["me"] or {}
        self.who_name.text = me.get("name") or "Bun"
        self.who_email.text = me.get("email") or ""
        self.who_email.visible = not st["guest"]
        self.guest_note.visible = st["guest"]
        self.coins.text = str(p.get("coins", 0))
        self.stars.text = str(s.get("stars", 0))
        self.stars_max.text = "/%s" % s.get("stars_max", 0)
        self.chops.text = str(s.get("chopsticks", 0))
        self.chops_max.text = "/%s" % s.get("chopsticks_max", 0)
        self.daily_btn.classes["glow"] = bool(st["daily_ready"])
        self.daily_dot.visible = bool(st["daily_ready"])
        self.kitchen_dot.visible = bun.can_cook_any()
        bun.put_portrait(self.dom_nodes["av"], 52, p.get("hat"))
        self.refresh_net()

    def refresh_net(self):
        """📴 Offline (playing from this device) / ☁️ Syncing / nothing when everything is on the server."""
        pill = self.dom_nodes["net_pill"]
        if not bun.online():
            text, tip = "📴 Offline", "Playing from this device. Your progress syncs when you're back online."
        elif bun.st["syncing"] or bun.pending():
            text, tip = "☁️ Syncing", "Adding the play saved on this device to your account."
        else:
            text, tip = "", ""
        pill.textContent = text
        pill.title = tip
        pill.hidden = not text

    def settings_click(self, event):
        flows.settings()

    def daily_click(self, event):
        flows.daily()

    def save_click(self, event):
        flows.sign_in("signup")

    def howto_click(self, event):
        flows.how_to()
