import yfinance as yf
import datetime

def get_data(ticker, name):
    try:
        t = yf.Ticker(ticker)
        df = t.history(period="1mo")
        if not df.empty:
            last = df['Close'].iloc[-1]
            date = df.index[-1].date()
            print(f"{name} ({ticker}): {last:.2f} on {date}")
            if len(df) >= 2:
                prev = df['Close'].iloc[-2]
                pct = (last - prev) / prev * 100
                print(f"  1d Change: {pct:.2f}%")
        else:
            print(f"{name} ({ticker}): No data")
    except Exception as e:
        print(f"{name} ({ticker}): Error {e}")

def get_200dma(ticker, name):
    try:
        t = yf.Ticker(ticker)
        df = t.history(period="1y")
        if not df.empty and len(df) >= 200:
            dma200 = df['Close'].tail(200).mean()
            last = df['Close'].iloc[-1]
            pct = (last - dma200) / dma200 * 100
            print(f"{name} 200DMA: {dma200:.2f}, Latest: {last:.2f}, Diff: {pct:.2f}%")
        else:
            print(f"{name} 200DMA: Not enough data")
    except Exception as e:
        print(f"{name} 200DMA: Error {e}")

print("--- Prices ---")
get_data("^NDX", "Nasdaq 100")
get_data("^GSPC", "S&P 500")
get_data("QQQ", "QQQ")
get_data("SPY", "SPY")
get_data("RSP", "RSP")
get_data("QQQE", "QQQE")
get_data("^VIX", "VIX")
get_data("^VXN", "VXN")
get_data("^TNX", "US10Y")
get_data("USDCNY=X", "USD/CNY")

print("\n--- 200 DMA ---")
get_200dma("^NDX", "Nasdaq 100")
get_200dma("^GSPC", "S&P 500")

print("\n--- Bull Market Context ---")
start = datetime.date(2022, 10, 12)
today = datetime.date.today()
years = (today - start).days / 365.25
print(f"Bull market start: {start}")
print(f"Today: {today}")
print(f"Duration: {years:.2f} years")

