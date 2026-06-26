"""
fetch_dark_pool.py
获取 SqueezeMetrics DIX/GEX 公开历史数据
数据来源: https://squeezemetrics.com/monitor/static/DIX.csv
"""
import requests
import pandas as pd
import warnings
warnings.filterwarnings('ignore')

def fetch_dix():
    url = "https://squeezemetrics.com/monitor/static/DIX.csv"
    try:
        r = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
        r.raise_for_status()
        from io import StringIO
        df = pd.read_csv(StringIO(r.text))
        df.columns = [c.strip() for c in df.columns]
        # 尝试解析日期列
        date_col = [c for c in df.columns if 'date' in c.lower() or 'Date' in c]
        if date_col:
            df['date'] = pd.to_datetime(df[date_col[0]])
            df = df.sort_values('date')
        print("✅ DIX数据获取成功")
        print(f"列名: {list(df.columns)}")
        print(f"最新10行:\n{df.tail(10).to_string()}")
        return df
    except Exception as e:
        print(f"❌ DIX数据获取失败: {e}")
        return None

if __name__ == "__main__":
    fetch_dix()
