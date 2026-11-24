import json
from datetime import date
from unittest.mock import Mock

import pandas as pd
import pytest
from alpaca.data.models import BarSet

from trading_bot.market_data import AlpacaProvider, collect, normalize

START = date(2024, 7, 3)
END = date(2024, 7, 5)
SESSIONS = pd.DatetimeIndex([START, END])


def bar(day):
    return dict(t=f"2024-07-{day:02}T04:00:00Z", o=100, h=105, l=99, c=103, v=123, n=4, vw=102)


def provider():
    client = Mock()
    client.get_stock_bars.return_value = BarSet({"MSFT": [bar(5), bar(3)], "SPY": [bar(3), bar(5)]})
    return AlpacaProvider(client)


def test_collection_across_holiday(tmp_path):
    source = provider()
    result = collect(source, ["msft", "SPY"], START, END, "split", tmp_path)
    request = source.client.get_stock_bars.call_args.args[0]
    assert request.adjustment.value == "split"
    assert request.feed.value == "iex"
    assert request.symbol_or_symbols == ["MSFT", "SPY"]
    raw = pd.read_parquet(result / "raw/bars.parquet")
    bars = pd.read_parquet(result / "processed/bars.parquet")
    assert len(raw) == 4
    assert bars.session.tolist() == [START, END, START, END]
    assert bars.close.tolist() == [103] * 4
    assert str(bars.timestamp.dt.tz) == "UTC"
    metadata = json.loads((result / "metadata.json").read_text())
    assert (metadata["rows"], metadata["adjustment"]) == (4, "split")
    assert (result / "close.png").read_bytes().startswith(b"\x89PNG")


@pytest.mark.parametrize(
    "fault",
    [
        "duplicate",
        "missing",
        "holiday",
        "naive",
        "intraday",
        "negative",
        "nan",
        "range",
        "volume",
    ],
)
def test_rejects_invalid_data(fault):
    rows = provider().fetch(["MSFT", "SPY"], START, END, "raw")
    if fault == "duplicate":
        rows = pd.concat([rows, rows.iloc[:1]])
    elif fault == "missing":
        rows = rows.iloc[1:]
    elif fault == "holiday":
        rows.loc[0, "timestamp"] = pd.Timestamp("2024-07-04T04:00Z")
    elif fault == "naive":
        rows.timestamp = rows.timestamp.dt.tz_localize(None)
    elif fault == "intraday":
        rows.loc[0, "timestamp"] += pd.Timedelta(hours=1)
    else:
        field, value = {
            "negative": ("low", -1),
            "nan": ("open", float("nan")),
            "range": ("high", 80),
            "volume": ("volume", -1),
        }[fault]
        rows.loc[0, field] = value
    with pytest.raises(ValueError):
        normalize(rows, ["MSFT", "SPY"], SESSIONS)


def test_partial_dataset_never_published(tmp_path):
    with pytest.raises(ValueError, match="missing"):
        collect(provider(), ["MSFT", "SPY", "AAPL"], START, END, "raw", tmp_path)
    assert list(tmp_path.iterdir()) == []

