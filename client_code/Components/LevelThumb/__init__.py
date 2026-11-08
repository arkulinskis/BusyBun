from anvil import *
from anvil.js import window

from ._anvil_designer import LevelThumbTemplate
from ... import bun


class LevelThumb(LevelThumbTemplate):
    """The level drawn small: tiles in the territory's look, a dot for every start, exit, item, pest and neighbour."""

    def __init__(self, **properties):
        super().__init__(**properties)

    def show(self, data, theme, width):
        box = self.dom_nodes["box"]
        box.innerHTML = ""
        box.appendChild(window.BB.Art.levelThumb(bun.js(data), theme or "kitchen", int(width)))
