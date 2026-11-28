import unittest
from datetime import datetime, timezone
from decimal import Decimal

from trading.paper_engine import (
    PaperTradingError, activate_emergency_stop, apply_paper_trade,
    create_initial_state, portfolio_snapshot, set_paper_enabled,
)


class PaperTradingEngineTests(unittest.TestCase):
    def setUp(self):
        self.state = set_paper_enabled(create_initial_state("200"), True)
        self.now = datetime(2026, 11, 26, 12, 0, tzinfo=timezone.utc)

    def test_starts_with_200_sek_and_no_live_capability(self):
        state = create_initial_state("200")
        snapshot = portfolio_snapshot(state)
        self.assertEqual(snapshot["cash"], "200.00")
        self.assertFalse(snapshot["paper_enabled"])
        self.assertFalse(snapshot["orders_enabled"])
        self.assertFalse(snapshot["withdrawals_enabled"])

    def test_rejects_trade_when_paper_mode_disabled(self):
        with self.assertRaises(PaperTradingError):
            apply_paper_trade(create_initial_state("200"), symbol="XBT/EUR",
                              side="buy", quantity="0.001", price_sek="1000000",
                              timestamp=self.now)

    def test_buy_applies_fee_and_slippage_and_reduces_cash(self):
        state = apply_paper_trade(
            self.state, symbol="XBT/EUR", side="buy", quantity="0.00001",
            price_sek="1000000", timestamp=self.now,
        )
        self.assertLess(Decimal(state["cash"]), Decimal("200"))
        self.assertEqual(len(state["trades"]), 1)
        self.assertEqual(state["trades"][0]["mode"], "paper_only")
        self.assertIn("XBT/EUR", state["positions"])

    def test_allows_one_qualifying_trade_to_use_almost_all_200_sek(self):
        quantity = Decimal("199.90") / (Decimal("1000000") * Decimal("1.0015") * Decimal("1.004"))
        bought = apply_paper_trade(
            self.state, symbol="XBT/EUR", side="buy", quantity=str(quantity),
            price_sek="1000000", timestamp=self.now,
        )
        self.assertLess(Decimal(bought["cash"]), Decimal("0.20"))
        self.assertGreater(Decimal(bought["cash"]), Decimal("0"))
        self.assertEqual(bought["risk"]["max_trade_pct"], "1.00")

    def test_trade_is_allowed_after_more_than_two_percent_daily_loss(self):
        state = dict(self.state)
        state["cash"] = "95.00"
        state["day_key"] = self.now.date().isoformat()
        state["day_start_equity"] = "100.00"
        state["peak_equity"] = "100.00"
        traded = apply_paper_trade(
            state, symbol="XBT/EUR", side="buy", quantity="0.000001",
            price_sek="1000000", timestamp=self.now,
        )
        self.assertIn("XBT/EUR", traded["positions"])
        self.assertNotIn("daily_loss_limit_pct", traded["risk"])

    def test_rejects_oversized_order(self):
        with self.assertRaises(PaperTradingError):
            apply_paper_trade(
                self.state, symbol="XBT/EUR", side="buy", quantity="0.001",
                price_sek="1000000", timestamp=self.now,
            )

    def test_cannot_sell_more_than_position(self):
        with self.assertRaises(PaperTradingError):
            apply_paper_trade(
                self.state, symbol="XBT/EUR", side="sell", quantity="0.001",
                price_sek="1000000", timestamp=self.now,
            )

    def test_emergency_stop_disables_paper_trading(self):
        stopped = activate_emergency_stop(self.state, "test")
        self.assertTrue(stopped["emergency_stop"])
        self.assertFalse(stopped["paper_enabled"])
        with self.assertRaises(PaperTradingError):
            set_paper_enabled(stopped, True)

    def test_requires_explicit_sek_price_for_open_positions(self):
        bought = apply_paper_trade(
            self.state, symbol="XBT/EUR", side="buy", quantity="0.00001",
            price_sek="1000000", timestamp=self.now,
        )
        with self.assertRaises(PaperTradingError):
            portfolio_snapshot(bought)

    def test_sell_records_realized_profit_or_loss(self):
        bought = apply_paper_trade(
            self.state, symbol="XBT/EUR", side="buy", quantity="0.00001",
            price_sek="1000000", timestamp=self.now,
        )
        sold = apply_paper_trade(
            bought, symbol="XBT/EUR", side="sell", quantity="0.00001",
            price_sek="1100000", timestamp=self.now,
            marks_sek={"XBT/EUR": "1100000"},
        )
        self.assertNotEqual(sold["realized_pnl"], "0.00")
        self.assertNotIn("XBT/EUR", sold["positions"])


if __name__ == "__main__":
    unittest.main()
