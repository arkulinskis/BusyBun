from anvil import *
import anvil.js
from anvil.js import window

from ._anvil_designer import JourneyTemplate
from ... import bun, flows


class Journey(JourneyTemplate):
    """#journey: a "continue" card, the overall progress, a picker with every world, then one world's road of levels.
    The road is laid out by bb-stage.js (BB.layoutRoad: nodes on a curvy SVG path), redone when the width changes."""

    def __init__(self, args=(), **properties):
        super().__init__(**properties)
        self._shown = False
        self._on_resize = anvil.js.report_exceptions(self._resize)
        self._ok = bun.ensure()
        bun.music("menu")
        if self._ok:
            self.draw()

    def draw(self):
        st, s, dn = bun.st, bun.st["status"], self.dom_nodes
        ws = bun.worlds()
        nxt = bun.next_level()
        nxt_world = bun.world_of_level(nxt)
        keys = [t["key"] for t in ws]
        if st["world"] not in keys:
            st["world"] = nxt_world or (keys[-1] if keys else None)
        dn["lead"].textContent = "%d worlds to free from the pests. Clear every level in a world to open the next one." % len(ws)
        self.guestbar.visible = st["guest"]
        f = bun.find_level(nxt) if nxt else None
        self.continue_card.visible = bool(f)
        self.all_free.visible = not f and bool(s["cleared"]) and len(s["cleared"]) == len(ws)
        if f:
            t, l = f
            dn["next_where"].textContent = "Next up · " + bun.level_label(t, l)
            dn["next_name"].textContent = l["name"]
            dn["next_world"].textContent = t["emoji"] + " " + t["name"]
            self.next_pv.show(st["progress"].get("hat"), 68)
        clears, total = s.get("clears") or 0, s.get("levels_max") or 0
        pct = int(round(100.0 * clears / max(1, total)))
        dn["prog_levels"].textContent = "🗺️ %d / %d levels" % (clears, total)
        dn["prog_fill"].style.width = "%d%%" % pct
        dn["prog_bar"].setAttribute("aria-valuenow", str(pct))
        dn["prog_worlds"].textContent = "🏮 %d / %d worlds free" % (len(s["cleared"]), len(ws))
        self.worlds_panel.items = [{"t": t, "i": i, "host": self, "next_world": nxt_world} for i, t in enumerate(ws)]
        self._draw_world(ws, nxt)

    def _draw_world(self, ws, nxt):
        st, s, dn = bun.st, bun.st["status"], self.dom_nodes
        ti = next((i for i, t in enumerate(ws) if t["key"] == st["world"]), 0)
        t = ws[ti] if ws else None
        dn["terr"].hidden = dn["wnav"].hidden = t is None
        if t is None:
            return
        self._ti = ti
        self.prev_button.enabled = ti > 0
        self.next_button.enabled = ti < len(ws) - 1
        dn["wnav_label"].textContent = "World %d of %d" % (ti + 1, len(ws))
        cleared = t["key"] in s["cleared"]
        locked = not any(bun.is_unlocked(l["key"]) for l in t["levels"])
        stars = sum(bun.stars_of(l["key"]) for l in t["levels"])
        dn["terr"].className = "g-terr th-%s%s" % (t["theme"], " locked" if locked else "")
        dn["terr_wm"].textContent = dn["terr_em"].textContent = t["emoji"]
        dn["terr_name"].textContent = t["name"]
        dn["terr_blurb"].textContent = t.get("blurb") or ""
        if cleared:
            dn["terr_flag"].className, dn["terr_flag"].textContent = "g-flag free", "🏮 Liberated"
        elif locked:
            dn["terr_flag"].className, dn["terr_flag"].textContent = "g-flag lock", "🔒 Locked"
        else:
            dn["terr_flag"].className = "g-flag pest"
            dn["terr_flag"].textContent = bun.PEST_EMOJI.get(t.get("pest"), "🐀") + " Pests in control"
        dn["terr_stars"].textContent = "⭐ %d/%d" % (stars, len(t["levels"]) * 3)
        self.postcard_button.visible = bool(t.get("postcard"))
        dn["fog"].hidden = not locked
        if locked:
            before = ws[ti - 1]["name"] if ti > 0 else "the world before"
            dn["fog_text"].textContent = "Free %s to travel here" % before
        self.nodes_panel.items = [{"t": t, "l": l, "i": i, "nxt": nxt, "host": self} for i, l in enumerate(t["levels"])]
        if self._shown:
            self._layout()

    def _layout(self):
        window.BB.layoutRoad(self.dom_nodes["road"])

    def _resize(self, event):
        self._layout()

    @handle("", "show")
    def form_show(self, **event_args):
        self._shown = True
        window.addEventListener("resize", self._on_resize)
        if not self._ok:
            return
        self._layout()
        key = bun.st["focus"]
        bun.st["focus"] = None
        if key:  # back from a level: show the road around it
            node = self.dom_nodes["road"].querySelector('.g-node[data-level="%s"]' % window.CSS.escape(key)) \
                or self.dom_nodes["road"].querySelector(".g-node.next")
            if node:
                window.setTimeout(lambda: node.scrollIntoView({"block": "center", "behavior": "smooth"}), 120)
        opened = bun.st.get("open")
        bun.st["open"] = None
        if opened:  # "Next level" on the results card: its intro card opens on the map
            flows.level_intro(opened)

    @handle("", "hide")
    def form_hide(self, **event_args):
        self._shown = False
        window.removeEventListener("resize", self._on_resize)

    # ---- called by the items
    def pick_world(self, key):
        bun.st["world"] = key
        self.draw()
        self._layout()
        self.dom_nodes["wnav"].scrollIntoView({"block": "start", "behavior": "smooth"})

    def open_level(self, key, locked=False):
        if locked:
            bun.toast("🔒 Finish the level before this one first.")
            return
        flows.level_intro(key)

    @handle("prev_button", "click")
    def prev_button_click(self, **event_args):
        ws = bun.worlds()
        if self._ti > 0:
            self.pick_world(ws[self._ti - 1]["key"])

    @handle("next_button", "click")
    def next_button_click(self, **event_args):
        ws = bun.worlds()
        if self._ti < len(ws) - 1:
            self.pick_world(ws[self._ti + 1]["key"])

    @handle("continue_button", "click")
    def continue_button_click(self, **event_args):
        nxt = bun.next_level()
        if nxt:
            flows.level_intro(nxt)

    @handle("postcard_button", "click")
    def postcard_button_click(self, **event_args):
        flows.postcard(bun.st["world"])

    @handle("save_button", "click")
    def save_button_click(self, **event_args):
        flows.sign_in("signup")
