from anvil import *

from ._anvil_designer import SettingsTemplate
from ... import bun, state


class Settings(SettingsTemplate):
    """Settings: your bun and name, sound and music, how to play, feedback, Privacy & Terms, the level builder (admins),
    sign out. Closes with "howto", "auth", "admin", "saved", "out" or None."""

    def __init__(self, **properties):
        super().__init__(**properties)
        st = bun.st
        me = st["me"] or {}
        self.dom_nodes["me_name"].textContent = me.get("name") or "Bun"
        self.dom_nodes["me_sub"].textContent = "Guest (this browser only)" if st["guest"] else (me.get("email") or "")
        self.guestbar.visible = st["guest"]
        self.name_row.visible = not st["guest"]
        self.name_box.text = me.get("name") or ""
        state.set_control_attr(self.name_box, "maxlength", "24")
        state.set_control_attr(self.name_box, "autocomplete", "nickname")
        self.admin_button.visible = bool(me.get("is_admin"))
        self.out_button.text = "⏏ Back to title" if st["guest"] else "⏏ Sign out"
        self._labels()

    def _labels(self):
        self.sfx_button.text = "🔊 Sounds on" if bun.sound_on() else "🔇 Sounds off"
        self.music_button.text = "🎵 Music on" if bun.music_on() else "🎵 Music off"

    @handle("", "show")
    def form_show(self, **event_args):
        self.pv.show((bun.st["progress"] or {}).get("hat"), 80)

    def _close(self, value):
        self.raise_event("x-close-alert", value=value)

    @handle("save_button", "click")
    def save_button_click(self, **event_args):
        r = bun.call("set_name", self.name_box.text or "", bun.today())
        if r and r.get("ok"):
            bun.apply(r)
            bun.toast("Name saved!")
            self._close("saved")
        else:
            state.toast((r or {}).get("error") or "Could not save.", "error")

    @handle("name_box", "pressed_enter")
    def name_box_pressed_enter(self, **event_args):
        self.save_button_click()

    @handle("sfx_button", "click")
    def sfx_button_click(self, **event_args):
        bun.set_sound(not bun.sound_on())
        self._labels()

    @handle("music_button", "click")
    def music_button_click(self, **event_args):
        bun.set_music(not bun.music_on())
        self._labels()

    @handle("howto_button", "click")
    def howto_button_click(self, **event_args):
        self._close("howto")

    @handle("feedback_button", "click")
    def feedback_button_click(self, **event_args):
        bun.feedback()

    @handle("admin_button", "click")
    def admin_button_click(self, **event_args):
        self._close("admin")

    @handle("auth_button", "click")
    def auth_button_click(self, **event_args):
        self._close("auth")

    @handle("out_button", "click")
    def out_button_click(self, **event_args):
        self._close("out")

    def close_click(self, event):
        self.raise_event("x-close-alert", value=None)
