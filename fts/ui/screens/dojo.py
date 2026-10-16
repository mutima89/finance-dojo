"""Daily Dojo: three real-life quests a day, quick-fire practice, belt path and streak."""
from __future__ import annotations

import datetime as dt

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QGridLayout, QHBoxLayout, QLineEdit, QProgressBar, QVBoxLayout

from ...content import curriculum, life
from ...core import achievements, gamify
from ...core.checker import check_numeric, format_value
from ..widgets import Card, Chart, button, label
from .base import Screen


def quests_left(db, day: dt.date) -> int:
    """Today's quests not yet solved or revealed."""
    left = 0
    for ch in life.daily_quests(day):
        ref = f"{day.isoformat()}:{ch.id}"
        if not (db.has_xp("quest", ref) or db.logged("quest_revealed", f"quest:{ref}")):
            left += 1
    return left


class QuestCard(QFrame):
    """One real-life challenge: story, question, answer box, hint, answer."""
    solved = Signal()

    def __init__(self, ctx, ch: life.Challenge, ref: str, xp: int, source: str = "quest"):
        super().__init__()
        self.setObjectName("Quest")
        self.ctx, self.ch, self.ref, self.xp, self.source = ctx, ch, ref, xp, source
        self.tries = 0
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 12, 16, 12)
        lay.setSpacing(6)
        head = QHBoxLayout()
        head.addWidget(label(ch.emoji, "Emoji", wrap=False))
        title = QVBoxLayout()
        title.setSpacing(0)
        title.addWidget(label(ch.title, "H3"))
        chips = QHBoxLayout()
        chips.setSpacing(6)
        chips.addWidget(label(ch.skill, "Chip", wrap=False))
        self.xp_chip = label(f"+{xp} XP" if xp else "practice", "Chip", wrap=False)
        chips.addWidget(self.xp_chip)
        chips.addStretch(1)
        title.addLayout(chips)
        head.addLayout(title, 1)
        lay.addLayout(head)
        lay.addWidget(label(ch.story))
        lay.addWidget(label(f"<b>{ch.question}</b>", rich=True))
        row = QHBoxLayout()
        self.input = QLineEdit()
        self.input.setPlaceholderText({"percent": "e.g. 12.5%", "currency": "e.g. 86.67",
                                       "years": "e.g. 3.3"}.get(ch.unit, "e.g. 59"))
        self.input.setMaximumWidth(170)
        self.input.returnPressed.connect(self.check)
        row.addWidget(self.input)
        self.btn_check = button("Check", self.check, primary=True)
        self.btn_hint = button("💡 Hint", self.hint)
        self.btn_show = button("Show answer", self.reveal)
        for b in (self.btn_check, self.btn_hint, self.btn_show):
            row.addWidget(b)
        row.addStretch(1)
        lay.addLayout(row)
        self.feedback = label("", rich=True)
        lay.addWidget(self.feedback)
        db = ctx.db
        if db.has_xp(source, ref):
            self._finish(True, "Already solved today. ")
        elif db.logged("quest_revealed", f"{source}:{ref}"):
            self._finish(False, "")

    def _finish(self, ok: bool, lead: str):
        p = self.ctx.pal
        tone = p.good if ok else p.warn
        self.feedback.setText(f"<span style='color:{tone}'>{lead}</span><b>Working:</b> {self.ch.solution}"
                              f"<br><span style='color:{p.muted}'>💼 At work: {self.ch.work_link}</span>")
        for w in (self.btn_check, self.btn_hint, self.btn_show):
            w.setEnabled(False)
        self.input.setReadOnly(True)
        self.setProperty("done", ok)
        self.style().unpolish(self)
        self.style().polish(self)

    def check(self):
        if not self.btn_check.isEnabled():
            return
        text = self.input.text()
        if not text.strip():
            self.feedback.setText("Type your answer first.")
            return
        r = check_numeric(text, float(self.ch.expected), self.ch.unit, self.ch.abs_tol)
        p = self.ctx.pal
        if r.status == "invalid":
            self.feedback.setText(f"<span style='color:{p.warn}'>{r.message}</span>")
            return
        self.tries += 1
        if r.correct:
            cheer = gamify.pick(gamify.CHEER_RIGHT, self.tries + len(self.ch.id))
            if self.xp:
                self.ctx.award(self.source, self.ref, self.xp, f"{self.ch.emoji} {self.ch.title} {cheer}")
            else:
                self.ctx.celebrate(f"✔ {cheer}", "Practice XP is capped for today, but the skill still counts.")
            self._finish(True, f"✔ {cheer} ")
            self.solved.emit()
            return
        msg = gamify.pick(gamify.ENCOURAGE_WRONG, self.tries)
        diag = r.diagnosis or ""
        if diag.startswith("Your answer is too "):          # the generic message talks about periods; keep it simple
            diag = f"Your answer is too {'high' if r.parsed > self.ch.expected else 'low'}. Try the hint."
        self.feedback.setText(f"<span style='color:{p.bad}'>Not quite.</span> {diag}<br><i>{msg}</i>")

    def hint(self):
        self.feedback.setText(f"💡 {self.ch.hint}")

    def reveal(self):
        self.ctx.db.log("quest_revealed", f"{self.source}:{self.ref}")
        shown = format_value(self.ch.expected, self.ch.unit, 2)
        self._finish(False, f"Answer: {shown}. No XP this time, and that's fine: now you know the move. ")
        self.ctx.window.refresh_xp()


