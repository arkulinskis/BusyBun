from anvil import *

from ._anvil_designer import AdminTemplate
from ... import auth, bun, flows, router, state


class Admin(AdminTemplate):
    """#admin: the level builder. Admins get four tabs: Levels (the canvas editor engine, Components/LevelBuilder),
    Territories, Players and Feedback (Forms). Everyone else gets a sign-in card. The server checks the admin flag
    on every call."""

    def __init__(self, args=(), **properties):
        super().__init__(**properties)
        self._tab = "levels"
        self._fb_filter = "new"
        self.data = None
        me = state.me()
        admin = bool(me and me.get("is_admin"))
        self.login_box.visible, self.app_box.visible = not admin, admin
        if not admin:
            signed = bool(me)
            if signed:
                self.dom_nodes["login_text"].textContent = (
                    "You're signed in as %s, which isn't an admin account." % me.get("email"))
            self.signin_button.visible = self.first_note.visible = not signed
            self.other_button.visible = signed
            return
        bun.stop_music()
        self.data = bun.call("admin_state")
        self._stats()
        self._show_tab("levels")

    @handle("", "show")
    def form_show(self, **event_args):
        if self.app_box.visible and self._tab == "levels":
            self.builder.start(self.data)

    def leave(self):
        self.builder.destroy()

    def _stats(self):
        d = self.data or {}
        s = d.get("stats") or {}
        me = state.me() or {}
        self.who.text = "%s · %s players · %s clears" % (me.get("email") or "", s.get("players", 0), s.get("clears", 0))
        self._fb_badge(s.get("feedback_new") or 0)

    def _fb_badge(self, n):
        self.dom_nodes["fb_count"].textContent = str(n)
        self.dom_nodes["fb_count"].hidden = not n

    # ---- sign in card
    @handle("signin_button", "click")
    def signin_button_click(self, **event_args):
        flows.sign_in("login")

    @handle("other_button", "click")
    def other_button_click(self, **event_args):
        auth.sign_out()
        flows.sign_in("login")

    # ---- tabs
    def tab_click(self, event):
        tab = event.currentTarget.getAttribute("data-tab")
        if tab == self._tab:
            return
        if self._tab == "levels" and not self.builder.ok_to_leave():
            return
        self._show_tab(tab)

    def _show_tab(self, tab):
        self._tab = tab
        for name, el in (("levels", self.tab_levels), ("territories", self.tab_territories), ("players", self.tab_players),
                         ("feedback", self.tab_feedback)):
            el.classes["on"] = name == tab
            state.set_attr(el, "aria-pressed", "true" if name == tab else "false")
        self.levels_box.visible = tab == "levels"
        self.terr_box.visible = tab == "territories"
        self.players_box.visible = tab == "players"
        self.fb_box.visible = tab == "feedback"
        if tab == "levels":
            self.builder.start(self.data)
        elif tab == "territories":
            self.data = bun.call("admin_state")
            self._stats()
            self._draw_territories()
        elif tab == "players":
            self._players(bun.call("list_players"))
        else:
            self._feedback(bun.call("list_feedback", self._fb_filter or None))

    # ---- territories
    def _draw_territories(self):
        d = self.data or {}
        ts = d.get("territories") or []
        cat = d.get("catalog") or {}
        themes = [(x["name"], x["key"]) for x in cat.get("themes") or []]
        pests = [(x["name"], x["key"]) for x in cat.get("pests") or []]
        self.terr_panel.items = [{"t": t, "i": i, "n": len(ts), "themes": themes, "pests": pests, "host": self}
                                 for i, t in enumerate(ts)]

    def territory_call(self, fn, *args, ok_text=None):
        d = bun.call(fn, *args)
        if d and d.get("ok") is False and d.get("error"):
            state.toast(d["error"], "error")
        if d and d.get("territories"):
            self.data = d
            self._stats()
            self._draw_territories()
            if ok_text or d.get("note"):
                bun.toast(ok_text or d["note"], "gold")

    @handle("add_terr_button", "click")
    def add_terr_button_click(self, **event_args):
        self.territory_call("save_territory", {"name": "New territory", "emoji": "🍜", "theme": "market", "pest": "rat",
                                               "blurb": "A brand new place to explore.", "published": False},
                            ok_text="Added at the end, hidden until you publish it.")

    @handle("restore_button", "click")
    def restore_button_click(self, **event_args):
        self.territory_call("restore_defaults")

    # ---- players
    def _players(self, r):
        rows = (r or {}).get("players") or []
        self.players_panel.items = [dict(p, host=self) for p in rows]
        self.no_players.visible = not rows

    def set_admin(self, email, flag):
        r = bun.call("set_admin", email, flag)
        if r and r.get("ok"):
            bun.toast("Updated.")
        else:
            state.toast((r or {}).get("error") or "Could not update", "error")
        self._players(r if r and r.get("ok") else bun.call("list_players"))

    # ---- feedback
    def _feedback(self, r):
        if not r or not r.get("ok"):
            return
        c = r["counts"]
        self._fb_badge(c.get("new") or 0)
        f = self._fb_filter
        for key, btn, label in (("new", self.f_new, "New"), ("read", self.f_read, "Read"), ("done", self.f_done, "Done"),
                                ("", self.f_all, "All")):
            n = c.get(key, 0) if key else c.get("new", 0) + c.get("read", 0) + c.get("done", 0)
            btn.text = "%s (%d)" % (label, n)
            btn.role = ["bb-btn", "small"] if f == key else ["bb-btn", "small", "cream"]
            state.set_control_attr(btn, "aria-pressed", "true" if f == key else "false")
        self.fb_panel.items = [dict(it, host=self) for it in r["items"]]
        self.dom_nodes["fb_empty"].textContent = "" if r["items"] else ("No new messages. 🎉" if f == "new" else "Nothing here.")

    def feedback_call(self, fn, *args):
        self._feedback(bun.call(fn, *(list(args) + [self._fb_filter or None])))

    def _filter(self, f):
        self._fb_filter = f
        self._feedback(bun.call("list_feedback", f or None))

    @handle("f_new", "click")
    def f_new_click(self, **event_args):
        self._filter("new")

    @handle("f_read", "click")
    def f_read_click(self, **event_args):
        self._filter("read")

    @handle("f_done", "click")
    def f_done_click(self, **event_args):
        self._filter("done")

    @handle("f_all", "click")
    def f_all_click(self, **event_args):
        self._filter("")

    # ---- header buttons
    @handle("game_button", "click")
    def game_button_click(self, **event_args):
        if self._tab != "levels" or self.builder.ok_to_leave():
            router.go("journey")

    @handle("out_button", "click")
    def out_button_click(self, **event_args):
        if self._tab != "levels" or self.builder.ok_to_leave():
            auth.sign_out()
            router.show()
