import argparse
import os
from datetime import date
from pathlib import Path

from alpaca.common.exceptions import APIError
from alpaca.data.historical import StockHistoricalDataClient
from requests.exceptions import RequestException

from trading_bot.market_data import AlpacaProvider, collect


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Collect complete daily US stock bars from Alpaca IEX."
    )
    parser.add_argument("--symbols", nargs="+", default=["MSFT"])
    parser.add_argument("--start", type=date.fromisoformat, required=True)
    parser.add_argument("--end", type=date.fromisoformat, required=True)
    parser.add_argument("--adjustment", choices=["raw", "split", "all"], default="raw")
    parser.add_argument("--output", type=Path, default=Path("data"))
    args = parser.parse_args()
    key, secret = (os.getenv(name) for name in ("APCA_API_KEY_ID", "APCA_API_SECRET_KEY"))
    if not key or not secret:
        parser.exit(
            2, "Set APCA_API_KEY_ID and APCA_API_SECRET_KEY locally using paper credentials.\n"
        )
    try:
        provider = AlpacaProvider(StockHistoricalDataClient(key, secret))
        print(collect(provider, args.symbols, args.start, args.end, args.adjustment, args.output))
    except (APIError, RequestException) as error:
        parser.exit(
            1,
            f"Historical data request failed ({type(error).__name__}). Check network and feed access.\n",
        )
    except ValueError as error:
        parser.exit(2, f"{error}\n")


if __name__ == "__main__":
    main()
