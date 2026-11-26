"""Safe Kraken market-data and paper-only trading endpoints."""
import hmac
import os
from datetime import datetime, timezone

from fastapi import APIRouter, Header, HTTPException, Query

from trading.kraken_monitor import KrakenPublicAPIError, fetch_ohlc_candles, scan_markets
from trading.paper_engine import (
    PaperTradingError,
    activate_emergency_stop,
    create_initial_state,
    portfolio_snapshot,
    set_paper_enabled,
)
from trading.paper_store import PaperStoreError, load_or_create, save_state
from trading.backtest import run_sma_backtest
from trading.strategy import StrategyDataError, build_strategy_preview, fetch_eur_sek_rate
from trading.worker import run_paper_tick
from trading.opportunity_radar import rank_opportunities
from trading.live_worker import run_live_tick
from trading.live_store import (
    LiveStoreError,
    load_or_create_live_state,
    save_live_state,
)
from trading.kraken_private import (
    KrakenPrivateAPIError,
    credentials_configured,
    run_read_only_preflight,
    validate_limit_order,
)
from decimal import Decimal, ROUND_DOWN

router = APIRouter(prefix="/api/trading", tags=["trading"])


def _control_guard(token: str | None):
    expected = os.getenv("TRADE_CONTROL_TOKEN", "").strip()
    if not expected:
        raise HTTPException(status_code=503, detail="Trade-kontroll är inte konfigurerad ännu.")
    supplied = (token or "").strip()
    if not supplied or not hmac.compare_digest(supplied, expected):
        raise HTTPException(status_code=401, detail="Ogiltig Trade AI-kontrollnyckel.")


def _github_actions_guard(
    authorization: str | None, *, manual_start: bool = False,
    allowed_workflows: set[str] | None = None,
):
    """Verify a short-lived GitHub Actions OIDC token; no shared scheduler secret."""
    supplied = (authorization or "").strip()
    if not supplied.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Schemaläggarens identitet saknas.")
    token = supplied[7:].strip()
    if not token:
        raise HTTPException(status_code=401, detail="Schemaläggarens identitet saknas.")
    try:
        import jwt
        client = jwt.PyJWKClient(
            "https://token.actions.githubusercontent.com/.well-known/jwks",
            cache_jwk_set=True,
            lifespan=300,
        )
        signing_key = client.get_signing_key_from_jwt(token)
        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            audience="nova-cloud-trade-worker",
            issuer="https://token.actions.githubusercontent.com",
            options={"require": ["exp", "iat", "iss", "aud", "repository", "ref", "event_name", "workflow_ref"]},
        )
    except Exception as exc:
        raise HTTPException(status_code=401, detail="Schemaläggarens identitet kunde inte verifieras.") from exc

    expected_workflows = allowed_workflows or {
        "posth83-byte/nova-cloud/.github/workflows/trade-paper-scheduler.yml@refs/heads/main"
    }
    if (
        claims.get("repository") != "posth83-byte/nova-cloud"
        or str(claims.get("repository_id")) != "1442711208"
        or claims.get("ref") != "refs/heads/main"
        or claims.get("workflow_ref") not in expected_workflows
    ):
        raise HTTPException(status_code=403, detail="Den här GitHub-workflowen är inte godkänd.")
    allowed_events = {"workflow_dispatch"} if manual_start else {"schedule", "workflow_dispatch"}
    if claims.get("event_name") not in allowed_events:
        raise HTTPException(status_code=403, detail="Den här schemaläggningshändelsen är inte tillåten.")


def _manual_control_guard(
    token: str | None, authorization: str | None,
    allowed_workflows: set[str] | None = None,
):
    if token:
        _control_guard(token)
    else:
        if allowed_workflows is None:
            _github_actions_guard(authorization, manual_start=True)
        else:
            _github_actions_guard(
                authorization, manual_start=True, allowed_workflows=allowed_workflows
            )


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
        "next_step": "Scheduled paper-only SMA worker is available after manual activation; live orders remain disabled.",
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


@router.get("/opportunities")
async def trading_opportunities(
    limit: int = Query(default=10, ge=1, le=20),
):
    """Rank liquid Kraken EUR markets for closer monitoring; never place orders."""
    try:
        state, _revision = _load()
        fx = fetch_eur_sek_rate()
        market_data = scan_markets(quote="EUR", limit=50)
        result = rank_opportunities(
            market_data.get("markets", []),
            equity_sek=float(state.get("starting_cash") or "200.00"),
            eur_sek=float(fx["rate"]),
            limit=limit,
        )
        result["fx"] = fx
        result["paper_balance_sek"] = float(state.get("cash") or "0")
        result["worker_last_tick_at"] = (state.get("worker") or {}).get("last_tick_at")
        return result
    except (StrategyDataError, KrakenPublicAPIError) as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except (TypeError, ValueError, KeyError) as exc:
        raise HTTPException(status_code=503, detail="Möjlighetsradarn kunde inte beräkna en säker topplista.") from exc


