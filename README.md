# Student Planner

A small planner that runs on your own computer and opens in your web browser.
It helps you keep track of assignments across all your courses:

- Add courses, then add assignments with a title, description, course, and due date.
- See every assignment in one place, split into **Overdue**, **Upcoming (next 7 days)**,
  **All incomplete**, and **Completed**.
- Mark assignments completed (or not), edit them, and delete them.
- See each course with how many incomplete assignments it still has.
- Everything is saved to a local JSON file (`planner_data.json`), so your data is
  still there after you close and reopen the app.

It uses only the Python 3 standard library: nothing to install, no accounts,
no API keys.

## Run it

```sh
python3 app.py
```

Then open <http://127.0.0.1:8000/> in your browser. Press `Ctrl+C` to stop.

Optional settings: `PORT=9000 python3 app.py` changes the port, and
`PLANNER_DATA=/path/to/file.json python3 app.py` changes where data is stored.

## Run the tests

```sh
python3 -m unittest discover tests
```

Each test name includes the requirement it checks (e.g. `test_R7_mark_completed`);
see `problem.md` for the requirements and `spec.md` for the detailed spec.
