import unittest

from trading_agent.config import load_policy
from trading_agent.domain import AssetType


class PolicyConfigTests(unittest.TestCase):
    def test_loads_default_policy(self):
        policy = load_policy()

        self.assertEqual(policy.initial_account_equity, 50000.0)
        self.assertFalse(policy.live_trading_enabled)
        self.assertTrue(policy.manual_approval_required)
        self.assertIn(AssetType.ETF, policy.allowed_asset_types)
        self.assertIn("TQQQ", policy.blocked_symbols)
        self.assertEqual(policy.benchmark_weights["SPY"], 0.5)
        self.assertEqual(policy.benchmark_weights["QQQ"], 0.5)


if __name__ == "__main__":
    unittest.main()

