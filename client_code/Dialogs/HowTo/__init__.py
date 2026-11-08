from anvil import *

from ._anvil_designer import HowToTemplate


class HowTo(HowToTemplate):
    """How to play: controls, goals, stars, bonuses, stoves."""

    def __init__(self, **properties):
        super().__init__(**properties)

    @handle("ok_button", "click")
    def ok_button_click(self, **event_args):
        self.raise_event("x-close-alert", value=None)

    def close_click(self, event):
        self.raise_event("x-close-alert", value=None)
