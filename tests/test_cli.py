import contextlib
import io
import unittest
from unittest import mock

from trading_agent import cli


def _run_demo_summary(**kwargs):
    stdout, stderr = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        code = cli.demo_summary(**kwargs)
    return code, stdout.getvalue(), stderr.getvalue()


@mock.patch(
    "trading_agent.demo.load_yahoo_close_prices",
    side_effect=RuntimeError("Install yfinance with: python3 -m pip install -e '.[dashboard]'"),
)
class DemoSummaryCliTests(unittest.TestCase):
    def test_refresh_fails_loudly_when_real_data_unavailable(self, _loader):
        code, stdout, stderr = _run_demo_summary(use_real_data=True, refresh_data=True)

        self.assertEqual(code, 1)
        self.assertIn("Install yfinance", stderr)
        self.assertNotIn("synthetic", stdout.lower())

    def test_default_run_warns_when_falling_back_to_synthetic(self, _loader):
        code, stdout, stderr = _run_demo_summary(use_real_data=True, refresh_data=False)

        self.assertEqual(code, 0)
        self.assertIn("SYNTHETIC", stderr)
        self.assertIn("Deterministic synthetic sample prices", stdout)

    def test_explicit_synthetic_mode_is_quiet(self, loader):
        code, stdout, stderr = _run_demo_summary(use_real_data=False, refresh_data=False)

        self.assertEqual(code, 0)
        self.assertEqual(stderr, "")
        loader.assert_not_called()


if __name__ == "__main__":
    unittest.main()
