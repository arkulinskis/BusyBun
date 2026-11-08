class AuthenticationFailed(Exception): pass
CURRENT = [None]
def get_user(): return CURRENT[0]
