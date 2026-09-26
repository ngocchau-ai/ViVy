"""C11.5 — lesson persistence across restart + held-out behaviour + memory-on/off.

Lessons are small key/value routing hints (avoid / prefer). They must survive a
process restart and change choices on a held-out task; gain/harm is measured
paired against a memory-off arm on the same candidate list.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path


LATENCY_CLAIM = "NOT_A_PHYSICAL_ZERO"
STATUS_LABEL = "PROVISIONAL_RESULT"


@dataclass(frozen=True)
class Lesson:
    lesson_id: str
    scope: str
    key: str
    value: str
    confidence: float
    provenance: str
    created_at_ms: int


class LessonStore:
    def __init__(self, path: Path):
        self._path = Path(path)
        self._by_id: dict[str, Lesson] = {}
        if self._path.exists():
            for line in self._path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                raw = json.loads(line)
                lesson = Lesson(**raw)
                self._by_id[lesson.lesson_id] = lesson

    def add(self, lesson: Lesson) -> None:
        if lesson.lesson_id in self._by_id:
            return  # idempotent by lesson_id
        self._by_id[lesson.lesson_id] = lesson
        self._append(lesson)

    def get(self, lesson_id: str) -> Lesson | None:
        return self._by_id.get(lesson_id)

    def count(self) -> int:
        return len(self._by_id)

    def all(self) -> list[Lesson]:
        return list(self._by_id.values())

    def checkpoint(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._path.open("w", encoding="utf-8", newline="\n") as fh:
            for lesson in self._by_id.values():
                fh.write(json.dumps(asdict(lesson), ensure_ascii=False, sort_keys=True) + "\n")

    def _append(self, lesson: Lesson) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._path.open("a", encoding="utf-8", newline="\n") as fh:
            fh.write(json.dumps(asdict(lesson), ensure_ascii=False, sort_keys=True) + "\n")


def apply_lessons(candidates, *, lessons, query: str = "") -> str:
    """Pick an action. Memory-off (lessons=[]) = first candidate. Memory-on applies avoid/prefer."""
    del query  # lexical query routing lives in memory_retrieval_ab; this path is rule-based
    cands = tuple(candidates)
    if not cands:
        raise ValueError("candidates must be non-empty")
    if not lessons:
        return cands[0]

    avoid = {l.value for l in lessons if l.key == "avoid"}
    prefer = [l.value for l in lessons if l.key == "prefer"]
    for value in prefer:
        if value in cands and value not in avoid:
            return value
    for value in cands:
        if value not in avoid:
            return value
    return cands[0]


def run_memory_on_off_lessons(tasks, *, candidates, lessons) -> dict:
    """Paired A/B: same tasks, memory-on vs memory-off. Reports gain/harm/tie with denominators.

    tasks: sequence of (task_id, query, gold_action).
    """
    n = 0
    gain = harm = tie = 0
    on_correct = off_correct = 0
    per_task = []
    for task_id, query, gold in tasks:
        n += 1
        chosen_on = apply_lessons(candidates, lessons=lessons, query=query)
        chosen_off = apply_lessons(candidates, lessons=[], query=query)
        on_ok = chosen_on == gold
        off_ok = chosen_off == gold
        on_correct += int(on_ok)
        off_correct += int(off_ok)
        if on_ok and not off_ok:
            gain += 1
        elif off_ok and not on_ok:
            harm += 1
        else:
            tie += 1
        per_task.append(
            {
                "task_id": task_id,
                "chosen_on": chosen_on,
                "chosen_off": chosen_off,
                "gold": gold,
                "on_ok": on_ok,
                "off_ok": off_ok,
            }
        )

    return {
        "n_tasks": n,
        "arm_on": {
            "denominator": n,
            "correct": on_correct,
            "wrong": n - on_correct,
            "memory_visible": True,
        },
        "arm_off": {
            "denominator": n,
            "correct": off_correct,
            "wrong": n - off_correct,
            "memory_visible": False,
        },
        "gain": gain,
        "harm": harm,
        "tie": tie,
        "per_task": per_task,
        "latency_claim": LATENCY_CLAIM,
        "status_label": STATUS_LABEL,
    }
