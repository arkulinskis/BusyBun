from anvil import *
from anvil.js import window

from ._anvil_designer import TitleBgTemplate


class TitleBg(TitleBgTemplate):
    """Falling ingredients behind the title (canvas). Starts on show, stops on hide (no animation left running)."""

    def __init__(self, **properties):
        self._stop = None
        super().__init__(**properties)

    @handle("", "show")
    def form_show(self, **event_args):
        if self._stop is None:
            self._stop = window.BB.titleBg(self.dom_nodes["cv"])

    @handle("", "hide")
    def form_hide(self, **event_args):
        self.stop()

    def stop(self):
        if self._stop is not None:
            self._stop()
            self._stop = None
