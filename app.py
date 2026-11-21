"""Student Planner web app. Run with: python3 app.py

`handle()` is a pure router (testable without sockets); `PlannerHandler`
only adapts it to http.server.
"""

import json
import os
import re
from datetime import date
from http.server import BaseHTTPRequestHandler, HTTPServer

from planner import Planner

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8000
DEFAULT_DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "planner_data.json")

ASSIGNMENT_PATH = re.compile(r"^/api/assignments/([^/]+)$")


def _with_status(items, today):
    return [{**a, "status": Planner.status(a, today)} for a in items]


def handle(planner, method, path, body, today):
    """Route one request. Returns (status_code, payload).

    payload is a str for HTML, otherwise a JSON-serialisable object.
    """
    path = path.split("?", 1)[0]
    if body is not None and not isinstance(body, dict):
        return 400, {"error": "request body must be a JSON object"}
    body = body or {}
    try:
        if method == "GET" and path == "/":
            return 200, PAGE
        if method == "GET" and path == "/api/data":
            return 200, {
                "today": today.isoformat(),
                "courses": planner.list_courses(),
                "assignments": _with_status(planner.list_assignments(), today),
                "upcoming": _with_status(planner.upcoming(today), today),
                "overdue": _with_status(planner.overdue(today), today),
            }
        if method == "POST" and path == "/api/courses":
            return 201, planner.add_course(body.get("name"))
        if method == "POST" and path == "/api/assignments":
            return 201, planner.add_assignment(
                body.get("title"), body.get("description", ""),
                body.get("course_id"), body.get("due_date"),
            )
        m = ASSIGNMENT_PATH.match(path)
        if m and method in ("PUT", "DELETE"):
            if not m.group(1).isdigit():
                return 404, {"error": "assignment not found"}
            aid = int(m.group(1))
            if method == "PUT":
                return 200, planner.update_assignment(aid, **body)
            planner.delete_assignment(aid)
            return 200, {"deleted": aid}
    except ValueError as e:
        return 400, {"error": str(e)}
    except KeyError as e:
        return 404, {"error": e.args[0] if e.args else "not found"}
    return 404, {"error": f"no route for {method} {path}"}


class PlannerHandler(BaseHTTPRequestHandler):
    planner = None  # set by make_server

    def _dispatch(self):
        body = None
        length = int(self.headers.get("Content-Length") or 0)
        if length:
            try:
                body = json.loads(self.rfile.read(length))
            except (json.JSONDecodeError, UnicodeDecodeError):
                return self._send(400, {"error": "invalid JSON"})
        status, payload = handle(self.planner, self.command, self.path, body,
                                 date.today())
        self._send(status, payload)

    def _send(self, status, payload):
        if isinstance(payload, str):
            data, ctype = payload.encode("utf-8"), "text/html; charset=utf-8"
        else:
            data, ctype = json.dumps(payload).encode("utf-8"), "application/json"
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    do_GET = do_POST = do_PUT = do_DELETE = _dispatch

    def log_message(self, fmt, *args):  # keep the terminal quiet
        pass


def make_server(planner, host=DEFAULT_HOST, port=DEFAULT_PORT):
    # Single-threaded on purpose: requests are handled one at a time, so
    # writes to the JSON file never race.
    handler = type("BoundHandler", (PlannerHandler,), {"planner": planner})
    return HTTPServer((host, port), handler)


