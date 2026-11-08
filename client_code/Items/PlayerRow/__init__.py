from anvil import *

from ._anvil_designer import PlayerRowTemplate
from ... import state


class PlayerRow(PlayerRowTemplate):
    """Admin → Players: one player's progress at a glance and the admin switch."""

    def __init__(self, **properties):
        super().__init__(**properties)
        p, dn = self.item, self.dom_nodes
        dn["name"].textContent = p.get("name") or ""
        dn["email"].textContent = p.get("email") or ""
        for k in ("stars", "cleared", "recipes", "found", "coins"):
            dn[k].textContent = str(p.get(k) or 0)
        dn["last"].textContent = (p.get("last_played") or "")[:10]
        self.admin_box.checked = bool(p.get("is_admin"))
        state.set_control_attr(self.admin_box, "aria-label", "Admin: " + (p.get("email") or ""))

    @handle("admin_box", "change")
    def admin_box_change(self, **event_args):
        self.item["host"].set_admin(self.item["email"], bool(self.admin_box.checked))