@router.get("/paper")
async def paper_status():
    state, revision = _load()
    worker = state.get("worker", {})
    marks = {}
    marked_at = worker.get("last_marked_at")
    if marked_at:
        try:
            mark_time = datetime.fromisoformat(str(marked_at).replace("Z", "+00:00"))
            if (datetime.now(timezone.utc) - mark_time).total_seconds() <= 1800:
                marks = worker.get("last_marks_sek", {})
        except (TypeError, ValueError):
            marks = {}
    try:
        snapshot = portfolio_snapshot(state, marks)
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
        "worker": worker,
    })
    return snapshot


@router.post("/paper/start")
async def paper_start(
    x_trade_control_token: str | None = Header(default=None),
    authorization: str | None = Header(default=None),
):
    _manual_control_guard(x_trade_control_token, authorization)
    state, revision = _load()
    try:
        updated = set_paper_enabled(state, True)
    except PaperTradingError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    next_revision = _save(updated, revision)
    return {"ok": True, "paper_enabled": True, "revision": next_revision, "orders_enabled": False}


@router.post("/paper/pause")
async def paper_pause(
    x_trade_control_token: str | None = Header(default=None),
    authorization: str | None = Header(default=None),
):
    _manual_control_guard(x_trade_control_token, authorization)
    state, revision = _load()
    updated = set_paper_enabled(state, False)
    next_revision = _save(updated, revision)
    return {"ok": True, "paper_enabled": False, "revision": next_revision, "orders_enabled": False}


@router.post("/paper/emergency-stop")
async def paper_emergency_stop(
    reason: str = "Manuellt nödstopp",
    x_trade_control_token: str | None = Header(default=None),
    authorization: str | None = Header(default=None),
):
    _manual_control_guard(x_trade_control_token, authorization)
    state, revision = _load()
    updated = activate_emergency_stop(state, reason)
    next_revision = _save(updated, revision)
    return {"ok": True, "paper_enabled": False, "emergency_stop": True, "revision": next_revision, "orders_enabled": False}


@router.post("/paper/worker-tick")
async def paper_worker_tick(
    x_trade_control_token: str | None = Header(default=None),
    authorization: str | None = Header(default=None),
):
    """Authenticated scheduler hook; only advances the simulation-only ledger."""
    if x_trade_control_token:
        _control_guard(x_trade_control_token)
    else:
        _github_actions_guard(authorization)
    try:
        return run_paper_tick()
    except PaperStoreError as exc:
        raise HTTPException(status_code=503, detail="Trade AI kunde inte läsa eller spara pappersjournalen.") from exc
    except Exception as exc:
        # Keep internal details out of the public response and never log secrets.
        raise HTTPException(status_code=503, detail="Trade AI:s schemalagda körning misslyckades säkert.") from exc


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


@router.post("/live/worker-tick")
async def live_worker_tick(
    x_trade_control_token: str | None = Header(default=None),
    authorization: str | None = Header(default=None),
):
    """Authenticated scheduled tick; no work is performed unless live state is enabled."""
    if x_trade_control_token:
        _control_guard(x_trade_control_token)
    else:
        _github_actions_guard(authorization, allowed_workflows={
            "posth83-byte/nova-cloud/.github/workflows/trade-paper-scheduler.yml@refs/heads/main",
            "posth83-byte/nova-cloud/.github/workflows/trade-live-scheduler.yml@refs/heads/main",
        })
    try:
        return run_live_tick()
    except (LiveStoreError, KrakenPrivateAPIError) as exc:
        raise HTTPException(
            status_code=503,
            detail="Livehandelns säkerhetskontroll misslyckades; inga nya order får skickas.",
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail="Livehandelns schemalagda körning stoppades säkert.",
        ) from exc


