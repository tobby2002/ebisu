# coding: UTF-8

import base64
import logging
import logging.handlers
import os
import time
import uuid
from datetime import timedelta
import datetime
import numpy as np
import pandas as pd
import requests
import talib
import pandas as pd

from bravado.exception import HTTPError

# logging settings for console and file by neo
logger = logging.getLogger(__name__)

logger.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - [%(levelname)s] (%(filename)s:%(lineno)d) > %(message)s')

log_max_size = 10 * 1024 * 1024  # 10M
log_file_count = 20  # allow until 20 files
log_filename = datetime.datetime.now().strftime('%Y-%m-%d') + '.log'
# fileHandler = logging.handlers.RotatingFileHandler(filename=log_filename, maxBytes=log_max_size, backupCount=log_file_count)
fileHandler = logging.FileHandler(filename=os.path.join('log', log_filename))

streamHandler = logging.StreamHandler()
fileHandler.setFormatter(formatter)
streamHandler.setFormatter(formatter)  # for console, if you want to hide, comment this line

logger.addHandler(fileHandler)
logger.addHandler(streamHandler)


# resolution
allowed_range = {
    "1m": ["1m", "1T", 1, 1], "2m":  ["1m", "2T", 2, 2], "3m":  ["1m", "3T", 3, 3],
    "4m": ["1m", "4T", 4, 4], "5m": ["1m", "5T", 5, 5], "6m": ["1m", "6T", 6, 6],
    "7m": ["1m", "7T", 7, 7], "8m": ["1m", "8T", 8, 8], "9m": ["1m", "9T", 9, 9],
    "10m": ["1m", "10T", 10, 10], "11m": ["1m", "11T", 11, 11], "15m": ["5m", "15T", 3, 15], "30m": ["5m", "30T", 6, 30],
    "1h": ["1h", "1H", 1, 1], "2h":  ["1h", "2H", 2, 2],
    "3h": ["1h", "3H", 3, 3], "4h":  ["1h", "4H", 4, 4],
    "6h": ["1h", "6H", 6, 6], "12h": ["1h", "12H", 12, 12],
    "1d": ["1d", "1D", 1, 1],
    # not support yet '3d', '1w', '2w', '1m'
}


class FatalError(Exception):
    pass

def ord_suffix():
    return "_" + base64.b64encode(uuid.uuid4().bytes).decode('utf-8').rstrip('=\n')

def load_data(file):
    """
    파일에서 데이타를 읽음
    """
    source = pd.read_csv(file)
    data_frame = pd.DataFrame({
        'timestamp': pd.to_datetime(source['timestamp']),
        'open': source['open'],
        'close': source['close'],
        'high': source['high'],
        'low': source['low'],
        'volume': source['volume']
    })
    data_frame = data_frame.set_index('timestamp')
    return data_frame.tz_localize(None).tz_localize('UTC', level=0)


def validate_continuous(data, bin_size):
    last_date = None
    for i in range(len(data)):
        index = data.iloc[-1 * (i + 1)].name
        if last_date is None:
            last_date = index
            continue
        if last_date - index != delta(bin_size):
            return False, index
        last_date = index
    return True, None


def to_data_frame(data):
    data_frame = pd.DataFrame(data, columns=["timestamp", "high", "low", "open", "close", "volume"])
    # print('[data_frame]:\n%s' % data_frame)
    data_frame = data_frame.set_index("timestamp")
    data_frame = data_frame.tz_localize(None).tz_localize('UTC', level=0)
    return data_frame


def resample(data_frame, bin_size):
    resample_time = allowed_range[bin_size][1]
    return data_frame.resample(resample_time).agg({
        "open": "first",
        "high": "max",
        "low": "min",
        "close": "last",
        "volume": "sum",
    })


def retry(func, count=5):
    err = None
    for i in range(count):
        try:
            ret, res = func()
            rate_limit = int(res.headers['X-RateLimit-Limit'])
            rate_remain = int(res.headers['X-RateLimit-Remaining'])
            if rate_remain < 10:
                time.sleep(5 * 60 * (1 + rate_limit - rate_remain) / rate_limit)
            return ret
        except HTTPError as error:
            status_code = error.status_code
            err = error
            if status_code >= 500:
                time.sleep(pow(2, i + 1))
                continue
            elif status_code == 400 or \
                    status_code == 401 or \
                    status_code == 402 or \
                    status_code == 403 or \
                    status_code == 404 or \
                    status_code == 429:
                raise FatalError(error)
    raise err


