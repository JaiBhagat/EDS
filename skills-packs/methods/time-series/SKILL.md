---
name: time-series
description: >
  Method pack for time-indexed data — forecasting, trend/seasonality
  decomposition, autocorrelation. Reach for this only when a rung-6
  baseline (seasonal-naive/last-value) genuinely fails to meet the bar
  because the series has structure (trend, seasonality, autocorrelation)
  a generic model can't capture cheaply. Not installed by default — this
  is an optional pack, not core.
license: MIT
---

# Time-series (method pack)

## Ladder position

Rung 7, conditionally. Before reaching here, `baseline-first` must have already tried and reported on the seasonal-naive/last-value baseline — if that baseline already meets the bar, stop there. This pack exists for when it doesn't, and the *reason* it doesn't is genuine time structure, not "time series sounds like it needs a special model."

## Canonical pitfalls

1. **Shuffled CV / random split on a time series** — leaks future into past. `leakage-check` and `ds-lint.js`'s time-shuffle check already flag this in code; this pack states the underlying principle: evaluation must be walk-forward, always.
2. **Stationarity assumed, not tested.** Run an ADF or KPSS test before applying a method that assumes it (ARIMA family); a series with an untreated unit root will fit "well" and forecast badly.
3. **Single-fold backtest overstates confidence.** Walk-forward validation across multiple expanding or rolling windows, not one holdout period — a model that wins on one window can lose on the next regime.
4. **Multiple/overlapping seasonalities glossed over** (daily + weekly + annual, or holiday effects folded into a single seasonal term) — check decomposition residuals for leftover structure before trusting the fit.
5. **Lag/window features constructed with a leak.** This is `fde`'s job (the `temporal`/`velocity`/`seasonality`/`trend` hypothesis families already cover this) — this pack prioritizes those families for time-indexed problems, it doesn't duplicate their construction logic.

## Library pointers

`statsmodels` (ARIMA/SARIMAX, decomposition, ADF/KPSS tests) for classical methods; `pmdarima` for automated order search; `prophet` or `orbit` for decomposition-based forecasting with holiday effects; `sktime`/`darts` for ML-based forecasting with a scikit-like API. Rung 7 says use the library — this pack tells you which, not how ARIMA works internally.

## Extends

- `baseline-first` — the forecasting baseline is seasonal-naive or last-value, not mean; this pack states that explicitly so the burden of proof is set correctly before reaching rung 7.
- `evaluation-design` — backtest split design (walk-forward, expanding vs. rolling window) is the time-series-specific half of split design.
- `fde` — re-weights `temporal`/`seasonality`/`trend`/`velocity` hypothesis family priority; adds no new loop logic or funnel stages (core owns those).
