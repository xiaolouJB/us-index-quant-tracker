# -*- coding: utf-8 -*-
"""
fetch_fund_flow.py — 主力大单资金流追踪
输出：SPY/QQQ的日级主力资金净流入（东财 push2his）
"""
import requests
from snapshot_util import update_snapshot

SNAP = {}

def fetch_flow(secid, symbol):
    url = 'http://push2his.eastmoney.com/api/qt/stock/fflow/kline/get'
    params = {
        'secid': secid,
        'lmt': '1',
        'klt': '101',
        'fields1': 'f1,f2,f3,f7',
        'fields2': 'f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61,f62,f63,f64,f65'
    }
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    try:
        r = requests.get(url, params=params, headers=headers, timeout=10)
        r.raise_for_status()
        data = r.json()
        klines = data.get('data', {}).get('klines', [])
        
        if not klines:
            print(f'{symbol}: 暂无资金流数据')
            return None
        
        # 格式: Date, 主力净流入, 小单净流入, 中单净流入, 大单净流入, 超大单净流入
        latest = klines[-1].split(',')
        date = latest[0]
        main_flow = float(latest[1])
        
        print(f'{symbol} ({date}): 主力资金净流入 {main_flow / 10000:+.0f} 万元')
        return main_flow
        
    except Exception as e:
        print(f'{symbol}: 资金流获取失败 ({e})')
        return None

def main():
    print('==== 核心宽基 ETF 主力资金流 ====')
    spy_flow = fetch_flow('107.SPY', 'SPY')
    qqq_flow = fetch_flow('105.QQQ', 'QQQ')
    
    SNAP.update({
        'spy_main_flow': spy_flow,
        'qqq_main_flow': qqq_flow
    })
    update_snapshot(SNAP)
    print('\n[OK] 关键字段已写入 data/latest_snapshot.json')

if __name__ == '__main__':
    main()
