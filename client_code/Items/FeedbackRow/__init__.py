from anvil import *

from ._anvil_designer import FeedbackRowTemplate
from ... import state


class FeedbackRow(FeedbackRowTemplate):
    """Admin → Feedback: one older message (new feedback goes to Prepsto): mark read / done / reopen, delete."""

    def __init__(self, **properties):
        super().__init__(**properties)
        it, dn = self.item, self.dom_nodes
        dn["box"].className = "a-fb " + (it.get("status") or "new")
        dn["kind"].className = "kind " + (it.get("kind") or "other")
        dn["kind"].textContent = it.get("kind_name") or "Other"
        dn["who"].textContent = it.get("name") or "Guest"
        self.email_link.visible = bool(it.get("email"))
        self.email_link.text = it.get("email") or ""
        self.email_link.url = "mailto:" + (it.get("email") or "")
        dn["when"].textContent = "%s UTC · %s" % ((it.get("created") or "").replace("T", " ")[:16], it.get("status"))
        dn["msg"].textContent = it.get("message") or ""
        ctx = it.get("context") or {}
        dn["details"].hidden = not ctx
        dn["ctx"].textContent = "\n".join("%s: %s" % (k, ctx[k]) for k in ctx)
        st = it.get("status")
        self.read_button.visible = st != "read"
        self.done_button.visible = st != "done"
        self.reopen_button.visible = st == "done"
        state.set_control_attr(self.delete_button, "aria-label", "Delete this message")

    def _set(self, status):
        self.item["host"].feedback_call("set_feedback_status", self.item["id"], status)

    @handle("read_button", "click")
    def read_button_click(self, **event_args):
        self._set("read")

    @handle("done_button", "click")
    def done_button_click(self, **event_args):
        self._set("done")

    @handle("reopen_button", "click")
    def reopen_button_click(self, **event_args):
        self._set("new")

    @handle("delete_button", "click")
    def delete_button_click(self, **event_args):
        if confirm("Delete this message?", buttons=[("Cancel", False), ("Delete", True)], role="app-dialog"):
            self.item["host"].feedback_call("delete_feedback", self.item["id"])
