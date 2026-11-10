"""The app starts here (anvil.yaml: startup module). One server call to learn who is signed in (the bouncing-bun
loading spinner shows meanwhile), the Privacy & Terms kit, then the page for the address in the browser bar.

Offline (Anvil's service worker serves the app from the phone's cache), that call fails: the game opens as whoever
played last on this device (bun.cached_me) and plays from the saves on the device until the server is back."""
import anvil.server
from anvil.js import window

from . import bun, legal, router, state

LEGAL_THEME = {"accent": "#b8352a"}  # colours for the Privacy & Terms page (soy-sauce red, --bb-red-2 in app.css)

legal.setup(LEGAL_THEME)
try:
    _who = anvil.server.call("admin_whoami")
except Exception as _e:
    if type(_e).__name__ not in ("AppOfflineError", "TimeoutError"):
        raise
    _who = None
if _who is None:
    bun.set_online(False)
    state.set_me(bun.cached_me())
else:
    state.set_me(_who if _who.get("signed_in") else None)
    if state.me():
        legal.refresh_soon()
router.start()
_html = window.document.documentElement
if _html is not None:
    _html.classList.add("bb-ready")  # ends the launch splash (app.css: app mode)
