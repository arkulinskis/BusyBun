"""The app starts here (anvil.yaml: startup module). One server call to learn who is signed in (the bouncing-bun
loading spinner shows meanwhile), the Privacy & Terms kit, then the page for the address in the browser bar."""
import anvil.server
from anvil.js import window

from . import legal, router, state

LEGAL_THEME = {"accent": "#b8352a"}  # colours for the Privacy & Terms page (soy-sauce red, --bb-red-2 in app.css)

legal.setup(LEGAL_THEME)
_who = anvil.server.call("admin_whoami")
state.set_me(_who if _who.get("signed_in") else None)
if state.me():
    legal.refresh_soon()
router.start()
_html = window.document.documentElement
if _html is not None:
    _html.classList.add("bb-ready")  # ends the launch splash (app.css: app mode)
