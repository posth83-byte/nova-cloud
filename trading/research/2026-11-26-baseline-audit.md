# JARVIS Trading — baseline research audit (2026-11-26)

## Decision

**Do not enable live trading.** The current EMA/RSI/volume baseline lost money after realistic Kraken Pro Tier 1 taker fees and slippage in every tested market/timeframe/stop combination. The results are research evidence, not a forecast.

## Assumptions

- Starting paper balance: 200 SEK, modelled as 17.81 EUR for this run. The actual Kraken balance was not read.
- Kraken Pro Tier 1 taker fee: 0.80% per side.
- Slippage: 0.05% per side.
- Maximum risk: 1% of equity per trade.
- Daily drawdown entry stop: 2%.
- Kraken pair-specific minimum base volume and EUR cost were retrieved from current CCXT market metadata, with documented fallbacks.
- Walk-forward evaluation; no same-candle look-ahead. Profits/fees are compounded between out-of-sample folds.
- Hourly REST history is limited to 720 candles (~30 days); 4-hour history is limited to 720 candles (~120 days).

## Results

| Pair | Timeframe | Stop | OOS folds | Closed trades | Net return | Worst fold drawdown |
|---|---:|---:|---:|---:|---:|---:|
| BTC/EUR | 1h (~30d) | 2.0% | 4 | 5 | -1.7725% | 1.99% |
| BTC/EUR | 1h (~30d) | 1.8% | 4 | 5 | -1.7603% | 1.99% |
| ETH/EUR | 1h (~30d) | 2.0% | 4 | 6 | -1.6523% | 2.3268% |
| ETH/EUR | 1h (~30d) | 1.8% | 4 | 6 | -1.5765% | 2.4030% |
| BTC/EUR | 4h (~120d) | 2.0% | 16 | 13 | -7.0453% | 1.99% |
| BTC/EUR | 4h (~120d) | 1.8% | 16 | 14 | -7.9332% | 1.99% |
| ETH/EUR | 4h (~120d) | 2.0% | 16 | 9 | -5.0776% | 1.99% |
| ETH/EUR | 4h (~120d) | 1.8% | 16 | 13 | -7.2489% | 1.99% |

## Interpretation

- Neither tested stop distance produced positive net returns.
- The 4-hour version performed worse over its longer sample.
- The 1-hour sample is only about 30 days and four out-of-sample folds; it is too short to establish a durable edge.
- The baseline beat buy-and-hold during a sharply falling sample, but it still lost money in absolute terms. That is not enough to approve it.
- Do not reduce the fee assumption, widen risk limits, or round position sizes up to force trades.

## Next gate

Keep the engine paper-only. Research a genuinely different low-turnover strategy and/or conservative maker-limit execution modelling. Any candidate must pass fee-aware, pair-minimum-aware walk-forward tests and then at least eight weeks of forward paper tracking before a separate live-activation decision.
