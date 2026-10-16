"""Glossary, formula reference, common mistakes and interview preparation."""
from __future__ import annotations

import html

from PySide6.QtWidgets import QComboBox, QHBoxLayout, QLineEdit, QTabWidget, QTextBrowser

from ...content import reference as ref
from ..widgets import Card, label
from .base import Screen


class ReferenceScreen(Screen):
    title = "Reference & interview prep"
    subtitle = "Search the glossary and formulas, review common mistakes, and practise interview answers."
    scrollable = False

    def __init__(self, ctx):
        super().__init__(ctx)
        top = QHBoxLayout()
        top.addWidget(label("Search:", wrap=False))
        self.q = QLineEdit()
        self.q.setPlaceholderText("e.g. RevPAR, NPV, variance…")
        self.q.textChanged.connect(self.refresh)
        top.addWidget(self.q, 1)
        self.body.addLayout(top)
        self.tabs = QTabWidget()
        self.views = {}
        for key, name in (("glossary", "Glossary"), ("formulas", "Formulas"), ("mistakes", "Common mistakes"),
                          ("interview", "Interview questions")):
            tb = QTextBrowser()
            tb.setOpenExternalLinks(False)
            self.views[key] = tb
            self.tabs.addTab(tb, name)
        self.role = QComboBox()
        self.role.addItem("All roles")
        self.role.addItems(sorted({r for r, *_ in ref.INTERVIEW_QUESTIONS}))
        self.role.currentIndexChanged.connect(self.refresh)
        rr = Card()
        h = QHBoxLayout()
        h.addWidget(label("Interview role filter:", wrap=False))
        h.addWidget(self.role)
        h.addStretch(1)
        rr.add(h)
        rr.add(label("Model answers are outlines to build your own answer from, not scripts. The interview "
                     "questions are typical of the roles; they are not taken from any specific employer.", "Muted"))
        self.body.addWidget(rr)
        self.body.addWidget(self.tabs, 1)
        self.refresh()

    @staticmethod
    def _hit(q: str, *parts) -> bool:
        return not q or any(q in str(p).lower() for p in parts)

    def refresh(self):
        q = self.q.text().strip().lower()
        e = html.escape
        g = [f"<p><b>{e(t)}</b><br>{e(d)}</p>" for t, d in ref.GLOSSARY if self._hit(q, t, d)]
        self.views["glossary"].setHtml("".join(g) or "<p>No matches.</p>")
        f = [f"<p><b>{e(n)}</b><br><code>{e(fm)}</code><br><i>Example:</i> {e(ex)}</p>"
             for n, fm, ex in ref.FORMULAS if self._hit(q, n, fm, ex)]
        self.views["formulas"].setHtml("".join(f) or "<p>No matches.</p>")
        mk = [f"<p><b>✘ {e(m)}</b><br>✔ {e(fix)}</p>" for m, fix in ref.COMMON_MISTAKES if self._hit(q, m, fix)]
        self.views["mistakes"].setHtml("".join(mk) or "<p>No matches.</p>")
        role = self.role.currentText()
        iq = [f"<p><b>[{e(r)} · {e(kind)}]</b> {e(qq)}<br><i>Model answer outline:</i> {e(a)}</p>"
              for r, kind, qq, a in ref.INTERVIEW_QUESTIONS
              if (role == "All roles" or r == role) and self._hit(q, r, kind, qq, a)]
        self.views["interview"].setHtml("".join(iq) or "<p>No matches.</p>")
        counts = [len(g), len(f), len(mk), len(iq)]
        for i, (name, n) in enumerate(zip(("Glossary", "Formulas", "Common mistakes", "Interview questions"), counts)):
            self.tabs.setTabText(i, f"{name} ({n})")
