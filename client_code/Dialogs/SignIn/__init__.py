import re

from anvil import *

from ._anvil_designer import SignInTemplate
from ... import auth, legal, state

TEXTS = {"login": ("Welcome back!", "Sign in to pick up where you left off.", "Sign in"),
         "signup": ("Create your account", "Save your journey, cook in the cloud, and race on the leaderboards.", "Create account"),
         "reset": ("Reset your password", "We'll email you a reset link.", "Send reset link")}
EMAIL = re.compile(r"^\S+@\S+\.\S+$")


class SignIn(SignInTemplate):
    """Sign in / create an account / reset the password, as a dialog over the game. Sign-up needs the Privacy & Terms
    tick (the legal kit draws it). Closes with {"ok": True, "new": bool} once someone is signed in, else None."""

    def __init__(self, mode="login", **properties):
        super().__init__(**properties)
        self._mode = mode if mode in TEXTS else "login"
        self.dom_nodes["consent"].innerHTML = legal.consent_field()
        state.set_control_attr(self.name_box, "autocomplete", "nickname")
        state.set_control_attr(self.email_box, "autocomplete", "email")
        state.set_control_attr(self.name_box, "maxlength", "24")
        img = state.control(self.google_button).querySelector("img")
        if img:
            img.setAttribute("alt", "")
        self._draw()

    def _draw(self, message=None, is_error=True):
        mode = self._mode
        title, sub, action = TEXTS[mode]
        self.dom_nodes["title"].textContent = title
        self.dom_nodes["sub"].textContent = sub
        self.submit_button.text = action
        self.name_field.visible = mode == "signup"
        self.password_field.visible = mode != "reset"
        self.password_hint.visible = mode == "signup"
        self.consent_box.visible = mode == "signup"
        self.google_part.visible = mode != "reset"
        self.to_signup.visible = mode == "login"
        self.to_login.visible = mode == "signup"
        self.to_back.visible = mode == "reset"
        state.set_control_attr(self.password_box, "autocomplete", "new-password" if mode == "signup" else "current-password")
        self._say(message, is_error)

    def _say(self, message, is_error=True):
        self.message.visible = bool(message)
        self.message.text = message or ""
        self.message.role = "bb-err" if is_error else "bb-ok"
        if message:
            state.live(self.message, is_error)

    def mode_click(self, event):
        self._mode = event.currentTarget.getAttribute("data-mode")
        self._draw()
        self.form_show()

    @handle("name_box", "pressed_enter")
    def name_box_pressed_enter(self, **event_args):
        self.submit_button_click()

    @handle("email_box", "pressed_enter")
    def email_box_pressed_enter(self, **event_args):
        self.submit_button_click()

    @handle("password_box", "pressed_enter")
    def password_box_pressed_enter(self, **event_args):
        self.submit_button_click()

    @handle("submit_button", "click")
    def submit_button_click(self, **event_args):
        mode = self._mode
        name, email, password = (self.name_box.text or "").strip(), (self.email_box.text or "").strip(), self.password_box.text or ""
        problem = None
        if not EMAIL.match(email):
            problem = "Please enter a valid email address."
        elif mode == "signup" and len(password) < 8:
            problem = "Pick a password with at least 8 characters."
        elif mode == "login" and not password:
            problem = "Please enter your password."
        if problem:
            self._say(problem)
            return
        if mode == "signup" and not legal.consent_ok(self.dom_nodes["consent"]):
            return  # the kit shows its own message next to the tick box
        self.submit_button.enabled = False
        try:
            if mode == "login":
                r = auth.sign_in(email, password)
            elif mode == "signup":
                r = auth.sign_up(name, email, password)
            else:
                r = auth.reset(email)
        finally:
            self.submit_button.enabled = True
        if not r["ok"]:
            self._say(r["error"])
        elif mode == "reset" or r.get("confirm"):
            self._mode = "login"
            self._draw(r["message"], False)
        else:
            self.raise_event("x-close-alert", value=r)

    @handle("google_button", "click")
    def google_button_click(self, **event_args):
        if self._mode == "signup" and not legal.consent_ok(self.dom_nodes["consent"]):
            return
        self.google_button.enabled = False
        try:
            r = auth.google((self.name_box.text or "") if self._mode == "signup" else "")
        finally:
            self.google_button.enabled = True
        if not r["ok"]:
            self._say(r["error"])
            return
        self.raise_event("x-close-alert", value=r)

    @handle("", "show")
    def form_show(self, **event_args):
        self.pv.show("none", 84)
        (self.name_box if self._mode == "signup" else self.email_box).focus()

    def close_click(self, event):
        self.raise_event("x-close-alert", value=None)
