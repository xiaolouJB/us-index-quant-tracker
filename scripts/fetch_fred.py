# -*- coding: utf-8 -*-
"""
fetch_fred.py — 宏观数据层（FRED 主源 + Yahoo 备源 + 本地缓存降级）
覆盖：US2Y、2s10s利差、HY信用利差、M2同比、居民股票配置、巴菲特指标近似。

降级策略（当前网络环境 FRED 经常不可达）：
  1. FRED fredgraph.csv（免Key）—— 成功时写入 data/fred_cache.json
  2. Yahoo 备源：US2Y→2YY=F期货；2s10s→^TNX−2YY=F；HY→HYG/IEF相对趋势(仅方向代理)
  3. 本地缓存 fred_cache.json（带数据日期，过期需人工注意）
  4. 全部失败 → 明确提示该字段需人工 WebSearch 核实，禁止凭记忆填写
"""
import io
import json
import os
import warnings
from datetime import datetime

import pandas as pd
import requests

warnings.filterwarnings('ignore')

from snapshot_util import update_snapshot, DATA_DIR

FRED_CSV = 'https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}'
HEADERS = {'User-Agent': 'Mozilla/5.0'}
CACHE_PATH = os.path.join(DATA_DIR, 'fred_cache.json')
SNAP = {}


