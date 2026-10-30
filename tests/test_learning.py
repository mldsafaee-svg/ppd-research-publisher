import datetime as dt
import unittest
from learning import due, next_lesson

class LearningTests(unittest.TestCase):
    def test_first_lesson_is_due(self):
        self.assertTrue(due({}, dt.date(2026, 10, 30)))
    def test_two_per_day_limit(self):
        self.assertTrue(due({"last_date":"2026-10-30", "daily_count":1}, dt.date(2026, 10, 30)))
        self.assertFalse(due({"last_date":"2026-10-30", "daily_count":2}, dt.date(2026, 10, 30)))
        self.assertTrue(due({"last_date":"2026-10-30", "daily_count":2}, dt.date(2026, 10, 31)))
    def test_stops_after_last_lesson(self):
        self.assertIsNone(next_lesson([{"topic":"A"}], {"next_index":1}, dt.date(2026,10,30)))
