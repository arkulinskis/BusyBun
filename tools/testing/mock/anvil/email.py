"""anvil.email for the tests: send() appends to OUTBOX."""
OUTBOX = []


def send(**kw):
    for k in ("to", "subject"):
        if not kw.get(k):
            raise ValueError("email needs %s" % k)
    OUTBOX.append(kw)
