# -*- coding: utf-8 -*-
"""
fetch_options_walls.py — 期权墙与 GEX 增强版（模块J / Gamma Walls）
输出：QQQ/SPY 的 Call/Put Wall（±15%限制）、净GEX（BS Gamma近似，做市商约定：
卖Put买Call视角 → Call贡献正Gamma、Put贡献负Gamma）、Gamma翻转位估算。
"""
import argparse
import math
import warnings
from datetime import datetime

import yfinance as yf

warnings.filterwarnings('ignore')

from snapshot_util import update_snapshot

SNAP = {}
RANGE_PCT = 0.15          # 仅统计现价±15%（SKILL 2.5节 绝对偏离度控制）
N_EXPIRATIONS = 4         # 默认统计最近4个交割日（SPY/QQQ为日度期权，约覆盖1周）
CONTRACT_MULT = 100
TOP_N = 5                 # 输出OI前N名行权价，便于核验Wall是否真实集中


def norm_pdf(x):
    return math.exp(-0.5 * x * x) / math.sqrt(2 * math.pi)


def bs_gamma(spot, strike, t_years, iv):
    """Black-Scholes Gamma（r=0简化）。"""
    if t_years <= 0 or iv is None or not (0.01 < iv < 5.0):
        return 0.0
    try:
        d1 = (math.log(spot / strike) + 0.5 * iv * iv * t_years) / (iv * math.sqrt(t_years))
        return norm_pdf(d1) / (spot * iv * math.sqrt(t_years))
    except (ValueError, ZeroDivisionError):
        return 0.0


def bs_delta(spot, strike, t_years, iv, opt_type):
    """Black-Scholes Delta（r=0简化）。"""
    if t_years <= 0 or iv is None or not (0.01 < iv < 5.0):
        return 0.0
    try:
        d1 = (math.log(spot / strike) + 0.5 * iv * iv * t_years) / (iv * math.sqrt(t_years))
        nd1 = (1.0 + math.erf(d1 / math.sqrt(2.0))) / 2.0
        return nd1 if opt_type == 'call' else nd1 - 1.0
    except (ValueError, ZeroDivisionError):
        return 0.0


