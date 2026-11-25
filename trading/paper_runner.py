"""Run one paper-trading cycle using public Kraken market data.

Example:
  python trading/paper_runner.py --starting-cash 470 --state-path trading/paper-state.json

starting-cash must be in EUR when trading BTC/EUR and ETH/EUR. Convert the
user's SEK budget with a current FX rate before first initialization.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from market_scanner import scan
from paper_engine import PaperBroker
from paper_strategy import run_cycle


def main() -> int:
    parser = argparse.ArgumentParser(description="JARVIS paper trading cycle")
    parser.add_argument("--starting-cash", type=float, required=True, help="Initial paper cash in quote currency")
    parser.add_argument("--state-path", default="trading/paper-state.json")
    parser.add_argument("--config", default="trading/paper_config.json")
    args = parser.parse_args()

    config = json.loads(Path(args.config).read_text(encoding="utf-8"))
    broker = PaperBroker(
        state_path=args.state_path,
        starting_cash=args.starting_cash,
        quote_currency=config["quote_currency"],
        allowed_symbols=tuple(config["allowed_symbols"]),
        max_risk_per_trade_pct=config["max_risk_per_trade_pct"],
        max_daily_drawdown_pct=config["max_daily_drawdown_pct"],
        fee_rate=config["fee_rate"],
        slippage_rate=config["slippage_rate"],
        minimum_notional=config["minimum_notional"],
    )
    market = scan()
    actions = run_cycle(broker, market["results"])
    marks = {
        item["symbol"]: item["last_price_eur"]
        for item in market["results"]
        if item.get("last_price_eur") is not None
    }
    output = {
        "mode": "paper",
        "strategy": "ema_trend_rsi_volume_v1",
        "market_data_generated_at": market["generated_at"],
        "market_errors": market["errors"],
        "actions": actions,
        "portfolio": broker.snapshot(marks),
        "live_orders_enabled": False,
    }
    print(json.dumps(output, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
