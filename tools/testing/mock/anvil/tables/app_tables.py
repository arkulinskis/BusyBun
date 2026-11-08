
from . import Table, SCHEMA
for _n in SCHEMA: globals()[_n] = Table(_n)
