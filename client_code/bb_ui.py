# bb_ui — client Module. Glue between the Python forms and the HTML/JS components in forms/*.html.
import json

import anvil.js
import anvil.server
import anvil.users
from anvil.js import window

from . import legal

# Server functions the game screen may call (the server checks who is signed in).
GAME_CALLS = {
    "get_state", "finish_level", "cook", "buy_hat", "wear_hat", "buy_market", "claim_daily", "set_name",
    "import_guest", "leaderboard", "guest_state", "guest_finish_level", "guest_cook", "guest_buy_hat",
    "guest_wear_hat", "guest_buy_market", "guest_claim_daily", "submit_feedback",
}
ADMIN_CALLS = {
    "admin_whoami", "admin_state", "save_level", "delete_level", "move_level", "save_territory", "move_territory",
    "delete_territory", "restore_level", "restore_defaults", "list_players", "set_admin",
    "list_feedback", "set_feedback_status", "delete_feedback",
}


def mount(form, name, data, on_event=None):
    """Draw component `name` inside `form` and route its events to on_event(event, payload).

    Data goes to JS as a JSON string. Whatever on_event returns goes back as a JSON string too,
    and resolves the Promise the component got from emit(). Returns the component's JS API object.
    """
    selector = '[data-bb-root="%s"]' % name
    node = anvil.js.get_dom_node(form)
    # A form whose HTML is a single element *is* that element, so check the node itself first.
    root = node if node.matches(selector) else node.querySelector(selector)

    def emit(event, payload_json):
        payload = json.loads(payload_json) if payload_json else {}
        if on_event is None:
            return None
        result = on_event(event, payload)
        return None if result is None else json.dumps(result)

    return window.BB.mount(name, root, json.dumps(data), emit)


def call(name, *args):
    """anvil.server.call that turns errors into {"ok": False, "error": ...} for the components."""
    try:
        return anvil.server.call(name, *args)
    except anvil.server.PermissionDenied as e:
        return {"ok": False, "error": str(e) or "You don't have access to that."}
    except anvil.server.SessionExpiredError:
        return {"ok": False, "error": "Your session expired. Reload the page and sign in again."}
    except anvil.server.AppOfflineError:
        return {"ok": False, "error": "You seem to be offline. Check your connection and try again."}
    except Exception as e:
        print("server call %s failed: %r" % (name, e))
        return {"ok": False, "error": "Something went wrong in the kitchen. Please try again."}


def auth(event, p):
    """Sign in / sign up / password reset, for the game and the admin page."""
    try:
        if event == "login":
            anvil.users.login_with_email(p.get("email", "").strip(), p.get("password", ""), remember=True)
            legal.refresh_soon()  # Privacy & Terms reminder if needed
        elif event == "signup":
            anvil.users.signup_with_email(p.get("email", "").strip(), p.get("password", ""), remember=True)
            if anvil.users.get_user() is None:
                return {"ok": True, "mode": "login",
                        "message": "Account created. Check your email for a confirmation link, then sign in."}
            name = (p.get("name") or "").strip()
            if name:
                call("set_name", name)
            legal.refresh_soon()  # records the sign-up tick box
        elif event == "reset":
            try:
                anvil.users.send_password_reset_email(p.get("email", "").strip())
            except anvil.users.AuthenticationFailed:
                pass  # same reply either way, so nobody can probe which emails have accounts
            return {"ok": True, "mode": "login", "message": "If that email has an account, a reset link is on its way."}
    except anvil.users.UserExists:
        return {"ok": False, "error": "An account with that email already exists. Try signing in."}
    except anvil.users.EmailNotConfirmed:
        return {"ok": False, "error": "Please confirm your email first. Check your inbox for the link."}
    except anvil.users.AccountIsNotEnabled:
        return {"ok": False, "error": "This account is disabled."}
    except anvil.users.TooManyPasswordFailures:
        return {"ok": False, "error": "Too many wrong attempts. Wait a while, or reset your password."}
    except anvil.users.PasswordNotAcceptable as e:
        return {"ok": False, "error": str(e) or "Please choose a stronger password."}
    except anvil.users.AuthenticationFailed:
        return {"ok": False, "error": "That email and password don't match."}
    return {"ok": True}