def main():
    path = os.environ.get("PLANNER_DATA", DEFAULT_DATA)
    port = int(os.environ.get("PORT", DEFAULT_PORT))
    server = make_server(Planner(path), DEFAULT_HOST, port)
    print(f"Student Planner running at http://{DEFAULT_HOST}:{port}/")
    print(f"Data file: {path}")
    print("Press Ctrl+C to stop.", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        server.server_close()


PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Student Planner</title>
<style>
  body { font-family: system-ui, sans-serif; max-width: 900px; margin: 2rem auto;
         padding: 0 1rem; color: #222; }
  h1 { margin-bottom: .25rem; }
  section { margin: 1.5rem 0; }
  form { display: flex; flex-wrap: wrap; gap: .5rem; align-items: end; }
  label { display: flex; flex-direction: column; font-size: .85rem; }
  input, select, textarea, button { font: inherit; padding: .3rem .5rem; }
  textarea { min-width: 16rem; }
  ul { list-style: none; padding: 0; }
  li { border: 1px solid #ddd; border-radius: 6px; padding: .5rem .75rem;
       margin: .4rem 0; display: flex; gap: .75rem; align-items: start; }
  li .main { flex: 1; }
  li .meta { font-size: .85rem; color: #555; }
  li .desc { font-size: .9rem; white-space: pre-wrap; }
  li.overdue { border-left: 5px solid #c62828; }
  li.upcoming { border-left: 5px solid #f9a825; }
  li.later { border-left: 5px solid #90a4ae; }
  li.completed { border-left: 5px solid #2e7d32; opacity: .7; }
  li.completed .title { text-decoration: line-through; }
  .badge { font-size: .75rem; padding: 0 .4rem; border-radius: 4px; color: #fff; }
  .badge.overdue { background: #c62828; } .badge.upcoming { background: #f9a825; }
  .badge.later { background: #90a4ae; } .badge.completed { background: #2e7d32; }
  #error { color: #c62828; min-height: 1.2em; }
  .empty { color: #777; font-style: italic; }
</style>
</head>
<body>
<h1>Student Planner</h1>
<div id="today" class="meta"></div>
<div id="error" role="alert"></div>

<section>
  <h2>Add a course</h2>
  <form id="course-form">
    <label>Course name <input name="name" required></label>
    <button>Add course</button>
  </form>
</section>

<section>
  <h2 id="form-title">Add an assignment</h2>
  <form id="assignment-form">
    <input type="hidden" name="id">
    <label>Title <input name="title" required></label>
    <label>Course <select name="course_id" required></select></label>
    <label>Due date <input type="date" name="due_date" required></label>
    <label>Description <textarea name="description" rows="2"></textarea></label>
    <button id="save-btn">Add assignment</button>
    <button type="button" id="cancel-btn" hidden>Cancel edit</button>
  </form>
</section>

<section><h2>Overdue</h2><ul id="overdue"></ul></section>
<section><h2>Upcoming (next 7 days)</h2><ul id="upcoming"></ul></section>
<section><h2>All incomplete</h2><ul id="incomplete"></ul></section>
<section><h2>Completed</h2><ul id="completed"></ul></section>

<script>
const $ = (s) => document.querySelector(s);
let state = null;

async function api(method, url, body) {
  const res = await fetch(url, {
    method, headers: {"Content-Type": "application/json"},
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || res.statusText);
  return data;
}

function showError(e) { $("#error").textContent = e ? e.message : ""; }

function el(tag, props = {}, children = []) {
  const n = Object.assign(document.createElement(tag), props);
  for (const c of children) n.append(c);
  return n;
}

function item(a) {
  const check = el("input", {type: "checkbox", checked: a.completed,
    title: "Mark completed"});
  check.onchange = () => act(() => api("PUT", `/api/assignments/${a.id}`,
                                       {completed: check.checked}));
  const edit = el("button", {textContent: "Edit", onclick: () => startEdit(a)});
  const del = el("button", {textContent: "Delete", onclick: () => {
    if (confirm(`Delete "${a.title}"?`))
      act(() => api("DELETE", `/api/assignments/${a.id}`));
  }});
  const main = el("div", {className: "main"}, [
    el("div", {}, [el("strong", {className: "title", textContent: a.title}), " ",
                   el("span", {className: `badge ${a.status}`, textContent: a.status})]),
    el("div", {className: "meta",
               textContent: `${a.course_name} · due ${a.due_date}`}),
    el("div", {className: "desc", textContent: a.description}),
  ]);
  return el("li", {className: a.status}, [check, main, edit, del]);
}

function fill(id, items) {
  const ul = $("#" + id);
  ul.replaceChildren(...(items.length ? items.map(item)
    : [el("li", {className: "empty", textContent: "Nothing here."})]));
}

function render() {
  $("#today").textContent = `Today: ${state.today}`;
  const sel = $("#assignment-form [name=course_id]");
  const current = sel.value;
  sel.replaceChildren(
    el("option", {value: "", textContent: state.courses.length
      ? "Choose a course" : "Add a course first"}),
    ...state.courses.map(c => el("option", {value: c.id, textContent: c.name})));
  sel.value = current;
  fill("overdue", state.overdue);
  fill("upcoming", state.upcoming);
  fill("incomplete", state.assignments.filter(a => !a.completed));
  fill("completed", state.assignments.filter(a => a.completed));
}

async function refresh() { state = await api("GET", "/api/data"); render(); }

async function act(fn) {
  try { await fn(); showError(null); } catch (e) { showError(e); }
  await refresh();
}

function startEdit(a) {
  const f = $("#assignment-form");
  f.elements.id.value = a.id; f.elements.title.value = a.title; f.elements.course_id.value = a.course_id;
  f.elements.due_date.value = a.due_date; f.elements.description.value = a.description;
  $("#form-title").textContent = "Edit assignment";
  $("#save-btn").textContent = "Save changes";
  $("#cancel-btn").hidden = false;
  f.scrollIntoView({behavior: "smooth"});
}

function resetForm() {
  const f = $("#assignment-form");
  f.reset(); f.elements.id.value = "";
  $("#form-title").textContent = "Add an assignment";
  $("#save-btn").textContent = "Add assignment";
  $("#cancel-btn").hidden = true;
}

$("#cancel-btn").onclick = resetForm;

$("#course-form").onsubmit = (ev) => {
  ev.preventDefault();
  const f = ev.target;
  act(async () => { await api("POST", "/api/courses", {name: f.elements.name.value});
                    f.reset(); });
};

$("#assignment-form").onsubmit = (ev) => {
  ev.preventDefault();
  const f = ev.target;
  const body = {title: f.elements.title.value, description: f.elements.description.value,
                course_id: Number(f.elements.course_id.value) || null,
                due_date: f.elements.due_date.value};
  act(async () => {
    if (f.elements.id.value) await api("PUT", `/api/assignments/${f.elements.id.value}`, body);
    else await api("POST", "/api/assignments", body);
    resetForm();
  });
};

refresh().catch(showError);
</script>
</body>
</html>
"""


if __name__ == "__main__":
    main()
