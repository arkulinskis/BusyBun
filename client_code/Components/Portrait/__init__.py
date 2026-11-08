from anvil import *

from ._anvil_designer import PortraitTemplate
from ... import bun


class Portrait(PortraitTemplate):
    """The bun on a canvas (BB.Art.bunPortrait). Set hat/size, or call show(hat, size, opts) for a face ("ouch")."""

    def __init__(self, **properties):
        self._hat, self._size, self._ready = "none", 56, False
        super().__init__(**properties)
        self._ready = True
        self._draw()

    def show(self, hat=None, size=None, opts=None):
        self._hat = hat or "none"
        if size:
            self._size = size
        self._draw(opts)

    def _draw(self, opts=None):
        if self._ready:
            bun.put_portrait(self.dom_nodes["box"], int(self._size or 56), self._hat, opts)

    @property
    def size(self):
        return self._size

    @size.setter
    def size(self, value):
        self._size = value or 56
        self._draw()

    @property
    def hat(self):
        return self._hat

    @hat.setter
    def hat(self, value):
        self._hat = value or "none"
        self._draw()
