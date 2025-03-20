import pandas as pd
import numpy as np
import MetaTrader5 as mt5
from ta.volatility import BollingerBands
from ta.trend import SMAIndicator
import time

# --- Connect to MetaTrader 5 ---
mt5.initialize()

# --- User Input for Currency Pair ---
symbol = input("Enter currency pair (e.g., EURUSD): ").strip().upper()
timeframe = mt5.TIMEFRAME_M1  # 1-Minute Data for Real-time Analysis
num_candles = 1000  # Fetch 1000 Candles for Live Updates

# --- Function to Fetch Latest Data ---
def fetch_data():
    data = mt5.copy_rates_from_pos(symbol, timeframe, 0, num_candles)
    df = pd.DataFrame(data)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    df.set_index('time', inplace=True)
    return df

# --- Function to Perform BBMA Analysis ---
def analyze_bbma(df):
    bb = BollingerBands(close=df['close'], window=20, window_dev=2)
    df['BB_Upper'] = bb.bollinger_hband()
    df['BB_Lower'] = bb.bollinger_lband()
    df['Mid_BB'] = bb.bollinger_mavg()
    df['MA5_High'] = SMAIndicator(df['close'], window=5).sma_indicator()
    df['MA10_High'] = SMAIndicator(df['close'], window=10).sma_indicator()

    df['Reentry'] = ((df['close'] < df['BB_Upper']) & (df['close'] > df['MA5_High'])) | \
                    ((df['close'] > df['BB_Lower']) & (df['close'] < df['MA5_High']))
    df['Momentum'] = ((df['close'] > df['BB_Upper']) & (df['close'].shift(1) < df['BB_Upper'])) | \
                     ((df['close'] < df['BB_Lower']) & (df['close'].shift(1) > df['BB_Lower']))

    df['Signal'] = 'Hold'
    df['Take_Profit'] = np.nan
    
    df.loc[df['Reentry'] & (df['Momentum']), 'Signal'] = 'Buy'
    df.loc[df['Signal'] == 'Buy', 'Take_Profit'] = df['close'] + (df['BB_Upper'] - df['Mid_BB'])
    
    df.loc[df['Reentry'] & (~df['Momentum']), 'Signal'] = 'Sell'
    df.loc[df['Signal'] == 'Sell', 'Take_Profit'] = df['close'] - (df['Mid_BB'] - df['BB_Lower'])
    
    return df

# --- Real-Time Analysis Loop (Without Graph) ---
while True:
    df = fetch_data()
    df = analyze_bbma(df)
    latest_signal = df[['close', 'Signal', 'Take_Profit']].tail(1)
    print(latest_signal)
    time.sleep(60)

# --- Shutdown MT5 Connection (Never Reached in Loop, but Useful for Debugging) ---
mt5.shutdown()
