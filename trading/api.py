"""Safe Kraken market-data and paper-only trading endpoints."""
import hmac
import os

from fastapi import APIRouter, Header, HTTPException, Query

from trading.kraken_monitor import KrakenPublicAPIError, scan_markets
from trading.paper_engine import (
    PaperTradingError,
    activate_emergency_stop,
    create_initial_state,
    portfolio_snapshot,
    set_paper_enabled,
)
from trading.paper_store import PaperStoreError, load_or_create, save_state

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
    snapshot = portfolio_snapshot(state)
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