class DojoScreen(Screen):
    title = "Daily Dojo"
    subtitle = ("Three one-minute quests from everyday life, with the same maths you'll use at work. "
                "New ones every day.")

    def __init__(self, ctx):
        super().__init__(ctx)
        r = self.row()
        belt = Card("Your belt")
        self.belt_lbl = label("", "H2")
        self.belt_bar = QProgressBar()
        self.belt_bar.setRange(0, 1000)
        self.belt_bar.setTextVisible(False)
        self.belt_sub = label("", "Muted")
        for w in (self.belt_lbl, self.belt_bar, self.belt_sub):
            belt.add(w)
        r.addWidget(belt, 1)
        st = Card("Streak")
        self.streak_lbl = label("", "H2")
        self.streak_sub = label("", "Muted")
        st.add(self.streak_lbl)
        st.add(self.streak_sub)
        r.addWidget(st, 1)
        goal = Card("Today's goal")
        self.goal_lbl = label("", "H2")
        self.goal_bar = QProgressBar()
        self.goal_bar.setRange(0, 1000)
        self.goal_bar.setTextVisible(False)
        self.goal_sub = label("Change the goal in Settings. Small and steady beats big and rare.", "Muted")
        for w in (self.goal_lbl, self.goal_bar, self.goal_sub):
            goal.add(w)
        r.addWidget(goal, 1)

        self.quests_card = Card("Today's quests")
        self.quests_box = QVBoxLayout()
        self.quests_box.setSpacing(10)
        self.quests_card.add(self.quests_box)
        self.body.addWidget(self.quests_card)

        quick = Card("Quick-fire practice 🎲")
        quick.add(label(f"Want more? Roll a new everyday challenge. The first {gamify.PRACTICE_DAILY_CAP} "
                        f"you solve each day earn +{gamify.PRACTICE_XP} XP.", "Muted"))
        self.quick_box = QVBoxLayout()
        quick.add(self.quick_box)
        qr = QHBoxLayout()
        qr.addWidget(button("🎲 New challenge", self.roll, primary=True))
        qr.addStretch(1)
        quick.add(qr)
        self.body.addWidget(quick)

        r2 = self.row()
        path = Card("Belt path")
        self.path_grid = QGridLayout()
        self.path_grid.setSpacing(6)
        path.add(self.path_grid)
        path.add(label(gamify.BELT_NOTE + " Your skill levels on the Progress screen are what measure "
                       "job-readiness.", "Muted"))
        r2.addWidget(path, 1)
        hist = Card("XP in the last 14 days")
        self.chart = Chart(ctx, 2.4)
        hist.add(self.chart)
        r2.addWidget(hist, 1)
        badges = Card("Badges")
        self.badge_next = label("", "Muted", rich=True)
        badges.add(self.badge_next)
        self.badge_grid = QGridLayout()
        self.badge_grid.setSpacing(8)
        badges.add(self.badge_grid)
        badges.add(label(achievements.BADGE_NOTE, "Muted"))
        self.body.addWidget(badges)
        self.badge_frames = {}
        for i, b in enumerate(achievements.BADGES):
            f = QFrame()
            f.setObjectName("Badge")
            fl = QHBoxLayout(f)
            fl.setContentsMargins(10, 8, 10, 8)
            fl.addWidget(label(b.emoji, "Emoji", wrap=False))
            tv = QVBoxLayout()
            tv.setSpacing(0)
            tv.addWidget(label(b.name, "H3", wrap=False))
            prog = label(b.desc, "Muted")
            tv.addWidget(prog)
            fl.addLayout(tv, 1)
            self.badge_frames[b.id] = (f, prog)
            self.badge_grid.addWidget(f, i // 4, i % 4)

        how = Card("How to earn XP")
        how.add(label("• Exercise solved: 20 on the first try (15 with hints), 12 on the second, 8 later\n"
                      f"• Quiz: {gamify.QUIZ_XP_PER_CORRECT} per correct answer when you beat your best\n"
                      f"• Practical task saved: {gamify.TASK_XP}  •  Lesson finished: {gamify.LESSON_XP}\n"
                      f"• Daily quest: {gamify.QUEST_XP}  •  Quick-fire: {gamify.PRACTICE_XP}  •  "
                      f"Focus session: {gamify.FOCUS_XP}\n"
                      f"• Hitting your daily goal: +{gamify.DAILY_GOAL_BONUS} bonus\n"
                      "Revealed solutions earn no XP, just like in your skill scores. Your streak survives "
                      "one rest day in a row, and XP never goes down.", "Muted"))
        self.body.addWidget(how)
        self.day = None
        self.practice_n = 0
        self.quick_card = None

    def on_show(self, **kw):
        today = dt.date.today()
        if self.day != today:
            self.day = today
            self._build_quests()
            self.practice_n = int(self.ctx.db.meta(f"practice:{today.isoformat()}") or 0)
            self._show_practice()
        self.on_xp()

    def _clear(self, box):
        while box.count():
            w = box.takeAt(0).widget()
            if w:
                w.setParent(None)
                w.deleteLater()

    def _build_quests(self):
        self._clear(self.quests_box)
        for ch in life.daily_quests(self.day):
            card = QuestCard(self.ctx, ch, f"{self.day.isoformat()}:{ch.id}", gamify.QUEST_XP)
            self.quests_box.addWidget(card)

    def _show_practice(self):
        self._clear(self.quick_box)
        ch = life.practice_challenge(self.day, self.practice_n)
        ref = f"{self.day.isoformat()}:{self.practice_n}"
        xp = gamify.PRACTICE_XP if self.practice_n < gamify.PRACTICE_DAILY_CAP else 0
        self.quick_card = QuestCard(self.ctx, ch, ref, xp, source="practice")
        self.quick_box.addWidget(self.quick_card)

    def roll(self):
        self.practice_n += 1
        self.ctx.db.set_meta(f"practice:{self.day.isoformat()}", str(self.practice_n))
        self._show_practice()

    def on_xp(self):
        db = self.ctx.db
        r = gamify.rank(db.xp_total())
        self.belt_lbl.setText(f"🥋 {r.belt.name}")
        self.belt_bar.setValue(round(r.fraction * 1000))
        self.belt_sub.setText(f"{r.xp:,} XP · {r.to_next:,} XP to {r.next_belt.name}" if r.next_belt
                              else f"{r.xp:,} XP · you reached the top belt")
        today = dt.date.today()
        s = gamify.streak(db.active_days(), today)
        self.streak_lbl.setText(f"🔥 {s.days} day{'s' if s.days != 1 else ''}")
        if s.active_today:
            self.streak_sub.setText("Done for today. Your streak is safe.")
        elif s.at_risk:
            self.streak_sub.setText("You rested yesterday. One small win today keeps the streak going.")
        elif s.days:
            self.streak_sub.setText("One small win today adds a day.")
        else:
            self.streak_sub.setText("Solve one quest to start a streak. One rest day in a row is allowed.")
        goal = db.int_setting("daily_goal", gamify.DAILY_GOAL_CHOICES, gamify.DEFAULT_DAILY_GOAL)
        xp_today = db.xp_on(today)
        self.goal_lbl.setText(f"🎯 {xp_today} / {goal} XP" + ("  ✔" if xp_today >= goal else ""))
        self.goal_bar.setValue(round(gamify.goal_fraction(xp_today, goal) * 1000))
        left = quests_left(db, today)
        self.quests_card.lay.itemAt(0).widget().setText(
            "Today's quests" + (f" · {left} to go" if left else " · all done! 🎉"))
        self._fill_path(r)
        self._fill_badges()
        by_day = db.xp_by_day(14)
        days = [today - dt.timedelta(days=i) for i in range(13, -1, -1)]

        def paint(fig, p):
            ax = fig.add_subplot(111)
            vals = [by_day.get(d, 0) for d in days]
            ax.bar(range(14), vals, color=[p.series[0] if d != today else p.good for d in days], width=0.7)
            ax.axhline(goal, color=p.muted, linestyle="--", linewidth=0.8)
            ax.set_xticks(range(14), [d.strftime("%a")[0] for d in days], fontsize=8)
            ax.set_facecolor(p.surface)
            for side in ("top", "right"):
                ax.spines[side].set_visible(False)
            for side in ("left", "bottom"):
                ax.spines[side].set_color(p.border)
            ax.tick_params(colors=p.text2, labelsize=8)
            ax.set_ylim(0, max([goal * 1.2] + vals) * 1.05)
        self.chart.plot(paint)

    def _fill_path(self, r):
        self._clear(self.path_grid)
        for i, b in enumerate(gamify.BELTS):
            lb = label(f"{'✔ ' if i < r.index else '▶ ' if i == r.index else ''}{b.name} · {b.min_xp:,}",
                       "BeltChip", wrap=False)
            dark_text = b.name.split()[0] in ("White", "Yellow", "Orange")
            on = i <= r.index
            lb.setStyleSheet(f"background:{b.color if on else 'transparent'}; color:"
                             f"{('#111' if dark_text else '#fff') if on else self.ctx.pal.muted};"
                             f"border:1px solid {b.color};")
            self.path_grid.addWidget(lb, i // 4, i % 4)

    def _fill_badges(self):
        db = self.ctx.db
        stats = achievements.collect_stats(db, [l for m in curriculum.modules() for l in m.lessons])
        got = {b.id for b in achievements.unlocked(stats)}
        for b in achievements.BADGES:
            f, prog = self.badge_frames[b.id]
            on = b.id in got
            f.setProperty("locked", "false" if on else "true")
            f.style().unpolish(f)
            f.style().polish(f)
            have = min(stats.get(b.stat, 0), b.need)
            counter = b.need > 1 and b.stat != "belt"
            prog.setText(b.desc + ("  ✔" if on else f"  ({have}/{b.need})" if counter else ""))
        nxt = achievements.next_badges(stats, 1)
        head = f"<b>{len(got)} of {len(achievements.BADGES)}</b> unlocked"
        if nxt:
            b = nxt[0][0]
            head += f" · closest next: {b.emoji} <b>{b.name}</b> ({b.desc[0].lower() + b.desc[1:-1]})"
        else:
            head += " · you collected them all! 🎉"
        self.badge_next.setText(head)

    def on_theme(self):
        if self.day:
            self.on_xp()
