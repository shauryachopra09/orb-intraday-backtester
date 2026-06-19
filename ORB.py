import yfinance as yf
import pandas as pd
import math  # Import math for rounding
import numpy as np  # Import numpy for data handling


def run_orb_backtest(ticker_symbol,
                     starting_balance,
                     risk_per_trade_percent=0.02,
                     period='60d',
                     risk_reward_ratio=2.0):
    """
    Runs a backtest of the 5-minute Opening Range Breakout (ORB) strategy
    over a specified period with capital and risk management.

    Parameters:
    - ticker_symbol: The stock or index symbol (e.g., 'RELIANCE.NS', '^NSEI').
    - starting_balance: The initial capital in Rupees (e.g., 100000).
    - risk_per_trade_percent: The percentage of capital to risk per trade (e.g., 0.02 for 2%).
    - period: The historical period to test (e.g., '60d', '30d').
    - risk_reward_ratio: The desired ratio of target profit to stop loss.
    """

#Fetch Historical Data
    try:
        data = yf.download(ticker_symbol,
                           period=period,
                           interval='5m',
                           auto_adjust=False,
                           progress=False)
    except Exception as e:
        print(f"Error fetching data: {e}")
        return

    if data.empty:
        print(f"No data fetched for {ticker_symbol}. Is the market open or the ticker correct?")
        return

#Pre-process Data
#Ensure index is timezone-naive for easier grouping
    try:
        data.index = data.index.tz_localize(None)
    except TypeError:
        # Index is already naive, but yfinance sometimes adds UTC. This handles both cases.
        pass

    data['date'] = data.index.date
    grouped_by_day = data.groupby('date')

    results_list = []
    current_balance = starting_balance

#Loop through each day in the backtest period
    for date, daily_data in grouped_by_day:

#Ensure there are enough candles for a trade
        if len(daily_data) < 2:
            results_list.append(
                {'date': date, 'outcome': 'NO_DATA', 'pnl_points': 0, 'pnl_rs': 0, 'reason': 'Not enough data'})
            continue

#Apply Daily ORB Logic
#Get all high/low/close values for the day as NumPy arrays
        try:
            high_values = daily_data['High'].values
            low_values = daily_data['Low'].values
            close_values = daily_data['Close'].values

#Get opening range from the first candle (index 0)
            opening_range_high = high_values[0]
            opening_range_low = low_values[0]
        except (KeyError, IndexError):
            results_list.append(
                {'date': date, 'outcome': 'NO_DATA', 'pnl_points': 0, 'pnl_rs': 0, 'reason': 'Data read error'})
            continue

        trade_range = opening_range_high - opening_range_low
        if trade_range <= 0:  # Check for zero range
            results_list.append(
                {'date': date, 'outcome': 'NO_TRADE', 'pnl_points': 0, 'pnl_rs': 0, 'reason': 'Zero/Negative range'})
            continue

        target_points = trade_range * risk_reward_ratio

#Calculate Position Size based on Risk
        risk_per_trade_rs = current_balance * risk_per_trade_percent
        number_of_shares = math.floor(risk_per_trade_rs / trade_range)  # Floor the number of shares

        if number_of_shares == 0:
            results_list.append({'date': date, 'outcome': 'NO_TRADE', 'pnl_points': 0, 'pnl_rs': 0,
                                 'reason': 'Insufficient capital for risk'})
            continue



        trade_taken = False
        trade_type = None
        entry_price = 0.0
        stop_loss = 0.0
        target_profit = 0.0
        day_result = {'date': date, 'outcome': 'NO_TRADE', 'pnl_points': 0, 'pnl_rs': 0, 'reason': 'No breakout'}
        pnl_rs = 0.0  # Track Rupee PnL for the day

#Loop from the second candle onwards for the day looking for breakout
        for i in range(1, len(daily_data)):

#Get current candle data from NumPy arrays
            try:
                current_low = low_values[i]
                current_high = high_values[i]
            except (KeyError, IndexError):
                continue

#Check for trade exit
            if trade_taken:
                if trade_type == 'LONG':
                    if current_low <= stop_loss:
                        pnl_points = -trade_range
                        pnl_rs = pnl_points * number_of_shares
                        current_balance += pnl_rs
                        day_result = {'date': date, 'outcome': 'SL_HIT', 'pnl_points': pnl_points, 'pnl_rs': pnl_rs}
                        break
                    elif current_high >= target_profit:
                        pnl_points = target_points
                        pnl_rs = pnl_points * number_of_shares
                        current_balance += pnl_rs
                        day_result = {'date': date, 'outcome': 'TARGET_HIT', 'pnl_points': pnl_points, 'pnl_rs': pnl_rs}
                        break
                elif trade_type == 'SHORT':
                    if current_high >= stop_loss:
                        pnl_points = -trade_range
                        pnl_rs = pnl_points * number_of_shares
                        current_balance += pnl_rs
                        day_result = {'date': date, 'outcome': 'SL_HIT', 'pnl_points': pnl_points, 'pnl_rs': pnl_rs}
                        break
                    elif current_low <= target_profit:
                        pnl_points = target_points
                        pnl_rs = pnl_points * number_of_shares
                        current_balance += pnl_rs
                        day_result = {'date': date, 'outcome': 'TARGET_HIT', 'pnl_points': pnl_points, 'pnl_rs': pnl_rs}
                        break
