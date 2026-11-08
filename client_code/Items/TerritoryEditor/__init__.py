from anvil import *

from ._anvil_designer import TerritoryEditorTemplate
from ... import state


class TerritoryEditor(TerritoryEditorTemplate):
    """Admin → Territories: one territory's name, emoji, look, pest, blurb, postcard and published switch, with
    move up/down, delete (only when it has no levels) and save."""

    def __init__(self, **properties):
        super().__init__(**properties)
        t, i, n = self.item["t"], self.item["i"], self.item["n"]
        self.emoji_box.text = t.get("emoji") or ""
        self.name_box.text = t.get("name") or ""
        self.theme_box.items = self.item["themes"]
        self.theme_box.selected_value = t.get("theme")
        self.pest_box.items = self.item["pests"]
        self.pest_box.selected_value = t.get("pest")
        self.blurb_box.text = t.get("blurb") or ""
        self.postcard_box.text = t.get("postcard") or ""
        levels = len(t.get("levels") or [])
        self.published_box.checked = bool(t.get("published"))
        self.published_box.text = "Published · %d level%s" % (levels, "" if levels == 1 else "s")
        self.up_button.enabled = i > 0
        self.down_button.enabled = i < n - 1
        self.delete_button.enabled = levels == 0
        if levels:
            self.delete_button.tooltip = "Move or delete its levels first"
        state.set_control_attr(self.up_button, "aria-label", "Move %s up" % t.get("name"))
        state.set_control_attr(self.down_button, "aria-label", "Move %s down" % t.get("name"))
        state.set_control_attr(self.emoji_box, "maxlength", "8")
        state.set_control_attr(self.name_box, "maxlength", "40")
        state.set_control_attr(self.blurb_box, "maxlength", "200")

    def _key(self):
        return self.item["t"]["key"]

    @handle("save_button", "click")
    def save_button_click(self, **event_args):
        self.item["host"].territory_call("save_territory", {
            "key": self._key(), "emoji": self.emoji_box.text or "", "name": self.name_box.text or "",
            "theme": self.theme_box.selected_value, "pest": self.pest_box.selected_value, "blurb": self.blurb_box.text or "",
            "postcard": self.postcard_box.text or "", "published": bool(self.published_box.checked)}, ok_text="💾 Saved")

    @handle("up_button", "click")
    def up_button_click(self, **event_args):
        self.item["host"].territory_call("move_territory", self._key(), -1)

    @handle("down_button", "click")
    def down_button_click(self, **event_args):
        self.item["host"].territory_call("move_territory", self._key(), 1)

    @handle("delete_button", "click")
    def delete_button_click(self, **event_args):
        if confirm("Delete this territory?", buttons=[("Cancel", False), ("Delete", True)], role="app-dialog"):
            self.item["host"].territory_call("delete_territory", self._key())
