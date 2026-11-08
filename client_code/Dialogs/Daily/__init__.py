from anvil import *
from anvil.js import window

from ._anvil_designer import DailyTemplate
from ... import bun, state
from ...Pages.Shop import badge_toasts


class Daily(DailyTemplate):
    """The daily market box: tap to open (coins + ingredients, a streak), or how long until the next one.
    self.claimed = it was opened now (the page redraws)."""

    def __init__(self, **properties):
        super().__init__(**properties)
        self.claimed = False
        ready = bool(bun.st["daily_ready"])
        self.waiting_part.visible, self.ready_part.visible = not ready, ready
        self.out_part.visible = False
        if not ready:
            mins = int(window.BB.minutesToMidnight())
            self.dom_nodes["wait_text"].textContent = "A fresh market box arrives in %dh %dm." % (mins // 60, mins % 60)
            streak = (bun.st["progress"].get("daily") or {}).get("streak") or 0
            self.dom_nodes["streak_text"].textContent = "Streak: %d day%s 🔥" % (streak, "" if streak == 1 else "s")

    def gift_click(self, event):
        gift = self.dom_nodes["gift"]
        if gift.classList.contains("open"):
            return
        gift.classList.add("open")
        bun.sfx("unlock")
        r = bun.act("claim_daily")
        if not r or not r.get("ok"):
            self.raise_event("x-close-alert", value=None)
            return
        self.claimed = True
        rep = r["report"]
        gift.textContent = "📦"
        bun.sfx("clear")
        self.dom_nodes["coins"].textContent = "+%s 🪙" % rep.get("coins", 0)
        new_items = rep.get("new_items") or []
        self.items_panel.items = [{"e": bun.item(k)["emoji"], "t": "%s ×%s" % (bun.item(k)["name"], n), "new": k in new_items}
                                  for k, n in (rep.get("items") or {}).items()]
        s = rep.get("streak") or 1
        self.dom_nodes["streak_out"].textContent = "🔥 %d-day streak%s" % (
            s, "! Keep it going for bigger boxes." if s > 1 else ". Come back tomorrow for a bonus!")
        badge_toasts(rep)
        self.out_part.visible = True
        state.focus(self.ok_button)

    @handle("ok_button", "click")
    def ok_button_click(self, **event_args):
        self.raise_event("x-close-alert", value=True)

    def close_click(self, event):
        self.raise_event("x-close-alert", value=None)
