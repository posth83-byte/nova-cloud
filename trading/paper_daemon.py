"""Continuous paper-only market watcher.

Polls public Kraken data, processes each completed hourly candle once, and
persists paper portfolio state. This is not a live trading service.
"""
from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path

from market_scanner import scan
from paper_engine import PaperBroker
from paper_strategy import run_cycle
from supabase_state import SupabaseStateStore


def build_broker(args: argparse.Namespace) -> PaperBroker:
    config = json.loads(Path(args.config).read_text(encoding="utf-8"))
    return PaperBroker(
        state_path=args.state_path,
        starting_cash=args.starting_cash,
        quote_currency=config["quote_currency"],
        allowed_symbols=tuple(config["allowed_symbols"]),
        max_risk_per_trade_pct=config["max_risk_per_trade_pct"],
        max_daily_drawdown_pct=config["max_daily_drawdown_pct"],
        fee_rate=config["fee_rate"],
        slippage_rate=config["slippage_rate"],
        minimum_notional=config["minimum_notional"],
        minimum_order_sizes=config.get("minimum_order_sizes", {}),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="JARVIS continuous paper watcher")
    parser.add_argument("--starting-cash", type=float, required=True, help="Initial paper balance in EUR")
    parser.add_argument("--state-path", default="trading/paper-state.json")
    parser.add_argument("--state-backend", choices=("file", "supabase"), default="file")
    parser.add_argument("--config", default="trading/paper_config.json")
    parser.add_argument("--interval-seconds", type=int, default=300)
    parser.add_argument("--once", action="store_true", help="Run a single scan and exit")
    args = parser.parse_args()
    if args.interval_seconds < 60:
        parser.error("--interval-seconds must be at least 60")

    store = None
    if args.state_backend == "supabase":
        store = SupabaseStateStore.from_env()
        persisted_state = store.load()
        if persisted_state is not None:
            state_file = Path(args.state_path)
            state_file.parent.mkdir(parents=True, exist_ok=True)
            state_file.write_text(json.dumps(persisted_state), encoding="utf-8")

    broker = build_broker(args)
    if store is not None and persisted_state is None:
        store.save(broker.state)

    while True:
        try:
            open_symbols = tuple(broker.state["positions"])
            market = scan(required_symbols=open_symbols)
            # Only normally filtered markets can become new entry candidates.
            broker.allowed_symbols = tuple(
                item["symbol"] for item in market["results"]
                if not item.get("monitor_only", False)
            )
            actions = run_cycle(broker, market["results"])
            if store is not None:
                store.save(broker.state)
            marks = {
                item["symbol"]: item.get("mark_price_eur") or item["last_price_eur"]
                for item in market["results"]
                if item.get("mark_price_eur") is not None or item.get("last_price_eur") is not None
            }
            record = {
                "observed_at": datetime.now(timezone.utc).isoformat(),
                "market_generated_at": market["generated_at"],
                "market_errors": market["errors"],
                "actions": actions,
                "portfolio": broker.snapshot(marks),
                "live_orders_enabled": False,
            }
            print(json.dumps(record), flush=True)
        except Exception as exc:
            print(json.dumps({
                "observed_at": datetime.now(timezone.utc).isoformat(),
                "mode": "paper",
                "error": str(exc)[:300],
                "live_orders_enabled": False,
            }), flush=True)
        if args.once:
            return 0
        time.sleep(args.interval_seconds)


if __name__ == "__main__":
    raise SystemExit(main())
