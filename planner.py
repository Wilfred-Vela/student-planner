"""Business logic and JSON persistence for the student planner.

No HTTP or HTML here, so everything can be unit-tested directly.
"""

import json
import os
import tempfile
from datetime import date, timedelta

UPCOMING_DAYS = 7
EDITABLE_FIELDS = {"title", "description", "course_id", "due_date", "completed"}


def _empty():
    return {"next_course_id": 1, "next_assignment_id": 1,
            "courses": [], "assignments": []}


def _clean_text(value, field, required):
    if value is None:
        value = ""
    if not isinstance(value, str):
        raise ValueError(f"{field} must be text")
    value = value.strip()
    if required and not value:
        raise ValueError(f"{field} is required")
    return value


def _clean_date(value):
    if not isinstance(value, str):
        raise ValueError("due_date is required (YYYY-MM-DD)")
    try:
        return date.fromisoformat(value.strip()).isoformat()
    except ValueError:
        raise ValueError(f"due_date must be YYYY-MM-DD, got {value!r}") from None


class Planner:
    def __init__(self, path):
        self.path = path
        self._data = self._load()

    # ---- persistence -------------------------------------------------
    def _load(self):
        try:
            with open(self.path, encoding="utf-8") as f:
                data = json.load(f)
        except FileNotFoundError:
            return _empty()
        base = _empty()
        base.update(data)
        return base

    def _save(self):
        folder = os.path.dirname(os.path.abspath(self.path))
        os.makedirs(folder, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=folder, prefix=".planner-", suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=2)
            os.replace(tmp, self.path)
        except BaseException:
            if os.path.exists(tmp):
                os.remove(tmp)
            raise

    # ---- courses (R2) ------------------------------------------------
    def list_courses(self):
        return [dict(c) for c in self._data["courses"]]

    def add_course(self, name):
        name = _clean_text(name, "name", required=True)
        if any(c["name"].lower() == name.lower() for c in self._data["courses"]):
            raise ValueError(f"course {name!r} already exists")
        course = {"id": self._data["next_course_id"], "name": name}
        self._data["next_course_id"] += 1
        self._data["courses"].append(course)
        self._save()
        return dict(course)

    def incomplete_counts(self):
        """R12: {course_id: number of incomplete assignments}, 0 included."""
        counts = {c["id"]: 0 for c in self._data["courses"]}
        for a in self._data["assignments"]:
            if not a["completed"] and a["course_id"] in counts:
                counts[a["course_id"]] += 1
        return counts

    def _course_name(self, course_id):
        for c in self._data["courses"]:
            if c["id"] == course_id:
                return c["name"]
        return None

    def _clean_course_id(self, course_id):
        if isinstance(course_id, bool) or not isinstance(course_id, int):
            raise ValueError("course_id is required")
        if self._course_name(course_id) is None:
            raise ValueError(f"course {course_id} does not exist")
        return course_id

    # ---- assignments (R3-R8) -----------------------------------------
    def _find(self, assignment_id):
        for a in self._data["assignments"]:
            if a["id"] == assignment_id:
                return a
        raise KeyError(f"assignment {assignment_id} not found")

    def _view(self, a):
        return {**a, "course_name": self._course_name(a["course_id"])}

    def get_assignment(self, assignment_id):
        return self._view(self._find(assignment_id))

    def add_assignment(self, title, description, course_id, due_date):
        a = {
            "id": self._data["next_assignment_id"],
            "title": _clean_text(title, "title", required=True),
            "description": _clean_text(description, "description", required=False),
            "course_id": self._clean_course_id(course_id),
            "due_date": _clean_date(due_date),
            "completed": False,
        }
        self._data["next_assignment_id"] += 1
        self._data["assignments"].append(a)
        self._save()
        return self._view(a)

    def update_assignment(self, assignment_id, **fields):
        a = self._find(assignment_id)
        unknown = set(fields) - EDITABLE_FIELDS
        if unknown:
            raise ValueError(f"cannot edit: {', '.join(sorted(unknown))}")
        changes = {}
        if "title" in fields:
            changes["title"] = _clean_text(fields["title"], "title", required=True)
        if "description" in fields:
            changes["description"] = _clean_text(
                fields["description"], "description", required=False)
        if "course_id" in fields:
            changes["course_id"] = self._clean_course_id(fields["course_id"])
        if "due_date" in fields:
            changes["due_date"] = _clean_date(fields["due_date"])
        if "completed" in fields:
            if not isinstance(fields["completed"], bool):
                raise ValueError("completed must be true or false")
            changes["completed"] = fields["completed"]
        # Validate everything before mutating so a bad field changes nothing.
        a.update(changes)
        self._save()
        return self._view(a)

    def set_completed(self, assignment_id, completed=True):
        return self.update_assignment(assignment_id, completed=bool(completed))

    def delete_assignment(self, assignment_id):
        a = self._find(assignment_id)
        self._data["assignments"].remove(a)
        self._save()

    def list_assignments(self, completed=None):
        items = self._data["assignments"]
        if completed is not None:
            items = [a for a in items if a["completed"] == completed]
        items = sorted(items, key=lambda a: (a["due_date"], a["id"]))
        return [self._view(a) for a in items]

    # ---- status (R9, R10) --------------------------------------------
    @staticmethod
    def status(assignment, today):
        if assignment["completed"]:
            return "completed"
        due = date.fromisoformat(assignment["due_date"])
        if due < today:
            return "overdue"
        if due <= today + timedelta(days=UPCOMING_DAYS):
            return "upcoming"
        return "later"

    def overdue(self, today):
        return [a for a in self.list_assignments(completed=False)
                if self.status(a, today) == "overdue"]

    def upcoming(self, today):
        return [a for a in self.list_assignments(completed=False)
                if self.status(a, today) == "upcoming"]
