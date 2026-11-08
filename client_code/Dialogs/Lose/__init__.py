from anvil import *

from ._anvil_designer import LoseTemplate
from ... import bun, state


class Lose(LoseTemplate):
    """Squished (or the result couldn't be saved: message). Closes with "retry" or "map"."""

    def __init__(self, message=None, **properties):
        super().__init__(**properties)
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

    @handle("map_button", "click")
    def map_button_click(self, **event_args):
        self.raise_event("x-close-alert", value="map")
