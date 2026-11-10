"""Render the installed-app icons from the game's own bun drawing (theme/assets/bb-art.js) with headless Chrome.

    python -I tools/app_icons.py

Writes into theme/assets:
  icon-192.png, icon-512.png   full-square icons on the dough background (the web manifest, Android, desktop)
  icon-maskable-512.png        the bun inside the centre safe zone, so round/squircle launcher masks never cut it
  apple-touch-icon.png         180 px, no transparency (iPhones fill transparent icons with black)
The manifest (server_code/app_mode.py) and head_html's app-mode block point at these. Run python tools/assets.py after.
"""
import pathlib
import subprocess
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
ASSETS = ROOT / "theme" / "assets"
CHROME = pathlib.Path("C:/Program Files/Google/Chrome/Application/chrome.exe")

# name, size, bun radius as a share of the size, bun centre height as a share of the size
ICONS = [("icon-192.png", 192, 0.30, 0.56), ("icon-512.png", 512, 0.30, 0.56),
         ("icon-maskable-512.png", 512, 0.22, 0.55), ("apple-touch-icon.png", 180, 0.30, 0.56)]

PAGE = """<!doctype html><meta charset="utf-8">
<style>html,body{margin:0;overflow:hidden;background:#f7e6c8}canvas{display:block}</style>
<canvas id="c" width="%(s)d" height="%(s)d"></canvas>
<script src="%(art)s"></script>
<script>
var s = %(s)d, c = document.getElementById('c'), x = c.getContext('2d');
var g = x.createRadialGradient(s / 2, s * .38, 0, s / 2, s * .38, s * .75);
g.addColorStop(0, '#fff7ea'); g.addColorStop(.5, '#f7e6c8'); g.addColorStop(1, '#efcf98');
x.fillStyle = g; x.fillRect(0, 0, s, s);
BB.Art.drawBun(x, s / 2, s * %(y)f, s * %(r)f, { face: 'happy', hat: 'none', t: 0 });
</script>"""


def main():
    art = (ASSETS / "bb-art.js").resolve().as_uri()
    with tempfile.TemporaryDirectory() as tmp:
        for name, size, r, y in ICONS:
            page = pathlib.Path(tmp) / (name + ".html")
            page.write_text(PAGE % {"s": size, "r": r, "y": y, "art": art}, encoding="utf-8")
            out = ASSETS / name
            subprocess.run([str(CHROME), "--headless=new", "--disable-gpu", "--hide-scrollbars", "--force-device-scale-factor=1",
                            "--allow-file-access-from-files", "--user-data-dir=" + str(pathlib.Path(tmp) / "profile"),
                            "--window-size=%d,%d" % (size, size), "--virtual-time-budget=2000",
                            "--screenshot=" + str(out), page.as_uri()], check=True, capture_output=True)
            print("wrote", out.relative_to(ROOT))


if __name__ == "__main__":
    main()
