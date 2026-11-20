from anvil import *

from ._anvil_designer import LoseTemplate
from ... import bun, state


class Lose(LoseTemplate):
    """Squished (or the result couldn't be saved: message). info = the engine's lose event: what got the bun, a tip
    for it and how far the goals were. offer_help = Grandma's help button (after two losses in a row).
    Closes with "retry", "assist" or "map"."""

    def __init__(self, message=None, info=None, offer_help=False, dish=False, **properties):
        super().__init__(**properties)
        self.help_row.visible = bool(offer_help) and not message
        if dish:
            self.map_button.text = "🍽️ Daily Dish"
        if info and not message:
            who, tip, prog = bun.loss_info(info)
            self.dom_nodes["text"].textContent = who + ". Every bun gets back up!"
            self.dom_nodes["tip"].textContent = "💡 " + tip
            self.dom_nodes["tip"].hidden = False
            self.dom_nodes["prog"].textContent = "So close: " + prog if prog else ""
            self.dom_nodes["prog"].hidden = not prog
        if message:
            self.dom_nodes["title"].textContent = "Hmm…"
            self.dom_nodes["text"].textContent = message
            self.retry_button.text = "↻ Play again"
            self.map_button.text = "Map"
            self.pv_box.visible = False
        else:
            bun.sfx("fail")

    @handle("", "show")
    def form_show(self, **event_args):
        if self.pv_box.visible:
            self.pv.show(bun.st["progress"].get("hat"), 120, {"face": "ouch", "sy": 0.7, "sx": 1.25})
        state.focus(self.retry_button)

    @handle("retry_button", "click")
    def retry_button_click(self, **event_args):
        self.raise_event("x-close-alert", value="retry")

    @handle("help_button", "click")
    def help_button_click(self, **event_args):
        self.raise_event("x-close-alert", value="assist")

    @handle("map_button", "click")
    def map_button_click(self, **event_args):
        self.raise_event("x-close-alert", value="map")
