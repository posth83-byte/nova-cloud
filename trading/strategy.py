"""Conservative, read-only strategy preview with verified EUR/SEK conversion.

This module produces candidates for human-reviewed paper simulation only.
It never submits orders or changes the paper ledger.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timezone
from typing import Any


class StrategyDataError(RuntimeError):
    """Market or FX data is unavailable or too stale for a preview."""


def fetch_eur_sek_rate() -> dict[str, Any]:
    query = urllib.parse.urlencode({"base": "EUR", "symbols": "SEK"})
    request = urllib.request.Request(
        "https://api.frankfurter.dev/v1/latest?" + query,
        headers={"User-Agent": "NOVA-Cloud-Trade-Preview/1.0"},
    )
    try:
        with urllib.request.urlopen(request, timeout=12) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise StrategyDataError("EUR/SEK-kursen kunde inte hämtas.") from exc
    try:
        rate = float(payload["rates"]["SEK"])
        rate_date = date.fromisoformat(payload["date"])
    except (KeyError, TypeError, ValueError) as exc:
        raise StrategyDataError("Valutakällan returnerade ett ogiltigt svar.") from exc
    age_days = (datetime.now(timezone.utc).date() - rate_date).days
    if rate <= 0 or age_days < 0 or age_days > 4:
        raise StrategyDataError("EUR/SEK-kursen är för gammal eller ogiltig.")
    return {
        "base": "EUR",
        "quote": "SEK",
        "rate": rate,
        "date": rate_date.isoformat(),
        "age_days": age_days,
        "source": "Frankfurter reference rates",
    }


def build_strategy_preview(
    markets: list[dict[str, Any]],
    fx: dict[str, Any],
    *,
    equity_sek: float = 200.0,
    max_trade_pct: float = 1.00,
    max_spread_pct: float = 0.35,
    min_turnover_eur: float = 10000.0,
) -> dict[str, Any]:
    """Rank liquid, tight-spread markets; return ideas, never executable orders."""
    rate = float(fx["rate"])
    if rate <= 0 or equity_sek <= 0:
        raise StrategyDataError("Ogiltigt SEK-saldo eller valutakurs.")
    if int(fx.get("age_days", 99)) > 4:
        raise StrategyDataError("Valutakursen är för gammal.")
    budget = round(equity_sek * max_trade_pct, 2)
    # Reserve room inside the trade cap for both fee and conservative slippage.
    fee_rate = 0.004
    slippage_rate = 0.0015
    max_notional_sek = budget / (1.0 + fee_rate + slippage_rate)
    candidates = []
    rejected = []
    for row in markets:
        symbol = str(row.get("symbol", ""))
        try:
            ask_eur = float(row["ask"])
            bid_eur = float(row["bid"])
            turnover = float(row["volume_24h_quote_est"])
            spread = float(row["spread_pct"])
            min_cost_eur = float(row.get("min_cost_quote") or 0)
            min_qty = float(row.get("min_order_qty") or 0)
        except (KeyError, TypeError, ValueError):
            rejected.append({"symbol": symbol, "reason": "missing_or_invalid_market_fields"})
            continue
        if not symbol or min(ask_eur, bid_eur) <= 0 or ask_eur < bid_eur:
            rejected.append({"symbol": symbol, "reason": "invalid_bid_ask"})
            continue
        if turnover < min_turnover_eur:
            rejected.append({"symbol": symbol, "reason": "turnover_below_threshold"})
            continue
        if spread < 0 or spread > max_spread_pct:
            rejected.append({"symbol": symbol, "reason": "spread_above_threshold"})
            continue
        # Kraken's minimum base quantity can imply a larger quote notional than
        # costmin. Enforce the stricter of both constraints; never treat a missing
        # costmin as zero when ordermin is present.
        min_qty_notional_eur = min_qty * ask_eur
        min_notional_eur = max(min_cost_eur, min_qty_notional_eur)
        min_notional_sek = round(min_notional_eur * rate, 2)
        min_cost_sek = round(min_cost_eur * rate, 2)
        if min_notional_sek > max_notional_sek:
            rejected.append({
                "symbol": symbol,
                "reason": "exchange_minimum_exceeds_trade_budget_after_costs",
                "minimum_notional_sek": min_notional_sek,
            })
            continue
        candidates.append({
            "symbol": symbol,
            "signal": "watch_for_paper_review",
            "reference_ask_sek": round(ask_eur * rate, 4),
            "reference_bid_sek": round(bid_eur * rate, 4),
            "spread_pct": round(spread, 4),
            "turnover_24h_sek_est": round(turnover * rate, 2),
            "exchange_min_cost_sek": min_cost_sek,
            "exchange_minimum_notional_sek": min_notional_sek,
            "exchange_min_qty": min_qty,
            "max_simulated_trade_budget_sek": budget,
            "max_order_notional_sek": round(max_notional_sek, 2),
            "note": "Kandidat för vidare paper-analys; ingen order har lagts.",
        })
    candidates.sort(key=lambda item: (item["spread_pct"], -item["turnover_24h_sek_est"]))
    return {
        "mode": "paper_preview_only",
        "orders_enabled": False,
        "withdrawals_enabled": False,
        "execution_enabled": False,
        "equity_assumption_sek": round(equity_sek, 2),
        "max_trade_budget_sek": budget,
        "allocation_policy": "up_to_100_percent_of_available_paper_equity_when_signal_and_risk_checks_pass",
        "fx": fx,
        "criteria": {
            "max_spread_pct": max_spread_pct,
            "min_turnover_eur": min_turnover_eur,
            "fee_rate_assumption": fee_rate,
            "slippage_rate_assumption": slippage_rate,
        },
        "candidate_count": len(candidates),
        "candidates": candidates[:10],
        "rejected_count": len(rejected),
        "rejected": rejected[:20],
        "disclaimer": "Detta är en marknadsfiltrerad bevakningslista, inte en köp- eller säljsignal.",
    }
