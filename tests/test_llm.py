import unittest

from bot.llm import normalize_activity


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


if __name__ == "__main__":
    unittest.main()
