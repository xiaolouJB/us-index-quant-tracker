# -*- coding: utf-8 -*-
"""
fetch_all.py — 统一行情入口（合并自旧 fetch_data/fetch_prices/get_market_data/fetch_macro）
输出：价格快照、200/50日均线与斜率、汇率、牛市年龄、相对强弱与领先指标（模块Q）。
关键字段自动写入 data/latest_snapshot.json。
统一算法约定：
  - 均线一律用 rolling(N) 收盘均线（按交易日）。
  - 年线斜率 = MA(200)当前值 vs 20个交易日前的 MA(200) 值（禁止用价格动量代替）。
"""
import datetime
import warnings

import yfinance as yf

warnings.filterwarnings('ignore')

from snapshot_util import update_snapshot

PRICE_SYMBOLS = [
    ('^NDX', 'NDX 纳指100'),
    ('^GSPC', 'SPX 标普500'),
    ('QQQ', 'QQQ'),
    ('SPY', 'SPY'),
    ('QQQE', 'QQQE 等权纳指'),
    ('RSP', 'RSP 等权标普'),
    ('^VIX', 'VIX'),
    ('^VXN', 'VXN'),
    ('^TNX', 'US10Y'),
    ('^IRX', 'US3M'),
    ('^SOX', 'SOX 费城半导体'),
    ('DX-Y.NYB', 'DXY 美元指数'),
    ('VUG', 'VUG 成长'),
    ('VTV', 'VTV 价值'),
    ('^W5000', 'Wilshire5000'),
]

SNAP = {}


def fetch_history(symbol, period):
    """统一历史数据入口：剔除 Close 为 NaN 的残缺行（yfinance 最新一根K线常见为 NaN）。"""
    h = yf.Ticker(symbol).history(period=period)
    if not h.empty:
        h = h[h['Close'].notna()]
    return h


def section_prices():
    print('=== 指数与ETF价格（收盘价 / 单日涨跌幅）===')
    closes = {}
    chgs = {}
    for sym, name in PRICE_SYMBOLS:
        try:
            h = fetch_history(sym, '10d')
            if h.empty:
                print(f'{name}: 无数据')
                continue
            c = float(h['Close'].iloc[-1])
            dt = h.index[-1].strftime('%Y-%m-%d')
            closes[sym] = c
            if len(h) >= 2:
                p = float(h['Close'].iloc[-2])
                chg = (c - p) / p * 100
                chgs[sym] = round(chg, 2)
                print(f'{name}: {c:.2f}  ({chg:+.2f}%)  [{dt}]')
            else:
                print(f'{name}: {c:.2f}  [{dt}]')
        except Exception as e:
            print(f'{name}: ERR {e}')
    SNAP.update({
        'ndx_close': closes.get('^NDX'),
        'spx_close': closes.get('^GSPC'),
        'qqq_close': closes.get('QQQ'),
        'spy_close': closes.get('SPY'),
        # 当日涨跌幅（存进快照，杜绝报告价格行靠模型手算）
        'ndx_chg_pct': chgs.get('^NDX'),
        'spx_chg_pct': chgs.get('^GSPC'),
        'qqq_chg_pct': chgs.get('QQQ'),
        'spy_chg_pct': chgs.get('SPY'),
        'vix': closes.get('^VIX'),
        'vxn': closes.get('^VXN'),
        'us10y': closes.get('^TNX'),
        'sox': closes.get('^SOX'),
        'dxy': closes.get('DX-Y.NYB'),
        'w5000': closes.get('^W5000'),
        'price_date': None,
    })
    try:
        SNAP['price_date'] = fetch_history('^GSPC', '5d').index[-1].strftime('%Y-%m-%d')
    except Exception:
        pass
    return closes


def ma_block(symbol, label, snap_prefix):
    """200/50日均线、斜率（MA对比20日前MA）、偏离度。"""
    try:
        h = fetch_history(symbol, '15mo')
        close = h['Close']
        ma200 = close.rolling(200).mean()
        ma50 = close.rolling(50).mean()
        c = float(close.iloc[-1])
        m200, m50 = float(ma200.iloc[-1]), float(ma50.iloc[-1])
        dev200 = (c - m200) / m200 * 100
        dev50 = (c - m50) / m50 * 100
        slope200 = '向上' if m200 > float(ma200.iloc[-21]) else '向下'
        slope50 = '向上' if m50 > float(ma50.iloc[-21]) else '向下'
        cross = '金叉(50>200)' if m50 > m200 else '死叉(50<200)'
        print(f'{label}: 收盘={c:.2f}')
        print(f'  200日MA={m200:.2f}  偏离={dev200:+.2f}%  斜率={slope200}')
        print(f'  50日MA ={m50:.2f}  偏离={dev50:+.2f}%  斜率={slope50}  状态={cross}')
        # 年线下方天数（结构破坏判定辅助：连续收于年线下方的交易日数）
        below = 0
        for i in range(1, min(30, len(close))):
            if float(close.iloc[-i]) < float(ma200.iloc[-i]):
                below += 1
            else:
                break
        if below:
            print(f'  ⚠️ 已连续 {below} 个交易日收于年线下方' + ('（>5日，结构破坏）' if below > 5 else ''))
        SNAP.update({
            f'{snap_prefix}_200dma': round(m200, 2),
            f'{snap_prefix}_50dma': round(m50, 2),
            f'{snap_prefix}_dev200': round(dev200, 2),
            f'{snap_prefix}_ma200_slope': slope200,
            f'{snap_prefix}_days_below_ma200': below,
        })
    except Exception as e:
        print(f'{label}: ERR {e}')


