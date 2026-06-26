# -*- coding: utf-8 -*-
"""
fetch_sentiment.py — 情绪面增强（模块C增强项）
输出：CNN 恐惧贪婪指数、SPY/QQQ 期权 PCR（成交量与持仓量两种口径，
由期权链直接计算，不依赖CBOE页面）。
"""
import warnings

import requests
import yfinance as yf

warnings.filterwarnings('ignore')

from snapshot_util import update_snapshot

SNAP = {}
FNG_URL = 'https://production.dataviz.cnn.io/index/fearandgreed/graphdata'


def section_fear_greed():
    print('=== CNN 恐惧贪婪指数 ===')
    try:
        r = requests.get(FNG_URL, timeout=20, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
            'Accept': 'application/json',
        })
        r.raise_for_status()
        fg = r.json()['fear_and_greed']
        score = float(fg['score'])
        rating = fg.get('rating', '')
        prev = fg.get('previous_close')
        if score <= 25:
            zone, action = '极度恐惧', '逆向信号：绿/黄灯下网格狙击置信度增强'
        elif score <= 45:
            zone, action = '恐惧', '常态区间，不修正操作'
        elif score <= 55:
            zone, action = '中性', '常态区间，不修正操作'
        elif score <= 75:
            zone, action = '贪婪', '常态区间，不修正操作'
        else:
            zone, action = '极度贪婪', '⚠️ 追高警示：禁止当日追涨买入，只允许回调后执行'
        print(f'F&G: {score:.0f}（{zone} / {rating}）  前收: {prev}')
        print(f'操作修正: {action}')
        SNAP['fear_greed'] = round(score, 0)
        SNAP['fear_greed_zone'] = zone
    except Exception as e:
        print(f'F&G 获取失败: {e} → 需人工查看 cnn.com/markets/fear-and-greed，或本期标注"数据缺失"')


def pcr(symbol, n_exp=3):
    tk = yf.Ticker(symbol)
    exps = tk.options[:n_exp]
    cv = pv = coi = poi = 0.0
    for exp in exps:
        try:
            chain = tk.option_chain(exp)
        except Exception:
            continue
        cv += float(chain.calls['volume'].fillna(0).sum())
        pv += float(chain.puts['volume'].fillna(0).sum())
        coi += float(chain.calls['openInterest'].fillna(0).sum())
        poi += float(chain.puts['openInterest'].fillna(0).sum())
    pcr_vol = pv / cv if cv else None
    pcr_oi = poi / coi if coi else None
    return pcr_vol, pcr_oi


def classify_pcr(v):
    if v is None:
        return 'N/A'
    if v < 0.6:
        return '极度贪婪（情绪过热警示）'
    if v <= 1.0:
        return '中性'
    return '恐慌（逆向关注区）'


def section_pcr():
    print()
    print('=== 期权 PCR（近3个交割日合计，由期权链计算）===')
    for sym in ('SPY', 'QQQ'):
        try:
            v, o = pcr(sym)
            v_str = f'{v:.2f} → {classify_pcr(v)}' if v is not None else 'N/A（成交量数据为空，盘前常见）'
            o_str = f'{o:.2f}' if o is not None else 'N/A'
            print(f'{sym}: PCR(成交量)={v_str} | PCR(持仓量)={o_str}')
            SNAP[f'{sym.lower()}_pcr_vol'] = round(v, 2) if v is not None else None
            SNAP[f'{sym.lower()}_pcr_oi'] = round(o, 2) if o is not None else None
        except Exception as e:
            print(f'{sym}: ERR {e}')


def main():
    section_fear_greed()
    section_pcr()
    update_snapshot(SNAP)
    print('\n✅ 关键字段已写入 data/latest_snapshot.json')


if __name__ == '__main__':
    main()
