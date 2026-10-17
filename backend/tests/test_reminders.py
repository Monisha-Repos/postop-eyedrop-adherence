"""Run from backend/:  python -m unittest discover -s tests -t ."""
import unittest

from app import reminders
from app.reminders import ReminderContext

MEDS = ["Moxifloxacin", "Prednisolone", "Ketorolac"]


def ctx(flag: str) -> ReminderContext:
    return ReminderContext(
        first_name="Ann", flag=flag, medication="Prednisolone", drops=1, eye="left",
        time_label="2:00 PM", minutes_off=45, next_label="Ketorolac at 4:00 PM", all_medications=MEDS,
    )


class Instructions(unittest.TestCase):
    def test_due_instruction_states_facts(self):
        self.assertEqual(reminders.instruction_for(ctx("due")), "It's time for your Prednisolone: 1 drop in your left eye.")

    def test_every_flag_has_a_template(self):
        for flag in reminders.FLAGS:
            self.assertTrue(reminders.instruction_for(ctx(flag)))


class Fallbacks(unittest.TestCase):
    def test_all_fallback_lines_pass_the_checks(self):
        for flag in reminders.FLAGS:
            for humor in ("full", "mild", "off"):
                c = ctx(flag)
                rem = reminders.build_reminder(c, humor, use_gemini=False)
                checks = reminders.script_checks(rem, c, humor)
                self.assertTrue(all(checks.values()), f"{flag}/{humor}: {checks}")


class WrapperChecks(unittest.TestCase):
    def test_rejects_medication_and_numbers(self):
        problems = reminders.wrapper_problems("Hi Ann, Prednisolone time!", "Take 2 drops.", ctx("due"), "full")
        self.assertTrue(any("medication" in p for p in problems))
        self.assertTrue(any("number" in p for p in problems))

    def test_rejects_praise_after_missed(self):
        problems = reminders.wrapper_problems("Great job, Ann!", "See you soon.", ctx("missed"), "full")
        self.assertTrue(any(p.startswith("praise") for p in problems))

    def test_rejects_medical_advice(self):
        problems = reminders.wrapper_problems("Hi Ann.", "If it stings, skip the next one.", ctx("due"), "full")
        self.assertTrue(any(p.startswith("medical") for p in problems))


if __name__ == "__main__":
    unittest.main()
