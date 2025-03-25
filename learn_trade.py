import pandas as pd
import numpy as np
import MetaTrader5 as mt5
import joblib
import time
import os
import xgboost as xgb
import colorama
from colorama import Fore, Style
from ta.volatility import BollingerBands
from ta.trend import SMAIndicator

# Initialize colorama
colorama.init(autoreset=True)

# Initialize MetaTrader 5
mt5.initialize()

# User Input
symbol = input("Enter currency pair (e.g., EURUSD, XAUUSD, BTCUSD): ").strip().upper()
timeframes = {'M1': mt5.TIMEFRAME_M1, 'M5': mt5.TIMEFRAME_M5, 'M15': mt5.TIMEFRAME_M15, 'H1': mt5.TIMEFRAME_H1, 'H4': mt5.TIMEFRAME_H4, 'D1': mt5.TIMEFRAME_D1}
num_candles = 1000

# File Paths
trade_history_file = f"data/trade_history_{symbol}.csv"
learning_model_file = f"data/learning_{symbol}.joblib"

# Load or Initialize Model
def load_model():
    if os.path.exists(learning_model_file):
        return joblib.load(learning_model_file)
    return xgb.XGBRegressor()

model = load_model()

def fetch_data(timeframe):
    data = mt5.copy_rates_from_pos(symbol, timeframe, 0, num_candles)
    df = pd.DataFrame(data)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    df.set_index('time', inplace=True)
    return df

def analyze_bbma(df):
    bb = BollingerBands(close=df['close'], window=20, window_dev=2)
    df['BB_Upper'] = bb.bollinger_hband()
    df['BB_Lower'] = bb.bollinger_lband()
    df['Mid_BB'] = bb.bollinger_mavg()
    df['MA5_High'] = SMAIndicator(df['close'], window=5).sma_indicator()
    df['MA10_High'] = SMAIndicator(df['close'], window=10).sma_indicator()

    df['Reentry'] = ((df['close'] < df['BB_Upper']) & (df['close'] > df['MA5_High'])) | ((df['close'] > df['BB_Lower']) & (df['close'] < df['MA5_High']))
    df['Momentum'] = ((df['close'] > df['BB_Upper']) & (df['close'].shift(1) < df['BB_Upper'])) | ((df['close'] < df['BB_Lower']) & (df['close'].shift(1) > df['BB_Lower']))

    df['Signal'] = 'Hold'
    df.loc[df['Reentry'] & df['Momentum'], 'Signal'] = 'Buy'
    df.loc[df['Reentry'] & (~df['Momentum']), 'Signal'] = 'Sell'
    return df

def record_trade(entry_price, tp, sl):
    # Wait for trade to close
    while True:
        history_orders = mt5.history_deals_get(position=open_trade)
        if history_orders:
            break
        time.sleep(30)
    
    # Check if trade hit TP or SL
    for deal in history_orders:
        if deal.profit > 0:
            result = 'win'
        else:
            result = 'loss'
    
    os.makedirs('data', exist_ok=True)
    trade_data = pd.DataFrame([[entry_price, tp, sl, result]], columns=['Entry Price', 'TP', 'SL', 'Result'])
    if os.path.exists(trade_history_file):
        trade_data.to_csv(trade_history_file, mode='a', header=False, index=False)
    else:
        trade_data.to_csv(trade_history_file, mode='w', header=True, index=False)
    os.makedirs('data', exist_ok=True)
    trade_data = pd.DataFrame([[entry_price, tp, sl, result]], columns=['Entry Price', 'TP', 'SL', 'Result'])
    if os.path.exists(trade_history_file):
        trade_data.to_csv(trade_history_file, mode='a', header=False, index=False)
    else:
        trade_data.to_csv(trade_history_file, mode='w', header=True, index=False)

