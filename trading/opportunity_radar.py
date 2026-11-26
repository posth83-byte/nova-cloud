"""Transparent ranking of Kraken spot markets for closer monitoring.

This is an opportunity radar, not a buy/sell signal. It never submits orders.
"""
from __future__ import annotations

from typing import Any


def rank_opportunities(
    markets: list[dict[str, Any]],
    *,
    equity_sek: float = 200.0,
    eur_sek: float,
    fee_rate: float = 0.004,
    slippage_rate: float = 0.0015,
    min_turnover_eur: float = 10_000.0,
    max_spread_pct: float = 0.35,
    limit: int = 10,
) -> dict[str, Any]:
    if equity_sek <= 0 or eur_sek <= 0 or limit < 1:
        raise ValueError("Invalid radar sizing or FX input.")
    max_budget_sek = equity_sek
    cost_factor = 1.0 + fee_rate + slippage_rate
    ranked = []
    rejected = []
    for row in markets:
        symbol = str(row.get("symbol") or "").upper()
        try:
            ask = float(row["ask"])
            bid = float(row["bid"])
            spread = float(row["spread_pct"])
            turnover = float(row["volume_24h_quote_est"])
            change = float(row["change_24h_pct"])
            high = float(row["high_24h"])
            low = float(row["low_24h"])
            last = float(row["last"])
            min_qty = float(row.get("min_order_qty") or 0)
            min_cost = float(row.get("min_cost_quote") or 0)
        except (KeyError, TypeError, ValueError):
            rejected.append({"symbol": symbol, "reason": "missing_market_data"})
            continue
        if not symbol or min(ask, bid, high, low, last) <= 0 or ask < bid or high < low:
            rejected.append({"symbol": symbol, "reason": "invalid_market_data"})
            continue
        if turnover < min_turnover_eur:
            rejected.append({"symbol": symbol, "reason": "low_turnover"})
            continue
        if spread < 0 or spread > max_spread_pct:
            rejected.append({"symbol": symbol, "reason": "spread_too_wide"})
            continue
        minimum_eur = max(min_cost, min_qty * ask)
        minimum_sek = minimum_eur * eur_sek
        if minimum_sek * cost_factor > max_budget_sek:
            rejected.append({"symbol": symbol, "reason": "minimum_order_exceeds_available_budget"})
            continue

        range_pct = ((high - low) / last) * 100.0
        # A gentle positive momentum is interesting; extreme 24h spikes are
        # penalized rather than automatically promoted as chase entries.
        momentum_score = max(0.0, min(30.0, 15.0 + change * 1.5))
        if change > 20:
            momentum_score -= min(12.0, (change - 20.0) * 0.5)
        elif change < -15:
            momentum_score = max(0.0, momentum_score - 8.0)
        liquidity_score = min(25.0, max(0.0, (turnover / min_turnover_eur) ** 0.35 * 8.0))
        spread_score = max(0.0, 25.0 * (1.0 - spread / max_spread_pct))
        range_score = 20.0 if 0.5 <= range_pct <= 12.0 else max(0.0, 20.0 - abs(range_pct - 5.0) * 1.5)
        score = round(max(0.0, min(100.0, momentum_score + liquidity_score + spread_score + range_score)), 1)
        priority = "high" if score >= 70 else "medium" if score >= 50 else "low"
        ranked.append({
            "symbol": symbol,
            "score": score,
            "priority": priority,
            "change_24h_pct": round(change, 3),
            "spread_pct": round(spread, 5),
            "turnover_24h_eur_est": round(turnover, 2),
            "range_24h_pct": round(range_pct, 3),
            "reference_price_eur": round(last, 8),
            "minimum_order_sek_est": round(minimum_sek, 2),
            "max_budget_sek": round(max_budget_sek, 2),
            "reasons": [
                "liquidity_ok",
                "spread_ok",
                "positive_momentum" if change > 0 else "momentum_not_positive",
            ],
            "buy_signal": False,
            "action": "monitor_closely",
        })
    ranked.sort(key=lambda item: (-item["score"], item["spread_pct"], -item["turnover_24h_eur_est"]))
    return {
        "mode": "opportunity_radar",
        "execution_enabled": False,
        "orders_enabled": False,
        "withdrawals_enabled": False,
        "buy_signal": False,
        "scanned_markets": len(markets),
        "eligible_count": len(ranked),
        "rejected_count": len(rejected),
        "equity_assumption_sek": round(equity_sek, 2),
        "ranking_method": "momentum + liquidity + spread + 24h range; score is a watch priority, not expected return",
        "candidates": ranked[:limit],
        "rejected_sample": rejected[:20],
    }
