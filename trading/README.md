# JARVIS Trading

An isolated, paper-first crypto trading project. No live orders are enabled in this phase.

## Mission
Build a modular crypto research and trading system with a multi-specialist review process:
- Market Scanner: collect spot market data and detect unusual movement/volume.
- Technical Analyst: calculate indicators and produce explainable signals.
- Opportunity Hunter: rank candidate setups; never place orders.
- Risk Manager: enforce hard limits independently of AI.
- Strategy Developer: run reproducible backtests and compare strategies.
- Final Review: approve/reject paper-trade intents and record the reason.

## First release scope
1. Read-only market data for spot markets.
2. Paper wallet starting at 500 SEK equivalent (quote currency conversion must be explicit).
3. BTC/EUR and ETH/EUR only, subject to exchange availability and minimum-order checks.
4. No margin, leverage, futures, shorting, borrowing, withdrawals, or transfer permissions.
5. Every signal and simulated trade is persisted with timestamps, fees, spread assumptions, and rationale.
6. Dashboard/API must clearly show PAPER mode. Live trading is not implemented or enabled.

## Risk policy (initial test defaults)
- Paper mode is mandatory.
- Maximum one open position at a time.
- Maximum planned loss per trade: 1% of paper equity.
- Daily stop: 2% drawdown from start-of-day equity; stop creating new positions after breach.
- Every position must have a defined exit/stop rule before entry.
- No averaging down or martingale.
- No trade if estimated fees + spread make the expected edge uneconomic.
- AI output is advisory; deterministic code enforces all limits.

These are simulation guardrails, not a promise of safety or profitability. They must be evaluated against realistic fees, slippage, minimum order sizes, and historical/live-forward data.

## Validation gates before any real-money discussion
- Unit tests for risk limits, sizing, fees, duplicate orders, stale data, and kill switch.
- Backtests with fees and out-of-sample periods.
- Forward paper trading on live market data for at least 8 weeks.
- Review drawdown, expectancy, win/loss distribution, turnover, and divergence between backtest and forward results.
- Explicit user approval required for any future live-trading implementation.
- Any eventual exchange key must be restricted to read/trade only, with withdrawals disabled, stored as a secret, never committed.

## Deployment note
Do not deploy the trading worker to a sleeping/free web service and assume continuous execution. Choose a suitable always-on worker only after costs and operational constraints are understood. Local Docker execution is acceptable for initial development.

## References
- Freqtrade dry-run and configuration: https://www.freqtrade.io/en/stable/configuration/
- Freqtrade strategy testing: https://www.freqtrade.io/en/latest/strategy-101/
- Freqtrade backtesting: https://www.freqtrade.io/en/stable/backtesting/