class Side:
    Long = "Long"
    Short = "Short"
    Close = "Close"
    Unknown = "Unknown"


def first(l=[]):
    return l[0]


def last(l=[]):
    return l[-1]


def highest(source, period):
    return pd.Series(source).rolling(period).max().values


def lowest(source, period):
    return pd.Series(source).rolling(period).min().values


def stdev(source, period):
    return pd.Series(source).rolling(period).std().values


def sma(source, period):
    return pd.Series(source).rolling(period).mean().values


def ema(source, period):
    return talib.EMA(np.array(source), period)


def double_ema(src, length):
    ema_val = ema(src, length)
    return 2 * ema_val - ema(ema_val, length)


def triple_ema(src, length):
    ema_val = ema(src, length)
    return 3 * (ema_val - ema(ema_val, length)) + ema(ema(ema_val, length), length)


def wma(src, length):
    return talib.WMA(src, length)


def ssma(src, length):
    return pd.Series(src).ewm(alpha=1.0 / length).mean().values.flatten()


def hull(src, length):
    return wma(2 * wma(src, length / 2) - wma(src, length), round(np.sqrt(length)))


def bbands(source, timeperiod=5, nbdevup=2, nbdevdn=2, matype=0):
    return talib.BBANDS(source, timeperiod, nbdevup, nbdevdn, matype)


def macd(close, fastperiod=12, slowperiod=26, signalperiod=9):
    return talib.MACD(close, fastperiod, slowperiod, signalperiod)


def adx(high, low, close, period=14):
    return talib.ADX(high, low, close, period)


def di_plus(high, low, close, period=14):
    return talib.PLUS_DI(high, low, close, period)


def di_minus(high, low, close, period=14):
    return talib.MINUS_DI(high, low, close, period)


def rsi(close, period=14):
    return talib.RSI(close, period)


def sar(high, low, acceleration=0, maximum=0):
    return talib.SAR(high, low, acceleration, maximum)


def delta(bin_size='1h'):
    if bin_size.endswith('d'):
        return timedelta(days=allowed_range[bin_size][3])
    elif bin_size.endswith('h'):
        return timedelta(hours=allowed_range[bin_size][3])
    elif bin_size.endswith('m'):
        return timedelta(minutes=allowed_range[bin_size][3])


def notify(message: object, fileName: object = None) -> object:
    url = 'https://notify-api.line.me/api/notify'
    # api_key = os.environ.get('LINE_APIKEY')
    api_key = ''
    if api_key is None or len(api_key) == 0:
        return

    payload = {'message': message}
    headers = {'Authorization': 'Bearer ' + api_key}
    if fileName is None:
        try:
            requests.post(url, data=payload, headers=headers)
        except:
            pass
    else:
        try:
            files = {"imageFile": open(fileName, "rb")}
            requests.post(url, data=payload, headers=headers, files=files)
        except:
            pass


def crossover(a, b):
    return a[-2] < b[-2] and a[-1] > b[-1]


def crossunder(a, b):
    return a[-2] > b[-2] and a[-1] < b[-1]


def over(a, b):
    if a > b:
        return True
    return False


def under(a, b):
    if a < b:
        return True
    return False

def ord(seq, sort_seq, idx, itv):
    p = seq[idx]
    for i in range(0, itv):
        if p >= sort_seq[i]:
            return i + 1


def d(src, itv):
    sort_src = np.sort(src)[::-1]
    sum = 0.0
    for i in range(0, itv):
        sum += pow((i + 1) - ord(src, sort_src, i, itv), 2)
    return sum


def rci(src, itv):
    reversed_src = src[::-1]
    ret = [(1.0 - 6.0 * d(reversed_src[i:i + itv], itv) / (itv * (itv * itv - 1.0))) * 100.0
           for i in range(2)]
    return ret[::-1]


def vix(close, low, pd=23, bbl=23, mult=1.9, lb=88, ph=0.85, pl=1.01):
    hst = highest(close, pd)
    wvf = (hst - low) / hst * 100
    s_dev = mult * stdev(wvf, bbl)
    mid_line = sma(wvf, bbl)
    lower_band = mid_line - s_dev
    upper_band = mid_line + s_dev

    range_high = (highest(wvf, lb)) * ph
    range_low = (lowest(wvf, lb)) * pl

    green_hist = [wvf[-i] >= upper_band[-i] or wvf[-i] >= range_high[-i] for i in range(8)][::-1]
    red_hist = [wvf[-i] <= lower_band[-i] or wvf[-i] <= range_low[-i] for i in range(8)][::-1]

    return green_hist, red_hist


