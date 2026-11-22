"""Logic tests for planner.py. Each test name carries its requirement ID."""

import json
import os
import tempfile
import unittest
from datetime import date

from planner import Planner

TODAY = date(2026, 11, 21)


class PlannerTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.tmp.name, "data.json")
        self.p = Planner(self.path)
        self.course = self.p.add_course("CSC 299")

    def tearDown(self):
        self.tmp.cleanup()

    def add(self, title="HW1", due="2026-11-25", **kw):
        return self.p.add_assignment(
            title=title,
            description=kw.get("description", ""),
            course_id=kw.get("course_id", self.course["id"]),
            due_date=due,
        )


class TestCourses(PlannerTestCase):
    def test_R2_add_course(self):
        c = self.p.add_course("MAT 150")
        self.assertEqual(c["name"], "MAT 150")
        self.assertIn(c, self.p.list_courses())

    def test_R2_course_name_is_trimmed(self):
        self.assertEqual(self.p.add_course("  HIS 101 ")["name"], "HIS 101")

    def test_R2_blank_course_name_rejected(self):
        with self.assertRaises(ValueError):
            self.p.add_course("   ")

    def test_R2_duplicate_course_name_rejected(self):
        with self.assertRaises(ValueError):
            self.p.add_course("csc 299")

    def test_R2_course_ids_are_unique(self):
        c2 = self.p.add_course("MAT 150")
        self.assertNotEqual(c2["id"], self.course["id"])


class TestAddAssignment(PlannerTestCase):
    def test_R3_add_assignment_with_title_and_description(self):
        a = self.add(title="Essay", description="1500 words on X")
        self.assertEqual(a["title"], "Essay")
        self.assertEqual(a["description"], "1500 words on X")
        self.assertFalse(a["completed"])

    def test_R3_description_may_be_empty(self):
        self.assertEqual(self.add()["description"], "")

    def test_R3_blank_title_rejected(self):
        with self.assertRaises(ValueError):
            self.add(title="  ")

    def test_R4_assignment_belongs_to_course(self):
        a = self.add()
        self.assertEqual(a["course_id"], self.course["id"])
        self.assertEqual(self.p.list_assignments()[0]["course_name"], "CSC 299")

    def test_R4_unknown_course_rejected(self):
        with self.assertRaises(ValueError):
            self.add(course_id=999)

    def test_R4_missing_course_rejected(self):
        with self.assertRaises(ValueError):
            self.add(course_id=None)

    def test_R5_due_date_is_stored(self):
        self.assertEqual(self.add(due="2026-12-01")["due_date"], "2026-12-01")

    def test_R5_invalid_due_date_rejected(self):
        for bad in ["", "tomorrow", "2026-13-01", "12/01/2026", None]:
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                self.add(due=bad)


class TestViewAll(PlannerTestCase):
    def test_R6_list_all_assignments_sorted_by_due_date(self):
        other = self.p.add_course("MAT 150")
        self.add("Late", "2026-12-10")
        self.add("Early", "2026-11-01", course_id=other["id"])
        self.add("Mid", "2026-11-22")
        titles = [a["title"] for a in self.p.list_assignments()]
        self.assertEqual(titles, ["Early", "Mid", "Late"])

    def test_R6_list_includes_completed_and_incomplete(self):
        a = self.add("A")
        self.add("B")
        self.p.set_completed(a["id"], True)
        self.assertEqual(len(self.p.list_assignments()), 2)


class TestComplete(PlannerTestCase):
    def test_R7_mark_completed(self):
        a = self.add()
        self.assertTrue(self.p.set_completed(a["id"], True)["completed"])

    def test_R7_mark_incomplete_again(self):
        a = self.add()
        self.p.set_completed(a["id"], True)
        self.assertFalse(self.p.set_completed(a["id"], False)["completed"])

    def test_R7_unknown_id_raises_key_error(self):
        with self.assertRaises(KeyError):
            self.p.set_completed(42, True)


class TestEditDelete(PlannerTestCase):
    def test_R8_edit_assignment_fields(self):
        a = self.add()
        other = self.p.add_course("MAT 150")
        b = self.p.update_assignment(
            a["id"], title="HW1 v2", description="new", course_id=other["id"],
            due_date="2026-12-24",
        )
        self.assertEqual(
            (b["title"], b["description"], b["course_id"], b["due_date"]),
            ("HW1 v2", "new", other["id"], "2026-12-24"),
        )

    def test_R8_edit_partial_keeps_other_fields(self):
        a = self.add(title="Keep", description="d")
        b = self.p.update_assignment(a["id"], due_date="2026-12-01")
        self.assertEqual((b["title"], b["description"]), ("Keep", "d"))

    def test_R8_edit_validates_like_create(self):
        a = self.add()
        for fields in [{"title": ""}, {"due_date": "nope"}, {"course_id": 999}]:
            with self.subTest(fields=fields), self.assertRaises(ValueError):
                self.p.update_assignment(a["id"], **fields)
        self.assertEqual(self.p.get_assignment(a["id"])["title"], "HW1")

    def test_R8_edit_rejects_unknown_field(self):
        a = self.add()
        with self.assertRaises(ValueError):
            self.p.update_assignment(a["id"], id=77)

    def test_R8_delete_assignment(self):
        a = self.add()
        self.p.delete_assignment(a["id"])
        self.assertEqual(self.p.list_assignments(), [])

    def test_R8_delete_unknown_raises_key_error(self):
        with self.assertRaises(KeyError):
            self.p.delete_assignment(42)

    def test_R8_ids_not_reused_after_delete(self):
        a = self.add()
        self.p.delete_assignment(a["id"])
        self.assertNotEqual(self.add()["id"], a["id"])


