import json

from anvil import *
import anvil.server
from anvil.js import window

from ._anvil_designer import LevelBuilderTemplate
from ... import bun

# The server functions the editor may call (each checks the admin flag again on the server).
ADMIN_CALLS = {"admin_state", "save_level", "delete_level", "move_level", "restore_level"}


class LevelBuilder(LevelBuilderTemplate):
    """Mounts the level editor engine and answers its requests: server calls (whitelisted) and the New level dialog."""

    def __init__(self, **properties):
        self._api = None
        self._first = None
        super().__init__(**properties)

    def start(self, data=None):
        """Mount the editor (once). data = an admin_state reply the page already has (saves loading it twice)."""
        if self._api is None:
            self._first = data
            self._api = window.BB.mount("builder", self.dom_nodes["box"], "{}", self._emit)

    def is_dirty(self):
        return bool(self._api and self._api.isDirty())

    def ok_to_leave(self):
        api = self._api
        if api is None or not api.isDirty():
            return True
        return confirm('You have unsaved changes to "%s". Leave without saving?' % api.dirtyName(),
                       buttons=[("Stay", False), ("Leave", True)], role="app-dialog")

    def destroy(self):
        if self._api is not None:
            self._api.destroy()
            self._api = None

    def _emit(self, event, payload_json):
        p = json.loads(payload_json) if payload_json else {}
        if event == "call":
            fn = p.get("fn")
            if fn not in ADMIN_CALLS:
                return json.dumps({"ok": False, "error": "Unknown action."})
            if fn == "admin_state" and self._first:
                first, self._first = self._first, None
                return json.dumps(first)
            return json.dumps(bun.call(fn, *(p.get("args") or [])))
        if event == "newlevel":
            from ...Dialogs.NewLevel import NewLevel
            r = alert(NewLevel(territory=p.get("territory"), territories=p.get("territories")), buttons=[], role="app-dialog")
            return json.dumps(r) if r else None
        return None
