
import yfinance as yf
import warnings
warnings.filterwarnings('ignore')

print("=== NDX 200DMA ===")
ndx = yf.Ticker('^NDX').history(period='250d')
ndx_200 = ndx['Close'].tail(200).mean()
ndx_latest = ndx['Close'].iloc[-1]
ndx_pct = (ndx_latest - ndx_200) / ndx_200 * 100
slope_recent = ndx['Close'].tail(20).mean()
slope_prior  = ndx['Close'].tail(40).iloc[:20].mean()
ndx_slope = "UP" if slope_recent > slope_prior else "DOWN"
print(f"NDX 200DMA: {ndx_200:.2f}")
print(f"NDX Latest: {ndx_latest:.2f}  Date: {str(ndx.index[-1].date())}")
print(f"NDX vs 200DMA: {ndx_pct:.2f}%")
print(f"NDX 200DMA slope: {ndx_slope}")

print()
print("=== SPX 200DMA ===")
spx = yf.Ticker('^GSPC').history(period='250d')
spx_200 = spx['Close'].tail(200).mean()
spx_latest = spx['Close'].iloc[-1]
spx_pct = (spx_latest - spx_200) / spx_200 * 100
slope_recent2 = spx['Close'].tail(20).mean()
slope_prior2  = spx['Close'].tail(40).iloc[:20].mean()
spx_slope = "UP" if slope_recent2 > slope_prior2 else "DOWN"
print(f"SPX 200DMA: {spx_200:.2f}")
print(f"SPX Latest: {spx_latest:.2f}  Date: {str(spx.index[-1].date())}")
print(f"SPX vs 200DMA: {spx_pct:.2f}%")
print(f"SPX 200DMA slope: {spx_slope}")

print()
print("=== US Treasury Yields ===")
tnx = yf.Ticker('^TNX').history(period='10d')
us10y = tnx['Close'].iloc[-1]
print(f"US10Y: {us10y:.3f}%  Date: {str(tnx.index[-1].date())}")

# 2Y yield via US2Y
try:
    us2y_t = yf.Ticker('^IRX').history(period='10d')  # 13-week
    us2y_v = us2y_t['Close'].iloc[-1]
    print(f"US13W (proxy short rate): {us2y_v:.3f}%")
except Exception as e:
    print(f"US2Y error: {e}")

# Try 2Y directly
try:
    twoyr = yf.Ticker('2YY=F').history(period='5d')
    if not twoyr.empty:
        print(f"2Y Futures: {twoyr['Close'].iloc[-1]:.3f}")
except:
    pass

print()
print("=== USD/CNY ===")
try:
    usdcny = yf.Ticker('USDCNY=X').history(period='100d')
    cny_latest = usdcny['Close'].iloc[-1]
    cny_30 = usdcny['Close'].iloc[-30] if len(usdcny) >= 30 else usdcny['Close'].iloc[0]
    cny_90 = usdcny['Close'].iloc[-90] if len(usdcny) >= 90 else usdcny['Close'].iloc[0]
    chg30 = (cny_latest - cny_30) / cny_30 * 100
    chg90 = (cny_latest - cny_90) / cny_90 * 100
    direction30 = "RMB Depreciation" if chg30 > 0 else "RMB Appreciation"
    print(f"USD/CNY: {cny_latest:.4f}  Date: {str(usdcny.index[-1].date())}")
    print(f"30d change: {chg30:.2f}% ({direction30})")
    print(f"90d change: {chg90:.2f}%")
except Exception as e:
    print(f"USD/CNY error: {e}")

print()
print("=== % above 200DMA (breadth) ===")
try:
    # SPX breadth via $SPXA200R proxy
    bpspx = yf.Ticker('^SP500').history(period='5d')
    print("SPX breadth: use web source")
except:
    pass

print()
print("=== Bull/Bear Market Context ===")
import datetime
start = datetime.date(2022, 10, 12)
today = datetime.date.today()
days = (today - start).days
years = days / 365.25
print(f"Bull market start: {start}")
print(f"Today: {today}")
print(f"Duration: {years:.2f} years ({days} days)")
print(f"Historical avg bull market: ~4.6 years")
print(f"Consumed: {years/4.6*100:.1f}%")