class TestStatus(PlannerTestCase):
    def test_R9_filter_completed_and_incomplete(self):
        a = self.add("Done")
        self.add("Todo")
        self.p.set_completed(a["id"], True)
        done = [x["title"] for x in self.p.list_assignments(completed=True)]
        todo = [x["title"] for x in self.p.list_assignments(completed=False)]
        self.assertEqual((done, todo), (["Done"], ["Todo"]))

    def test_R9_status_labels(self):
        cases = {
            "2026-11-20": "overdue",
            "2026-11-21": "upcoming",
            "2026-11-28": "upcoming",
            "2026-11-29": "later",
        }
        for due, expected in cases.items():
            with self.subTest(due=due):
                a = self.add(due=due)
                self.assertEqual(Planner.status(a, TODAY), expected)
        done = self.p.set_completed(self.add(due="2026-01-01")["id"], True)
        self.assertEqual(Planner.status(done, TODAY), "completed")


class TestUpcomingOverdue(PlannerTestCase):
    def test_R10_overdue_is_incomplete_and_past_due(self):
        self.add("Past", "2026-11-20")
        self.add("Today", "2026-11-21")
        done = self.add("PastDone", "2026-11-01")
        self.p.set_completed(done["id"], True)
        self.assertEqual([a["title"] for a in self.p.overdue(TODAY)], ["Past"])

    def test_R10_upcoming_is_within_next_seven_days(self):
        self.add("Today", "2026-11-21")
        self.add("Week", "2026-11-28")
        self.add("TooFar", "2026-11-29")
        self.add("Past", "2026-11-20")
        done = self.add("SoonDone", "2026-11-22")
        self.p.set_completed(done["id"], True)
        self.assertEqual(
            [a["title"] for a in self.p.upcoming(TODAY)], ["Today", "Week"]
        )


class TestIncompleteCounts(PlannerTestCase):
    def test_R12_incomplete_count_per_course(self):
        other = self.p.add_course("MAT 150")
        empty = self.p.add_course("HIS 101")
        self.add("HW1")
        self.add("HW2")
        done = self.add("HW3")
        self.p.set_completed(done["id"], True)
        self.add("Quiz", course_id=other["id"])
        self.assertEqual(self.p.incomplete_counts(), {
            self.course["id"]: 2, other["id"]: 1, empty["id"]: 0})

    def test_R12_count_follows_completion_edit_and_delete(self):
        other = self.p.add_course("MAT 150")
        a = self.add("HW1")
        b = self.add("HW2")
        self.p.set_completed(a["id"], True)
        self.p.update_assignment(b["id"], course_id=other["id"])
        self.assertEqual(self.p.incomplete_counts(),
                         {self.course["id"]: 0, other["id"]: 1})
        self.p.set_completed(a["id"], False)
        self.p.delete_assignment(b["id"])
        self.assertEqual(self.p.incomplete_counts(),
                         {self.course["id"]: 1, other["id"]: 0})


class TestPersistence(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.tmp.name, "data.json")

    def tearDown(self):
        self.tmp.cleanup()

    def test_R11_data_survives_reopen(self):
        p = Planner(self.path)
        c = p.add_course("CSC 299")
        a = p.add_assignment("HW1", "desc", c["id"], "2026-11-25")
        p.set_completed(a["id"], True)

        reopened = Planner(self.path)
        self.assertEqual(reopened.list_courses(), p.list_courses())
        self.assertEqual(reopened.list_assignments(), p.list_assignments())

    def test_R11_edits_and_deletes_are_persisted(self):
        p = Planner(self.path)
        c = p.add_course("CSC 299")
        a = p.add_assignment("HW1", "", c["id"], "2026-11-25")
        b = p.add_assignment("HW2", "", c["id"], "2026-11-26")
        p.update_assignment(a["id"], title="HW1 edited")
        p.delete_assignment(b["id"])
        titles = [x["title"] for x in Planner(self.path).list_assignments()]
        self.assertEqual(titles, ["HW1 edited"])

    def test_R11_ids_continue_after_reopen(self):
        p = Planner(self.path)
        c = p.add_course("CSC 299")
        a = p.add_assignment("HW1", "", c["id"], "2026-11-25")
        p.delete_assignment(a["id"])
        a2 = Planner(self.path).add_assignment("HW2", "", c["id"], "2026-11-25")
        self.assertNotEqual(a2["id"], a["id"])

    def test_R11_file_is_plain_json(self):
        Planner(self.path).add_course("CSC 299")
        with open(self.path, encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(data["courses"][0]["name"], "CSC 299")

    def test_R11_missing_file_means_empty_planner(self):
        p = Planner(os.path.join(self.tmp.name, "nope", "data.json"))
        self.assertEqual((p.list_courses(), p.list_assignments()), ([], []))

    def test_R11_no_temp_files_left_behind(self):
        Planner(self.path).add_course("CSC 299")
        self.assertEqual(os.listdir(self.tmp.name), ["data.json"])


if __name__ == "__main__":
    unittest.main()
