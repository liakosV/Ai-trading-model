"""Daily US equity data collection and session-level validation."""

import json
import re
from datetime import UTC, date, datetime, time, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Protocol
from uuid import uuid4
from zoneinfo import ZoneInfo

import exchange_calendars as xcals
import numpy as np
import pandas as pd
from alpaca.data.enums import Adjustment, DataFeed
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from matplotlib.figure import Figure

NEW_YORK = ZoneInfo("America/New_York")
FIELDS = ["open", "high", "low", "close", "volume"]


class DailyProvider(Protocol):
    name: str
    feed: str

    def fetch(
        self, symbols: list[str], start: date, end: date, adjustment: str
    ) -> pd.DataFrame: ...


class AlpacaProvider:
    name = "alpaca"
    feed = "iex"

    def __init__(self, client: StockHistoricalDataClient):
        self.client = client

    def fetch(self, symbols: list[str], start: date, end: date, adjustment: str) -> pd.DataFrame:
        request = StockBarsRequest(
            symbol_or_symbols=symbols,
            timeframe=TimeFrame.Day,
            start=datetime.combine(start, time.min, NEW_YORK),
            end=datetime.combine(end + timedelta(days=1), time.min, NEW_YORK)
            - timedelta(seconds=1),
            adjustment=Adjustment(adjustment),
            feed=DataFeed.IEX,
        )
        return self.client.get_stock_bars(request).df.reset_index()


def normalize(raw: pd.DataFrame, symbols: list[str], sessions: pd.Index) -> pd.DataFrame:
    required = ["symbol", "timestamp", *FIELDS]
    if raw.empty or not set(required).issubset(raw.columns):
        raise ValueError("Empty response or missing OHLCV columns")
    frame = raw[required].copy()
    timestamps = pd.to_datetime(frame.timestamp, errors="raise")
    if timestamps.dt.tz is None or timestamps.isna().any():
        raise ValueError("Expected timezone-aware bar timestamps")
    local = timestamps.dt.tz_convert(NEW_YORK)
    if not local.eq(local.dt.normalize()).all():
        raise ValueError("Expected midnight New York daily bar timestamps")
    frame["timestamp"] = timestamps.dt.tz_convert("UTC")
    frame["session"] = local.dt.date
    keys = ["symbol", "session"]
    observed = pd.MultiIndex.from_frame(frame[keys])
    expected = pd.MultiIndex.from_product([symbols, sessions.date], names=keys)
    missing = expected.difference(observed)
    extra = observed.difference(expected)
    if observed.has_duplicates or len(missing) or len(extra):
        raise ValueError(
            f"Invalid session coverage: duplicates={observed.has_duplicates}, "
            f"missing={list(missing[:5])}, unexpected={list(extra[:5])}"
        )
    for column in FIELDS:
        frame[column] = pd.to_numeric(frame[column], errors="raise")
    if not np.isfinite(frame[FIELDS]).all().all():
        raise ValueError("Non-finite OHLCV")
    if (
        (frame.low <= 0)
        | (frame.low > frame[["open", "close"]].min(axis=1))
        | (frame.high < frame[["open", "close"]].max(axis=1))
        | (frame.volume < 0)
        | (frame.volume % 1 != 0)
    ).any():
        raise ValueError("Invalid price range or share volume")
    frame["volume"] = frame.volume.astype("int64")
    return frame.sort_values(keys).reset_index(drop=True)


def collect(
    provider: DailyProvider, symbols: list[str], start: date, end: date, adjustment: str, root: Path
) -> Path:
    symbols = sorted({s.strip().upper() for s in symbols})
    if not symbols or any(not re.fullmatch(r"[A-Z][A-Z0-9.-]*", s) for s in symbols):
        raise ValueError("Supply one or more valid US equity symbols")
    if start > end or end >= datetime.now(NEW_YORK).date():
        raise ValueError("Use an inclusive historical interval ending before today in New York")
    if adjustment not in {"raw", "split", "all"}:
        raise ValueError("Unsupported adjustment")
    calendar = xcals.get_calendar(
        "XNYS", start=start - timedelta(days=7), end=end + timedelta(days=7)
    )
    sessions = calendar.sessions_in_range(start, end)
    if sessions.empty:
        raise ValueError("No exchange sessions in the requested interval")
    raw = provider.fetch(symbols, start, end, adjustment)
    downloaded = datetime.now(UTC)
    bars = normalize(raw, symbols, sessions)
    root.mkdir(parents=True, exist_ok=True)
    destination = root / f"{downloaded:%Y%m%dT%H%M%SZ}-{uuid4().hex[:12]}"
    with TemporaryDirectory(dir=root) as temp:
        stage = Path(temp) / "dataset"
        (stage / "raw").mkdir(parents=True)
        (stage / "processed").mkdir()
        raw.to_parquet(stage / "raw/bars.parquet", index=False)
        bars.to_parquet(stage / "processed/bars.parquet", index=False)
        metadata = dict(
            provider=provider.name,
            feed=provider.feed,
            adjustment=adjustment,
            timeframe="1Day",
            downloaded_at=downloaded.isoformat(),
            symbols=symbols,
            start=start.isoformat(),
            end=end.isoformat(),
            calendar="XNYS",
            rows=len(bars),
        )
        (stage / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
        fig = Figure(figsize=(9, 5), layout="constrained")
        ax = fig.subplots()
        for symbol, rows in bars.groupby("symbol"):
            ax.plot(rows.session, rows.close, label=symbol, marker="." if len(rows) == 1 else None)
        ax.set(title=f"Daily close ({provider.feed}, {adjustment})", ylabel="USD", xlabel="Session")
        ax.legend()
        fig.savefig(stage / "close.png")
        stage.rename(destination)
    return destination
