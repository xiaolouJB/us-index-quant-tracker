import yfinance as yf
import pandas as pd
import warnings
warnings.filterwarnings('ignore')

def get_walls(ticker_symbol):
    try:
        ticker = yf.Ticker(ticker_symbol)
        expirations = ticker.options
        if not expirations:
            print(f"[{ticker_symbol}] 未找到期权数据。")
            return None, None
        
        call_oi = {}
        put_oi = {}
        
        current_price = ticker.history(period="1d")['Close'].iloc[-1]
        
        # 统计最近 4 个交割日的持仓量，限制在当前价格的 +/- 15% 范围内
        for exp in expirations[:4]:
            opt = ticker.option_chain(exp)
            
            for _, row in opt.calls.iterrows():
                strike = row['strike']
                if abs(strike - current_price) / current_price <= 0.15:
                    call_oi[strike] = call_oi.get(strike, 0) + row['openInterest']
                
            for _, row in opt.puts.iterrows():
                strike = row['strike']
                if abs(strike - current_price) / current_price <= 0.15:
                    put_oi[strike] = put_oi.get(strike, 0) + row['openInterest']
                
        call_wall = max(call_oi, key=call_oi.get) if call_oi else None
        put_wall = max(put_oi, key=put_oi.get) if put_oi else None
        
        print(f"==== {ticker_symbol} 期权水位 (Option Walls) ====")
        print(f"当前价格: {current_price:.2f}")
        print(f"正 Gamma (Call Wall 强阻力卖点): {call_wall} (OI: {call_oi.get(call_wall, 0)})")
        print(f"负 Gamma (Put Wall 强支撑买点): {put_wall} (OI: {put_oi.get(put_wall, 0)})")
        print("="*40)
        
        return {
            "current_price": current_price,
            "call_wall": call_wall,
            "put_wall": put_wall
        }
    except Exception as e:
        print(f"[{ticker_symbol}] 获取期权数据失败: {e}")
        return None, None

def fetch_all():
    print("正在获取真实期权数据...\n")
    get_walls("QQQ")
    get_walls("SPY")

if __name__ == "__main__":
    fetch_all()
