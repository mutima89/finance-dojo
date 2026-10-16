"""Local SQLite progress store. One file per user; no network, no accounts."""
from __future__ import annotations

import datetime as dt
import json
import shutil
import sqlite3
from pathlib import Path
from typing import Any, Iterable, Optional

from ..paths import user_data_dir

SCHEMA_VERSION = 1
SCHEMA = """
CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE IF NOT EXISTS attempts(
    id INTEGER PRIMARY KEY AUTOINCREMENT, exercise_id TEXT, lesson_id TEXT, module_id TEXT,
    skill TEXT, answer TEXT, correct INTEGER, attempt_no INTEGER, ts TEXT);
CREATE TABLE IF NOT EXISTS exercise_status(
    exercise_id TEXT PRIMARY KEY, lesson_id TEXT, module_id TEXT, skill TEXT, practical INTEGER,
    attempts INTEGER DEFAULT 0, wrong INTEGER DEFAULT 0, solved INTEGER DEFAULT 0,
    solved_on INTEGER, revealed INTEGER DEFAULT 0, hints_used INTEGER DEFAULT 0, updated TEXT);
CREATE TABLE IF NOT EXISTS quiz_answers(
    lesson_id TEXT, question_id TEXT, skill TEXT, correct INTEGER, ts TEXT,
    PRIMARY KEY(lesson_id, question_id));
CREATE TABLE IF NOT EXISTS quiz_results(
    id INTEGER PRIMARY KEY AUTOINCREMENT, lesson_id TEXT, module_id TEXT, score INTEGER,
    total INTEGER, ts TEXT);
CREATE TABLE IF NOT EXISTS lesson_progress(
    lesson_id TEXT PRIMARY KEY, module_id TEXT, sections TEXT DEFAULT '[]',
    seconds INTEGER DEFAULT 0, last_opened TEXT);
CREATE TABLE IF NOT EXISTS tasks(
    task_id TEXT PRIMARY KEY, lesson_id TEXT, module_id TEXT, content TEXT,
    checklist TEXT DEFAULT '[]', updated TEXT, exported INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS workbook_results(
    task_id INTEGER PRIMARY KEY, status TEXT, source TEXT, ts TEXT);
CREATE TABLE IF NOT EXISTS capstone(item_id TEXT PRIMARY KEY, answer TEXT, updated TEXT);
CREATE TABLE IF NOT EXISTS capstone_scores(
    id INTEGER PRIMARY KEY AUTOINCREMENT, total REAL, passed INTEGER, detail TEXT, ts TEXT);
CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY AUTOINCREMENT, kind TEXT, detail TEXT, ts TEXT);
CREATE TABLE IF NOT EXISTS xp(
    id INTEGER PRIMARY KEY AUTOINCREMENT, source TEXT, ref TEXT, amount INTEGER, note TEXT, ts TEXT,
    UNIQUE(source, ref));
"""

DEFAULT_SETTINGS = {"theme": "dark", "max_attempts": "3", "student_name": "", "font_size": "10",
                    "daily_goal": "50", "celebrations": "1", "reduce_motion": "0", "focus_minutes": "10"}


def now() -> str:
    return dt.datetime.now().isoformat(timespec="seconds")


