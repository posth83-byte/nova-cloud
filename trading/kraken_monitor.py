"""Read-only Kraken market scanner. No credentials and no order placement."""
from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

KRAKEN_API = "https://api.kraken.com/0/public"
EXCLUDED_BASES = {"EUR", "USD", "USDT", "USDC", "DAI", "PYUSD", "EURT", "TUSD"}


class KrakenPublicAPIError(RuntimeError):
    """Raised when Kraken's public market-data API cannot be read."""


def _public_get(endpoint: str) -> dict[str, Any]:
    request = urllib.request.Request(
        f"{KRAKEN_API}/{endpoint}",
        headers={"User-Agent": "NOVA-Cloud-Kraken-Monitor/1.0"},
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise KrakenPublicAPIError(f"Kraken market data unavailable: {type(exc).__name__}") from exc
    errors = payload.get("error") or []
    if errors:
        raise KrakenPublicAPIError("Kraken API: " + "; ".join(str(item) for item in errors[:3]))
    result = payload.get("result")
    if not isinstance(result, dict):
        raise KrakenPublicAPIError("Kraken returned an invalid market-data response.")
    return result


def build_market_rows(asset_pairs: dict[str, Any], tickers: dict[str, Any], quote: str = "EUR") -> list[dict[str, Any]]:
    """Join public pair metadata with tickers and calculate transparent 24h metrics."""
    rows: list[dict[str, Any]] = []
    quote = quote.upper()
    for pair_key, metadata in asset_pairs.items():
        if not isinstance(metadata, dict) or metadata.get("status", "online") != "online":
            continue
        wsname = str(metadata.get("wsname") or "")
        altname = str(metadata.get("altname") or pair_key)
        if "/" not in wsname:
            continue
        base, pair_quote = wsname.split("/", 1)
        if pair_quote.upper() != quote or base.upper() in EXCLUDED_BASES:
            continue
        ticker = tickers.get(altname) or tickers.get(pair_key)
        if not isinstance(ticker, dict):
            continue
        try:
            last = float(ticker["c"][0])
            opening = float(ticker["o"])
            volume_24h = float(ticker["v"][1])
            vwap = float(ticker["p"][1])
            ask = float(ticker["a"][0])
            bid = float(ticker["b"][0])
            high_24h = float(ticker["h"][1])
            low_24h = float(ticker["l"][1])
        except (KeyError, IndexError, TypeError, ValueError):
            continue
        if min(last, opening, volume_24h, vwap, ask, bid, high_24h, low_24h) <= 0 or ask < bid:
            continue
        change_pct = ((last / opening) - 1.0) * 100.0
        rows.append({
            "symbol": wsname,
            "base": base,
            "quote": pair_quote,
            "last": round(last, 8),
            "ask": round(ask, 8),
            "bid": round(bid, 8),
            "spread_pct": round(((ask - bid) / ((ask + bid) / 2.0)) * 100.0, 5),
            "min_order_qty": float(metadata.get("ordermin") or 0),
            "min_cost_quote": float(metadata.get("costmin") or 0),
            "change_24h_pct": round(change_pct, 3),
            "volume_24h_base": round(volume_24h, 6),
            "volume_24h_quote_est": round(volume_24h * vwap, 2),
            "high_24h": round(high_24h, 8),
            "low_24h": round(low_24h, 8),
            "vwap_24h": round(vwap, 8),
        })
    return sorted(rows, key=lambda row: row["volume_24h_quote_est"], reverse=True)


def scan_markets(quote: str = "EUR", limit: int = 25) -> dict[str, Any]:
    quote = quote.upper()
    if quote not in {"EUR", "USD"}:
        raise ValueError("quote must be EUR or USD")
    if not 1 <= limit <= 50:
        raise ValueError("limit must be between 1 and 50")
    pairs = _public_get("AssetPairs")
    tickers = _public_get("Ticker")
    rows = build_market_rows(pairs, tickers, quote=quote)
    return {
        "provider": "Kraken public API",
        "quote": quote,
        "markets_found": len(rows),
        "markets": rows[:limit],
        "mode": "read_only",
        "orders_enabled": False,
        "note": "Ranked by estimated 24h quote turnover; ranking is not a buy/sell signal.",
    }
