import unittest
from datetime import datetime, timezone

from bot.time_utils import is_daytime, seconds_until_next_hour


class TimeUtilsTests(unittest.TestCase):
    def test_is_daytime_wraparound(self) -> None:
        late = datetime(2024, 1, 1, 23, 0, tzinfo=timezone.utc)
        midday = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
        self.assertTrue(is_daytime(late, 22, 6))
        self.assertFalse(is_daytime(midday, 22, 6))

    def test_seconds_until_next_hour(self) -> None:
        now = datetime(2024, 1, 1, 10, 30, tzinfo=timezone.utc)
        self.assertAlmostEqual(seconds_until_next_hour(now), 1800.0, places=4)


if __name__ == "__main__":
    unittest.main()
