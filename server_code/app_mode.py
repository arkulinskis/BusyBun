"""App mode: the installed app's web manifest, served at /_/api/manifest.json.

Anvil serves its own /_/manifest.json with Anvil's colours (a blue status bar, a white launch screen), the name
"BusyBun" and a 190 px icon labelled 512. head_html's app-mode block points the page's <link rel="manifest"> here.
"id" stays "/" (the same identity as Anvil's start_url), so phones that already installed the game keep it.
Paths are root-relative so the manifest works on busybun.com and on the anvil.app address alike.
"""
import json

import anvil.server

COLOR = "#f7e6c8"  # --bb-dough in app.css: the launch screen and the status bar


def _icon(name, size, purpose="any"):
    return {"src": "/_/theme/" + name, "sizes": "%dx%d" % (size, size), "type": "image/png", "purpose": purpose}


def manifest_data():
    icon = _icon("icon-192.png", 192)
    return {
        "id": "/", "start_url": "/", "scope": "/",
        "name": "Busy Bun", "short_name": "Busy Bun",
        "description": "A little bao bun on a big culinary journey: errands, pests, recipes and 16 worlds.",
        "lang": "en", "dir": "ltr", "categories": ["games", "entertainment"],
        "display": "standalone", "orientation": "any",
        "background_color": COLOR, "theme_color": COLOR,
        "icons": [icon, _icon("icon-512.png", 512), _icon("icon-maskable-512.png", 512, "maskable")],
        # Long-press the home-screen icon (Android, desktop Chrome/Edge) to jump straight in.
        "shortcuts": [
            {"name": "Continue the journey", "short_name": "Journey", "url": "/#journey", "icons": [icon]},
            {"name": "Grandma's kitchen", "short_name": "Kitchen", "url": "/#kitchen", "icons": [icon]},
            {"name": "The shop", "short_name": "Shop", "url": "/#shop", "icons": [icon]},
        ],
    }


@anvil.server.http_endpoint("/manifest.json")
def manifest(**kw):
    return anvil.server.HttpResponse(200, json.dumps(manifest_data()),
                                     headers={"Content-Type": "application/manifest+json",
                                              "Cache-Control": "public, max-age=3600"})
