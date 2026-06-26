# -*- coding: utf-8 -*-
"""
cn_source.py — 国内可达的美股数据源（腾讯财经 qt.gtimg.cn / web.ifzq.gtimg.cn）
用途：当 Yahoo(yfinance) 因墙不可达时的兜底。国内裸网可用、且更快。
覆盖：核心指数/ETF 最新价+涨跌幅（quote）；指数日K线历史（kline，用于均线/RSI）。
说明：涨跌幅一律用 (现价-昨收)/昨收 自算，不依赖字段位置，稳健。
"""
import warnings

import pandas as pd
import requests

warnings.filterwarnings('ignore')

H = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

# 我方代号 → 腾讯代号；index=True 表示有完整日K线（指数），False 仅取最新价（ETF）
TENCENT = {
    '^NDX': ('us.NDX', True),    # 纳斯达克100（已核对=29440.32）
    '^GSPC': ('us.INX', True),   # 标普500
    'QQQ': ('usQQQ', False),
    'SPY': ('usSPY', False),
    '^VIX': ('us.VIX', False),   # 实时VIX（与收盘可能略有差异）
}
QUOTE_URL = 'https://qt.gtimg.cn/q={code}'
KLINE_URL = 'https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param={code},day,,,{n},qfq'


def quote(symbol, timeout=8):
    """返回 (price, prev_close, chg_pct)；失败返回 (None,None,None)。"""
    code = TENCENT.get(symbol, (symbol, False))[0]
    try:
        r = requests.get(QUOTE_URL.format(code=code), timeout=timeout, headers=H)
        r.encoding = 'gbk'
        body = r.text.split('"')[1]
        p = body.split('~')
        price = float(p[3])
        prev = float(p[4])
        chg = (price - prev) / prev * 100 if prev else None
        return price, prev, (round(chg, 2) if chg is not None else None)
    except Exception:
        return None, None, None


def history(symbol, days=300, timeout=12):
    """返回 yfinance 同构的 DataFrame（含 'Close' 列、日期索引）；仅指数有完整历史。"""
    code, has_kline = TENCENT.get(symbol, (symbol, False))
    if not has_kline:
        # ETF 无完整K线：用最新价构造单行，至少不为空
        price, _, _ = quote(symbol, timeout)
        if price is None:
            return pd.DataFrame()
        return pd.DataFrame({'Close': [price]}, index=[pd.Timestamp.today().normalize()])
    try:
        d = requests.get(KLINE_URL.format(code=code, n=days), timeout=timeout, headers=H).json()
        node = d['data'][code]
        kl = node.get('day') or node.get('qfqday') or []
        if not kl:
            return pd.DataFrame()
        rows = [(pd.Timestamp(x[0]), float(x[1]), float(x[2]), float(x[3]), float(x[4])) for x in kl]
        df = pd.DataFrame(rows, columns=['date', 'Open', 'Close', 'High', 'Low']).set_index('date')
        return df
    except Exception:
        return pd.DataFrame()


if __name__ == '__main__':
    for s in ['^NDX', '^GSPC', 'QQQ', 'SPY', '^VIX']:
        pr, pv, ch = quote(s)
        h = history(s, 260)
        print(f'{s}: quote={pr} ({ch}%)  kline={len(h)}根')