def vwap(high, low, volume):
    average_price = volume * (high + low) / 2
    return average_price.sum() / volume.sum()


def is_under(src, value, p):
    for i in range(p, -1, -1):
        if src[-i - 1] > value:
            return False
    return True

def is_over(src, value, p):
    for i in range(p, -1, -1):
        if src[-i - 1] < value:
            return False
    return True

def atr(high, low, close, period=14):
    return talib.ATR(high, low, close, period)

def supertrend(df, f, n): #df is the dataframe, n is the period, f is the factor; f=3, n=7 are commonly used.
    #Calculation of ATR
    pd.options.mode.chained_assignment = None
    df['H-L']=abs(df['high']-df['low'])
    df['H-PC']=abs(df['high']-df['close'].shift(1))
    df['L-PC']=abs(df['low']-df['close'].shift(1))
    df['TR']=df[['H-L','H-PC','L-PC']].max(axis=1)
    df['ATR']=np.nan
    df.ix[n-1,'ATR']=df['TR'][:n-1].mean() #.ix is deprecated from pandas verion- 0.19
    for i in range(n,len(df)):
        df['ATR'][i]=(df['ATR'][i-1]*(n-1)+ df['TR'][i])/n

    #Calculation of SuperTrend
    df['Upper Basic']=(df['high']+df['low'])/2+(f*df['ATR'])
    df['Lower Basic']=(df['high']+df['low'])/2-(f*df['ATR'])
    df['Upper Band']=df['Upper Basic']
    df['Lower Band']=df['Lower Basic']
    df['Trend']=True  # Up(case of Bull or Long)-> True, Dn-> False
    df['TSL']=None  # Trailing Stop Loss Value
    for i in range(n,len(df)):
        if df['close'][i-1]<=df['Upper Band'][i-1]:
            df['Upper Band'][i]=min(df['Upper Basic'][i],df['Upper Band'][i-1])
        else:
            df['Upper Band'][i]=df['Upper Basic'][i]
    for i in range(n,len(df)):
        if df['close'][i-1]>=df['Lower Band'][i-1]:
            df['Lower Band'][i]=max(df['Lower Basic'][i],df['Lower Band'][i-1])
        else:
            df['Lower Band'][i]=df['Lower Basic'][i]
    df['SuperTrend']=np.nan
    for i in df['SuperTrend']:
        if df['close'][n-1]<=df['Upper Band'][n-1]:
            df['SuperTrend'][n-1]=df['Upper Band'][n-1]
            df['Trend'][n-1]=False
            df['TSL'][n-1]=df['Upper Band'][n-1]
        elif df['close'][n-1]>df['Upper Band'][i]:
            df['SuperTrend'][n-1]=df['Lower Band'][n-1]
            df['Trend'][n-1]=True
            df['TSL'][n-1]=df['Lower Band'][n-1]
    for i in range(n,len(df)):
        if df['SuperTrend'][i-1]==df['Upper Band'][i-1] and df['close'][i]<=df['Upper Band'][i]:
            df['SuperTrend'][i]=df['Upper Band'][i]
            df['Trend'][i]=False
            df['TSL'][i]=df['Upper Band'][i]
        elif  df['SuperTrend'][i-1]==df['Upper Band'][i-1] and df['close'][i]>=df['Upper Band'][i]:
            df['SuperTrend'][i]=df['Lower Band'][i]
            df['Trend'][i]=True
            df['TSL'][i]=df['Lower Band'][i]
        elif df['SuperTrend'][i-1]==df['Lower Band'][i-1] and df['close'][i]>=df['Lower Band'][i]:
            df['SuperTrend'][i]=df['Lower Band'][i]
            df['Trend'][i]=True
            df['TSL'][i]=df['Lower Band'][i]
        elif df['SuperTrend'][i-1]==df['Lower Band'][i-1] and df['close'][i]<=df['Lower Band'][i]:
            df['SuperTrend'][i]=df['Upper Band'][i]
            df['Trend'][i]=False
            df['TSL'][i]=df['Upper Band'][i]
    return df



