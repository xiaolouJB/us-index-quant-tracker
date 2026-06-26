# -*- coding: utf-8 -*-
"""
fetch_prices_cn.py — 国内价格兜底层（Yahoo 被墙时启用）
用腾讯财经填核心字段：NDX/SPX/QQQ/SPY 最新价+涨跌幅、VIX、NDX/SPX 200/50日均线及偏离/斜率。
被 run_inspection 在检测到 Yahoo 核心字段缺失时自动调用。
所有本脚本写入的字段在快照里打来源标记 _src_<field>='腾讯财经'。
"""
import warnings

warnings.filterwarnings('ignore')
from snapshot_util import update_snapshot, load_snapshot
import cn_source as cn

SNAP = {}
SRC = '腾讯财经(qt.gtimg.cn)'
EXISTING = {}


def put(key, value, src):
    """只填补缺失字段，不覆盖 Yahoo 已成功获取的值。"""
    if value is None:
        return False
    if EXISTING.get(key) is not None:
        return False
    SNAP[key] = value
    src.append(key)
    return True


def main():
    global EXISTING
    EXISTING = load_snapshot()
    print('==== 国内价格兜底层（腾讯财经，仅补缺失）====')
    filled = []

    # 最新价 + 涨跌幅
    for sym, key in [('^NDX', 'ndx'), ('^GSPC', 'spx'), ('QQQ', 'qqq'), ('SPY', 'spy')]:
        price, _, chg = cn.quote(sym)
        if price is not None:
            a = put(f'{key}_close', round(price, 2), filled)
            b = put(f'{key}_chg_pct', chg, filled)
            if a or b:
                print(f'{key.upper()}: {price:.2f} ({chg:+.2f}%)  [补缺]')
    vix, _, _ = cn.quote('^VIX')
    if put('vix', round(vix, 2) if vix is not None else None, filled):
        print(f'VIX: {vix:.2f}（实时值）[补缺]')

    # 指数均线 + RSI（用指数日K线）
    for sym, key in [('^NDX', 'ndx'), ('^GSPC', 'spx')]:
        # 只在该指数的技术字段确有缺失时才拉K线，省网络
        if all(EXISTING.get(f'{key}{f}') is not None for f in ('_rsi', '_200dma', '_50dma', '_dev200')):
            continue
        h = cn.history(sym, 300)
        if len(h) >= 200:
            close = h['Close']
            delta = close.diff()
            gain = delta.clip(lower=0).ewm(alpha=1 / 14, adjust=False).mean()
            loss = (-delta.clip(upper=0)).ewm(alpha=1 / 14, adjust=False).mean()
            rsi = float((100 - 100 / (1 + (gain / loss))).iloc[-1])
            ma200 = close.rolling(200).mean()
            ma50 = close.rolling(50).mean()
            c = float(close.iloc[-1])
            m200, m50 = float(ma200.iloc[-1]), float(ma50.iloc[-1])
            below = 0
            for i in range(1, min(30, len(close))):
                if float(close.iloc[-i]) < float(ma200.iloc[-i]):
                    below += 1
                else:
                    break
            put(f'{key}_rsi', round(rsi, 1), filled)
            put(f'{key}_200dma', round(m200, 2), filled)
            put(f'{key}_50dma', round(m50, 2), filled)
            put(f'{key}_dev200', round((c - m200) / m200 * 100, 2), filled)
            put(f'{key}_ma200_slope', '向上' if m200 > float(ma200.iloc[-21]) else '向下', filled)
            put(f'{key}_days_below_ma200', below, filled)
            print(f'{key.upper()} RSI={rsi:.1f} 200MA={m200:.2f} [补缺]')

    if not EXISTING.get('price_date'):
        try:
            put('price_date', cn.history('^GSPC', 5).index[-1].strftime('%Y-%m-%d'), filled)
        except Exception:
            pass

    if filled:
        src_map = {k: (SRC + ('(指数日K线计算)' if ('rsi' in k or 'dma' in k or 'dev' in k or 'slope' in k or 'below' in k) else '')) for k in filled}
        merged_src = dict(EXISTING.get('_src', {}))
        merged_src.update(src_map)
        SNAP['_src'] = merged_src
        update_snapshot(SNAP)
        print(f'\n[OK] 国内兜底补齐 {len(filled)} 个缺失字段（来源：{SRC}）')
    else:
        print('\n[OK] 无缺失字段需要兜底（Yahoo 数据完整）')


if __name__ == '__main__':
    main()
