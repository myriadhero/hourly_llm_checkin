import unittest

from bot.llm import (
    NotEventsError,
    UnclearEventError,
    normalize_activities,
    normalize_activity,
)


class NormalizeActivityTests(unittest.TestCase):
    def test_parse_string_numbers(self) -> None:
        payload = {
            "description": "Deep work on project",
            "duration_minutes": "45",
            "quadrant": "2",
            "tags": ["work", "focus"],
            "when": "2024-01-01 10:00",
        }
        activity = normalize_activity(payload)
        self.assertEqual(activity.description, "Deep work on project")
        self.assertEqual(activity.duration_minutes, 45.0)
        self.assertEqual(activity.quadrant, 2)
        self.assertEqual(activity.tags, ["work", "focus"])
        self.assertEqual(activity.when, "2024-01-01 10:00")

    def test_parse_comma_tags(self) -> None:
        payload = {
            "description": "Planning session",
            "duration_minutes": 30,
            "quadrant": 2,
            "tags": "work,planning, focus",
        }
        activity = normalize_activity(payload)
        self.assertEqual(activity.tags, ["work", "planning", "focus"])

    def test_normalize_activity_list(self) -> None:
        payload = [
            {
                "description": "Email triage",
                "duration_minutes": 15,
                "quadrant": 3,
                "tags": ["work"],
            },
            {
                "description": "Deep work block",
                "duration_minutes": "60",
                "quadrant": "2",
                "tags": "focus,work",
            },
        ]
        activities = normalize_activities(payload)
        self.assertEqual(len(activities), 2)
        self.assertEqual(activities[0].quadrant, 3)
        self.assertEqual(activities[1].duration_minutes, 60.0)

    def test_normalize_not_events(self) -> None:
        payload = {"error": "notEvents", "message": "Thanks!"}
        with self.assertRaises(NotEventsError) as context:
            normalize_activities(payload)
        self.assertIn("Thanks", str(context.exception))

    def test_normalize_unclear_event(self) -> None:
        payload = {
            "error": "unclearEvent",
            "message": "Can you clarify what you did and for how long?",
        }
        with self.assertRaises(UnclearEventError) as context:
            normalize_activities(payload)
        self.assertIn("clarify", str(context.exception))


if __name__ == "__main__":
    unittest.main()
