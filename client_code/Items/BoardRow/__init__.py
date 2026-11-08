from anvil import *

from ._anvil_designer import BoardRowTemplate
from ... import bun


class BoardRow(BoardRowTemplate):
    """A leaderboard line: rank, name, best time ({"rank", "name", "time", "you"}; rank None = a note line)."""

    def __init__(self, **properties):
        super().__init__(**properties)
        i, dn = self.item, self.dom_nodes
        dn["row"].className = "g-brow" + (" you" if i.get("you") else "") + (" note" if i.get("rank") is None else "")
        dn["rank"].textContent = "" if i.get("rank") is None else str(i["rank"])
        dn["name"].textContent = i.get("name") or ""
        dn["time"].textContent = "" if i.get("rank") is None else bun.fmt_time(i.get("time"))
