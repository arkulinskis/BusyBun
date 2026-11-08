from anvil import *

from ._anvil_designer import LandingTemplate
from ... import auth, bun, flows, router, state

YT_VIDEO = bun.YT_VIDEO  # "mFIuuENN_nI": the Busy Bun video on the Addanapp YouTube channel


class Landing(LandingTemplate):
    """The title screen (# and #landing): the bun, Play / Continue as guest / Sign in, then the Watch section (the
    YouTube video, nothing loads before the click) and the footer."""

    def __init__(self, args=(), **properties):
        super().__init__(**properties)
        me = state.me()
        guest = bun.get(bun.GUEST_KEY) or {}
        self.play_button.visible = self.signout_button.visible = bool(me)
        self.guest_button.visible = self.auth_button.visible = self.guest_note.visible = not me
        self.guest_button.text = "▶ Continue as guest" if (guest.get("levels") or {}) else "▶ Play now"
        hat = (bun.st["progress"] or {}).get("hat") if bun.st["loaded"] else None
        self.hero.show(hat or bun.get("bb.lastHat", "none"), 190)
        self.dom_nodes["yt_cover"].addEventListener("click", self._play_video)
        bun.music("menu")

    def _play_video(self, event):
        """Swap the cover for YouTube's player (privacy-enhanced); the menu music stops while it plays."""
        bun.stop_music()
        self.dom_nodes["yt_frame"].innerHTML = (
            '<iframe src="https://www.youtube-nocookie.com/embed/' + YT_VIDEO + '?autoplay=1&rel=0&playsinline=1" '
            'title="Busy Bun video" allow="autoplay; encrypted-media; picture-in-picture; fullscreen" allowfullscreen '
            'referrerpolicy="strict-origin-when-cross-origin"></iframe>')

    @handle("play_button", "click")
    def play_button_click(self, **event_args):
        router.go("journey")

    @handle("guest_button", "click")
    def guest_button_click(self, **event_args):
        router.go("journey")

    @handle("auth_button", "click")
    def auth_button_click(self, **event_args):
        flows.sign_in("login")

    @handle("signout_button", "click")
    def signout_button_click(self, **event_args):
        auth.sign_out()
        state.toast("Signed out. See you soon!")
        router.show()

    def watch_click(self, event):
        self.dom_nodes["watch"].scrollIntoView({"behavior": "smooth", "block": "start"})

    def howto_click(self, event):
        flows.how_to()

    def leave(self):
        self.bg.stop()
