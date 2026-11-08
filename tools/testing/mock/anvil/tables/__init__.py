import itertools
_ids = itertools.count(1)
# The schema comes from anvil.yaml's db_schema (the live database's tables), minus Anvil's built-in users columns.
import pathlib as _pl
import yaml as _yaml
_DB = _yaml.safe_load((_pl.Path(__file__).resolve().parents[5] / "anvil.yaml").read_text(encoding="utf-8"))["db_schema"]
_BUILTIN = {"email", "enabled", "signed_up", "last_login", "password_hash", "confirmed_email", "n_password_failures",
            "remembered_logins", "email_confirmation_key"}
_TABLES = {name: [(c["name"], c["type"]) + ((c["target"],) if c.get("target") else ())
                  for c in t["columns"] if not (name == "users" and c["name"] in _BUILTIN)]
           for name, t in _DB.items()}
_USERS_BUILTIN = "email enabled signed_up last_login password_hash confirmed_email n_password_failures"
SCHEMA = {name: " ".join(c[0] for c in cols) for name, cols in _TABLES.items()}
SCHEMA["users"] = _USERS_BUILTIN + " " + SCHEMA.get("users", "")
TYPES = {name: {c[0]: c[1] for c in cols} for name, cols in _TABLES.items()}


class Row:
    def __init__(self, table, kw):
        self._t = table; self._id = '[%d,%d]' % (len(table.name), next(_ids)); self._d = {c: None for c in table.cols}
        self.update(**kw)
    def __getitem__(self, k):
        if k not in self._t.cols: raise KeyError('No column %r in %s' % (k, self._t.name))
        return self._d[k]
    def __setitem__(self, k, v): self.update(**{k: v})
    def update(self, **kw):
        import datetime as _dt, json as _json
        for k, v in kw.items():
            if k not in self._t.cols: raise KeyError('No column %r in %s' % (k, self._t.name))
            typ = TYPES.get(self._t.name, {}).get(k)
            # Strictness: values must match the column type, like Anvil's data tables.
            if v is not None and typ == 'date' and (not isinstance(v, _dt.date) or isinstance(v, _dt.datetime)):
                raise TypeError('%s.%s needs a date, got %r' % (self._t.name, k, v))
            if v is not None and typ == 'datetime' and not isinstance(v, _dt.datetime):
                raise TypeError('%s.%s needs a datetime, got %r' % (self._t.name, k, v))
            if v is not None and typ == 'number' and (isinstance(v, bool) or not isinstance(v, (int, float))):
                raise TypeError('%s.%s needs a number, got %r' % (self._t.name, k, v))
            if v is not None and typ == 'string' and not isinstance(v, str):
                raise TypeError('%s.%s needs a string, got %r' % (self._t.name, k, v))
            if v is not None and typ == 'bool' and not isinstance(v, bool):
                raise TypeError('%s.%s needs a bool, got %r' % (self._t.name, k, v))
            if v is not None and typ == 'link_single' and not isinstance(v, Row):
                raise TypeError('%s.%s needs a row, got %r' % (self._t.name, k, v))
            if v is not None and typ == 'simpleObject':
                v = _json.loads(_json.dumps(v))  # must be JSON-able; stored as a copy like Anvil does
            self._d[k] = v
    def get_id(self): return self._id
    def delete(self): self._t.rows.remove(self)
    def __eq__(self, o): return self is o
    def __ne__(self, o): return self is not o
    def __hash__(self): return id(self)


class order_by:
    def __init__(self, col, ascending=True): self.col, self.asc = col, ascending


class Table:
    def __init__(self, name): self.name = name; self.cols = SCHEMA[name].split(); self.rows = []
    def add_row(self, **kw): r = Row(self, kw); self.rows.append(r); return r
    def search(self, *orders, **kw):
        for k in kw:
            if k not in self.cols: raise KeyError('No column %r in %s' % (k, self.name))
        out = [r for r in self.rows if all(r[k] == v for k, v in kw.items())]
        for o in reversed(orders):
            out.sort(key=lambda r: (r[o.col] is None, r[o.col] if r[o.col] is not None else 0), reverse=not o.asc)
        return out
    def get(self, **kw):
        m = self.search(**kw)
        if len(m) > 1: raise Exception('more than one row')
        return m[0] if m else None
    def get_by_id(self, i): return next((r for r in self.rows if r._id == i), None)


def in_transaction(f): return f
