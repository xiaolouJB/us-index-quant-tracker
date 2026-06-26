import yfinance as yf
import warnings
warnings.filterwarnings('ignore')

syms = [
    ('QQQ','QQQ'),
    ('SPY','SPY'),
    ('^NDX','NDX'),
    ('^GSPC','SPX'),
    ('^VIX','VIX'),
    ('^VXN','VXN'),
    ('QQQE','QQQE'),
    ('RSP','RSP'),
    ('^TNX','US10Y'),
    ('^FVX','US5Y'),
    ('^TYX','US30Y'),
    ('^IRX','US3M'),
    ('^TU','US2Y_fut'),
]

print("=== 指数与ETF价格 ===")
for sym, name in syms:
    try:
        h = yf.Ticker(sym).history(period='5d')
        if len(h) >= 2:
            c = h['Close'].iloc[-1]
            p = h['Close'].iloc[-2]
            d = (c - p) / p * 100
            dt = h.index[-1].strftime('%m/%d')
            print(f"{name}: {c:.4f}  ({d:+.2f}%)  [{dt}]")
        elif len(h) == 1:
            c = h['Close'].iloc[-1]
            dt = h.index[-1].strftime('%m/%d')
            print(f"{name}: {c:.4f}  [{dt}]")
        else:
            print(f"{name}: no data")
    except Exception as e:
        print(f"{name}: ERR {e}")

print()
print("=== 200日均线 ===")
for sym, name in [('^NDX','NDX'), ('^GSPC','SPX')]:
    try:
        h = yf.Ticker(sym).history(period='15mo')
        ma = h['Close'].rolling(200).mean().iloc[-1]
        c = h['Close'].iloc[-1]
        dev = (c - ma) / ma * 100
        slope_prev = h['Close'].rolling(200).mean().iloc[-20]
        slope = 'UP' if ma > slope_prev else 'DOWN'
        above_ma = (h['Close'].iloc[-50:] > h['Close'].rolling(200).mean().iloc[-50:]).sum()
        print(f"{name}: 200MA={ma:.2f}  Close={c:.2f}  Dev={dev:+.2f}%  Slope={slope}")
    except Exception as e:
        print(f"{name}: ERR {e}")

print()
print("=== USD/CNY ===")
try:
    h = yf.Ticker('USDCNY=X').history(period='35d')
    c = h['Close'].iloc[-1]
    p30 = h['Close'].iloc[0]
    chg30 = (c - p30) / p30 * 100
    print(f"USD/CNY: {c:.4f}  30d_chg={chg30:+.2f}%")
except Exception as e:
    print(f"USD/CNY: ERR {e}")

print()
print("=== US2Y (^IRX proxy) ===")
try:
    h2 = yf.Ticker('^IRX').history(period='5d')
    us2y = h2['Close'].iloc[-1] / 100
    print(f"US2Y(proxy 3M bill): {us2y*100:.4f}%")
except Exception as e:
    print(f"US2Y: ERR {e}")
