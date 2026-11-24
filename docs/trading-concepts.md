# Reading a daily stock bar

A share represents ownership in one company. MSFT identifies Microsoft. An exchange-traded fund (ETF) holds a portfolio and its shares trade on exchanges. An exchange matches buyers and sellers. One stock can trade on multiple venues, so the selected feed affects the observations.

| Field | Synthetic MSFT example | Meaning within the feed |
| --- | ---: | --- |
| Open | $100 | First eligible trade price |
| High | $105 | Highest eligible price |
| Low | $99 | Lowest eligible price |
| Close | $103 | Last eligible trade price |
| Volume | 12,300 | Shares traded |

The example gained 3% from open to close. Computing the daily close-to-close return requires the previous session's close. The order of the intraday high and low cannot be reconstructed from these five fields.

The regular US equity session runs from 09:30 to 16:00 New York time, with holiday closures and some early closes. A daily timestamp labels the session. Its closing price becomes available after the session. [NYSE hours](https://www.nyse.com/trade/hours-calendars)

The bid is the highest quoted buying price and the ask is the lowest quoted selling price. A $100.00 bid and $100.04 ask give a $0.04 spread. A market order prioritizes execution and its price can move. A buy limit of $100 sets the highest acceptable purchase price and may remain unfilled. Liquidity describes how easily size trades without moving the price. Volatility describes variation in returns over time. [SEC order guide](https://www.investor.gov/introduction-investing/investing-basics/how-stock-markets-work/types-orders)

A dividend distributes value to shareholders. A two-for-one stock split doubles the share count and roughly halves the per-share price. A raw close series can therefore show an apparent 50% decline without a corresponding economic loss. Keep the adjustment setting with every observation set. Alpaca's all-adjusted history incorporates splits, dividends and spin-offs. A newly downloaded adjusted history can reflect events that were unknown on earlier dates. [Alpaca adjustments](https://docs.alpaca.markets/us/reference/stockbars)

Selecting MSFT today introduces survivorship and selection bias if results are generalized to the historical market. A broader study needs a universe reconstructed as of each research date.
