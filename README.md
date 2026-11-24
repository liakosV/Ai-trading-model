# Ai-trading-model

A local Python project for research on daily US stock and ETF data. The planned architecture is a modular monolith. The first milestone provides an installable package and offline checks. The earlier MSFT exploration in `experiment.py` is standalone and runs only when invoked directly.

## Local setup

Use Python 3.12. From the repository root in PowerShell, create the environment once, then install the package and development tools.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m pytest
```

On Linux or WSL, create the environment with `python3.12 -m venv .venv` and use `.venv/bin/python` for the remaining commands. Create a separate environment for each operating system.

Application code lives in `src/trading_bot/` and tests in `tests/`. No credentials are required for setup or testing. See the [development roadmap](docs/roadmap.md) for milestone scope.

## Historical daily data

Set `APCA_API_KEY_ID` and `APCA_API_SECRET_KEY` in the process environment using Alpaca paper account credentials. The example file documents their names. The collector reads environment variables directly.

```powershell
.\.venv\Scripts\collect-bars.exe --symbols MSFT --start 2023-01-01 --end 2025-12-31
```

Pass space-separated symbols to collect multiple securities. Dates are inclusive New York session dates and the end must precede today. The default is IEX with unadjusted prices. Select `--adjustment split` or `--adjustment all` to request a separately labeled series. Basic includes historical equity data since 2016 and a 200 requests/minute limit. IEX represents one venue, so its volume and prices can differ from consolidated data. [Alpaca coverage](https://docs.alpaca.markets/us/docs/about-market-data-api)

Each successful run prints a new directory under `data/`. It contains the SDK-returned rows in `raw/bars.parquet`, normalized UTC timestamps and New York session dates in `processed/bars.parquet`, request metadata in `metadata.json` and a close-price chart in `close.png`. Raw here means the provider output for the selected adjustment. The SDK handles pagination. The collector requires one bar per requested symbol and XNYS session and rejects gaps, duplicates and invalid prices. Choose dates within each security's listed history. A halt or absent IEX trades may cause a legitimate gap that needs investigation. Corporate-action factors are applied by the provider and are not independently audited.

See [market fundamentals](docs/trading-concepts.md) for a worked OHLCV example.
