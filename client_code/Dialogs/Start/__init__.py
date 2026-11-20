from anvil import *
from anvil.js import window

from ._anvil_designer import StartTemplate
from ... import bun, state


class Start(StartTemplate):
    """The card before a level starts: goals, the controls for this device, the perks you've learned.
    Daily Dish: the dish number, the twist and the twist's perks instead of yours (perks=, dish=).
    Grandma's help (assist=True): a note that this run has an extra heart and a shield. Closes with "go" or "map"."""

    def __init__(self, key=None, perks=None, dish=None, assist=False, **properties):
        super().__init__(**properties)
        t, l = bun.find_level(key)
        data, dn = l["data"], self.dom_nodes
        info = bun.level_info(data)
        dn["where"].textContent = "%s %s · %s" % (t["emoji"], t["name"], bun.level_label(t, l))
        self.note_box.visible = bool(dish) or bool(assist)
        if dish:
            tw = dish["twist"]
            dn["where"].textContent = "🍽️ Daily Dish #%d · %s" % (dish["no"], dish["tier"])
            dn["note_em"].textContent = tw["emoji"]
            dn["note_text"].textContent = "%s: %s" % (tw["name"], tw["desc"])
            self.map_button.text = "Back to the dish"
        elif assist:
            dn["note_em"].textContent = "🧓"
            dn["note_text"].textContent = "Grandma's help: +1 ❤️ and a steam shield. Winning with help won't go on the leaderboard."
        dn["name"].textContent = l["name"]
        dn["intro"].textContent = data.get("intro") or ""
        dn["intro"].hidden = not data.get("intro")
        self.goals_panel.items = [{"e": e, "t": txt} for e, txt in bun.goals(data, info)]
        touch = bool(window.BB.isTouch())
        self.keys_help.visible, self.touch_help.visible = not touch, touch
        chips = []
        for p in (perks if perks is not None else (bun.st["status"].get("perks") or [])):
            r = next((x for x in bun.st["catalog"]["recipes"] if x.get("perk") == p), None)
            if r:
                chips.append({"e": r["emoji"], "t": r["perk_name"]})
        if perks is not None and not chips:
            chips.append({"e": "🥟", "t": "No perks today"})
        self.perks_panel.items = chips

    @handle("", "show")
    def form_show(self, **event_args):
        state.focus(self.go_button)

    @handle("go_button", "click")
    def go_button_click(self, **event_args):
        self.raise_event("x-close-alert", value="go")

    @handle("map_button", "click")
    def map_button_click(self, **event_args):
        self.raise_event("x-close-alert", value="map")