def section_fx():
    print()
    print('=== USD/CNY（QDII汇率层，模块H）===')
    try:
        h = fetch_history('USDCNY=X', '7mo')
        c = float(h['Close'].iloc[-1])
        c30 = float(h['Close'].iloc[-22]) if len(h) >= 22 else float(h['Close'].iloc[0])
        c90 = float(h['Close'].iloc[-64]) if len(h) >= 64 else float(h['Close'].iloc[0])
        chg30 = (c - c30) / c30 * 100
        chg90 = (c - c90) / c90 * 100
        trend = '人民币贬值(QDII顺风)' if chg30 > 0 else '人民币升值(QDII逆风)'
        print(f'USD/CNY: {c:.4f}  30日变动={chg30:+.2f}%  90日变动={chg90:+.2f}%  → {trend}')
        if abs(chg30) > 2:
            print('  ⚠️ 单月波动>2%，标注为汇率扰动期')
        if chg90 < -3:
            print('  ⚠️ 近90日人民币升值超3%，主动加仓意愿降权')
        SNAP.update({'usdcny': round(c, 4), 'usdcny_chg30': round(chg30, 2), 'usdcny_chg90': round(chg90, 2)})
    except Exception as e:
        print(f'USD/CNY: ERR {e}')


def pct_change_20d(symbol):
    h = fetch_history(symbol, '3mo')
    c = float(h['Close'].iloc[-1])
    p = float(h['Close'].iloc[-21])
    return (c - p) / p * 100


def ratio_change_20d(sym_a, sym_b):
    ha = fetch_history(sym_a, '3mo')['Close']
    hb = fetch_history(sym_b, '3mo')['Close']
    n = min(len(ha), len(hb))
    ra_now = float(ha.iloc[-1]) / float(hb.iloc[-1])
    ra_then = float(ha.iloc[n - 21]) / float(hb.iloc[n - 21]) if n >= 21 else ra_now
    return ra_now, (ra_now - ra_then) / ra_then * 100


def section_relative_strength():
    print()
    print('=== 相对强弱与领先指标（模块Q）===')
    headwinds = 0
    try:
        _, chg = ratio_change_20d('^NDX', '^GSPC')
        d = '成长占优' if chg > 0 else '资金防御化'
        if chg < 0:
            headwinds += 1
        print(f'NDX/SPX 比价 20日变动: {chg:+.2f}%  → {d}')
        SNAP['ndx_spx_ratio_chg20'] = round(chg, 2)
    except Exception as e:
        print(f'NDX/SPX: ERR {e}')
    try:
        h = fetch_history('^SOX', '6mo')
        c = float(h['Close'].iloc[-1])
        ma50 = float(h['Close'].rolling(50).mean().iloc[-1])
        pos = '上方(健康)' if c > ma50 else '下方(领先预警⚠️)'
        if c < ma50:
            headwinds += 1
        print(f'SOX vs 自身50DMA: {c:.2f} vs {ma50:.2f} → {pos}')
        SNAP['sox_above_50dma'] = c > ma50
    except Exception as e:
        print(f'SOX: ERR {e}')
    try:
        _, chg = ratio_change_20d('VUG', 'VTV')
        d = '成长风格占优' if chg > 0 else '价值风格切换'
        if chg < 0:
            headwinds += 1
        print(f'VUG/VTV 比价 20日变动: {chg:+.2f}%  → {d}')
        SNAP['vug_vtv_chg20'] = round(chg, 2)
    except Exception as e:
        print(f'VUG/VTV: ERR {e}')
    try:
        h = fetch_history('DX-Y.NYB', '10d')
        dxy = float(h['Close'].iloc[-1])
        d = '强美元逆风' if dxy > 105 else ('弱美元顺风' if dxy < 100 else '中性')
        if dxy > 105:
            headwinds += 1
        print(f'DXY 美元指数: {dxy:.2f} → {d}')
    except Exception as e:
        print(f'DXY: ERR {e}')
    try:
        _, chg = ratio_change_20d('HG=F', 'GC=F')
        d = '风险偏好扩张' if chg > 0 else '风险偏好收缩(衰退交易)'
        if chg < 0:
            headwinds += 1
        print(f'铜金比 20日变动: {chg:+.2f}%  → {d}')
        SNAP['copper_gold_chg20'] = round(chg, 2)
    except Exception as e:
        print(f'铜金比: ERR {e}')
    verdict = '逆风' if headwinds >= 3 else ('中性' if headwinds == 2 else '顺风')
    print(f'>>> 领先指标净判定: {verdict}（逆风项 {headwinds}/5）')
    SNAP['leading_verdict'] = verdict


def section_bull_age():
    print()
    print('=== 牛市年龄（模块F）===')
    start = datetime.date(2022, 10, 12)
    today = datetime.date.today()
    years = (today - start).days / 365.25
    consumed = years / 4.6 * 100
    stage = '早期' if years < 2 else ('中期' if years < 4 else '成熟期')
    print(f'起点: {start} | 今日: {today} | 已运行 {years:.2f} 年 | 历史均值4.6年消耗 {consumed:.1f}% | 阶段: {stage}')
    SNAP.update({'bull_age_years': round(years, 2), 'bull_consumed_pct': round(consumed, 1)})


def main():
    closes = section_prices()
    print()
    print('=== 均线与价格结构（模块E基础层）===')
    ma_block('^NDX', 'NDX', 'ndx')
    ma_block('^GSPC', 'SPX', 'spx')
    section_fx()
    section_relative_strength()
    section_bull_age()
    update_snapshot(SNAP)
    print()
    print('✅ 关键字段已写入 data/latest_snapshot.json')


if __name__ == '__main__':
    main()
