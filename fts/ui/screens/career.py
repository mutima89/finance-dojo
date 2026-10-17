"""Career Mode: a chapter map, manager briefings and boss battles with lives and stars."""
from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QGridLayout, QHBoxLayout, QLineEdit, QVBoxLayout, QWidget

from ...content import career, curriculum, story
from ...core import gamify, mastery
from ...core.checker import check_numeric, format_value
from ..widgets import Card, button, label
from .base import Screen


@dataclass
class ChapterState:
    chapter: career.Chapter
    lessons: list            # [(lesson, done)]
    stars: int               # best stars (capstone: 3 when passed)
    beaten: bool
    unlocked: bool

    @property
    def boss_ready(self) -> bool:
        return self.unlocked and all(done for _l, done in self.lessons)


def career_progress(db) -> list[ChapterState]:
    status, tasks = db.all_exercise_status(), db.all_tasks()
    mods = {m.number: m for m in curriculum.modules()}
    out: list[ChapterState] = []
    prev_beaten = True
    for ch in career.chapters():
        if ch.boss is None:
            lessons = []
            best = db.best_capstone()
            beaten = bool(best and best["passed"])
            stars = 3 if beaten else 0
        else:
            lessons = [(l, mastery.lesson_complete(l, status, db.best_quiz(l.id), tasks.get(l.task.id)))
                       for l in mods[ch.number].lessons]
            stars = int(db.meta(f"boss:{ch.number}") or 0)
            beaten = stars > 0
        out.append(ChapterState(ch, lessons, stars, beaten, prev_beaten))
        prev_beaten = prev_beaten and beaten
    return out


def chapters_done(states: list[ChapterState]) -> int:
    n = 0
    for s in states:
        if not s.beaten:
            break
        n += 1
    return n


def current_rank(db) -> str:
    return career.rank_for(chapters_done(career_progress(db)))


def star_text(n: int) -> str:
    return "⭐" * n + "☆" * (3 - n)


