# Opening Range Breakout (ORB) Backtester

A Python backtesting engine for the **5-minute Opening Range Breakout** strategy on Indian stocks and indices, with full risk management including dynamic position sizing and a fixed Risk-Reward ratio.

---

## What This Does

The Opening Range Breakout is one of the most widely used intraday strategies. The idea is simple: the first 5-minute candle of the trading day defines a "range." If price breaks above that range, you go long. If it breaks below, you go short. You hold until your target or stop-loss is hit.

This backtester automates that entire process across **60 days of 5-minute data**, so you can see exactly how the strategy has performed — trade by trade — rather than relying on gut feel.

### What makes this different from a basic backtest:
- **Dynamic position sizing**: risk per trade is capped at 2% of current capital — so position size adjusts as your balance grows or shrinks
- **Strict 1:2 Risk-Reward**: target is always 2× the stop distance, enforced automatically
- **Full trade log**: every day is recorded — whether a trade was taken, whether it hit target or stop, and the exact ₹ PnL

---

## Strategy Logic

```
1. Define Opening Range = High and Low of the first 5-minute candle
2. If any subsequent candle breaks ABOVE the range high → Enter LONG
   - Stop Loss = Opening Range Low
   - Target = Entry + (2 × Range Size)
3. If any subsequent candle breaks BELOW the range low → Enter SHORT
   - Stop Loss = Opening Range High
   - Target = Entry - (2 × Range Size)
4. Position size = floor((2% of capital) / Range Size)
5. Exit at SL, Target, or end of day — whichever comes first
```

---

## How to Run

**1. Install dependencies**
```bash
pip install yfinance pandas numpy
```

**2. Run the script**
```bash
python ORB.py
```

**3. Follow the prompt**
```
Enter stock ticker (e.g., RELIANCE, TCS, or ^NSEI for NIFTY 50): NIFTY
```
The script automatically appends `.NS` for Indian stocks. For Nifty 50, enter `^NSEI`.

---

## Example Output

```
Performance Summary
Starting Balance: Rs 100,000.00
Final Balance:    Rs 112,430.00
Total PnL (Rs):   Rs 12,430.00
---------------------------
Total Days Tested: 60
Total Trading Days: 47
No-Trade Days: 13
---------------------------
Wins (Target Hit): 24
Losses (Stop Hit): 19
Held to EOD: 4
Win Rate: 51.06%
---------------------------
Profit Factor (Rs): 1.84
Average Win (Rs):   Rs 1,240.00
Average Loss (Rs):  Rs -620.00
```

---

## Configuration

You can change these parameters directly in the script:

```python
PERIOD_TO_TEST   = '60d'    # Max 60 days for 5-minute data (yfinance limit)
RR_RATIO         = 2.0      # Risk-Reward ratio (1:2 by default)
STARTING_BALANCE = 100000.0 # Starting capital in ₹
RISK_PER_TRADE   = 0.02     # 2% of capital risked per trade
```

---

## Performance Metrics Explained

| Metric | What It Tells You |
|--------|------------------|
| **Win Rate** | % of trades that hit the target |
| **Profit Factor** | Total profits ÷ Total losses. > 1.0 means the strategy is profitable |
| **Average Win / Loss** | With a 1:2 RR, average win should be ~2× average loss |
| **No-Trade Days** | Days where no breakout occurred — the strategy correctly sat out |

---

## Tech Stack

| Library | Purpose |
|---------|---------|
| `yfinance` | 5-minute OHLCV data via Yahoo Finance |
| `pandas` | Trade log and results analysis |
| `numpy` | Numerical calculations |
| `math` | Floor rounding for integer share quantities |

---

## Key Design Decisions

**Why drift-free position sizing?** Using a fixed % of *current* capital (not starting capital) means position sizes shrink during drawdowns, protecting the account from compounding losses — a critical feature missing from most amateur backtests.

**Why only one trade per day?** The ORB strategy fires once at market open. Taking multiple trades would require a different framework (e.g., re-entry logic) and is out of scope here.

**Why 5-minute candles?** The opening range is typically defined on the first 5 or 15 minutes. 5-minute data gives more granular entry/exit simulation than daily bars.

---

## Limitations

- yfinance provides maximum 60 days of 5-minute data, so the backtest window is limited
- Slippage and brokerage costs are not modelled — real-world returns will be slightly lower
- Past performance on backtested data does not guarantee future results

---

*This is not financial advice. Built for educational and research purposes.*