def retrain_model():
    if os.path.exists(trade_history_file):
        df = pd.read_csv(trade_history_file)
        if len(df) >= 30:
            X = df[['Entry Price', 'TP', 'SL']]
            y = df['Result'].apply(lambda x: 1 if x == 'win' else 0)
            model.fit(X, y)
            joblib.dump(model, learning_model_file)

def modify_trade(tp, sl):
    request = {
        "action": mt5.TRADE_ACTION_SLTP,
        "position": open_trade,
        "sl": sl,
        "tp": tp,
    }
    result = mt5.order_send(request)
    if result.retcode == mt5.TRADE_RETCODE_DONE:
        print(f"{Fore.CYAN}Updated TP: {tp}, SL: {sl} for open trade.{Style.RESET_ALL}")
    else:
        print(f"{Fore.RED}Failed to update TP/SL. Retcode: {result.retcode}{Style.RESET_ALL}")
        print(f"{Fore.RED}Last Error: {mt5.last_error()}{Style.RESET_ALL}")

def countdown_timer(seconds):
    for remaining in range(seconds, 0, -1):
        print(f"{Fore.YELLOW}Next analysis: {remaining} seconds...{Style.RESET_ALL}", end="\r", flush=True)
        time.sleep(1)
    print("\n")

open_trade = None

while True:
    signals = {}
    tp, sl = None, None
    timestamp = pd.Timestamp.now()
    print("\n========================================")
    print(f"{Fore.CYAN}Timestamp: {timestamp}{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}Fetching and analyzing data...{Style.RESET_ALL}")
    
    for tf_name, tf_value in timeframes.items():
        df = fetch_data(tf_value)
        df = analyze_bbma(df)
        signals[tf_name] = df['Signal'].iloc[-1]
    
    print(f"Signals:", signals)
    print(f"Suggested TP: {tp if tp else 'N/A'}, Suggested SL: {sl if sl else 'N/A'}")
    print(f"Suggested TP: {tp}, Suggested SL: {sl}")
    
    if all(sig == 'Buy' for sig in signals.values()):
        final_decision = 'BUY'
    elif all(sig == 'Sell' for sig in signals.values()):
        final_decision = 'SELL'
    else:
        final_decision = 'HOLD'
    
    print(f"{Fore.CYAN}Final Decision: {final_decision}{Style.RESET_ALL}")
    
    if open_trade:
        print(f"{Fore.YELLOW}Trade still floating. Adjusting TP and SL dynamically.{Style.RESET_ALL}")
        countdown_timer(60)
        continue
    
    if final_decision in ['BUY', 'SELL']:
        entry_price = mt5.symbol_info_tick(symbol).bid
        df_m15 = fetch_data(mt5.TIMEFRAME_M15)
        df_m15 = analyze_bbma(df_m15)
        latest_m15 = df_m15.iloc[-1]

        if final_decision == 'BUY':
            tp = latest_m15['BB_Upper']
            sl = latest_m15['BB_Lower']
        else:
            tp = latest_m15['BB_Lower']
            sl = latest_m15['BB_Upper']
        
        print(f"Executing {final_decision} trade for {symbol} with TP: {tp} and SL: {sl}")
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": 0.01,
            "type": mt5.ORDER_TYPE_BUY if final_decision == 'BUY' else mt5.ORDER_TYPE_SELL,
            "price": entry_price,
            "sl": sl,
            "tp": tp,
            "deviation": 10,
            "magic": 123456,
            "comment": f"Learning {symbol}",
            "type_filling": mt5.ORDER_FILLING_FOK
        }
        result = mt5.order_send(request)
        if result.retcode == mt5.TRADE_RETCODE_DONE:
            open_trade = result.order
            print(f"{Fore.GREEN}Trade executed successfully!{Style.RESET_ALL}")
            record_trade(entry_price, tp, sl)
        else:
            print(f"Trade execution failed. Retcode: {result.retcode}")
            print(f"Last Error: {mt5.last_error()}")
    
    retrain_model()
    print(f"Waiting for the next analysis cycle...")
    countdown_timer(60)