def analyze(symbol, n_exp=N_EXPIRATIONS):
    print(f'==== {symbol} 期权水位与GEX ====')
    try:
        tk = yf.Ticker(symbol)
        h = tk.history(period='5d')
        h = h[h['Close'].notna()]
        spot = float(h['Close'].iloc[-1])
        expirations = tk.options
        if not expirations:
            print(f'[{symbol}] 未找到期权数据')
            return

        used_exps = list(expirations[:n_exp])
        print(f'统计交割日: {", ".join(used_exps)}')
        call_oi, put_oi = {}, {}
        gex_by_strike = {}       # 净GEX（$ per 1% move），call正/put负
        dex_by_strike = {}       # 做市商净DEX（$），假定客户买入，做市商做反向
        today = datetime.now().date()

        for exp in used_exps:
            try:
                chain = tk.option_chain(exp)
            except Exception:
                continue
            t_years = max(((datetime.strptime(exp, '%Y-%m-%d').date() - today).days, 0.5)[0], 0.5) / 365.0
            for df, sign, oi_map, opt_type in ((chain.calls, +1, call_oi, 'call'), (chain.puts, -1, put_oi, 'put')):
                for _, row in df.iterrows():
                    strike = float(row['strike'])
                    if abs(strike - spot) / spot > RANGE_PCT:
                        continue
                    oi = float(row.get('openInterest') or 0)
                    if oi <= 0:
                        continue
                    oi_map[strike] = oi_map.get(strike, 0) + oi
                    iv = row.get('impliedVolatility')
                    v = float(iv) if iv else None
                    gamma = bs_gamma(spot, strike, t_years, v)
                    delta = bs_delta(spot, strike, t_years, v, opt_type)
                    
                    # 美元Gamma每1%波动: gamma * OI * 100 * spot^2 * 0.01
                    gex = sign * gamma * oi * CONTRACT_MULT * spot * spot * 0.01
                    gex_by_strike[strike] = gex_by_strike.get(strike, 0) + gex
                    
                    # 做市商净DEX: 客户买入 Delta = delta * oi * 100 * spot，做市商持有反向
                    dex = -1.0 * delta * oi * CONTRACT_MULT * spot
                    dex_by_strike[strike] = dex_by_strike.get(strike, 0) + dex

        if not call_oi or not put_oi:
            print(f'[{symbol}] OI数据不足')
            return

        def find_wall(oi_dict, spot_price, is_call):
            valid_strikes = [k for k in oi_dict.keys() if (k >= spot_price if is_call else k <= spot_price)]
            if not valid_strikes:
                return max(oi_dict, key=oi_dict.get) if oi_dict else None
            for pct in [0.05, 0.10, 0.15]:
                in_range = [k for k in valid_strikes if abs(k - spot_price)/spot_price <= pct]
                if in_range:
                    return max(in_range, key=lambda k: oi_dict[k])
            return max(valid_strikes, key=lambda k: oi_dict[k])

        call_wall = find_wall(call_oi, spot, True)
        put_wall = find_wall(put_oi, spot, False)

        # OI排行榜：核验Wall是否真实集中（防止单一极值误导）
        top_puts = sorted(put_oi.items(), key=lambda kv: kv[1], reverse=True)[:TOP_N]
        top_calls = sorted(call_oi.items(), key=lambda kv: kv[1], reverse=True)[:TOP_N]
        print('Put OI 前{}名: '.format(TOP_N) + ' | '.join(f'{k}({v:,.0f})' for k, v in top_puts))
        print('Call OI 前{}名: '.format(TOP_N) + ' | '.join(f'{k}({v:,.0f})' for k, v in top_calls))
        net_gex = sum(gex_by_strike.values())
        net_gex_bn = net_gex / 1e9
        net_dex = sum(dex_by_strike.values())
        net_dex_bn = net_dex / 1e9

        # Gamma翻转位估算：按行权价升序累计净GEX，取符号翻转处
        flip = None
        cum = 0.0
        for k in sorted(gex_by_strike):
            prev = cum
            cum += gex_by_strike[k]
            if prev < 0 <= cum or prev > 0 >= cum:
                flip = k
        gamma_state = '偏正Gamma（局部减震）' if net_gex > 0 else '偏负Gamma（局部波动放大倾向）'
        dex_state = 'DEX偏空(下行引力)' if net_dex < 0 else 'DEX偏多(上行引力)'

        print(f'现价: {spot:.2f}')
        print(f'Call Wall（阻力）: {call_wall}  (OI: {call_oi.get(call_wall, 0):,.0f})')
        print(f'Put Wall（支撑）: {put_wall}  (OI: {put_oi.get(put_wall, 0):,.0f})')
        if put_wall and call_wall and put_wall > call_wall:
            print('⛔ 常识校验失败：Put Wall 高于 Call Wall，数据异常，禁止用于实盘！')
        print(f'净GEX（近{len(used_exps)}个交割日，±15%）: {net_gex_bn:+.2f} $B/1%波动 → {gamma_state}')
        print(f'净DEX（做市商敞口近似）: {net_dex_bn:+.2f} $B → {dex_state}')
        print('   注：此为ETF期权链局部近似参考值；模块J"负Gamma熔断"判定一律以 SqueezeMetrics GEX 为准')
        if flip:
            pos = '现价上方' if flip > spot else '现价下方'
            print(f'Gamma翻转位估算: ~{flip}（{pos}；跌破/升破此位附近Gamma状态可能反转）')
        else:
            print('Gamma翻转位: 未在±15%范围内出现符号翻转（净GEX方向在全区间一致）')
        print('=' * 46)

        p = symbol.lower()
        SNAP.update({
            f'{p}_spot': round(spot, 2),
            f'{p}_call_wall': call_wall,
            f'{p}_put_wall': put_wall,
            f'{p}_net_gex_bn': round(net_gex_bn, 2) if not math.isnan(net_gex_bn) else None,
            f'{p}_net_dex_bn': round(net_dex_bn, 2) if not math.isnan(net_dex_bn) else None,
            f'{p}_gamma_flip': flip,
        })
    except Exception as e:
        print(f'[{symbol}] 获取失败: {e}')
        p = symbol.lower()
        SNAP.update({
            f'{p}_spot': None,
            f'{p}_call_wall': None,
            f'{p}_put_wall': None,
            f'{p}_net_gex_bn': None,
            f'{p}_net_dex_bn': None,
            f'{p}_gamma_flip': None,
        })


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--expirations', type=int, default=N_EXPIRATIONS,
                    help='统计最近N个交割日（默认4≈1周；加大可纳入月度OPEX大持仓）')
    args = ap.parse_args()
    print(f'正在获取真实期权数据（限定现价±15%，最近{args.expirations}个交割日）...\n')
    analyze('QQQ', args.expirations)
    analyze('SPY', args.expirations)
    update_snapshot(SNAP)
    print('\n✅ 关键字段已写入 data/latest_snapshot.json')


if __name__ == '__main__':
    main()
