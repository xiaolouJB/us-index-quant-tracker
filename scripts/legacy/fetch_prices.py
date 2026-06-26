import yfinance as yf

tickers = {'QQQ': 'QQQ ETF', 'SPY': 'SPY ETF', 'RSP': 'RSP (Equal-Weight SPY)', 'QQQE': 'QQQE (Equal-Weight QQQ)'}
for sym, name in tickers.items():
    try:
        data = yf.Ticker(sym).history(period='10d')
        if not data.empty:
            latest_close = data['Close'].iloc[-1]
            prev_close = data['Close'].iloc[-2]
            chg = (latest_close - prev_close) / prev_close * 100
            date_str = str(data.index[-1].date())
            print(f'{name} ({sym}): Close={latest_close:.2f}, Date={date_str}, 1d chg={chg:.2f}%')
    except Exception as e:
        print(f'{sym}: Error - {e}')

# NDX Index
try:
    ndx = yf.Ticker('^NDX').history(period='10d')
    latest = ndx['Close'].iloc[-1]
    prev = ndx['Close'].iloc[-2]
    chg = (latest - prev) / prev * 100
    date_str = str(ndx.index[-1].date())
    print(f'NDX Index: Close={latest:.2f}, Date={date_str}, 1d chg={chg:.2f}%')
except Exception as e:
    print(f'NDX Error: {e}')

# SPX Index
try:
    spx = yf.Ticker('^GSPC').history(period='10d')
    latest = spx['Close'].iloc[-1]
    prev = spx['Close'].iloc[-2]
    chg = (latest - prev) / prev * 100
    date_str = str(spx.index[-1].date())
    print(f'SPX Index: Close={latest:.2f}, Date={date_str}, 1d chg={chg:.2f}%')
except Exception as e:
    print(f'SPX Error: {e}')

# VIX
try:
    vix = yf.Ticker('^VIX').history(period='5d')
    print(f'VIX: {vix["Close"].iloc[-1]:.2f}')
except Exception as e:
    print(f'VIX Error: {e}')

# VXN
try:
    vxn = yf.Ticker('^VXN').history(period='5d')
    print(f'VXN: {vxn["Close"].iloc[-1]:.2f}')
except Exception as e:
    print(f'VXN Error: {e}')
