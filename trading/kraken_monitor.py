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
            "api_pair": altname,
            "base": base,
            "quote": pair_quote,
            "base_asset": str(metadata.get("base") or ""),
            "quote_asset": str(metadata.get("quote") or ""),
            "last": round(last, 8),
            "ask": round(ask, 8),
            "bid": round(bid, 8),
            "spread_pct": round(((ask - bid) / ((ask + bid) / 2.0)) * 100.0, 5),
            "min_order_qty": float(metadata.get("ordermin") or 0),
            "min_cost_quote": float(metadata.get("costmin") or 0),
            "price_decimals": int(metadata.get("pair_decimals") if metadata.get("pair_decimals") is not None else 8),
            "lot_decimals": int(metadata.get("lot_decimals") if metadata.get("lot_decimals") is not None else 8),
            "change_24h_pct": round(change_pct, 3),
            "volume_24h_base": round(volume_24h, 6),
            "volume_24h_quote_est": round(volume_24h * vwap, 2),
            "high_24h": round(high_24h, 8),
            "low_24h": round(low_24h, 8),
            "vwap_24h": round(vwap, 8),
        })
    return sorted(rows, key=lambda row: row["volume_24h_quote_est"], reverse=True)


def scan_markets(
    quote: str = "EUR",
    limit: int = 25,
    *,
    include_symbols: list[str] | None = None,
) -> dict[str, Any]:
    quote = quote.upper()
    if quote not in {"EUR", "USD"}:
        raise ValueError("quote must be EUR or USD")
    if not 1 <= limit <= 50:
        raise ValueError("limit must be between 1 and 50")
    pairs = _public_get("AssetPairs")
    tickers = _public_get("Ticker")
    rows = build_market_rows(pairs, tickers, quote=quote)
    selected = list(rows[:limit])
    selected_symbols = {str(row.get("symbol", "")).upper() for row in selected}
    for requested_symbol in (include_symbols or [])[:20]:
        wanted = str(requested_symbol or "").strip().upper()
        if wanted and wanted not in selected_symbols:
            match = next((row for row in rows if str(row.get("symbol", "")).upper() == wanted), None)
            if match is not None:
                selected.append(match)
                selected_symbols.add(wanted)
    return {
        "provider": "Kraken public API",
        "quote": quote,
        "markets_found": len(rows),
        "markets": selected,
        "mode": "read_only",
        "orders_enabled": False,
        "note": "Ranked by estimated 24h quote turnover; ranking is not a buy/sell signal.",
    }


def fetch_ohlc_candles(
    symbol: str,
    interval: int = 60,
    *,
    api_pair: str | None = None,
    min_order_qty: float | None = None,
    min_cost_eur: float | None = None,
) -> dict[str, Any]:
    """Fetch closed public Kraken OHLC candles for one listed EUR market."""
    symbol = str(symbol or "").strip().upper()
    if interval != 60:
        raise ValueError("Endast 60-minutersljusstakar stöds i första versionen.")
    metadata = None
    if api_pair:
        altname = str(api_pair).strip()
        metadata = {
            "ordermin": min_order_qty if min_order_qty is not None else 0,
            "costmin": min_cost_eur if min_cost_eur is not None else 0,
        }
    else:
        pairs = _public_get("AssetPairs")
        metadata = next(
            (row for row in pairs.values()
             if isinstance(row, dict) and str(row.get("wsname", "")).upper() == symbol),
            None,
        )
        if not metadata:
            raise ValueError("Marknaden finns inte i Krakens EUR-lista.")
        altname = str(metadata.get("altname") or "")
    if not altname:
        raise KrakenPublicAPIError("Kraken saknar marknadsidentifierare för paret.")
    query = urllib.parse.urlencode({"pair": altname, "interval": interval})
    payload = _public_get("OHLC?" + query)
    raw_rows = next((value for key, value in payload.items() if key != "last"), None)
    if not isinstance(raw_rows, list):
        raise KrakenPublicAPIError("Kraken returnerade inga OHLC-ljusstakar.")
    candles = []
    # Kraken's final OHLC row is the still-open candle; exclude it to avoid look-ahead.
    for row in raw_rows[:-1]:
        try:
            timestamp = int(row[0])
            close = float(row[4])
        except (IndexError, TypeError, ValueError, OverflowError):
            continue
        if timestamp > 0 and close > 0:
            candles.append({"timestamp": timestamp, "close": close})
    return {
        "symbol": symbol,
        "interval_minutes": interval,
        "candles": candles[-720:],
        "min_order_qty": float(metadata.get("ordermin") or 0),
        "min_cost_eur": float(metadata.get("costmin") or 0),
    }



