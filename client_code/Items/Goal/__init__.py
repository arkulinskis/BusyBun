from anvil import *

from ._anvil_designer import GoalTemplate


class Goal(GoalTemplate):
    """A level goal line: {"e": emoji, "t": text}."""

    def __init__(self, **properties):
        super().__init__(**properties)
        self.dom_nodes["emo"].textContent = self.item["e"]
        self.dom_nodes["txt"].textContent = self.item["t"]