def heikinashi__(df):
    '''
    Heikin Ashi candlesticks in the forms of lines
    Formula:
        ha_open = (ha_open(-1) + ha_close(-1)) / 2
        ha_high = max(hi, ha_open, ha_close)
        ha_low = min(lo, ha_open, ha_close)
        ha_close = (open + high + low + close) / 4
    See also:
        https://en.wikipedia.org/wiki/Candlestick_chart#Heikin_Ashi_candlesticks
        http://stockcharts.com/school/doku.php?id=chart_school:chart_analysis:heikin_ashi
    '''
    heikin_ashi_df = pd.DataFrame(index=df.index.values, columns=['open', 'high', 'low', 'close'])

    heikin_ashi_df['close'] = (df['open'] + df['high'] + df['low'] + df['close']) / 4

    for i in range(len(df)):
        if i == 0:
            heikin_ashi_df.iat[0, 0] = df['open'].iloc[0]
        else:
            heikin_ashi_df.iat[i, 0] = (heikin_ashi_df.iat[i - 1, 0] + heikin_ashi_df.iat[i - 1, 3]) / 2

    heikin_ashi_df['high'] = heikin_ashi_df.loc[:, ['open', 'close']].join(df['high']).max(axis=1)

    heikin_ashi_df['low'] = heikin_ashi_df.loc[:, ['open', 'close']].join(df['low']).min(axis=1)

    return heikin_ashi_df


def heikinashi(df, ohlc=['open', 'high', 'low', 'close']):
    """
    Function to compute Heiken Ashi Candles (HA)

    Args :
        df : Pandas DataFrame which contains ['date', 'open', 'high', 'low', 'close', 'volume'] columns
        ohlc: List defining OHLC Column names (default ['Open', 'High', 'Low', 'Close'])

    Returns :
        df : Pandas DataFrame with new columns added for
            Heiken Ashi Close (HA_$ohlc[3])
            Heiken Ashi Open (HA_$ohlc[0])
            Heiken Ashi High (HA_$ohlc[1])
            Heiken Ashi Low (HA_$ohlc[2])
    """

    ha_open = 'HA_' + ohlc[0]
    ha_high = 'HA_' + ohlc[1]
    ha_low = 'HA_' + ohlc[2]
    ha_close = 'HA_' + ohlc[3]

    df[ha_close] = (df[ohlc[0]] + df[ohlc[1]] + df[ohlc[2]] + df[ohlc[3]]) / 4

    df[ha_open] = 0.00
    for i in range(0, len(df)):
        if i == 0:
            df[ha_open].iat[i] = (df[ohlc[0]].iat[i] + df[ohlc[3]].iat[i]) / 2
        else:
            df[ha_open].iat[i] = (df[ha_open].iat[i - 1] + df[ha_close].iat[i - 1]) / 2

    df[ha_high] = df[[ha_open, ha_close, ohlc[1]]].max(axis=1)
    df[ha_low] = df[[ha_open, ha_close, ohlc[2]]].min(axis=1)

    return df
# SuperTrend 로직
# BASIC UPPERBAND = (HIGH + LOW) / 2 + Multiplier * ATR
# BASIC LOWERBAND = (HIGH + LOW) / 2 - Multiplier * ATR
#
# FINAL UPPERBAND = IF( (Current BASICUPPERBAND < Previous FINAL UPPERBAND) and (Previous Close > Previous FINAL UPPERBAND)) THEN (Current BASIC UPPERBAND) ELSE Previous FINALUPPERBAND)
# FINAL LOWERBAND = IF( (Current BASIC LOWERBAND > Previous FINAL LOWERBAND) and (Previous Close < Previous FINAL LOWERBAND)) THEN (Current BASIC LOWERBAND) ELSE Previous FINAL LOWERBAND)

# TradingView Pine Source
# // supertrend define
# Factor=input(3, minval=1,maxval = 100, title="Supertrend Factor")
# Pd=input(7, minval=1,maxval = 100,  title="Supertrend Period")
#
#
# Up=hl2-(Factor*atr(Pd))
# Dn=hl2+(Factor*atr(Pd))
#
#
# TrendUp=close[1]>TrendUp[1]? max(Up,TrendUp[1]) : Up
# TrendDown=close[1]<TrendDown[1]? min(Dn,TrendDown[1]) : Dn
#
# Trend = close > TrendDown[1] ? 1: close< TrendUp[1]? -1: nz(Trend[1],1)
# Tsl = Trend==1? TrendUp: TrendDown
# longCondition_supertrend = cross(close,Tsl) and close>Tsl
# shortCondition_supertrend = cross(Tsl,close) and close<Tsl