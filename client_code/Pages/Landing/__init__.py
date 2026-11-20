from anvil import *

from ._anvil_designer import LandingTemplate
from ... import auth, bun, flows, router, state

YT_VIDEO = bun.YT_VIDEO  # "mFIuuENN_nI": the Busy Bun video on the Addanapp YouTube channel


def _guest_played():
    """Has the guest on this device won a level? (Their save is in the device store; the old localStorage key is
    moved there and deleted on the first load, so read both.)"""
    rec = bun._load("acct:guest") or {}
    prog = rec.get("progress") or bun.get(bun.GUEST_KEY) or {}
    return bool(((prog.get("stats") or {}).get("runs")) or any((v or {}).get("stars", [False])[0]
                                                                for v in (prog.get("levels") or {}).values()))


class Landing(LandingTemplate):
    """The title screen (# and #landing): the bun, Play / Continue as guest / Sign in, the Daily Dish link, then the
    Watch section (the YouTube video, nothing loads before the click) and the footer. A brand-new player's Play goes
    straight into level 1 (its start card shows the controls); the map comes after the first win."""

    def __init__(self, args=(), **properties):
        super().__init__(**properties)
        me = state.me()
        self.play_button.visible = self.signout_button.visible = bool(me)
        self.guest_button.visible = self.auth_button.visible = self.guest_note.visible = not me
        self.guest_button.text = "▶ Continue as guest" if (not me and _guest_played()) else "▶ Play now"
        dish = bun.dish_basics()
        self.dom_nodes["dish_text"].textContent = "Daily Dish #%d · %s %s" % (dish["no"], dish["twist"]["emoji"],
                                                                            dish["twist"]["name"])
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

    def _play(self):
        """Players with no wins yet go straight into the next level (level 1); everyone else to the Journey."""
        if bun.ensure() and not (bun.st["status"] or {}).get("clears") and not (bun.st["progress"]["stats"] or {}).get("runs"):
            first = bun.next_level()
            if first:
                router.go("play", first)
                return
        router.go("journey")

    @handle("play_button", "click")
    def play_button_click(self, **event_args):
        self._play()

    @handle("guest_button", "click")
    def guest_button_click(self, **event_args):
        self._play()

    def dish_click(self, event):
        router.go("daily")

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