def load_cache():
    if os.path.exists(CACHE_PATH):
        try:
            with open(CACHE_PATH, encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


CACHE = load_cache()


def save_cache():
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(CACHE_PATH, 'w', encoding='utf-8') as f:
        json.dump(CACHE, f, ensure_ascii=False, indent=2)


_FRED_DOWN = False


def fred_series(sid, tail=400, timeout=(4, 7)):
    """timeout=(连接, 读取)：首次失败即触发 _FRED_DOWN 快速降级，避免每个序列各等20s。"""
    global _FRED_DOWN
    if _FRED_DOWN:
        raise ConnectionError('FRED 本次运行已判定不可达，跳过重试')
    try:
        r = requests.get(FRED_CSV.format(sid=sid), timeout=timeout, headers=HEADERS)
    except (requests.exceptions.Timeout, requests.exceptions.ConnectionError):
        _FRED_DOWN = True  # 同一次运行内不再重试其他序列，直接走备源/缓存
        raise
    r.raise_for_status()
    df = pd.read_csv(io.StringIO(r.text))
    df.columns = ['date', 'value']
    df['date'] = pd.to_datetime(df['date'])
    df['value'] = pd.to_numeric(df['value'], errors='coerce')
    df = df.dropna().tail(tail).reset_index(drop=True)
    if df.empty:
        raise ValueError(f'{sid}: 无有效数据')
    # 缓存最新值与若干历史点
    CACHE[sid] = {
        'latest': float(df.iloc[-1]['value']),
        'latest_date': df.iloc[-1]['date'].strftime('%Y-%m-%d'),
        'prev21': float(df.iloc[-22]['value']) if len(df) >= 22 else None,
        'prev13': float(df.iloc[-13]['value']) if len(df) >= 13 else None,
        'hist_max': float(df['value'].max()),
        'cached_at': datetime.now().strftime('%Y-%m-%d'),
    }
    save_cache()
    return df


def cached(sid):
    c = CACHE.get(sid)
    if c:
        return c
    return None


def yahoo_close(symbol, period='10d'):
    import yfinance as yf
    h = yf.Ticker(symbol).history(period=period)
    h = h[h['Close'].notna()]
    return float(h['Close'].iloc[-1]), h.index[-1].strftime('%Y-%m-%d'), h


def section_rates():
    print('=== 利率与收益率曲线（模块B/I）===')
    us2y = None
    try:
        df = fred_series('DGS2')
        us2y = float(df.iloc[-1]['value'])
        print(f"US2Y (FRED DGS2): {us2y:.2f}%  [{df.iloc[-1]['date']:%Y-%m-%d}]")
    except Exception:
        try:
            v, d, _ = yahoo_close('2YY=F')
            us2y = v
            print(f'US2Y (备源 2YY=F 收益率期货): {us2y:.2f}%  [{d}]')
        except Exception as e2:
            c = cached('DGS2')
            if c:
                us2y = c['latest']
                print(f"US2Y (本地缓存 {c['cached_at']}): {us2y:.2f}%  [数据日 {c['latest_date']}] ⚠️ 注意时效")
            else:
                print(f'US2Y: 全部数据源失败({e2})，需人工核实 FRED DGS2')
    if us2y is not None:
        SNAP['us2y'] = round(us2y, 2)

    try:
        df = fred_series('T10Y2Y')
        bp = float(df.iloc[-1]['value']) * 100
        src = 'FRED T10Y2Y'
    except Exception:
        bp, src = None, None
        try:
            us10y, _, _ = yahoo_close('^TNX')
            if us2y is not None:
                bp = (us10y - us2y) * 100
                src = '备源 ^TNX − 2YY=F'
        except Exception:
            pass
    if bp is not None:
        if bp > 0:
            shape = '正常化（健康）'
        elif bp > -50:
            shape = '平坦化（放缓信号，加风险注脚）'
        else:
            shape = '深度倒挂（宏观衰退预警激活⚠️）'
        print(f'2s10s 利差 ({src}): {bp:+.1f}bp → {shape}')
        SNAP['t10y2y_bp'] = round(bp, 1)
    else:
        print('2s10s: 全部数据源失败，需人工核实')


def section_credit():
    print()
    print('=== HY 信用利差（模块B 资金链预警）===')
    try:
        df = fred_series('BAMLH0A0HYM2')
        v = float(df.iloc[-1]['value'])
        prev20 = float(df.iloc[-21]['value']) if len(df) >= 21 else v
        widening = v - prev20
        flag = '⚠️ 急剧走阔，资金链预警' if widening > 0.75 else ('走阔中，关注' if widening > 0.3 else '平稳')
        print(f"HY OAS (FRED): {v:.2f}%  [{df.iloc[-1]['date']:%Y-%m-%d}]  近20日变动 {widening:+.2f}pp → {flag}")
        SNAP['hy_oas'] = v
        return
    except Exception:
        pass
    c = cached('BAMLH0A0HYM2')
    if c:
        print(f"HY OAS (本地缓存 {c['cached_at']}): {c['latest']:.2f}%  [数据日 {c['latest_date']}] ⚠️ 注意时效")
        SNAP['hy_oas'] = c['latest']
    # 方向代理：HYG/IEF 相对强弱（高收益债 vs 国债，下行=信用压力上升）
    try:
        _, _, hyg = yahoo_close('HYG', '3mo')
        _, _, ief = yahoo_close('IEF', '3mo')
        n = min(len(hyg), len(ief))
        ratio_now = float(hyg['Close'].iloc[-1]) / float(ief['Close'].iloc[-1])
        ratio_20 = float(hyg['Close'].iloc[n - 21]) / float(ief['Close'].iloc[n - 21])
        chg = (ratio_now - ratio_20) / ratio_20 * 100
        d = '信用压力上升⚠️（利差或在走阔）' if chg < -1.5 else ('轻微承压' if chg < -0.5 else '平稳/改善')
        print(f'HYG/IEF 20日相对变化 (方向代理): {chg:+.2f}% → {d}')
        SNAP['hyg_ief_chg20'] = round(chg, 2)
    except Exception as e:
        print(f'HY 方向代理失败: {e}，OAS绝对值需人工核实 FRED BAMLH0A0HYM2')


def section_m2():
    print()
    print('=== M2 同比（季度模块N背景）===')
    try:
        df = fred_series('M2SL', tail=30)
        v = float(df.iloc[-1]['value'])
        prev = float(df.iloc[-13]['value'])
        yoy = (v - prev) / prev * 100
        zone = '宽松扩张' if yoy > 5 else ('中性' if yoy >= 0 else ('边际收紧' if yoy > -3 else '极端收紧⚠️'))
        print(f"M2 (FRED): {v:,.0f}B  [{df.iloc[-1]['date']:%Y-%m}]  同比 {yoy:+.2f}% → {zone}")
        SNAP['m2_yoy'] = round(yoy, 2)
        return
    except Exception:
        pass
    c = cached('M2SL')
    if c and c.get('prev13'):
        yoy = (c['latest'] - c['prev13']) / c['prev13'] * 100
        print(f"M2 (本地缓存 {c['cached_at']}): 同比 {yoy:+.2f}%  [数据日 {c['latest_date']}] ⚠️ 注意时效")
        SNAP['m2_yoy'] = round(yoy, 2)
    else:
        print('M2: 数据源失败且无缓存 → 季度模块N需人工核实 FRED M2SL')


def section_household():
    print()
    print('=== 居民股票配置比例（模块D 长周期否决）===')
    try:
        df = fred_series('BOGZ1FL153064486Q', tail=200)
        v = float(df.iloc[-1]['value'])
        hist_max = float(df['value'].max())
        at_high = v >= hist_max * 0.995
        flag = '⚠️ 处于/逼近历史新高 → 模块D否决触发，额度八折' if at_high else '未触历史极值'
        print(f"居民股票配置 (FRED): {v:.1f}%  [{df.iloc[-1]['date']:%Y-%m-%d}季度]  历史最高 {hist_max:.1f}% → {flag}")
        SNAP['household_equity_pct'] = v
        SNAP['household_at_high'] = bool(at_high)
        return
    except Exception:
        pass
    c = cached('BOGZ1FL153064486Q')
    if c:
        at_high = c['latest'] >= c['hist_max'] * 0.995
        print(f"居民股票配置 (本地缓存 {c['cached_at']}): {c['latest']:.1f}%  [数据日 {c['latest_date']}] ⚠️ 季度数据，缓存通常可用")
        SNAP['household_equity_pct'] = c['latest']
        SNAP['household_at_high'] = bool(at_high)
    else:
        print('居民配置: 数据源失败且无缓存 → 需人工核实（FRED Z.1 表 BOGZ1FL153064486Q）')


def section_buffett():
    print()
    print('=== 巴菲特指标近似（模块K）===')
    w5000 = None
    try:
        w5000, wd, _ = yahoo_close('^W5000')
    except Exception as e:
        print(f'W5000 获取失败: {e}')
    gdp = None
    try:
        df = fred_series('GDP', tail=8)
        gdp = float(df.iloc[-1]['value'])
        gd = f"{df.iloc[-1]['date']:%Y-%m-%d}"
    except Exception:
        c = cached('GDP')
        if c:
            gdp, gd = c['latest'], f"缓存,数据日{c['latest_date']}"
    if w5000 and gdp:
        ratio = w5000 / gdp * 100  # 近似：W5000 1点 ≈ $10亿总市值
        if ratio < 100:
            zone = '低估区（战略大底）'
        elif ratio < 150:
            zone = '合理区'
        elif ratio < 175:
            zone = '偏贵区（注脚预警）'
        elif ratio < 200:
            zone = '高危区（长周期估值预警，叠加模块D→八折）'
        else:
            zone = '极端泡沫区（叠加红灯→机动五折/全锁）⚠️'
        print(f'W5000: {w5000:,.0f}点 [{wd}] | 名义GDP: {gdp:,.0f}B [{gd}]')
        print(f'巴菲特指标 ≈ {ratio:.0f}% → {zone}')
        print('   （近似值，正式报告必须与 currentmarketvaluation.com 人工交叉核验）')
        SNAP['buffett_ratio'] = round(ratio, 0)
    else:
        print('巴菲特指标: GDP 数据缺失 → 需人工从 currentmarketvaluation.com 获取比率')


def main():
    section_rates()
    section_credit()
    section_m2()
    section_household()
    section_buffett()
    update_snapshot(SNAP)
    print()
    print('✅ 关键字段已写入 data/latest_snapshot.json')


if __name__ == '__main__':
    main()
