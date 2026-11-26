"""Safe Kraken market-data and paper-only trading endpoints."""
import hmac
import os

from fastapi import APIRouter, Header, HTTPException, Query

from trading.kraken_monitor import KrakenPublicAPIError, fetch_ohlc_candles, scan_markets
from trading.paper_engine import (
    PaperTradingError,
    activate_emergency_stop,
    create_initial_state,
    portfolio_snapshot,
    set_paper_enabled,
)
from trading.paper_store import PaperStoreError, load_or_create, save_state\nfrom trading.backtest import run_sma_backtest
from trading.strategy import StrategyDataError, build_strategy_preview, fetch_eur_sek_rate

router = APIRouter(prefix="/api/trading", tags=["trading"])


def _control_guard(token: str | None):
    expected = os.getenv("TRADE_CONTROL_TOKEN", "").strip()
    if not expected:
        raise HTTPException(status_code=503, detail="Trade-kontroll är inte konfigurerad ännu.")
    supplied = (token or "").strip()
    if not supplied or not hmac.compare_digest(supplied, expected):
        raise HTTPException(status_code=401, detail="Ogiltig Trade AI-kontrollnyckel.")


def _load():
    try:
        return load_or_create(create_initial_state)
    except PaperStoreError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


def _save(state, revision):
    try:
        return save_state(state, revision)
    except PaperStoreError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/status")
async def trading_status():
    return {
        "status": "online",
        "exchange": "Kraken",
        "market_data": "public_read_only",
        "mode": "paper_only",
        "orders_enabled": False,
        "withdrawals_enabled": False,
        "api_credentials_required": False,
        "next_step": "Paper ledger is persisted; strategy and market-to-SEK validation remain before autonomous simulation.",
    }


@router.get("/markets")
async def trading_markets(
    quote: str = Query(default="EUR", pattern="^(EUR|USD|eur|usd)$"),
    limit: int = Query(default=25, ge=1, le=50),
):
    try:
        return scan_markets(quote=quote, limit=limit)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except KrakenPublicAPIError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/paper")
async def paper_status():
    state, revision = _load()
    try:
        snapshot = portfolio_snapshot(state)
        snapshot["valuation_status"] = "complete"
    except PaperTradingError:
        snapshot = {
            "mode": "paper_only", "currency": "SEK",
            "paper_enabled": bool(state.get("paper_enabled")),
            "emergency_stop": bool(state.get("emergency_stop")),
            "cash": state.get("cash"), "equity": None,
            "starting_cash": state.get("starting_cash"),
            "total_pnl": None, "realized_pnl": state.get("realized_pnl"),
            "positions": state.get("positions", {}),
            "trade_count": len(state.get("trades", [])),
            "orders_enabled": False, "withdrawals_enabled": False,
            "valuation_status": "awaiting_fresh_sek_market_marks",
        }
    snapshot.update({
        "revision": revision,
        "storage": "supabase",
        "history": state.get("trades", [])[-25:],
        "risk": state.get("risk", {}),
        "stop_reason": state.get("stop_reason"),
    })
    return snapshot


@router.post("/paper/start")
async def paper_start(x_trade_control_token: str | None = Header(default=None)):
    _control_guard(x_trade_control_token)
    state, revision = _load()
    try:
        updated = set_paper_enabled(state, True)
    except PaperTradingError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    next_revision = _save(updated, revision)
    return {"ok": True, "paper_enabled": True, "revision": next_revision, "orders_enabled": False}


@router.post("/paper/pause")
async def paper_pause(x_trade_control_token: str | None = Header(default=None)):
    _control_guard(x_trade_control_token)
    state, revision = _load()
    updated = set_paper_enabled(state, False)
    next_revision = _save(updated, revision)
    return {"ok": True, "paper_enabled": False, "revision": next_revision, "orders_enabled": False}


@router.post("/paper/emergency-stop")
async def paper_emergency_stop(
    reason: str = "Manuellt nödstopp",
    x_trade_control_token: str | None = Header(default=None),
):
    _control_guard(x_trade_control_token)
    state, revision = _load()
    updated = activate_emergency_stop(state, reason)
    next_revision = _save(updated, revision)
    return {"ok": True, "paper_enabled": False, "emergency_stop": True, "revision": next_revision, "orders_enabled": False}


@router.get("/paper/strategy-preview")
async def paper_strategy_preview():
    """Return a read-only watchlist with EUR prices converted to SEK."""
    try:
        state, _revision = _load()
        fx = fetch_eur_sek_rate()
        market_data = scan_markets(quote="EUR", limit=50)
        return build_strategy_preview(
            market_data.get("markets", []),
            fx,
            equity_sek=float(state.get("starting_cash") or "200.00"),
        )
    except (StrategyDataError, KrakenPublicAPIError) as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=503, detail="Trade AI kunde inte beräkna en säker förhandsanalys.") from exc



@router.get("/paper/backtest")
async def paper_backtest(
    pair: str = Query(default="XBT/EUR", pattern="^[A-Z0-9]+/EUR$"),
):
    """Run a fixed SMA strategy on closed historical Kraken candles; simulation only."""
    try:
        state, _revision = _load()
        history = fetch_ohlc_candles(pair, interval=60)
        markets = scan_markets(quote="EUR", limit=50).get("markets", [])
        current_market = next(
            (row for row in markets if row.get("symbol", "").upper() == pair.upper()),
            None,
        )
        if current_market is None:
            raise HTTPException(status_code=422, detail="Marknaden saknar verifierad aktuell spreaddata.")
        fx = fetch_eur_sek_rate()
        result = run_sma_backtest(
            history["candles"],
            fx_sek_per_eur=float(fx["rate"]),
            starting_cash_sek=float(state.get("starting_cash") or "200.00"),
            min_order_qty=float(history["min_order_qty"]),
            min_cost_eur=float(history["min_cost_eur"]),
            spread_pct=float(current_market["spread_pct"]),
        )
        result["market"] = pair
        result["candle_interval_minutes"] = 60
        result["fx_reference"] = fx
        result["orders_enabled"] = False
        result["withdrawals_enabled"] = False
        return result
    except (StrategyDataError, KrakenPublicAPIError) as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except (TypeError, KeyError) as exc:
        raise HTTPException(status_code=503, detail="Trade AI kunde inte beräkna ett säkert historiskt test.") from exc
