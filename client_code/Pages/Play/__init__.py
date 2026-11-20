from anvil import *
from anvil.js import window

from ._anvil_designer import PlayTemplate
from ... import bun, flows, router


class Play(PlayTemplate):
    """#play/<level>: the level running in the canvas engine (Components/Stage). The intro card first; pause, lose and
    results are dialog Forms; a win is scored on the device by the shared rules (bun.act) and synced.
    #play/dish = today's Daily Dish (no unlock needed, the twist's perks and hearts for everyone, never Grandma's help).
    #play/first = the next level to play. Grandma's help (+1 heart, a shield) is offered on the lose card after two
    losses in a row; an assisted win scores normally but stays off the leaderboard."""

    def __init__(self, args=(), **properties):
        super().__init__(**properties)
        self.key = args[0] if args else None
        self.dish: dict = {}
        self.assist = False
        self._f = None
        self._pause_open = False
        self._live = True
        want = bun.st.get("assist_for")
        bun.st["assist_for"] = None
        if not (bun.ensure() and self.key):
            return
        if self.key == "dish":
            self.dish = bun.dish() or {}
            self._f = (self.dish["t"], self.dish["l"]) if self.dish else None
            return
        if self.key == "first":
            self.key = bun.next_level() or (bun.all_levels()[0][1]["key"] if bun.all_levels() else None)
        self._f = bun.find_level(self.key) if self.key else None
        if self._f and not bun.is_unlocked(self.key):
            bun.toast("🔒 Finish the level before this one first.")
            self._f = None
        self.assist = bool(self._f) and want == self.key

    @handle("", "show")
    def form_show(self, **event_args):
        if not self._f:
            window.setTimeout(lambda: router.go("daily" if self.key == "dish" else "journey"), 0)
            return
        t, l = self._f
        bun.music(t.get("theme") or "menu")
        if self.dish:
            tw = self.dish["twist"]
            perks, extra = tw["perks"], ({"hearts": tw["hearts"]} if tw["hearts"] else {})
        else:
            perks, extra = bun.st["status"].get("perks") or [], ({"assist": True} if self.assist else {})
        self.stage.mount(l["data"], t["theme"], perks, bun.st["progress"].get("hat"), self._event, extra)
        from ...Dialogs.Start import Start
        start = Start(key=l["key"], perks=perks if self.dish else None, dish=self.dish or None, assist=self.assist)
        if flows.dialog(start, closable=False) == "go":
            self.stage.start()
        else:
            self.back_to_map()

    def leave(self):
        self._live = False
        self.stage.destroy()

    def back_to_map(self, key=None):
        if self.dish:
            router.go("daily")
            return
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
            self.lose(info=data)

    def pause_menu(self):
        if self._pause_open:
            return
        self._pause_open = True
        self.stage.pause()
        from ...Dialogs.Pause import Pause
        r = flows.dialog(Pause(key=self._f[1]["key"] if self._f else self.key))
        self._pause_open = False
        if r == "restart":
            self._again(self.assist)
        elif r == "quit":
            self.back_to_map()
        else:
            self.stage.resume()

    def _again(self, assist=False):
        """Play this level (or today's dish) again; Grandma's help carries over when asked."""
        if assist and not self.dish:
            bun.st["assist_for"] = self.key
        router.show()

    def lose(self, message=None, info=None):
        from ...Dialogs.Lose import Lose
        offer = False
        if info is not None and not self.dish:
            losses = bun.note_loss(self.key)
            offer = losses >= 2 and bun.assist_on() and not self.assist
        r = flows.dialog(Lose(message=message, info=info, offer_help=offer, dish=bool(self.dish)), closable=False)
        if r == "assist":
            self._again(True)
        elif r == "retry":
            self._again(self.assist)
        else:
            self.back_to_map()

    def win(self, data):
        if self.dish:
            self.win_dish(data)
            return
        prev_rec = dict(bun.level_rec(self.key))
        r = bun.act("finish_level", self.key, data.get("result") or {}, assisted=self.assist)
        if not r or not r.get("ok"):
            self.lose((r or {}).get("error") or "Your result could not be saved.")
            return
        from ...Dialogs.Results import Results
        res = Results(key=self.key, report=r["report"], found=data.get("found"), total=data.get("totalItems"), prev=prev_rec,
                      assisted=self.assist)
        a = flows.dialog(res, closable=False)
        if a == "next" and res.next_key:
            bun.st["open"] = res.next_key
            self.back_to_map(res.next_key)
        elif a == "replay":
            router.show()  # a replay is solo: try it for the leaderboard
        elif a == "auth":
            self.back_to_map()
            flows.sign_in("signup")
        else:
            self.back_to_map()

    def win_dish(self, data):
        result = data.get("result") or {}
        r = bun.act("finish_dish", self.dish["level"], result)
        if not r or not r.get("ok"):
            self.lose((r or {}).get("error") or "Your result could not be saved.")
            return
        from ...Dialogs.DishResults import DishResults
        res = DishResults(dish=self.dish, report=r["report"], result=result, found=data.get("found"),
                          total=data.get("totalItems"))
        a = flows.dialog(res, closable=False)
        if a == "replay":
            router.show()
        elif a == "auth":
            router.go("daily")
            flows.sign_in("signup")
        else:
            router.go("daily")
