"""Just enough of anvil.server for the tests."""
def callable(*a, **k):
    if a and hasattr(a[0], '__call__'): return a[0]
    return lambda f: f


ENDPOINTS = {}
def http_endpoint(path, **k):
    def deco(f):
        ENDPOINTS[path] = f
        return f
    return deco


class HttpResponse(object):
    def __init__(self, status=200, body="", headers=None):
        self.status, self.body, self.headers = status, body, headers or {}


class PermissionDenied(Exception): pass
class HttpError(Exception): pass


def get_app_origin(*a): return "https://planplate-test.anvil.app"


class _Session(object):
    """Like Anvil's anvil.server.session: item access, get() and `in` only (no pop/del/clear)."""
    def __init__(self): self._d = {}
    def __getitem__(self, k): return self._d[k]
    def __setitem__(self, k, v): self._d[k] = v
    def __contains__(self, k): return k in self._d
    def get(self, k, default=None): return self._d.get(k, default)


session = _Session()
