"""Run from backend/:  python -m unittest discover -s tests -t ."""
import unittest
from datetime import date, datetime, time, timedelta, timezone

from app import rules

TZ = timezone(timedelta(hours=-4))  # fixed offset so tests don't need tzdata
NOON = datetime(2026, 10, 17, 12, 0, tzinfo=TZ)


def at(minutes: int) -> datetime:
    return NOON + timedelta(minutes=minutes)


class ClassifyLift(unittest.TestCase):
    def test_on_time_window_is_inclusive(self):
        self.assertEqual(rules.classify_lift(NOON, at(30)), "on_time")
        self.assertEqual(rules.classify_lift(NOON, at(-30)), "on_time")

    def test_late_and_early(self):
        self.assertEqual(rules.classify_lift(NOON, at(31)), "late")
        self.assertEqual(rules.classify_lift(NOON, at(-31)), "early")


class ChooseDose(unittest.TestCase):
    def test_prefers_oldest_overdue_dose(self):
        pending = [rules.PendingDose(1, at(-120)), rules.PendingDose(2, at(60))]
        self.assertEqual(rules.choose_dose(pending, NOON).id, 1)

    def test_falls_back_to_upcoming_dose(self):
        pending = [rules.PendingDose(2, at(60))]
        self.assertEqual(rules.choose_dose(pending, NOON).id, 2)

    def test_ignores_doses_past_missed_window(self):
        pending = [rules.PendingDose(1, at(-181))]
        self.assertIsNone(rules.choose_dose(pending, NOON))

    def test_ignores_doses_too_far_ahead(self):
        pending = [rules.PendingDose(2, at(121))]
        self.assertIsNone(rules.choose_dose(pending, NOON))

    def test_staggered_doses_match_in_order(self):
        pending = [rules.PendingDose(1, at(0)), rules.PendingDose(2, at(5))]
        self.assertEqual(rules.choose_dose(pending, at(1)).id, 1)
        self.assertEqual(rules.choose_dose(pending[1:], at(6)).id, 2)


class DueAndMissed(unittest.TestCase):
    def test_due_until_missed(self):
        self.assertFalse(rules.is_due(NOON, at(-1)))
        self.assertTrue(rules.is_due(NOON, at(0)))
        self.assertTrue(rules.is_due(NOON, at(179)))
        self.assertFalse(rules.is_due(NOON, at(180)))
        self.assertTrue(rules.is_missed(NOON, at(180)))


class PlannedDoses(unittest.TestCase):
    def setUp(self):
        d0, d6 = date(2026, 10, 15), date(2026, 10, 21)
        self.steps = [
            rules.Step(1, d0, d6, (time(8), time(20))),
            rules.Step(2, d0, d6, (time(8),)),
            rules.Step(3, date(2026, 10, 22), date(2026, 10, 28), (time(9),)),
        ]

    def test_same_time_drops_are_staggered(self):
        slots = rules.planned_doses(self.steps, date(2026, 10, 17), TZ)
        times = [(sid, dt.strftime("%H:%M")) for sid, dt in slots]
        self.assertEqual(times, [(1, "08:00"), (2, "08:05"), (1, "20:00")])

    def test_steps_outside_their_dates_are_skipped(self):
        slots = rules.planned_doses(self.steps, date(2026, 10, 22), TZ)
        self.assertEqual([sid for sid, _ in slots], [3])


if __name__ == "__main__":
    unittest.main()
