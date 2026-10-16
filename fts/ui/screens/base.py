"""Base class for full-page screens."""
from __future__ import annotations

from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget

from ..widgets import label, scroll


class Screen(QWidget):
    title = ""
    subtitle = ""
    scrollable = True

    def __init__(self, ctx):
        super().__init__()
        self.ctx = ctx
        self.setObjectName("Page")
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        inner = QWidget()
        inner.setObjectName("Page")
        self.body = QVBoxLayout(inner)
        self.body.setContentsMargins(26, 20, 26, 20)
        self.body.setSpacing(14)
        head = QVBoxLayout()
        head.setSpacing(2)
        self.h1 = label(self.title, "H1")
        head.addWidget(self.h1)
        if self.subtitle:
            head.addWidget(label(self.subtitle, "Muted"))
        self.body.addLayout(head)
        outer.addWidget(scroll(inner) if self.scrollable else inner)

    def row(self) -> QHBoxLayout:
        r = QHBoxLayout()
        r.setSpacing(12)
        self.body.addLayout(r)
        return r

    def on_show(self, **kwargs):
        pass
