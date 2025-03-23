import pandas as pd
import numpy as np
import MetaTrader5 as mt5
from ta.volatility import BollingerBands, AverageTrueRange
from ta.trend import SMAIndicator
import time
import requests
from bs4 import BeautifulSoup
import sys
import colorama
from colorama import Fore, Style
import itertools

colorama.init(autoreset=True)

# --- Connect to MetaTrader 5 ---
mt5.initialize()

# --- User Input for Currency Pair ---
symbol = input("Enter currency pair (e.g., EURUSD): ").strip().upper()
timeframes = {
    'M1': mt5.TIMEFRAME_M1,
    'M5': mt5.TIMEFRAME_M5,
    'M15': mt5.TIMEFRAME_M15,
    'H1': mt5.TIMEFRAME_H1,
    'H4': mt5.TIMEFRAME_H4,
    'D1': mt5.TIMEFRAME_D1
}
num_candles = 1000  # Fetch 1000 Candles for Live Updates

# --- Function to Show Progress Bar ---
def progress_bar(task_name, duration=5, bar_length=30):
    for i in range(duration + 1):
        progress = int((i / duration) * bar_length)
        bar = "█" * progress + "-" * (bar_length - progress)
        sys.stdout.write(f"\r{Fore.CYAN}{task_name}: [{bar}] {int((i/duration)*100)}%{Style.RESET_ALL} ")
        sys.stdout.flush()
        time.sleep(0.5)
    sys.stdout.write("\r" + " " * (bar_length + len(task_name) + 10) + "\r")  # Clear the line
    sys.stdout.flush()

# --- Function to Show Countdown While Waiting ---
def countdown_timer(duration=60):
    for remaining in range(duration, 0, -1):
        sys.stdout.write(f"\r{Fore.YELLOW}Waiting for next analysis in {remaining} seconds...{Style.RESET_ALL}   ")
        sys.stdout.flush()
        time.sleep(1)
    sys.stdout.write("\r" + " " * 50 + "\r")  # Clear the countdown line properly
    sys.stdout.flush()

# --- Function to Fetch Latest Data ---
def fetch_data(timeframe):
    progress_bar(f"Fetching {timeframe} data")
    data = mt5.copy_rates_from_pos(symbol, timeframe, 0, num_candles)
    df = pd.DataFrame(data)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    df.set_index('time', inplace=True)
    return df

# --- Function to Fetch High-Impact News ---
def check_high_impact_news():
    progress_bar("Checking high-impact news")
    url = "https://www.forexfactory.com/calendar"
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.content, "html.parser")
    
    news_items = soup.find_all("tr", class_="calendar__row")
    upcoming_news = []
    
    for item in news_items:
        impact = item.find("td", class_="impact")
        if impact and "high" in str(impact):  # High impact news
            time = item.find("td", class_="time").text.strip()
            currency = item.find("td", class_="currency").text.strip()
            event = item.find("td", class_="event").text.strip()
            upcoming_news.append(f"{time} - {currency}: {event}")
    
    return upcoming_news

# --- Function to Perform BBMA Analysis ---
def analyze_bbma(df):
    bb = BollingerBands(close=df['close'], window=20, window_dev=2)
    df['BB_Upper'] = bb.bollinger_hband()
    df['BB_Lower'] = bb.bollinger_lband()
    df['Mid_BB'] = bb.bollinger_mavg()
    df['SMA200'] = SMAIndicator(df['close'], window=200).sma_indicator()
    df['ATR'] = AverageTrueRange(df['high'], df['low'], df['close'], window=14).average_true_range()
    
    df['Reentry'] = ((df['close'] < df['BB_Upper']) & (df['close'] > df['Mid_BB'])) | \
                    ((df['close'] > df['BB_Lower']) & (df['close'] < df['Mid_BB']))
    df['Momentum'] = ((df['close'] > df['BB_Upper']) & (df['close'].shift(1) < df['BB_Upper'])) | \
                     ((df['close'] < df['BB_Lower']) & (df['close'].shift(1) > df['BB_Lower']))
    
    df['Signal'] = 'Hold'
    df['Take_Profit'] = np.nan
    
    df.loc[df['Reentry'] & (df['Momentum']), 'Signal'] = 'Buy'
    df.loc[df['Reentry'] & (~df['Momentum']), 'Signal'] = 'Sell'
    
    df['Trending'] = df['close'] > df['SMA200']
    df['Ranging'] = df['BB_Upper'] - df['BB_Lower'] < df['BB_Upper'].median()
    
    df['Filtered_Signal'] = df['Signal']
    df.loc[df['Ranging'], 'Filtered_Signal'] = 'Hold'  # Avoid trading in ranging market
    df.loc[df['ATR'] > df['ATR'].quantile(0.9), 'Filtered_Signal'] = 'Hold'  # Avoid high volatility
    
    return df

# --- Real-Time Multi-Timeframe Analysis ---
while True:
    signals = {}
    tp_values = {}
    timestamp = pd.Timestamp.now()
    
    news_events = check_high_impact_news()
    
    for tf_name, tf_value in timeframes.items():
        df = fetch_data(tf_value)
        df = analyze_bbma(df)
        latest_signal = df[['close', 'Filtered_Signal', 'Take_Profit']].tail(1)
        signals[tf_name] = latest_signal['Filtered_Signal'].values[0]
        tp_values[tf_name] = round(latest_signal['Take_Profit'].values[0], 5) if not np.isnan(latest_signal['Take_Profit'].values[0]) else None
    
    if news_events:
        final_decision = 'HOLD (Due to News)'
    elif all(sig == 'Buy' for sig in signals.values()):
        final_decision = 'BUY'
    elif all(sig == 'Sell' for sig in signals.values()):
        final_decision = 'SELL'
    else:
        final_decision = 'HOLD'
    
    take_profit_suggestions = {
        'TP1 (M1)': tp_values.get('M1', None),
        'TP2 (M15)': tp_values.get('M15', None),
        'TP3 (H1)': tp_values.get('H1', None)
    }
    
    print("\n========================================")
    print(f"Timestamp: {timestamp}")
    print(f"Currency Pair: {symbol}")
    print(f"Signals: {signals}")
    print(f"\nFinal Decision: {final_decision}")
    print(f"Suggested Take Profit Points: {take_profit_suggestions}")
    print("")
    if news_events:
        print("⚠️ High-impact news detected, avoid trading ⚠️")
        for news in news_events:
            print(news)
    
    countdown_timer(60)  # Countdown while waiting for next signal

# --- Shutdown MT5 Connection (Never Reached in Loop, but Useful for Debugging) ---
mt5.shutdown()