#Check for trade entry (After trade exit as it nullifies previous candle and then focuses on the next one)
            if not trade_taken:
                if current_high > opening_range_high:
                    trade_taken = True
                    trade_type = 'LONG'
                    entry_price = opening_range_high
                    stop_loss = opening_range_low
                    target_profit = entry_price + target_points
                    day_result = {'date': date, 'outcome': 'EOD_OPEN', 'pnl_points': 0,
                                  'pnl_rs': 0}  # Default if not closed
                elif current_low < opening_range_low:
                    trade_taken = True
                    trade_type = 'SHORT'
                    entry_price = opening_range_low
                    stop_loss = opening_range_high
                    target_profit = entry_price - target_points
                    day_result = {'date': date, 'outcome': 'EOD_OPEN', 'pnl_points': 0,
                                  'pnl_rs': 0}  # Default if not closed

#End of Day Check
        if trade_taken and day_result['outcome'] == 'EOD_OPEN':
            #Get last closing price from NumPy array
            try:
                last_price = close_values[-1]
                if trade_type == 'LONG':
                    pnl_points = last_price - entry_price
                else:  # SHORT
                    pnl_points = entry_price - last_price

                pnl_rs = pnl_points * number_of_shares
                current_balance += pnl_rs
                day_result['pnl_points'] = pnl_points
                day_result['pnl_rs'] = pnl_rs

            except (KeyError, IndexError):
                day_result['outcome'] = 'EOD_OPEN'
                day_result['pnl_points'] = 0
                day_result['pnl_rs'] = 0
                day_result['reason'] = 'EOD price read error'

        results_list.append(day_result)

#Analyze and Print Results
    if not results_list:
        print("No trades were analyzed.")
        return

    results_df = pd.DataFrame(results_list)

    total_days = len(results_df)
    trade_days = results_df[results_df['outcome'].isin(['SL_HIT', 'TARGET_HIT', 'EOD_OPEN'])]
    total_trades = len(trade_days)

    no_trade_days = results_df[~results_df['outcome'].isin(['SL_HIT', 'TARGET_HIT', 'EOD_OPEN'])]

    wins = trade_days[trade_days['outcome'] == 'TARGET_HIT']
    losses = trade_days[trade_days['outcome'] == 'SL_HIT']
    eod_open = trade_days[trade_days['outcome'] == 'EOD_OPEN']

    win_rate = (len(wins) / total_trades) * 100 if total_trades > 0 else 0
    total_pnl_points = float(results_df['pnl_points'].sum())
    total_pnl_rs = float(results_df['pnl_rs'].sum())

    avg_win_rs = float(wins['pnl_rs'].mean()) if len(wins) > 0 else 0.0
    avg_loss_rs = float(losses['pnl_rs'].mean()) if len(losses) > 0 else 0.0

    # Calculate profit factor
    total_profit_rs = float(wins['pnl_rs'].sum())
    total_loss_rs = float(abs(losses['pnl_rs'].sum()))
    profit_factor_rs = total_profit_rs / total_loss_rs if total_loss_rs > 0 else float('inf')

    print("Performance Summary")
    print(f"Starting Balance: Rs {starting_balance:,.2f}")

    print(f"Final Balance:    Rs {float(current_balance):,.2f}")
    print(f"Total PnL (Rs):   Rs {total_pnl_rs:,.2f}")
    print(f"Total PnL (Points): {total_pnl_points:.2f}")
    print("-" * 27)
    print(f"Total Days Tested: {total_days}")
    print(f"Total Trading Days: {total_trades}")
    print(f"No-Trade Days: {total_days - total_trades}")
    print("-" * 27)
    print(f"Wins (Target Hit): {len(wins)}")
    print(f"Losses (Stop Hit): {len(losses)}")
    print(f"Held to EOD: {len(eod_open)}")
    print(f"Win Rate: {win_rate:.2f}%")
    print("-" * 27)
    print(f"Profit Factor (Rs): {profit_factor_rs:.2f}")
    print(f"Average Win (Rs):   Rs {avg_win_rs:,.2f}")
    print(f"Average Loss (Rs):  Rs {avg_loss_rs:,.2f}")

if __name__ == "__main__":


#Get ticker input from user
    ticker_input = input("Enter stock ticker (e.g., RELIANCE, TCS, or ^NSEI for NIFTY 50): ").strip().upper()
    if not ticker_input.startswith('^') and not ticker_input.endswith('.NS'):
        TICKER = ticker_input + '.NS'
        print(f"Assuming Indian stock, using: {TICKER}")
    else:
        TICKER = ticker_input
        print(f"Using ticker: {TICKER}")

    PERIOD_TO_TEST = '60d'  # Max 60 days for 5m interval
    RR_RATIO = 2.0  # 1:2 Risk/Reward Ratio
    STARTING_BALANCE = 100000.0
    RISK_PER_TRADE = 0.02  # 2% risk per trade

    run_orb_backtest(TICKER,
                     starting_balance=STARTING_BALANCE,
                     risk_per_trade_percent=RISK_PER_TRADE,
                     period=PERIOD_TO_TEST,
                     risk_reward_ratio=RR_RATIO)

