from anvil import *
from anvil.js import window

from ._anvil_designer import PlayTemplate
from ... import bun, flows, router


class Play(PlayTemplate):
    """#play/<level>: the level running in the canvas engine (Components/Stage). The intro card first; pause, lose and
    results are dialog Forms; a win goes to the server (finish_level) which checks it and hands out the rewards."""

    def __init__(self, args=(), **properties):
        super().__init__(**properties)
        self.key = args[0] if args else None
        self._f = None
        self._pause_open = False
        self._live = True
        if bun.ensure() and self.key:
            self._f = bun.find_level(self.key)
        if self._f and not bun.is_unlocked(self.key):
            bun.toast("🔒 Finish the level before this one first.")
            self._f = None

    @handle("", "show")
    def form_show(self, **event_args):
        if not self._f:
            window.setTimeout(lambda: router.go("journey"), 0)
            return
        t, l = self._f
        bun.music(t.get("theme") or "menu")
        self.stage.mount(l["data"], t["theme"], bun.st["status"].get("perks") or [], bun.st["progress"].get("hat"), self._event)
        from ...Dialogs.Start import Start
        if flows.dialog(Start(key=self.key), closable=False) == "go":
            self.stage.start()
        else:
            self.back_to_map()

    def leave(self):
        self._live = False
        self.stage.destroy()

    def back_to_map(self, key=None):
        key = key or self.key
        bun.st["focus"] = key
        bun.st["world"] = bun.world_of_level(key) or bun.st["world"]
        router.go("journey")

    def _event(self, name, data):
        if not self._live:
            return
        if name == "pause":
            self.pause_menu()
        elif name == "win":
            self.win(data)
        elif name == "lose":
            self.lose()

    def pause_menu(self):
        if self._pause_open:
            return
        self._pause_open = True
        self.stage.pause()
        from ...Dialogs.Pause import Pause
        r = flows.dialog(Pause(key=self.key))
        self._pause_open = False
        if r == "restart":
            router.show()
        elif r == "quit":
            self.back_to_map()
        else:
            self.stage.resume()

    def lose(self, message=None):
        from ...Dialogs.Lose import Lose
        if flows.dialog(Lose(message=message), closable=False) == "retry":
            router.show()
        else:
            self.back_to_map()

    def win(self, data):
        prev_rec = dict(bun.level_rec(self.key))
        r = bun.act("finish_level", self.key, data.get("result") or {})
        if not r or not r.get("ok"):
            self.lose((r or {}).get("error") or "Your result could not be saved.")
            return
        from ...Dialogs.Results import Results
        res = Results(key=self.key, report=r["report"], found=data.get("found"), total=data.get("totalItems"), prev=prev_rec)
        a = flows.dialog(res, closable=False)
        if a == "next" and res.next_key:
            bun.st["open"] = res.next_key
            self.back_to_map(res.next_key)
        elif a == "replay":
            router.show()
        elif a == "auth":
            self.back_to_map()
            flows.sign_in("signup")
        else:
            self.back_to_map()