def value_account_balances(balances: dict[str, Any], eur_sek: float) -> dict[str, Any]:
    """Value Kraken account balances in EUR using live public spot tickers.

    Assets without a direct or USD-quoted EUR-convertible market remain
    explicitly unpriced; they are never silently counted as zero.
    """
    if not isinstance(balances, dict) or not isinstance(eur_sek, (int, float)) or eur_sek <= 0:
        raise ValueError("Invalid account valuation inputs.")
    pairs = _public_get("AssetPairs")
    tickers = _public_get("Ticker")
    market_rows: list[tuple[str, str, float]] = []
    usd_to_eur = None

    for pair_key, metadata in pairs.items():
        if not isinstance(metadata, dict) or metadata.get("status", "online") != "online":
            continue
        wsname = str(metadata.get("wsname") or "")
        if "/" not in wsname:
            continue
        base, quote = wsname.split("/", 1)
        altname = str(metadata.get("altname") or pair_key)
        ticker = tickers.get(altname) or tickers.get(pair_key)
        if not isinstance(ticker, dict):
            continue
        try:
            last = float(ticker["c"][0])
        except (KeyError, IndexError, TypeError, ValueError):
            continue
        if not last or last <= 0:
            continue
        if base.upper() == "USD" and quote.upper() == "EUR":
            usd_to_eur = last
        elif base.upper() == "EUR" and quote.upper() == "USD":
            usd_to_eur = 1.0 / last

        base_asset = str(metadata.get("base") or "").upper()
        if quote.upper() == "EUR":
            market_rows.append((base_asset, wsname, last))
        elif quote.upper() == "USD":
            # Applied after the USD/EUR cross has been discovered below.
            market_rows.append((base_asset, wsname, -last))

    price_by_asset: dict[str, tuple[str, float]] = {}
    for asset_code, symbol, quote_price in market_rows:
        if quote_price > 0:
            price_by_asset[asset_code] = (symbol, quote_price)
        elif quote_price < 0 and usd_to_eur:
            price_by_asset[asset_code] = (symbol, abs(quote_price) * usd_to_eur)

    valued_assets = []
    unpriced_assets = []
    total_eur = 0.0
    for asset_code, raw_balance in balances.items():
        try:
            amount = float(raw_balance)
        except (TypeError, ValueError):
            continue
        if amount <= 0:
            continue
        code = str(asset_code).upper()
        if code in {"ZEUR", "EUR"}:
            symbol, price_eur = "EUR", 1.0
        else:
            market = price_by_asset.get(code)
            if market is None:
                unpriced_assets.append({"asset": code, "balance": amount})
                continue
            symbol, price_eur = market
        value_eur = amount * price_eur
        total_eur += value_eur
        valued_assets.append({
            "asset": code,
            "symbol": symbol,
            "balance": amount,
            "price_eur": round(price_eur, 10),
            "value_eur": round(value_eur, 8),
            "value_sek": round(value_eur * float(eur_sek), 2),
            "valuation_status": "priced",
        })

    valued_assets.sort(key=lambda row: row["value_sek"], reverse=True)
    return {
        "assets": valued_assets,
        "unpriced_assets": unpriced_assets,
        "total_eur": round(total_eur, 8),
        "total_sek": round(total_eur * float(eur_sek), 2),
        "valuation_complete": not unpriced_assets,
        "fx_eur_sek": float(eur_sek),
    }


def fetch_chart_candles(symbol: str, interval: int, limit: int) -> dict[str, Any]:
    """Fetch closed public Kraken candles for dashboard charts."""
    symbol = str(symbol or "").strip().upper()
    if interval not in {5, 60}:
        raise ValueError("Unsupported chart interval.")
    if not 1 <= limit <= 168:
        raise ValueError("Invalid chart candle limit.")
    pairs = _public_get("AssetPairs")
    metadata = next(
        (row for row in pairs.values()
         if isinstance(row, dict) and str(row.get("wsname", "")).upper() == symbol),
        None,
    )
    if not metadata:
        raise ValueError("Marknaden finns inte i Krakens EUR-lista.")
    altname = str(metadata.get("altname") or "")
    query = urllib.parse.urlencode({"pair": altname, "interval": interval})
    payload = _public_get("OHLC?" + query)
    raw_rows = next((value for key, value in payload.items() if key != "last"), None)
    if not isinstance(raw_rows, list):
        raise KrakenPublicAPIError("Kraken returnerade inga OHLC-ljusstakar.")
    candles = []
    for row in raw_rows[:-1]:
        try:
            timestamp = int(row[0])
            close = float(row[4])
        except (IndexError, TypeError, ValueError, OverflowError):
            continue
        if timestamp > 0 and close > 0:
            candles.append({"timestamp": timestamp, "close": close})
    return {
        "symbol": symbol,
        "interval_minutes": interval,
        "candles": candles[-limit:],
        "mode": "read_only",
        "orders_enabled": False,
    }
