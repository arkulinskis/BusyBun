from anvil import *
from anvil.js import window

from ._anvil_designer import StartTemplate
from ... import bun, state


class Start(StartTemplate):
    """The card before a level starts: goals, the controls for this device, the perks you've learned.
    Closes with "go" or "map"."""

    def __init__(self, key=None, **properties):
        super().__init__(**properties)
        t, l = bun.find_level(key)
        data, dn = l["data"], self.dom_nodes
        info = bun.level_info(data)
        dn["where"].textContent = "%s %s · %s" % (t["emoji"], t["name"], bun.level_label(t, l))
        dn["name"].textContent = l["name"]
        dn["intro"].textContent = data.get("intro") or ""
        dn["intro"].hidden = not data.get("intro")
        self.goals_panel.items = [{"e": e, "t": txt} for e, txt in bun.goals(data, info)]
        touch = bool(window.BB.isTouch())
        self.keys_help.visible, self.touch_help.visible = not touch, touch
        perks = []
        for p in bun.st["status"].get("perks") or []:
            r = next((x for x in bun.st["catalog"]["recipes"] if x.get("perk") == p), None)
            if r:
                perks.append({"e": r["emoji"], "t": r["perk_name"]})
        self.perks_panel.items = perks

    @handle("", "show")
    def form_show(self, **event_args):
        state.focus(self.go_button)

    @handle("go_button", "click")
    def go_button_click(self, **event_args):
        self.raise_event("x-close-alert", value="go")

    @handle("map_button", "click")
    def map_button_click(self, **event_args):
        self.raise_event("x-close-alert", value="map")