class Progress:
    def __init__(self, path: Optional[Path] = None):
        self.path = Path(path) if path else user_data_dir() / "progress.sqlite3"
        self.conn = self._open(self.path)

    @staticmethod
    def _open(path: Path) -> sqlite3.Connection:
        path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(path))
        conn.row_factory = sqlite3.Row
        conn.executescript(SCHEMA)
        conn.execute("INSERT OR IGNORE INTO meta VALUES('schema_version', ?)", (str(SCHEMA_VERSION),))
        conn.execute("INSERT OR IGNORE INTO meta VALUES('created', ?)", (now(),))
        conn.commit()
        return conn

    def close(self):
        self.conn.close()

    def _q(self, sql: str, args: Iterable = ()) -> list[sqlite3.Row]:
        return self.conn.execute(sql, tuple(args)).fetchall()

    def _x(self, sql: str, args: Iterable = ()):
        self.conn.execute(sql, tuple(args))
        self.conn.commit()

    # ------------------------------------------------------------ settings
    def setting(self, key: str) -> str:
        r = self._q("SELECT value FROM settings WHERE key=?", [key])
        return r[0]["value"] if r else DEFAULT_SETTINGS.get(key, "")

    def set_setting(self, key: str, value: Any):
        self._x("INSERT OR REPLACE INTO settings VALUES(?,?)", [key, str(value)])

    def max_attempts(self) -> int:
        try:
            return max(1, min(10, int(self.setting("max_attempts"))))
        except ValueError:
            return 3

    def meta(self, key: str) -> Optional[str]:
        r = self._q("SELECT value FROM meta WHERE key=?", [key])
        return r[0]["value"] if r else None

    def set_meta(self, key: str, value: str):
        self._x("INSERT OR REPLACE INTO meta VALUES(?,?)", [key, value])

    def log(self, kind: str, detail: str = ""):
        self._x("INSERT INTO events(kind, detail, ts) VALUES(?,?,?)", [kind, detail, now()])

    def logged(self, kind: str, detail: str) -> bool:
        return bool(self._q("SELECT 1 FROM events WHERE kind=? AND detail=? LIMIT 1", [kind, detail]))

    # ----------------------------------------------------------- exercises
    def _ensure_status(self, ex, lesson_id, module_id):
        self._x("INSERT OR IGNORE INTO exercise_status(exercise_id, lesson_id, module_id, skill, practical, updated) "
                "VALUES(?,?,?,?,?,?)", [ex.id, lesson_id, module_id, ex.skill, int(ex.practical), now()])

    def exercise_state(self, exercise_id: str) -> dict:
        r = self._q("SELECT * FROM exercise_status WHERE exercise_id=?", [exercise_id])
        if not r:
            return {"attempts": 0, "wrong": 0, "solved": 0, "solved_on": None, "revealed": 0, "hints_used": 0}
        return dict(r[0])

    def record_attempt(self, ex, lesson_id: str, module_id: str, answer: str, correct: bool) -> dict:
        self._ensure_status(ex, lesson_id, module_id)
        st = self.exercise_state(ex.id)
        n = st["attempts"] + 1
        self._x("INSERT INTO attempts(exercise_id, lesson_id, module_id, skill, answer, correct, attempt_no, ts) "
                "VALUES(?,?,?,?,?,?,?,?)", [ex.id, lesson_id, module_id, ex.skill, str(answer), int(correct), n, now()])
        if correct and not st["solved"]:
            self._x("UPDATE exercise_status SET attempts=?, solved=1, solved_on=?, updated=? WHERE exercise_id=?",
                    [n, n, now(), ex.id])
        else:
            self._x("UPDATE exercise_status SET attempts=?, wrong=wrong+?, updated=? WHERE exercise_id=?",
                    [n, 0 if correct else 1, now(), ex.id])
        self.set_meta("last_lesson", lesson_id)
        return self.exercise_state(ex.id)

    def record_hint(self, ex, lesson_id: str, module_id: str):
        self._ensure_status(ex, lesson_id, module_id)
        self._x("UPDATE exercise_status SET hints_used=hints_used+1, updated=? WHERE exercise_id=?", [now(), ex.id])

    def record_reveal(self, ex, lesson_id: str, module_id: str):
        self._ensure_status(ex, lesson_id, module_id)
        self._x("UPDATE exercise_status SET revealed=1, updated=? WHERE exercise_id=?", [now(), ex.id])

    def all_exercise_status(self) -> dict[str, dict]:
        return {r["exercise_id"]: dict(r) for r in self._q("SELECT * FROM exercise_status")}

    def attempts_total(self) -> tuple[int, int]:
        r = self._q("SELECT COUNT(*) n, COALESCE(SUM(correct),0) c FROM attempts")[0]
        return r["n"], r["c"]

    # ---------------------------------------------------------------- quiz
    def record_quiz(self, lesson_id: str, module_id: str, results: list[tuple[str, str, bool]]):
        ts = now()
        for qid, skill, ok in results:
            self.conn.execute("INSERT OR REPLACE INTO quiz_answers VALUES(?,?,?,?,?)",
                              [lesson_id, qid, skill, int(ok), ts])
        score = sum(1 for *_, ok in results if ok)
        self.conn.execute("INSERT INTO quiz_results(lesson_id, module_id, score, total, ts) VALUES(?,?,?,?,?)",
                          [lesson_id, module_id, score, len(results), ts])
        self.conn.commit()
        self.set_meta("last_lesson", lesson_id)

    def best_quiz(self, lesson_id: str) -> Optional[tuple[int, int]]:
        r = self._q("SELECT score, total FROM quiz_results WHERE lesson_id=? ORDER BY score DESC LIMIT 1", [lesson_id])
        return (r[0]["score"], r[0]["total"]) if r else None

    def quiz_history(self) -> list[dict]:
        return [dict(r) for r in self._q("SELECT * FROM quiz_results ORDER BY ts")]

    def quiz_answers(self) -> list[dict]:
        return [dict(r) for r in self._q("SELECT * FROM quiz_answers")]

    # ------------------------------------------------------ lesson progress
    def view_section(self, lesson_id: str, module_id: str, section: str):
        r = self._q("SELECT sections FROM lesson_progress WHERE lesson_id=?", [lesson_id])
        secs = set(json.loads(r[0]["sections"])) if r else set()
        secs.add(section)
        self._x("INSERT INTO lesson_progress(lesson_id, module_id, sections, last_opened) VALUES(?,?,?,?) "
                "ON CONFLICT(lesson_id) DO UPDATE SET sections=excluded.sections, last_opened=excluded.last_opened",
                [lesson_id, module_id, json.dumps(sorted(secs)), now()])
        self.set_meta("last_lesson", lesson_id)

    def sections_viewed(self, lesson_id: str) -> set[str]:
        r = self._q("SELECT sections FROM lesson_progress WHERE lesson_id=?", [lesson_id])
        return set(json.loads(r[0]["sections"])) if r else set()

    def add_time(self, lesson_id: str, module_id: str, seconds: int):
        """Active study time. The UI only counts time while the lesson screen
        is visible and the user has interacted within the last 5 minutes."""
        if seconds <= 0:
            return
        self._x("INSERT INTO lesson_progress(lesson_id, module_id, seconds, last_opened) VALUES(?,?,?,?) "
                "ON CONFLICT(lesson_id) DO UPDATE SET seconds=seconds+?",
                [lesson_id, module_id, int(seconds), now(), int(seconds)])

    def lesson_seconds(self) -> dict[str, int]:
        return {r["lesson_id"]: r["seconds"] for r in self._q("SELECT lesson_id, seconds FROM lesson_progress")}

    # --------------------------------------------------------------- tasks
    def save_task(self, task_id: str, lesson_id: str, module_id: str, content: str, checklist: list[bool]):
        self._x("INSERT INTO tasks(task_id, lesson_id, module_id, content, checklist, updated) VALUES(?,?,?,?,?,?) "
                "ON CONFLICT(task_id) DO UPDATE SET content=excluded.content, checklist=excluded.checklist, "
                "updated=excluded.updated", [task_id, lesson_id, module_id, content, json.dumps(checklist), now()])
        self.set_meta("last_lesson", lesson_id)

    def mark_task_exported(self, task_id: str):
        self._x("UPDATE tasks SET exported=1 WHERE task_id=?", [task_id])

    def task(self, task_id: str) -> Optional[dict]:
        r = self._q("SELECT * FROM tasks WHERE task_id=?", [task_id])
        if not r:
            return None
        d = dict(r[0])
        d["checklist"] = json.loads(d["checklist"] or "[]")
        return d

    def all_tasks(self) -> dict[str, dict]:
        return {r["task_id"]: dict(r) for r in self._q("SELECT * FROM tasks")}

    # ------------------------------------------------------------ workbook
    def save_workbook_results(self, results: list[tuple[int, str]], source: str):
        ts = now()
        for tid, status in results:
            if status == "not_attempted":
                continue
            self.conn.execute("INSERT OR REPLACE INTO workbook_results VALUES(?,?,?,?)", [tid, status, source, ts])
        self.conn.commit()

    def workbook_results(self) -> dict[int, str]:
        return {r["task_id"]: r["status"] for r in self._q("SELECT * FROM workbook_results")}

    # ------------------------------------------------------------ capstone
    def capstone_answers(self) -> dict[str, Any]:
        return {r["item_id"]: json.loads(r["answer"]) for r in self._q("SELECT * FROM capstone")}

    def save_capstone_answer(self, item_id: str, answer: Any):
        self._x("INSERT OR REPLACE INTO capstone VALUES(?,?,?)", [item_id, json.dumps(answer), now()])

    def record_capstone_score(self, total: float, passed: bool, detail: dict):
        self._x("INSERT INTO capstone_scores(total, passed, detail, ts) VALUES(?,?,?,?)",
                [total, int(passed), json.dumps(detail), now()])

    def best_capstone(self) -> Optional[dict]:
        r = self._q("SELECT * FROM capstone_scores ORDER BY total DESC LIMIT 1")
        return dict(r[0]) if r else None

    # ------------------------------------------------------------------ XP
    def add_xp(self, source: str, ref: str, amount: int, note: str = "", ts: Optional[str] = None) -> bool:
        """Award XP once per (source, ref). Returns True only when it was newly awarded."""
        if amount <= 0:
            return False
        cur = self.conn.execute("INSERT OR IGNORE INTO xp(source, ref, amount, note, ts) VALUES(?,?,?,?,?)",
                                [source, ref, int(amount), note, ts or now()])
        self.conn.commit()
        return cur.rowcount == 1

    def has_xp(self, source: str, ref: str) -> bool:
        return bool(self._q("SELECT 1 FROM xp WHERE source=? AND ref=?", [source, ref]))

    def xp_total(self) -> int:
        return int(self._q("SELECT COALESCE(SUM(amount),0) t FROM xp")[0]["t"])

    def xp_on(self, day: dt.date) -> int:
        return int(self._q("SELECT COALESCE(SUM(amount),0) t FROM xp WHERE substr(ts,1,10)=?",
                           [day.isoformat()])[0]["t"])

    def xp_count_on(self, source: str, day: dt.date) -> int:
        return int(self._q("SELECT COUNT(*) n FROM xp WHERE source=? AND substr(ts,1,10)=?",
                           [source, day.isoformat()])[0]["n"])

    def active_days(self) -> list[dt.date]:
        return [dt.date.fromisoformat(r["d"]) for r in self._q("SELECT DISTINCT substr(ts,1,10) d FROM xp")]

    def xp_by_day(self, days: int = 14) -> dict[dt.date, int]:
        since = (dt.date.today() - dt.timedelta(days=days - 1)).isoformat()
        return {dt.date.fromisoformat(r["d"]): int(r["t"]) for r in self._q(
            "SELECT substr(ts,1,10) d, SUM(amount) t FROM xp WHERE substr(ts,1,10)>=? GROUP BY d", [since])}

    def int_setting(self, key: str, allowed: tuple[int, ...], default: int) -> int:
        try:
            v = int(self.setting(key))
        except ValueError:
            return default
        return v if v in allowed else default

    def flag(self, key: str) -> bool:
        return self.setting(key) == "1"

    # -------------------------------------------------------- backup/reset
    def backup(self, dest: Path) -> Path:
        dest = Path(dest)
        dest.parent.mkdir(parents=True, exist_ok=True)
        target = sqlite3.connect(str(dest))
        with target:
            self.conn.backup(target)
        target.close()
        return dest

    @staticmethod
    def validate_backup(src: Path) -> None:
        try:
            c = sqlite3.connect(f"file:{Path(src).as_posix()}?mode=ro", uri=True)
            names = {r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            c.close()
        except sqlite3.DatabaseError as exc:
            raise ValueError(f"This file is not a valid progress backup ({exc}).") from exc
        missing = {"meta", "exercise_status", "quiz_results", "tasks"} - names
        if missing:
            raise ValueError("This file is not a progress backup from this app (missing: "
                             + ", ".join(sorted(missing)) + ").")

    def restore(self, src: Path):
        self.validate_backup(src)
        self.conn.close()
        safety = self.path.with_suffix(".before_restore.sqlite3")
        if self.path.exists():
            shutil.copy2(self.path, safety)
        shutil.copy2(src, self.path)
        self.conn = self._open(self.path)

    def reset(self):
        for t in ("attempts", "exercise_status", "quiz_answers", "quiz_results", "lesson_progress", "tasks",
                  "workbook_results", "capstone", "capstone_scores", "events", "xp"):
            self.conn.execute(f"DELETE FROM {t}")
        self.conn.execute("DELETE FROM meta WHERE key IN ('last_lesson', 'xp_backfilled')")
        self.conn.commit()
