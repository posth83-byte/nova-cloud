"""Safe read-only Kraken market endpoints; live trading is deliberately disabled."""
from fastapi import APIRouter, HTTPException, Query

from trading.kraken_monitor import KrakenPublicAPIError, scan_markets

router = APIRouter(prefix="/api/trading", tags=["trading"])


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
        "next_step": "Validate market scanner and build paper-trading ledger before any live-order capability.",
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
