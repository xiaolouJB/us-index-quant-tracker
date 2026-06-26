# -*- coding: utf-8 -*-
"""
fetch_technicals.py — 技术结构与分型层（模块E增强：E2/E3）
输出：RSI(14)、MACD(12,26,9)、距ATH回撤、ATR(14)、周线趋势(30周MA)、
顶底分型结构（swing high/low → HH/HL/LH/LL）、RSI背离提示。
"""
import warnings

import pandas as pd
import yfinance as yf

warnings.filterwarnings('ignore')

from snapshot_util import update_snapshot

SNAP = {}
SWING_WINDOW = 5   # 分型识别窗口：前后各5个交易日


def fetch(symbol, period):
    h = yf.Ticker(symbol).history(period=period)
    return h[h['Close'].notna()]


def rsi_series(close, n=14):
    delta = close.diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    rs = gain / loss
    return 100 - 100 / (1 + rs)


def macd(close):
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    line = ema12 - ema26
    signal = line.ewm(span=9, adjust=False).mean()
    hist = line - signal
    return line, signal, hist


def atr_pct(h, n=14):
    tr = pd.concat([
        h['High'] - h['Low'],
        (h['High'] - h['Close'].shift()).abs(),
        (h['Low'] - h['Close'].shift()).abs(),
    ], axis=1).max(axis=1)
    atr = tr.ewm(alpha=1 / n, adjust=False).mean().iloc[-1]
    return float(atr), float(atr / h['Close'].iloc[-1] * 100)


def find_swings(close, window=SWING_WINDOW):
    """识别摆动高低点（分型）：窗口内极值，排除最近window日（未确认）。"""
    highs, lows = [], []
    vals = close.values
    for i in range(window, len(vals) - window):
        seg = vals[i - window:i + window + 1]
        if vals[i] == seg.max():
            highs.append((close.index[i], float(vals[i])))
        if vals[i] == seg.min():
            lows.append((close.index[i], float(vals[i])))
    return highs, lows


def swing_structure(highs, lows):
    if len(highs) < 2 or len(lows) < 2:
        return '数据不足', None
    h1, h2 = highs[-2][1], highs[-1][1]   # 次新高点 / 最新高点
    l1, l2 = lows[-2][1], lows[-1][1]
    hh = h2 > h1
    hl = l2 > l1
    if hh and hl:
        return 'HH+HL 上升结构（趋势多头，回踩低点为网格参考位）', 'up'
    if (not hh) and (not hl):
        return 'LH+LL 下降结构（趋势空头预警）', 'down'
    return '高低点混合 → 震荡结构（区间市，网格步长用ATR加宽）', 'range'


def analyze(symbol, label, prefix):
    print(f'==== {label} 技术结构（模块E增强）====')
    try:
        h = fetch(symbol, '2y')
        hmax = fetch(symbol, 'max')
        close = h['Close']
        c = float(close.iloc[-1])

        # RSI
        rsi = rsi_series(close)
        rsi_now = float(rsi.iloc[-1])
        rsi_zone = '超买(>70，禁止追涨)' if rsi_now > 70 else ('超卖(<30，年线完好时狙击信号增强)' if rsi_now < 30 else '中性')
        print(f'RSI(14): {rsi_now:.1f} → {rsi_zone}')

        # MACD
        _, _, hist = macd(close)
        hnow, hprev = float(hist.iloc[-1]), float(hist.iloc[-2])
        direction = '扩张' if abs(hnow) > abs(hprev) else '收缩'
        sign = '正值' if hnow > 0 else '负值'
        warn = '（动能衰减预警）' if (hnow > 0 and direction == '收缩') else ''
        print(f'MACD柱: {hnow:+.2f}（{sign}，{direction}）{warn}')

        # 距ATH回撤
        ath = float(hmax['Close'].max())
        dd = (c - ath) / ath * 100
        if dd > -5:
            dd_zone = '高位区（狙击性价比低）'
        elif dd > -10:
            dd_zone = '常规回调区'
        elif dd > -20:
            dd_zone = '技术性回调（结合灯号评估狙击窗口）'
        else:
            dd_zone = '技术性熊市（触发牛市起点重新锚定）⚠️'
        print(f'距历史最高点({ath:.2f})回撤: {dd:.2f}% → {dd_zone}')

        # ATR
        atr_abs, atr_p = atr_pct(h)
        print(f'ATR(14): {atr_abs:.2f}（{atr_p:.2f}%）→ 网格单格间距参考 ≥ {atr_abs:.0f} 点')

        # 周线趋势
        wk = close.resample('W-FRI').last().dropna()
        ma30w = float(wk.rolling(30).mean().iloc[-1])
        wk_pos = '上方（长波段健康）' if c > ma30w else '下方（与年线信号互相印证）⚠️'
        print(f'周线趋势: 现价 vs 30周MA({ma30w:.2f}) → {wk_pos}')

        # 分型结构
        recent = close.tail(180)
        highs, lows = find_swings(recent)
        struct_desc, struct = swing_structure(highs, lows)
        print(f'分型结构（近180日，{SWING_WINDOW}日窗口）: {struct_desc}')
        if highs:
            print(f'  最近摆动高点: ' + ', '.join(f'{d:%m-%d}@{v:.0f}' for d, v in highs[-2:]))
        if lows:
            print(f'  最近摆动低点: ' + ', '.join(f'{d:%m-%d}@{v:.0f}' for d, v in lows[-2:]))

        # RSI背离
        divergence = '无'
        if len(highs) >= 2:
            (d1, p1), (d2, p2) = highs[-2], highs[-1]
            try:
                r1, r2 = float(rsi.loc[d1]), float(rsi.loc[d2])
                if p2 > p1 and r2 < r1:
                    divergence = '顶部分型背离预警⚠️（价格新高、RSI未新高）'
            except KeyError:
                pass
        if len(lows) >= 2 and divergence == '无':
            (d1, p1), (d2, p2) = lows[-2], lows[-1]
            try:
                r1, r2 = float(rsi.loc[d1]), float(rsi.loc[d2])
                if p2 < p1 and r2 > r1:
                    divergence = '底部分型背离信号（狙击置信度加分）'
            except KeyError:
                pass
        print(f'背离检测: {divergence}')
        print('=' * 46)

        SNAP.update({
            f'{prefix}_rsi': round(rsi_now, 1),
            f'{prefix}_macd_hist': round(hnow, 2),
            f'{prefix}_drawdown_pct': round(dd, 2),
            f'{prefix}_atr_pct': round(atr_p, 2),
            f'{prefix}_above_30wma': c > ma30w,
            f'{prefix}_swing_structure': struct,
            f'{prefix}_divergence': divergence,
        })
    except Exception as e:
        print(f'{label}: ERR {e}')


def main():
    analyze('^NDX', 'NDX 纳指100', 'ndx')
    analyze('^GSPC', 'SPX 标普500', 'spx')
    update_snapshot(SNAP)
    print('\n✅ 关键字段已写入 data/latest_snapshot.json')


if __name__ == '__main__':
    main()
