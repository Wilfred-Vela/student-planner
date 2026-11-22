"""Tests for the HTTP layer in app.py: routing logic and that the server runs."""

import ast
import json
import os
import sys
import tempfile
import threading
import unittest
import urllib.request
from datetime import date
from pathlib import Path

import app
from planner import Planner

ROOT = Path(__file__).resolve().parent.parent
TODAY = date(2026, 11, 21)


class HandleTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.p = Planner(os.path.join(self.tmp.name, "data.json"))

    def tearDown(self):
        self.tmp.cleanup()

    def call(self, method, path, body=None):
        return app.handle(self.p, method, path, body, TODAY)

    def make_course(self, name="CSC 299"):
        return self.call("POST", "/api/courses", {"name": name})[1]

    def make_assignment(self, due="2026-11-25", title="HW1"):
        cid = self.make_course()["id"] if not self.p.list_courses() else \
            self.p.list_courses()[0]["id"]
        body = {"title": title, "description": "d", "course_id": cid,
                "due_date": due}
        return self.call("POST", "/api/assignments", body)


class TestRunsLocally(unittest.TestCase):
    def test_R1_only_standard_library_imports(self):
        local = {"planner", "app"}
        for name in ["app.py", "planner.py"]:
            tree = ast.parse((ROOT / name).read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    mods = [a.name for a in node.names]
                elif isinstance(node, ast.ImportFrom):
                    mods = [node.module or ""]
                else:
                    continue
                for m in mods:
                    top = m.split(".")[0]
                    with self.subTest(file=name, module=m):
                        self.assertTrue(
                            top in sys.stdlib_module_names or top in local
                        )

    def test_R1_server_serves_page_and_api_over_http(self):
        with tempfile.TemporaryDirectory() as tmp:
            planner = Planner(os.path.join(tmp, "data.json"))
            server = app.make_server(planner, "127.0.0.1", 0)
            port = server.server_address[1]
            t = threading.Thread(target=server.serve_forever, daemon=True)
            t.start()
            try:
                base = f"http://127.0.0.1:{port}"
                with urllib.request.urlopen(base + "/") as r:
                    self.assertEqual(r.status, 200)
                    self.assertIn("text/html", r.headers["Content-Type"])
                req = urllib.request.Request(
                    base + "/api/courses", method="POST",
                    data=json.dumps({"name": "CSC 299"}).encode(),
                    headers={"Content-Type": "application/json"},
                )
                with urllib.request.urlopen(req) as r:
                    self.assertEqual(r.status, 201)
                with urllib.request.urlopen(base + "/api/data") as r:
                    data = json.load(r)
                self.assertEqual(data["courses"][0]["name"], "CSC 299")
            finally:
                server.shutdown()
                server.server_close()

    def test_R1_default_binds_to_localhost(self):
        self.assertEqual(app.DEFAULT_HOST, "127.0.0.1")


class TestHandle(HandleTestCase):
    def test_R1_root_returns_html(self):
        status, body = self.call("GET", "/")
        self.assertEqual(status, 200)
        self.assertIsInstance(body, str)
        self.assertIn("<html", body.lower())

    def test_R2_post_course(self):
        status, body = self.call("POST", "/api/courses", {"name": "CSC 299"})
        self.assertEqual((status, body["name"]), (201, "CSC 299"))

    def test_R2_post_bad_course_is_400(self):
        status, body = self.call("POST", "/api/courses", {"name": ""})
        self.assertEqual(status, 400)
        self.assertIn("error", body)

    def test_R3_R4_R5_post_assignment(self):
        status, body = self.make_assignment()
        self.assertEqual(status, 201)
        self.assertEqual(body["title"], "HW1")
        self.assertEqual(body["due_date"], "2026-11-25")

    def test_R5_post_assignment_bad_date_is_400(self):
        self.assertEqual(self.make_assignment(due="soon")[0], 400)

    def test_R6_get_data_lists_everything(self):
        self.make_assignment(title="A")
        self.make_assignment(title="B")
        status, body = self.call("GET", "/api/data")
        self.assertEqual(status, 200)
        self.assertEqual(body["today"], "2026-11-21")
        self.assertEqual([a["title"] for a in body["assignments"]], ["A", "B"])
        self.assertEqual(len(body["courses"]), 1)

    def test_R6_R9_each_assignment_has_status(self):
        self.make_assignment(due="2026-11-01")
        body = self.call("GET", "/api/data")[1]
        self.assertEqual(body["assignments"][0]["status"], "overdue")

    def test_R7_put_completed(self):
        aid = self.make_assignment()[1]["id"]
        status, body = self.call("PUT", f"/api/assignments/{aid}",
                                 {"completed": True})
        self.assertEqual((status, body["completed"]), (200, True))

    def test_R8_put_edit(self):
        aid = self.make_assignment()[1]["id"]
        status, body = self.call("PUT", f"/api/assignments/{aid}",
                                 {"title": "New"})
        self.assertEqual((status, body["title"]), (200, "New"))

    def test_R8_delete(self):
        aid = self.make_assignment()[1]["id"]
        self.assertEqual(self.call("DELETE", f"/api/assignments/{aid}"),
                         (200, {"deleted": aid}))
        self.assertEqual(self.call("GET", "/api/data")[1]["assignments"], [])

    def test_R8_unknown_assignment_is_404(self):
        self.assertEqual(self.call("DELETE", "/api/assignments/9")[0], 404)
        self.assertEqual(self.call("PUT", "/api/assignments/9", {})[0], 404)

    def test_R8_non_numeric_id_is_404(self):
        self.assertEqual(self.call("DELETE", "/api/assignments/abc")[0], 404)

    def test_R10_get_data_has_upcoming_and_overdue(self):
        self.make_assignment(due="2026-11-20", title="Late")
        self.make_assignment(due="2026-11-23", title="Soon")
        body = self.call("GET", "/api/data")[1]
        self.assertEqual([a["title"] for a in body["overdue"]], ["Late"])
        self.assertEqual([a["title"] for a in body["upcoming"]], ["Soon"])

    def test_R12_get_data_courses_have_incomplete_count(self):
        aid = self.make_assignment(title="A")[1]["id"]
        self.make_assignment(title="B")
        self.call("PUT", f"/api/assignments/{aid}", {"completed": True})
        self.make_course("MAT 150")
        courses = self.call("GET", "/api/data")[1]["courses"]
        self.assertEqual([(c["name"], c["incomplete_count"]) for c in courses],
                         [("CSC 299", 1), ("MAT 150", 0)])

    def test_R1_unknown_route_is_404(self):
        self.assertEqual(self.call("GET", "/nope")[0], 404)

    def test_R1_non_object_body_is_400(self):
        self.assertEqual(self.call("POST", "/api/courses", ["x"])[0], 400)


if __name__ == "__main__":
    unittest.main()
