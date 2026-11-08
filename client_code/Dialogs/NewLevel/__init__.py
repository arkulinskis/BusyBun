from anvil import *

from ._anvil_designer import NewLevelTemplate

SIZES = [("Small · 20×12", "20x12"), ("Medium · 28×16", "28x16"), ("Large · 34×20", "34x20"), ("Huge · 44×28", "44x28")]


class NewLevel(NewLevelTemplate):
    """The level builder's "+ New level": a name, its territory, a size. Closes with {name, territory, w, h} or None.
    territories = [[label, key], ...] from the builder."""

    def __init__(self, territory=None, territories=None, **properties):
        super().__init__(**properties)
        self.territory_box.items = [(str(a), str(b)) for a, b in territories or []]
        if territory:
            self.territory_box.selected_value = territory
        self.size_box.items = SIZES
        self.size_box.selected_value = "28x16"

    @handle("create_button", "click")
    def create_button_click(self, **event_args):
        w, h = (self.size_box.selected_value or "28x16").split("x")
        self.raise_event("x-close-alert", value={"name": ((self.name_box.text or "").strip() or "New level")[:40],
                                                 "territory": self.territory_box.selected_value, "w": int(w), "h": int(h)})

    def close_click(self, event):
        self.raise_event("x-close-alert", value=None)
