from anvil import *

from ._anvil_designer import PauseTemplate
from ... import bun, state


class Pause(PauseTemplate):
    """The pause menu: resume, restart, sound and music switches, feedback, quit. Closes with "restart", "quit" or None."""

    def __init__(self, key=None, **properties):
        super().__init__(**properties)
        t, l = bun.find_level(key)
        self._mood = t.get("theme") or "menu"
        self.dom_nodes["where"].textContent = bun.level_label(t, l) + " · " + l["name"]
        self._labels()

    def _labels(self):
        self.sfx_button.text = "🔊 Sounds on" if bun.sound_on() else "🔇 Sounds off"
        self.music_button.text = "🎵 Music on" if bun.music_on() else "🎵 Music off"

    @handle("", "show")
    def form_show(self, **event_args):
        state.focus(self.resume_button)

    @handle("resume_button", "click")
    def resume_button_click(self, **event_args):
        self.raise_event("x-close-alert", value=None)

    @handle("restart_button", "click")
    def restart_button_click(self, **event_args):
        self.raise_event("x-close-alert", value="restart")

    @handle("quit_button", "click")
    def quit_button_click(self, **event_args):
        self.raise_event("x-close-alert", value="quit")

    @handle("sfx_button", "click")
    def sfx_button_click(self, **event_args):
        bun.set_sound(not bun.sound_on())
        self._labels()

    @handle("music_button", "click")
    def music_button_click(self, **event_args):
        bun.set_music(not bun.music_on(), self._mood)
        self._labels()

    @handle("feedback_button", "click")
    def feedback_button_click(self, **event_args):
        bun.feedback()

    def close_click(self, event):
        self.raise_event("x-close-alert", value=None)
