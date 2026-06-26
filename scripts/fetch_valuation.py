# -*- coding: utf-8 -*-
"""
fetch_valuation.py — 估值字段脚本化（减少人工 WebSearch 依赖）
当前可靠脚本化：CAPE 席勒市盈率（multpl.com，高成功率）。
Forward P/E / Top10 / 巴菲特 数据源多为 JS 渲染或反爬，保留人工，但打印权威链接提醒。
拿不到一律不写（报告显示 待核实），绝不编造。
"""
import re
import warnings

import requests

warnings.filterwarnings('ignore')
from snapshot_util import update_snapshot

H = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
SNAP = {}


def fetch_cape():
    try:
        r = requests.get('https://www.multpl.com/shiller-pe', timeout=15, headers=H)
        r.raise_for_status()
        m = re.search(r'Current\s+Shiller\s+PE\s+Ratio[^0-9]*([0-9]+\.[0-9]+)', r.text, re.I)
        if m:
            cape = float(m.group(1))
            print(f'CAPE 席勒市盈率 (multpl): {cape}')
            SNAP['cape_spx'] = cape
            return
    except Exception as e:
        print(f'CAPE 获取失败: {e}')
    print('CAPE: 需人工核实 → https://www.multpl.com/shiller-pe')


def main():
    print('==== 估值字段脚本化 ====')
    fetch_cape()
    print('\n📝 以下字段仍需人工 WebSearch（写入 narrative.json）:')
    print('   Forward P/E → gurufocus / FactSet Earnings Insight')
    print('   Top10 集中度 → invesco(QQQ) / slickcharts(SPY)')
    print('   巴菲特指标 → currentmarketvaluation.com')
    if SNAP:
        update_snapshot(SNAP)
        print('\n[OK] CAPE 已写入 data/latest_snapshot.json')


if __name__ == '__main__':
    main()