@router.get("/live/status")
async def live_status():
    """Show isolated live ledger and readiness without exposing private data."""
    try:
        state, revision = load_or_create_live_state()
    except LiveStoreError as exc:
        raise HTTPException(status_code=503, detail="Livejournalen är inte tillgänglig.") from exc
    return {
        "mode": "live_spot_disabled",
        "exchange": "Kraken Spot",
        "credentials_configured": credentials_configured(),
        "private_api_preflight_available": credentials_configured(),
        "live_enabled": bool(state.get("enabled")),
        "emergency_stop": bool(state.get("emergency_stop")),
        "stop_reason": state.get("stop_reason"),
        "cash_sek": state.get("cash_sek"),
        "positions": state.get("positions", {}),
        "realized_pnl_sek": state.get("realized_pnl_sek"),
        "revision": revision,
        "risk": state.get("risk", {}),
        "worker": state.get("worker", {}),
        "orders_enabled": False,
        "withdrawals_enabled": False,
        "budget_policy": "all_available_kraken_eur_balance",
        "live_order_engine": "guarded_autonomous_spot_worker",
        "next_step": "Use the manual Trade AI workflow with arm_live=true to activate after account preflight.",
    }


@router.post("/live/start")
async def live_start(
    x_trade_control_token: str | None = Header(default=None),
    authorization: str | None = Header(default=None),
):
    """Arm live trading only after server gate and fresh Kraken preflight pass."""
    _manual_control_guard(
        x_trade_control_token,
        authorization,
        allowed_workflows={
            "posth83-byte/nova-cloud/.github/workflows/trade-live-scheduler.yml@refs/heads/main"
        },
    )
    if os.getenv("TRADE_LIVE_ENABLED", "").strip().lower() != "true":
        raise HTTPException(
            status_code=409,
            detail="Livehandelns servergrind är fortfarande avstängd.",
        )
    try:
        state, revision = load_or_create_live_state()
        if state.get("emergency_stop"):
            raise HTTPException(
                status_code=409,
                detail="Nödstoppet är aktivt och måste granskas separat.",
            )
        fx = fetch_eur_sek_rate()
        preflight = run_read_only_preflight(Decimal(str(fx["rate"])))
        if not preflight.get("connected") or not preflight.get("open_orders_clear"):
            raise HTTPException(
                status_code=409,
                detail="Kraken-kontot klarade inte livehandelns säkerhetskontroll.",
            )
        state["enabled"] = True
        state["worker"] = {
            **dict(state.get("worker") or {}),
            "status": "armed",
            "last_error": None,
            "armed_at": datetime.now(timezone.utc).isoformat(),
        }
        next_revision = save_live_state(state, revision)
    except HTTPException:
        raise
    except (LiveStoreError, StrategyDataError, KrakenPrivateAPIError) as exc:
        raise HTTPException(
            status_code=503,
            detail="Livehandel kunde inte aktiveras säkert.",
        ) from exc
    return {
        "ok": True, "live_enabled": True, "mode": "live_spot",
        "budget_policy": "all_available_kraken_eur_balance", "open_orders_clear": True,
        "withdrawals_enabled": False, "revision": next_revision,
    }


@router.post("/live/pause")
async def live_pause(
    x_trade_control_token: str | None = Header(default=None),
    authorization: str | None = Header(default=None),
):
    """Disable future live worker ticks; does not cancel exchange orders."""
    _manual_control_guard(
        x_trade_control_token,
        authorization,
        allowed_workflows={
            "posth83-byte/nova-cloud/.github/workflows/trade-live-scheduler.yml@refs/heads/main"
        },
    )
    try:
        state, revision = load_or_create_live_state()
        state["enabled"] = False
        worker = dict(state.get("worker") or {})
        worker["status"] = "paused"
        state["worker"] = worker
        next_revision = save_live_state(state, revision)
    except LiveStoreError as exc:
        raise HTTPException(status_code=503, detail="Livejournalen kunde inte pausas säkert.") from exc
    return {
        "ok": True, "live_enabled": False, "revision": next_revision,
        "open_exchange_orders_cancelled": False, "withdrawals_enabled": False,
    }


@router.post("/live/emergency-stop")
async def live_emergency_stop(
    reason: str = "Manuellt live-nödstopp",
    x_trade_control_token: str | None = Header(default=None),
):
    """Persist a durable stop that prevents future live worker ticks."""
    _control_guard(x_trade_control_token)
    try:
        state, revision = load_or_create_live_state()
        state["enabled"] = False
        state["emergency_stop"] = True
        state["stop_reason"] = str(reason or "Manuellt live-nödstopp")[:240]
        worker = dict(state.get("worker") or {})
        worker.update({"status": "emergency_stopped", "last_error": state["stop_reason"]})
        state["worker"] = worker
        next_revision = save_live_state(state, revision)
    except LiveStoreError as exc:
        raise HTTPException(status_code=503, detail="Livejournalens nödstopp kunde inte sparas.") from exc
    return {
        "ok": True, "live_enabled": False, "emergency_stop": True,
        "revision": next_revision, "open_exchange_orders_cancelled": False,
        "withdrawals_enabled": False,
    }


