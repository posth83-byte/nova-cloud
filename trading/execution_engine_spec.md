# Automatic execution engine

## Purpose
When live mode has been explicitly enabled after all activation gates pass, execute approved strategy intents automatically. LLM text must never call the exchange directly.

## Order lifecycle
1. Receive structured trade intent from Final Review.
2. Validate mode, market allowlist, data freshness, exchange status and kill switch.
3. Reconcile available balance, open orders and positions.
4. Fetch market minimums, amount/price precision and trading status.
5. Estimate fees, spread and slippage; reject if expected edge is not positive after costs.
6. Size from risk budget and stop distance; cap by balance and 500 SEK funding ceiling.
7. Submit spot orders only, with deterministic client order IDs and idempotency.
8. Track partial fills, average price, fees and remaining quantity.
9. Manage exits and reconcile state after reconnect/restart.
10. Persist all decisions, rejections, orders, fills and net P&L.

## Hard prohibitions
No withdrawals, transfers, leverage, margin, futures, shorts, borrowing or unapproved markets. No order without an exit rule. No increasing size to meet minimums. No duplicate submission after timeout until exchange state is checked. No trading with stale data, unreconciled exchange state or active kill switch.

## Kill switch
Immediately block new entries and record the event. Cancel open orders or close positions only according to a separately tested user-configured policy; never assume a blind market sell is always safer.

## Reporting
Show cash/assets, open positions, realized and unrealized P&L, fees, estimated slippage, net P&L and drawdown. Distinguish paper and live mode prominently.
