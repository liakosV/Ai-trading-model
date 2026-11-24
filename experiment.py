"""Compare a daily MSFT direction model with an always-up baseline."""

import json
import math
from datetime import datetime, timezone
from urllib.request import Request, urlopen


def load_prices():

    url = (
        "https://query1.finance.yahoo.com/v8/finance/chart/MSFT"
        "?period1=1262304000&period2=1767225600&interval=1d"
    )

    with urlopen(Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=30) as response:
        chart = json.load(response)["chart"]["result"][0]
    closes = chart["indicators"]["quote"][0]["close"]

    return [
        (datetime.fromtimestamp(t, timezone.utc).date(), p)
        for t, p in zip(chart["timestamp"], closes, strict=True)
    ]


def main():
    prices = load_prices()

    samples = []
    
    for i in range(5, len(prices) - 1):
        window = [p for _, p in prices[i - 5:i + 2]]
        if any(p is None or p <= 0 for p in window):
            continue
        features = [1, 100 * math.log(window[5] / window[4]),
                    100 * math.log(window[5] / window[0])]
        samples.append((prices[i + 1][0], features, int(window[6] > window[5])))
    
    if len(samples) < 100:
        raise ValueError("Insufficient price history")
    
    split = len(samples) * 4 // 5
    
    train, test = samples[:split], samples[split:]
    
    weights = [0.0] * 3
    
    for epoch in range(30):
        for _, features, label in train:
            score = sum(w * x for w, x in zip(weights, features))
           
            probability = 1 / (1 + math.exp(-max(-40, min(40, score))))
          
            for j, x in enumerate(features):
                weights[j] += 0.001 / (1 + epoch) * (label - probability) * x
    
    correct = sum((sum(w * x for w, x in zip(weights, f)) >= 0) == y for _, f, y in test)
    
    print(f"MSFT | Test: {test[0][0]} to {test[-1][0]} ({len(test)} sessions)")
    
    print(f"Model accuracy: {correct / len(test):.2%}")
    
    print(f"Always-up accuracy: {sum(y for _, _, y in test) / len(test):.2%}")


if __name__ == "__main__":
    main()
