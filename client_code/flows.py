"""Screens several pages open: How to play, sign in, settings, the daily box, a level's intro card.
Each is a dialog Form (client_code/Dialogs); this module opens it and does what the answer asks for."""
from anvil import alert

from . import auth, bun, router, state


def dialog(form, closable=True, large=False):
    """alert() with our look (role app-dialog); closable=False = no backdrop/Esc close (the old 'noClose' cards)."""
    return alert(form, buttons=[], dismissible=closable, large=large, role="app-dialog")


def how_to():
    from .Dialogs.HowTo import HowTo
    dialog(HowTo())


def sign_in(mode="login"):
    """The sign-in dialog; on success the guest's progress moves to the account and the journey opens."""
    from .Dialogs.SignIn import SignIn
    if not bun.online():
        state.toast("Signing in needs the internet. Keep playing: your game is saved on this device.", "error")
        return False
    r = dialog(SignIn(mode=mode))
    if not r or not r.get("ok"):
        return False
    bun.after_sign_in(bool(r.get("new")))
    if router.current() in ("landing", "journey", "pantry", "kitchen", "shop", "badges", "play"):
        router.go("journey")
    else:
        router.show()
    return True


def settings():
    from .Dialogs.Settings import Settings
    r = dialog(Settings())
    if r == "howto":
        how_to()
    elif r == "auth":
        sign_in("signup")
    elif r == "admin":
        router.go("admin")
    elif r == "saved":
        router.show()
    elif r == "out":
        if bun.st["guest"]:
            router.go("landing")
        elif not bun.online():
            state.toast("You're offline. Sign out when you're back online; your game is saved on this device.", "error")
        else:
            auth.sign_out()
            state.toast("Signed out. See you soon!")
            router.go("landing")


def daily():
    from .Dialogs.Daily import Daily
    d = Daily()
    dialog(d)
    if d.claimed:
        router.show()


def level_intro(key):
    from .Dialogs.LevelIntro import LevelIntro
    if dialog(LevelIntro(key=key)) == "play":
        router.go("play", key)


def postcard(tkey):
    from .Dialogs.Postcard import Postcard
    t = bun.territory(tkey)
    if t and t.get("postcard"):
        bun.sfx("unlock")
        dialog(Postcard(tkey=tkey))


def item_info(key):
    from .Dialogs.ItemInfo import ItemInfo
    dialog(ItemInfo(key=key))
