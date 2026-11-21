# 0001 — Store data in a single JSON file with atomic writes

- Status: accepted
- Date: 2026-11-21

## Decision (Y-statement)

In the context of **persisting a single student's courses and assignments
locally (R11) with only the Python standard library**,
facing **the need for data that survives restarts, stays readable and easy to
back up, and cannot be corrupted if the app is killed mid-save**,
we decided for **one JSON file rewritten in full on every change, via a temp
file and `os.replace`, served by a single-threaded `http.server`**,
and neglected **SQLite (`sqlite3`), an append-only JSON Lines event log, and
one-file-per-record storage**,
to achieve **a human-readable file the user can open, copy, or hand-edit, very
little storage code, and crash-safe saves**,
accepting **that every write rewrites the whole file (fine for hundreds of
assignments, not for millions) and that concurrent writers are not supported,
which is why the server handles one request at a time**.

## Alternatives considered

- **SQLite via `sqlite3`** — also stdlib, gives transactions and concurrent
  access for free. Rejected for this build: the data is tiny, a binary `.db` file
  is opaque to students, and schema/migration code would outweigh the logic. It is
  the natural next step if the data grows or multiple users are added.
- **JSON Lines event log** — append-only, cheap writes, keeps history. Rejected:
  needs replay/compaction logic to rebuild current state, and edits/deletes make
  the log grow without bound.
- **One JSON file per assignment** — limits each write to one record, but makes
  ID allocation, listing, and atomic multi-record changes harder.

## Consequences

- `Planner` loads the file once at start and saves after each mutation.
- A missing file means an empty planner; the file is created on first change.
- `os.replace` is atomic on the same filesystem, so the file is always either the
  old or the new version, never half-written.
