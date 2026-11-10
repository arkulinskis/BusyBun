"""Page addresses: #name/arg1/arg2 -> a page Form (open_form).

    ""  / #landing   the title screen (Pages/Landing): play as a guest, sign in, the video
    #journey #pantry #kitchen #shop #badges   the hub tabs (Layouts/Shell); signed out = playing as a guest
    #play/<level>    a level (Pages/Play: the canvas engine)
    #admin           the level builder (Pages/Admin: shows its own sign-in card to non-admins, like the old #admin)

Links in templates are plain <a href="#journey">; code calls router.go("play", key).
PAGES[name] = browser-tab title. New page: add it to PAGES and _form().
"""
import anvil
import anvil.js
from anvil.js import window

PAGES = {
    "landing": "A cute bao bun adventure",
    "journey": "The Journey",
    "pantry": "The Pantry",
    "kitchen": "Grandma's Kitchen",
    "shop": "The Shop",
    "badges": "Badges",
    "play": "Playing",
    "admin": "Level Builder",
}
TABS = [("journey", "🗺️", "Journey"), ("pantry", "🧺", "Pantry"), ("kitchen", "🍳", "Kitchen"), ("shop", "🎩", "Shop"),
        ("badges", "🏅", "Badges")]
APP_NAME = "Busy Bun"
HUB = [tab[0] for tab in TABS]
# Phone status-bar colour per screen (app mode): the hub's cream top bar, the dough title, the black play screen.
BAR = {"landing": "#f7e6c8", "play": "#000000", "admin": "#efe3cf"}
HUB_BAR = "#fff7ea"
_r: dict = {"listening": False, "page": None, "name": ""}


def _form(name):
    """The page's Form class (imported when first needed, so start-up stays quick)."""
    if name == "journey":
        from .Pages.Journey import Journey
        return Journey
    if name == "pantry":
        from .Pages.Pantry import Pantry
        return Pantry
    if name == "kitchen":
        from .Pages.Kitchen import Kitchen
        return Kitchen
    if name == "shop":
        from .Pages.Shop import Shop
        return Shop
    if name == "badges":
        from .Pages.Badges import Badges
        return Badges
    if name == "play":
        from .Pages.Play import Play
        return Play
    if name == "admin":
        from .Pages.Admin import Admin
        return Admin
    from .Pages.Landing import Landing
    return Landing


def parse(hash_text):
    h = (hash_text or "").lstrip("#").lstrip("!").lstrip("/").split("?")[0]
    parts = [window.decodeURIComponent(p) for p in h.split("/") if p]
    return (parts[0].lower() if parts else ""), parts[1:]


def href(name, *args):
    """'#name/arg1/arg2' with every part URL-encoded; the title screen is plain '#'."""
    if name in ("", "landing") and not args:
        return "#"
    return "#" + "/".join([name] + [window.encodeURIComponent(str(a)) for a in args if a not in (None, "")])


def current():
    return _r["name"]


def show():
    """Open the page for the current address."""
    name, args = parse(window.location.hash)
    if name not in PAGES:
        name, args = "landing", []
    old = _r["page"]
    if old is not None and hasattr(old, "leave"):
        old.leave()  # stop the game loop, the title animation, the builder
    window.document.title = PAGES[name] + " · " + APP_NAME
    _chrome(_r["name"], name)
    window.UI_READY = False
    page = _form(name)(args=args)
    _r["page"], _r["name"] = page, name
    anvil.open_form(page)
    shell = getattr(page, "layout", None)
    if shell is not None and hasattr(shell, "refresh"):
        shell.refresh(name)  # Anvil reuses the layout between pages: tell it which page is open
    window.scrollTo(0, 0)
    window.UI_READY = True  # tests and screenshots wait for this


def _chrome(old, name):
    """App feel: which way the hub page slides in (app.css reads html[data-nav]) and the status-bar colour."""
    nav = ""
    if old in HUB and name in HUB and old != name:
        nav = "fwd" if HUB.index(name) > HUB.index(old) else "back"
    html = window.document.documentElement
    if html is not None:
        html.setAttribute("data-nav", nav)
    try:
        window.bbThemeColor(BAR.get(name, HUB_BAR))  # defined in head_html's app-mode block
    except Exception:
        pass


def go(name, *args):
    """Go to a page. Same address again = reload the page."""
    target = href(name, *args)
    here = window.location.hash or "#"
    if here == target:
        show()
    else:
        window.location.hash = target


def _on_hash(event):
    show()


def start():
    if not _r["listening"]:
        window.addEventListener("hashchange", anvil.js.report_exceptions(_on_hash))
        _r["listening"] = True
    show()