class CareerScreen(Screen):
    title = "Career Mode"
    subtitle = ("Climb from intern to Finance Director at The Aurelia Grand (a fictional hotel). Finish a "
                "chapter's lessons, then beat its boss to get promoted and unlock the next chapter.")

    def __init__(self, ctx):
        super().__init__(ctx)
        self.selected = 1
        self.boss_chapter = None

        # ---- map page
        self.map_page = QWidget()
        mv = QVBoxLayout(self.map_page)
        mv.setContentsMargins(0, 0, 0, 0)
        mv.setSpacing(14)
        head = Card()
        hr = QHBoxLayout()
        self.rank_lbl = label("", "H2")
        hr.addWidget(self.rank_lbl, 1)
        self.score_lbl = label("", "H3", wrap=False)
        hr.addWidget(self.score_lbl)
        head.add(hr)
        self.next_lbl = label("", "Muted")
        head.add(self.next_lbl)
        mv.addWidget(head)
        grid_card = Card("Your career path")
        self.grid = QGridLayout()
        self.grid.setSpacing(10)
        grid_card.add(self.grid)
        self.cards = {}
        for i, ch in enumerate(career.chapters()):
            f = QFrame()
            f.setObjectName("Chapter")
            fl = QVBoxLayout(f)
            fl.setContentsMargins(12, 10, 12, 10)
            fl.setSpacing(3)
            top = QHBoxLayout()
            num = label("👑" if ch.boss is None else str(ch.number), "ChapterNum", wrap=False)
            num.setFixedSize(30, 30)
            num.setAlignment(Qt.AlignCenter)
            top.addWidget(num)
            state = label("", "Muted", wrap=False)
            top.addStretch(1)
            top.addWidget(state)
            fl.addLayout(top)
            fl.addWidget(label(ch.title, "H3"))
            fl.addWidget(label(f"🎖 Promotion: {ch.rank}", "Muted"))
            btn = button("Open", lambda _=False, n=ch.number: self.select(n))
            fl.addWidget(btn)
            self.cards[ch.number] = (f, state, btn)
            self.grid.addWidget(f, i // 3, i % 3)
        grid_card.add(label(career.RANK_NOTE, "Muted"))
        mv.addWidget(grid_card)

        self.detail = Card()
        self.d_title = label("", "H2")
        self.detail.add(self.d_title)
        brief = QFrame()
        brief.setObjectName("Manager")
        bl = QVBoxLayout(brief)
        bl.setContentsMargins(14, 10, 14, 10)
        self.d_from = label("", "Muted", rich=True)
        self.d_msg = label("")
        bl.addWidget(self.d_from)
        bl.addWidget(self.d_msg)
        self.detail.add(brief)
        self.detail.add(label("Objectives", "H3"))
        self.obj_box = QVBoxLayout()
        self.obj_box.setSpacing(6)
        self.detail.add(self.obj_box)
        self.obj_rows = []
        for _ in range(3):
            row = QHBoxLayout()
            lb = label("", rich=True)
            b = button("", None)
            b.clicked.connect(lambda _=False, k=len(self.obj_rows): self._objective(k))
            row.addWidget(lb, 1)
            row.addWidget(b)
            self.obj_box.addLayout(row)
            self.obj_rows.append((lb, b))
        self.d_note = label("", "Muted")
        self.detail.add(self.d_note)
        mv.addWidget(self.detail)
        self.body.addWidget(self.map_page)

        # ---- boss page
        self.boss_page = Card()
        bh = QHBoxLayout()
        self.b_title = label("", "H2")
        bh.addWidget(self.b_title, 1)
        self.b_hearts = label("", "Hearts", wrap=False)
        bh.addWidget(self.b_hearts)
        self.boss_page.add(bh)
        self.b_story = label("")
        self.boss_page.add(self.b_story)
        self.b_step = label("", "StepLbl")
        self.boss_page.add(self.b_step)
        self.b_question = label("", "H3")
        self.boss_page.add(self.b_question)
        ar = QHBoxLayout()
        self.b_input = QLineEdit()
        self.b_input.setMaximumWidth(200)
        self.b_input.returnPressed.connect(self.check)
        ar.addWidget(self.b_input)
        self.b_check = button("Attack ⚔", self.check, primary=True)
        ar.addWidget(self.b_check)
        self.b_hint = button("💡 Hint", self.hint)
        ar.addWidget(self.b_hint)
        self.b_next = button("Next step ▶", self.next_step, primary=True)
        ar.addWidget(self.b_next)
        self.b_retry = button("↺ Try again", self.retry, primary=True)
        ar.addWidget(self.b_retry)
        ar.addStretch(1)
        self.b_back = button("◀ Back to the map", self.back)
        ar.addWidget(self.b_back)
        self.boss_page.add(ar)
        self.b_feedback = label("", rich=True)
        self.boss_page.add(self.b_feedback)
        self.boss_page.add(label("Lives: a wrong answer costs one. Typos that aren't numbers don't count. Lose all "
                                 "three and you simply try again: nothing is lost.", "Muted"))
        self.body.addWidget(self.boss_page)
        self.boss_page.setVisible(False)
        self.body.addStretch(1)

    # ------------------------------------------------------------------ map
    def on_show(self, chapter: int | None = None, **kw):
        states = career_progress(self.ctx.db)
        if chapter is not None:
            self.selected = chapter
        elif self.boss_chapter is None:
            self.selected = next((s.chapter.number for s in states if s.unlocked and not s.beaten), 9)
        self.refresh(states)

    def on_xp(self):
        if self.boss_chapter is None:
            self.refresh()

    def refresh(self, states=None):
        states = states or career_progress(self.ctx.db)
        done = chapters_done(states)
        rank = career.rank_for(done)
        stars = sum(s.stars for s in states if s.chapter.boss)
        self.rank_lbl.setText(f"🎖 {rank}")
        self.score_lbl.setText(f"⭐ {stars} / 24   ·   ⚔ {sum(s.beaten for s in states[:8])} / 8 bosses")
        nxt = next((s for s in states if not s.beaten), None)
        self.next_lbl.setText(f"Next promotion: {nxt.chapter.rank}, by finishing Chapter "
                              f"{nxt.chapter.number}." if nxt and nxt.chapter.boss else
                              "Next: pass the capstone to become Finance Director." if nxt else
                              "You reached the top of the ladder. Replay any boss for 3 stars.")
        for s in states:
            f, state, btn = self.cards[s.chapter.number]
            if s.beaten:
                txt = star_text(s.stars) if s.chapter.boss else "✔ Passed"
            elif not s.unlocked:
                txt = "🔒 Locked"
            elif s.boss_ready or s.chapter.boss is None:
                txt = "⚔ Boss ready"
            else:
                txt = f"📘 {sum(d for _l, d in s.lessons)}/{len(s.lessons)} lessons"
            state.setText(txt)
            f.setProperty("state", "done" if s.beaten else "open" if s.unlocked else "locked")
            f.setProperty("selected", s.chapter.number == self.selected)
            f.style().unpolish(f)
            f.style().polish(f)
            btn.setText("Replay" if s.beaten else "Open" if s.unlocked else "Peek")
        self._fill_detail(states[self.selected - 1])

    def select(self, n: int):
        self.selected = n
        self.refresh()

    def _fill_detail(self, s: ChapterState):
        ch = s.chapter
        self.d_title.setText(f"Chapter {ch.number}: {ch.title}" if ch.boss else ch.title)
        subject, msg = story.note_for(ch.number if ch.boss else None)
        self.d_from.setText(f"📩 <b>{story.MANAGER}</b> · {subject}")
        self.d_msg.setText(msg)
        self._objectives = []
        for lesson, done in s.lessons:
            self._objectives.append((f"{'✔' if done else '○'} 📘 Lesson: <b>{lesson.title}</b>",
                                     "Review" if done else "Play lesson", ("lesson", lesson.id), True))
        if ch.boss:
            b = ch.boss
            got = f" · best {star_text(s.stars)}" if s.beaten else ""
            self._objectives.append((f"{'✔' if s.beaten else '○'} {b.emoji} Boss: <b>{b.name}</b>{got}",
                                     "Replay boss" if s.beaten else "Face the boss ⚔", ("boss", ch.number),
                                     s.boss_ready))
        else:
            self._objectives.append((f"{'✔' if s.beaten else '○'} 👑 Pass the capstone project (70+ out of 100)",
                                     "Open the capstone", ("capstone", None), True))
        for k, (lb, b) in enumerate(self.obj_rows):
            if k < len(self._objectives):
                text, btext, _act, enabled = self._objectives[k]
                lb.setText(text)
                b.setText(btext)
                b.setEnabled(enabled)
                lb.setVisible(True)
                b.setVisible(True)
            else:
                lb.setVisible(False)
                b.setVisible(False)
        if not s.unlocked:
            self.d_note.setText("🔒 This chapter unlocks when you beat the previous boss. You can still peek and "
                                "study its lessons any time.")
        elif ch.boss and not s.boss_ready:
            self.d_note.setText("Finish both lessons (exercises, quiz and practical task) to unlock the boss.")
        else:
            self.d_note.setText(f"Beating the boss earns +{gamify.BOSS_XP} XP once, and a promotion to {ch.rank}."
                                if ch.boss else "Pass the capstone to finish the game as Finance Director.")

    def _objective(self, k: int):
        if k >= len(getattr(self, "_objectives", [])):
            return
        _t, _b, (kind, ref), enabled = self._objectives[k]
        if not enabled:
            return
        if kind == "lesson":
            self.ctx.navigate("lessons", lesson=ref)
        elif kind == "boss":
            self.start_boss(ref)
        else:
            self.ctx.navigate("capstone")

    # ----------------------------------------------------------------- boss
    def start_boss(self, n: int):
        ch = career.chapters()[n - 1]
        if ch.boss is None:
            return
        self.boss_chapter = ch
        self.hearts = career.HEARTS
        self.step = 0
        self.map_page.setVisible(False)
        self.boss_page.setVisible(True)
        self.b_title.setText(f"{ch.boss.emoji} Chapter {n} boss: {ch.boss.name}")
        self.b_story.setText(ch.boss.story)
        self._show_step()

    def _show_step(self):
        st = self.boss_chapter.boss.steps[self.step]
        n = len(self.boss_chapter.boss.steps)
        self.b_step.setText(f"Step {self.step + 1} of {n}  " + "●" * self.step + "○" * (n - self.step))
        self.b_question.setText(st.question)
        self.b_input.clear()
        self.b_input.setReadOnly(False)
        self.b_input.setVisible(True)
        self.b_input.setPlaceholderText({"percent": "e.g. 12.5%", "currency": "e.g. 1,234",
                                         "years": "e.g. 3.5"}.get(st.unit, "e.g. 59"))
        self.b_feedback.setText("")
        self._buttons(fighting=True)
        self._hearts()

    def _buttons(self, fighting=False, between=False, over=False):
        self.b_check.setVisible(fighting)
        self.b_check.setEnabled(fighting)
        self.b_hint.setVisible(fighting)
        self.b_hint.setEnabled(fighting)
        self.b_next.setVisible(between)
        self.b_next.setEnabled(between)
        self.b_retry.setVisible(over)
        self.b_retry.setEnabled(over)

    def _hearts(self):
        self.b_hearts.setText("❤️" * self.hearts + "🖤" * (career.HEARTS - self.hearts))

    def hint(self):
        if self.boss_chapter is None or not self.b_hint.isEnabled():
            return
        self.b_feedback.setText(f"💡 {self.boss_chapter.boss.steps[self.step].hint}")

    def check(self):
        if self.boss_chapter is None or not self.b_check.isEnabled():
            return
        st = self.boss_chapter.boss.steps[self.step]
        text = self.b_input.text()
        p = self.ctx.pal
        if not text.strip():
            self.b_feedback.setText("Type your answer first.")
            return
        r = check_numeric(text, float(st.expected), st.unit, st.abs_tol)
        if r.status == "invalid":
            self.b_feedback.setText(f"<span style='color:{p.warn}'>{r.message}</span>")
            return
        if r.correct:
            self.b_input.setReadOnly(True)
            last = self.step == len(self.boss_chapter.boss.steps) - 1
            self.b_feedback.setText(f"<span style='color:{p.good}'><b>✔ Hit!</b></span> {st.solution}")
            if last:
                self._win()
            else:
                self._buttons(between=True)
            return
        self.hearts -= 1
        self._hearts()
        if self.hearts <= 0:
            shown = format_value(st.expected, st.unit, 2)
            self.b_feedback.setText(f"<span style='color:{p.bad}'><b>💥 Knocked out.</b></span> The answer was "
                                    f"<b>{shown}</b>. {st.solution}<br>Nothing is lost. Catch your breath and "
                                    "try again.")
            self.b_input.setReadOnly(True)
            self._buttons(over=True)
            return
        side = "high" if r.parsed > st.expected else "low"
        self.b_feedback.setText(f"<span style='color:{p.bad}'><b>Ouch, -1 life.</b></span> That's too {side}. "
                                f"{gamify.pick(gamify.ENCOURAGE_WRONG, self.hearts)}")

    def next_step(self):
        if self.boss_chapter is None or not self.b_next.isEnabled():
            return
        self.step += 1
        self._show_step()

    def retry(self):
        if self.boss_chapter is not None:
            self.start_boss(self.boss_chapter.number)

    def _win(self):
        ch = self.boss_chapter
        db = self.ctx.db
        stars = career.stars_for(self.hearts)
        before = chapters_done(career_progress(db))
        old = int(db.meta(f"boss:{ch.number}") or 0)
        if stars > old:
            db.set_meta(f"boss:{ch.number}", str(stars))
        after = chapters_done(career_progress(db))
        self._buttons()
        self.b_step.setText(f"Boss beaten! {star_text(stars)}")
        self.b_question.setText(f"“{ch.boss.win_line}” — {story.MANAGER}")
        self.b_input.setVisible(False)
        if after > before:
            self.ctx.celebrate(f"🎖 Promoted to {career.rank_for(after)}!",
                               f"Chapter {ch.number} complete. " + career.RANK_NOTE, True)
        self.ctx.award("boss", f"ch{ch.number}", gamify.BOSS_XP, f"{ch.boss.emoji} Boss beaten: {ch.boss.name}",
                       big=True)
        if stars > old and old:
            self.ctx.celebrate(f"New best: {star_text(stars)}", "You improved your boss score.")
        self.ctx.window.refresh_xp()

    def back(self):
        self.boss_chapter = None
        self.boss_page.setVisible(False)
        self.map_page.setVisible(True)
        self.refresh()
