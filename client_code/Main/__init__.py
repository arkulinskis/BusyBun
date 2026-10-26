# Main — Custom HTML form, the Startup Form. HTML: forms/Main.html
#   #admin          the level builder (AdminPage)
#   anything else   the game (GamePage)
import anvil
from ._anvil_designer import MainTemplate
from anvil import *

from ..GamePage import GamePage
from ..AdminPage import AdminPage


class Main(MainTemplate):
    def __init__(self, **properties):
        super().__init__(**properties)
        self.started = False
        self.add_event_handler("show", self._on_show)

    def _on_show(self, **event_args):
        if self.started:
            return
        self.started = True
        h = anvil.get_url_hash()
        if isinstance(h, str) and h.strip("/").lower().startswith("admin"):
            self.open_admin()
        else:
            self.open_game()

    def open_game(self):
        anvil.set_url_hash("")
        self.clear()
        self.add_component(GamePage())

    def open_admin(self):
        anvil.set_url_hash("admin")
        self.clear()
        self.add_component(AdminPage())
