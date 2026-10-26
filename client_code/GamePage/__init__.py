# GamePage — Custom HTML form: the whole game (title, map, levels, pantry, kitchen, shop, badges).
# HTML + JS: forms/GamePage.html. Everything visual happens in JS; Python signs in and calls the server.
from ._anvil_designer import GamePageTemplate
from anvil import *
import anvil.server
import anvil.users

from .. import bb_ui


class GamePage(GamePageTemplate):
    def __init__(self, **properties):
        super().__init__(**properties)
        self.mounted = False
        self.add_event_handler("show", self._on_show)

    def _on_show(self, **event_args):
        if self.mounted:
            return
        self.mounted = True
        bb_ui.mount(self, "game", {"signed_in": anvil.users.get_user() is not None}, self._on_event)

    def _on_event(self, event, p):
        if event == "call":
            fn = p.get("fn")
            if fn not in bb_ui.GAME_CALLS:
                return {"ok": False, "error": "Unknown action."}
            return bb_ui.call(fn, *(p.get("args") or []))
        if event in ("login", "signup", "reset"):
            return bb_ui.auth(event, p)
        if event == "logout":
            anvil.users.logout()
            return {"ok": True}
        if event == "admin":
            get_open_form().open_admin()
        return None