@router.post("/live/preflight")
async def live_preflight(
    x_trade_control_token: str | None = Header(default=None),
):
    """Check Kraken credentials, permissions, EUR balance and open orders only."""
    _control_guard(x_trade_control_token)
    try:
        fx = fetch_eur_sek_rate()
        result = run_read_only_preflight(Decimal(str(fx["rate"])))
        result["fx_reference"] = {
            "date": fx.get("date"),
            "source": fx.get("source"),
            "age_days": fx.get("age_days"),
        }
        result["orders_enabled"] = False
        result["withdrawals_enabled"] = False
        return result
    except (StrategyDataError, KrakenPrivateAPIError) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/live/validate-order")
async def live_validate_order(
    x_trade_control_token: str | None = Header(default=None),
):
    """Validate one bounded EUR spot limit order at Kraken; never submit it."""
    _control_guard(x_trade_control_token)
    try:
        fx = fetch_eur_sek_rate()
        rate = Decimal(str(fx["rate"]))
        account = run_read_only_preflight(rate)
        if not account.get("open_orders_clear"):
            raise HTTPException(
                status_code=409,
                detail="Det finns redan öppna Kraken-order. De måste granskas innan ordervalidering.",
            )
        markets = scan_markets(quote="EUR", limit=50).get("markets", [])
        radar = rank_opportunities(
            markets,
            equity_sek=200.0,
            eur_sek=float(rate),
            limit=10,
        )
        market_by_symbol = {
            str(row.get("symbol", "")).upper(): row for row in markets
        }
        # The 200 SEK ceiling includes estimated fee and slippage reserves.
        total_cost_factor = Decimal("1.004") * Decimal("1.0015")
        # Validation sizing follows all currently available EUR on Kraken;
        # no fixed 200 SEK ceiling remains.
        budget_eur = Decimal(str(account["eur_balance"])) / total_cost_factor
        for candidate in radar.get("candidates", []):
            row = market_by_symbol.get(str(candidate.get("symbol", "")).upper())
            if not row:
                continue
            try:
                pair = str(row["api_pair"]).strip().upper()
                ask = Decimal(str(row["ask"]))
                price_decimals = max(0, min(10, int(row.get("price_decimals", 8))))
                lot_decimals = max(0, min(10, int(row.get("lot_decimals", 8))))
                price_quantum = Decimal("1").scaleb(-price_decimals)
                volume_quantum = Decimal("1").scaleb(-lot_decimals)
                price = ask.quantize(price_quantum, rounding=ROUND_DOWN)
                volume = (budget_eur / price).quantize(
                    volume_quantum, rounding=ROUND_DOWN
                )
                min_qty = Decimal(str(row.get("min_order_qty") or 0))
                min_cost = Decimal(str(row.get("min_cost_quote") or 0))
            except (KeyError, TypeError, ValueError, ArithmeticError):
                continue
            notional = volume * price
            if price <= 0 or volume < min_qty or notional < min_cost or notional <= 0:
                continue
            validation = validate_limit_order(
                pair=pair, side="buy", volume=volume, price=price
            )
            validation.update({
                "candidate": candidate,
                "budget_policy": "all_available_kraken_eur_balance",
                "estimated_notional_eur": str(notional.quantize(Decimal("0.01"))),
                "estimated_notional_sek": str(
                    (notional * rate).quantize(Decimal("0.01"))
                ),
                "fee_and_slippage_reserve": "0.5506%",
                "fx_reference": {
                    "rate": str(rate),
                    "date": fx.get("date"),
                    "source": fx.get("source"),
                },
                "orders_enabled": False,
                "withdrawals_enabled": False,
            })
            return validation
        raise HTTPException(
            status_code=409,
            detail="Ingen bevakad EUR-marknad klarar Krakens minsta orderkrav inom 200 kr.",
        )
    except HTTPException:
        raise
    except (StrategyDataError, KrakenPublicAPIError, KrakenPrivateAPIError) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except (TypeError, ValueError, KeyError) as exc:
        raise HTTPException(
            status_code=503,
            detail="Trade AI kunde inte beräkna en order som håller sig inom riskgränsen.",
        ) from exc
