# Student Planner — Specification

Derived from `problem.md`. Each requirement keeps its ID (R1–R11) so tests can
be traced back to it (`test_R<n>_...`).

## Constraints

- Python 3 standard library only. Nothing to install, no API keys, no accounts.
- Starts with one command: `python3 app.py`, served by `http.server`.
- Data is stored in one JSON file on the user's computer.
- Business logic lives apart from HTTP and HTML so it can be unit-tested.

## Data model

**Course**

| field | type | rules |
|-------|------|-------|
| `id` | int | assigned by the app, unique, never reused |
| `name` | str | required, trimmed, non-empty, unique (case-insensitive) |

**Assignment**

| field | type | rules |
|-------|------|-------|
| `id` | int | assigned by the app, unique, never reused |
| `title` | str | required, trimmed, non-empty |
| `description` | str | optional, defaults to `""` |
| `course_id` | int | required, must refer to an existing course |
| `due_date` | str | required, ISO date `YYYY-MM-DD` |
| `completed` | bool | defaults to `false` |

Invalid input raises `ValueError` in the logic layer; the HTTP layer turns it
into `400` with `{"error": "<message>"}`. Unknown IDs raise `KeyError` → `404`.

## Requirements

- **R1 — Runs locally, one command, in a browser, no keys/accounts.**
  `python3 app.py` starts an HTTP server on `127.0.0.1:8000` (override with
  `PORT` env var). `GET /` returns the HTML page. The code imports only
  standard-library modules.
- **R2 — Add courses.** `add_course(name)` returns the new course. Blank or
  duplicate names are rejected.
- **R3 — Add assignments with title and description.**
  `add_assignment(title, description, course_id, due_date)` returns the new
  assignment. Blank title is rejected; description may be empty.
- **R4 — Assign each assignment to a course.** `course_id` is required and must
  exist; otherwise `ValueError`.
- **R5 — Due date per assignment.** `due_date` is required and must parse as an
  ISO date; otherwise `ValueError`.
- **R6 — View all assignments in one place.** `list_assignments()` returns every
  assignment, sorted by due date then id, each including its `course_name`.
  `GET /api/data` returns courses, all assignments, upcoming, and overdue.
- **R7 — Mark completed.** `set_completed(id, True)` marks an assignment done;
  `set_completed(id, False)` undoes it.
- **R8 — Edit and delete.** `update_assignment(id, **fields)` changes any of
  `title`, `description`, `course_id`, `due_date`, `completed` with the same
  validation as creation. `delete_assignment(id)` removes it. Unknown ids raise
  `KeyError`.
- **R9 — Distinguish completed vs incomplete.** `status(assignment, today)`
  returns `"completed"`, `"overdue"`, `"upcoming"`, or `"later"`;
  `list_assignments(completed=True|False)` filters. The page shows completed
  items struck through in their own section.
- **R10 — Upcoming and overdue.** For a given `today`:
  - *overdue*: incomplete and `due_date < today`.
  - *upcoming*: incomplete and `today <= due_date <= today + 7 days`.
  - Completed assignments are never upcoming or overdue.
  `upcoming(today)` and `overdue(today)` return them sorted by due date.
- **R11 — Saved locally across restarts.** Every change is written to the JSON
  file (default `planner_data.json` next to `app.py`, override with
  `PLANNER_DATA` env var). A new `Planner` opened on the same file sees the same
  courses and assignments. Writes are atomic (temp file + `os.replace`) so a
  crash mid-write cannot corrupt the file. A missing file means an empty planner.

## HTTP API

| method | path | body | result |
|--------|------|------|--------|
| GET | `/` | — | HTML page |
| GET | `/api/data` | — | `{today, courses, assignments, upcoming, overdue}` |
| POST | `/api/courses` | `{name}` | `201` course |
| POST | `/api/assignments` | `{title, description, course_id, due_date}` | `201` assignment |
| PUT | `/api/assignments/<id>` | any editable fields | `200` assignment |
| DELETE | `/api/assignments/<id>` | — | `200 {"deleted": id}` |

Routing is done by a pure function `handle(planner, method, path, body, today)`
returning `(status, payload)`, so the API can be tested without a socket.

## Out of scope (first build)

Editing/deleting courses, reminders/notifications, multiple users, priorities.
