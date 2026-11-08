import json

from anvil import *
import anvil.js
from anvil.js import window

from ._anvil_designer import StageTemplate
from ... import bun


class Stage(StageTemplate):
    """Wraps BB.mountStage (theme/assets/bb-stage.js): one level running in the canvas engine."""

    def __init__(self, **properties):
        self._api = None
        self._on_event = None
        super().__init__(**properties)

    def mount(self, level_data, theme, perks, hat, on_event):
        self.destroy()
        self._on_event = on_event
        opts = {"level": level_data, "theme": theme, "items": bun.st["catalog"] and {i["key"]: i for i in bun.st["catalog"]["items"]},
                "perks": perks or [], "hat": hat or "none"}
        self._api = window.BB.mountStage(self.dom_nodes["box"], bun.js(opts), self._event)

    def _event(self, name, data_json):
        if self._on_event is not None:
            self._on_event(str(name), json.loads(data_json or "{}"))

    def start(self):
        if self._api:
            self._api.start()

    def pause(self):
        if self._api:
            self._api.pause()

    def resume(self):
        if self._api:
            self._api.resume()

    def destroy(self):
        if self._api:
            self._api.destroy()
            self._api = None

    @handle("", "hide")
    def form_hide(self, **event_args):
        self.destroy()
