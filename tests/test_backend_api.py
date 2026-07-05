import unittest

from fastapi.testclient import TestClient

from backend.app.main import app


class BackendApiTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_health(self):
        response = self.client.get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_policy_endpoint(self):
        response = self.client.get("/api/policy")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertFalse(payload["live_trading_enabled"])
        self.assertTrue(payload["manual_approval_required"])
        self.assertEqual(payload["benchmark_weights"]["SPY"], 0.5)

    def test_localhost_cors_preflight_allows_127_frontend(self):
        response = self.client.options(
            "/api/policy",
            headers={
                "Origin": "http://127.0.0.1:3000",
                "Access-Control-Request-Method": "GET",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["access-control-allow-origin"], "http://127.0.0.1:3000")

    def test_dashboard_endpoint_returns_synthetic_json(self):
        response = self.client.get("/api/dashboard?use_real_data=false")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertFalse(payload["is_real_data"])
        self.assertEqual(len(payload["summary"]), 6)
        self.assertIn("ETF Momentum Rotation", payload["equity_curves"])
        self.assertIn("70/30 Combined Policy", payload["drawdowns"])
        self.assertIn("SPY", payload["prices"])
        self.assertIn("AAPL", payload["prices"])
        self.assertIn("SPY", payload["sample_etfs"])
        self.assertIn("AAPL", payload["sample_stocks"])

    def test_strategy_detail_endpoint_returns_trades(self):
        response = self.client.get("/api/strategies/etf-momentum-rotation?use_real_data=false")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["summary"]["name"], "ETF Momentum Rotation")
        self.assertGreater(len(payload["trade_history"]), 0)
        self.assertIn("latest_weights", payload)

    def test_strategy_trades_endpoint_uses_strategy_ids(self):
        response = self.client.get("/api/strategies/50-50-spy-qqq/trades?use_real_data=false")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertGreater(len(payload), 0)
        self.assertEqual({row["action"] for row in payload}, {"Entry", "Mark"})

    def test_missing_strategy_returns_404(self):
        response = self.client.get("/api/strategies/not-a-strategy?use_real_data=false")

        self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main()
