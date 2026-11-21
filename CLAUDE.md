# CLAUDE.md

Guidance for working in this repo.

## Project

A local, browser-based student planner (courses + assignments with due dates).
Requirements are in `problem.md`; the detailed spec is `spec.md`.

## Hard constraints

- Python 3 **standard library only**. Do not add dependencies, `requirements.txt`,
  package managers, API keys, or logins.
- The app runs with one command: `python3 app.py` (uses `http.server`).
- Data lives in a single JSON file (`planner_data.json` by default).

## Layout

- `planner.py` — all business logic and JSON persistence. No HTTP, no HTML.
- `app.py` — HTTP layer: `handle()` routes requests to `Planner` (pure, testable);
  the `http.server` handler only does I/O. The HTML/JS page is embedded here.
- `tests/` — `unittest` tests.
- `docs/decisions/` — architecture decision records (Y-statements).

## Tests

- Run: `python3 -m unittest discover tests` — must pass with nothing skipped.
- Every test name includes the requirement ID it covers, e.g. `test_R7_mark_completed`.
- Test logic, not page layout. Pass `today` explicitly; never depend on the real
  clock. Use temp directories for data files.

## Git

- Small commits; messages say what changed and why.
- Never amend, rebase, or revert published commits.
