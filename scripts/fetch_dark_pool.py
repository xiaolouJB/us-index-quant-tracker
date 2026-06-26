# -*- coding: utf-8 -*-
"""
fetch_dark_pool.py — SqueezeMetrics DIX/GEX 增强版（模块J）
数据源: https://squeezemetrics.com/monitor/static/DIX.csv
在旧版基础上增加：模块J阈值自动判定、5日趋势、操作联动结论输出。
"""
import io
import warnings

import pandas as pd
import requests

warnings.filterwarnings('ignore')

from snapshot_util import update_snapshot

URL = 'https://squeezemetrics.com/monitor/static/DIX.csv'
SNAP = {}


def classify_dix(dix_pct):
    if dix_pct > 45.0:
        return '机构极度吸筹（强烈看涨/底背离信号）'
    if dix_pct > 40.0:
        return '机构正常（市场常态）'
    return '机构极度派发/无接盘（看跌/破位预警⚠️）'


def main():
    try:
        r = requests.get(URL, timeout=30, headers={'User-Agent': 'Mozilla/5.0'})
        r.raise_for_status()
        df = pd.read_csv(io.StringIO(r.text))
        df.columns = [c.strip().lower() for c in df.columns]
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'])
            df = df.sort_values('date')
    except Exception as e:
        print(f'❌ DIX数据获取失败: {e}')
        print('   → 模块J本期降级：DIX/GEX 标注"数据缺失"，按保守原则处理（视同无超级抄底共振信号）')
        return

    last = df.iloc[-1]
    dix = float(last['dix']) * 100
    gex = float(last['gex'])
    date = last['date'].strftime('%Y-%m-%d') if 'date' in df.columns else 'N/A'
    dix5 = float(df['dix'].tail(5).mean()) * 100

    gamma_state = '正Gamma压舱石（做市商抑制波动）' if gex > 0 else '负Gamma波动陷阱⚠️'
    print('=== SqueezeMetrics 暗池与GEX（模块J）===')
    print(f'数据日期: {date}')
    print(f'DIX: {dix:.2f}%（5日均值 {dix5:.2f}%）→ {classify_dix(dix)}')
    print(f'GEX: {gex:,.0f}（${gex/1e9:.2f}B）→ {gamma_state}')

    print()
    print('--- 操作联动结论 ---')
    if gex < 0:
        print('⛔ 负Gamma熔断生效：任何灯号下强制冻结所有主动加仓，仅保留周四定投，待GEX转正解封')
        if dix <= 40.0:
            print('⛔⛔ 暗流溃败共振（DIX≤40% + GEX<0）：流动性真空，立刻收缩战线，防守最优先')
    else:
        if dix > 45.0:
            print('✅ 机构吸筹 + 正Gamma：若主灯号为红/黄且GEX为由负转正，构成"超级抄底共振"窗口（需核对前一日GEX符号）')
        else:
            print('✅ 正Gamma常态：无模块J否决，按主灯号执行')

    print(f'\n最近5个交易日:\n{df.tail(5).to_string(index=False)}')
    SNAP.update({'dix_pct': round(dix, 2), 'gex_dollars': gex, 'gex_bn': round(gex / 1e9, 2), 'dix_date': date})
    update_snapshot(SNAP)
    print('\n✅ 关键字段已写入 data/latest_snapshot.json')


if __name__ == '__main__':
    main()
