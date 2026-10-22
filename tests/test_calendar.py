import unittest
from datetime import date

from trading_agent.calendar import business_days_between


class BusinessDaysBetweenTests(unittest.TestCase):
    def test_same_day_is_zero(self):
        self.assertEqual(business_days_between(date(2026, 7, 6), date(2026, 7, 6)), 0)
        self.assertEqual(business_days_between(date(2026, 7, 4), date(2026, 7, 4)), 0)

    def test_next_weekday_is_one(self):
        self.assertEqual(business_days_between(date(2026, 7, 6), date(2026, 7, 7)), 1)

    def test_full_week(self):
        # Monday -> next Monday counts Tue..Fri plus the following Monday.
        self.assertEqual(business_days_between(date(2026, 7, 6), date(2026, 7, 13)), 5)

    def test_start_is_excluded_and_end_is_included(self):
        # Friday -> Monday: only Monday counts.
        self.assertEqual(business_days_between(date(2026, 7, 10), date(2026, 7, 13)), 1)

    def test_weekend_only_span_is_zero(self):
        # Friday -> Sunday.
        self.assertEqual(business_days_between(date(2026, 7, 10), date(2026, 7, 12)), 0)
        # Saturday -> Sunday.
        self.assertEqual(business_days_between(date(2026, 7, 11), date(2026, 7, 12)), 0)

    def test_weekend_start(self):
        # Saturday -> Monday.
        self.assertEqual(business_days_between(date(2026, 7, 11), date(2026, 7, 13)), 1)

    def test_reversed_range_is_negative(self):
        self.assertEqual(business_days_between(date(2026, 7, 13), date(2026, 7, 6)), -5)
        self.assertEqual(business_days_between(date(2026, 7, 7), date(2026, 7, 6)), -1)

    def test_antisymmetric(self):
        start = date(2026, 1, 1)
        for offset in range(0, 40, 3):
            end = date.fromordinal(start.toordinal() + offset)
            with self.subTest(end=end):
                self.assertEqual(
                    business_days_between(start, end),
                    -business_days_between(end, start),
                )

    def test_spans_year_and_leap_day(self):
        # 2028 is a leap year; 2028-02-29 is a Tuesday.
        self.assertEqual(business_days_between(date(2028, 2, 28), date(2028, 3, 1)), 2)
        # Wed 2025-12-31 -> Fri 2026-01-02.
        self.assertEqual(business_days_between(date(2025, 12, 31), date(2026, 1, 2)), 2)

    def test_full_year(self):
        # 2026 has 261 weekdays; counting from 2025-12-31 includes all of them.
        self.assertEqual(business_days_between(date(2025, 12, 31), date(2026, 12, 31)), 261)

    def test_market_holidays_are_counted(self):
        # Documented limitation: holidays are ignored (2026-07-03 is a market
        # holiday but still counted as a business day).
        self.assertEqual(business_days_between(date(2026, 7, 2), date(2026, 7, 3)), 1)


if __name__ == "__main__":
    unittest.main()
