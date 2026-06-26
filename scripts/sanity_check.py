# -*- coding: utf-8 -*-
"""
sanity_check.py — 金融数据三重审核门禁（SKILL.md 第3节的脚本化实现）
用法：
  python scripts/sanity_check.py [--fwd-pe-ndx 23.7] [--fwd-pe-spx 20.7] [--commit]

流程：
  1. 读取 data/latest_snapshot.json（各 fetch 脚本的汇总输出）
  2. 与 history/indicators.csv 最后一期对比，执行环比熔断与常识校验
  3. 全部通过且带 --commit 时，把本期数据追加写入 history/indicators.csv
退出码：0=通过（可出报告）；1=存在⛔级失败（禁止出报告，先排查数据源）
"""
import argparse
import csv
import os
import sys
from datetime import datetime

from snapshot_util import load_snapshot, HISTORY_PATH

HISTORY_COLUMNS = [
    'date', 'ndx_close', 'spx_close', 'qqq_close', 'spy_close',
    'us10y', 'us2y', 'vix', 'vxn', 'usdcny',
    'ndx_200dma', 'spx_200dma',
    'fwd_pe_ndx', 'fwd_pe_spx', 'erp_ndx', 'erp_spx',
    'dix_pct', 'gex_bn',
    'qqq_call_wall', 'qqq_put_wall', 'spy_call_wall', 'spy_put_wall',
    'ndx_rsi', 'spx_rsi', 'fear_greed', 'spy_pcr_vol',
]

PASS, WARN, FAIL = '✅', '⚠️', '⛔'
issues = {'warn': 0, 'fail': 0}


def report(level, msg):
    print(f'{level} {msg}')
    if level == WARN:
        issues['warn'] += 1
    elif level == FAIL:
        issues['fail'] += 1


def load_last_history():
    if not os.path.exists(HISTORY_PATH):
        return None
    with open(HISTORY_PATH, encoding='utf-8-sig', newline='') as f:
        rows = list(csv.DictReader(f))
    return rows[-1] if rows else None


def fnum(d, key):
    v = d.get(key)
    if v in (None, '', 'None'):
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def check_sanity(snap):
    print('--- 常识性校验 ---')
    critical_fields = ['ndx_close', 'spx_close', 'us10y', 'vix', 'dix_pct', 'spy_call_wall', 'spy_put_wall', 'qqq_call_wall', 'qqq_put_wall']
    missing = [f for f in critical_fields if snap.get(f) is None]
    if missing:
        report(FAIL, f'关键字段缺失: {", ".join(missing)}。由于快照已清空，此报错代表本次抓取彻底失败，请排查数据源，禁止出报告！')

    us10y = fnum(snap, 'us10y')
    vix = fnum(snap, 'vix')
    if us10y is None:
        report(FAIL, 'US10Y 缺失：fetch_all.py 未成功运行')
    elif not (0 < us10y < 10):
        report(FAIL, f'US10Y={us10y} 违背金融常识（应在0–10%）')
    else:
        report(PASS, f'US10Y={us10y:.2f}% 正常')
    if vix is None:
        report(WARN, 'VIX 缺失')
    elif vix < 8 or vix > 100:
        report(FAIL, f'VIX={vix} 违背常识（<8或>100）')
    else:
        report(PASS, f'VIX={vix:.2f} 正常')
    usdcny = fnum(snap, 'usdcny')
    if usdcny is not None and not (5.5 < usdcny < 9.0):
        report(FAIL, f'USD/CNY={usdcny} 超出合理区间(5.5–9.0)')

    for p in ('qqq', 'spy'):
        cw, pw = fnum(snap, f'{p}_call_wall'), fnum(snap, f'{p}_put_wall')
        spot = fnum(snap, f'{p}_spot')
        close = fnum(snap, f'{p}_close')
        if cw and pw:
            if pw > cw:
                report(FAIL, f'{p.upper()} Put Wall({pw}) 高于 Call Wall({cw})，期权数据异常')
            else:
                report(PASS, f'{p.upper()} Walls 排列正常 (Put {pw} < Call {cw})')
            if spot:
                for name, w in (('Call Wall', cw), ('Put Wall', pw)):
                    if abs(w - spot) / spot > 0.20:
                        report(FAIL, f'{p.upper()} {name}={w} 距现价{spot}超20%，禁止作为实盘参考点')
                if close and abs(spot - close) / close > 0.01:
                    report(FAIL, f'{p.upper()} 期权现货价({spot}) 与 主行情收盘价({close}) 严重脱节！期权数据可能滞后，禁止出报告！')


def check_dod(snap, last, fwd_pe_ndx, fwd_pe_spx):
    print()
    print('--- 环比变动熔断（对比上期 history/indicators.csv）---')
    if last is None:
        report(WARN, '无历史数据（首次运行），跳过环比检查；--commit 后建立基线')
        return
    print(f"上期基准日: {last.get('date')}")

    us10y_now, us10y_prev = fnum(snap, 'us10y'), fnum(last, 'us10y')
    if us10y_now and us10y_prev:
        d_bp = (us10y_now - us10y_prev) * 100
        if abs(d_bp) > 25:
            report(FAIL, f'US10Y 环比变动 {d_bp:+.0f}bp > 25bp：先核实是否有非农/CPI/FOMC等重大事件，无事件则判定数据源错误')
        else:
            report(PASS, f'US10Y 环比 {d_bp:+.1f}bp 正常')

    for label, key in (('NDX', 'ndx_close'), ('SPX', 'spx_close')):
        now, prev = fnum(snap, key), fnum(last, key)
        if now and prev:
            chg = (now - prev) / prev * 100
            if abs(chg) > 8:
                report(FAIL, f'{label} 价格环比 {chg:+.2f}% 超过±8%熔断带，核实数据日期是否错位')
            else:
                report(PASS, f'{label} 价格环比 {chg:+.2f}% 正常')

    pairs = (('NDX', fwd_pe_ndx, 'fwd_pe_ndx', 'erp_ndx'), ('SPX', fwd_pe_spx, 'fwd_pe_spx', 'erp_spx'))
    for label, pe_now, pe_key, erp_key in pairs:
        pe_prev = fnum(last, pe_key)
        if pe_now and pe_prev:
            chg = (pe_now - pe_prev) / pe_prev * 100
            if abs(chg) > 5:
                report(FAIL, f'{label} Forward P/E 环比 {chg:+.1f}% > 5%：核实数据来源/财报事件')
            else:
                report(PASS, f'{label} Forward P/E 环比 {chg:+.1f}% 正常')
        if pe_now and us10y_now:
            erp_now = 100 / pe_now - us10y_now
            erp_prev = fnum(last, erp_key)
            print(f'   {label} ERP = 100/{pe_now} − {us10y_now:.2f} = {erp_now:+.2f}%')
            if erp_prev is not None and abs(erp_now - erp_prev) > 1.0:
                report(FAIL, f'{label} ERP 环比波动 {erp_now - erp_prev:+.2f}pp > 1.0pp：暂停输出，核实宏观事件或数据源')


def commit(snap, fwd_pe_ndx, fwd_pe_spx, force=False):
    row = {}
    for c in HISTORY_COLUMNS:
        v = snap.get(c, '')
        if isinstance(v, float):
            v = round(v, 4)
        row[c] = v
    row['date'] = snap.get('price_date') or datetime.now().strftime('%Y-%m-%d')
    last = load_last_history()
    if last and last.get('date') and row['date'] <= last['date'] and not force:
        print(f"\n⚠️ 拒绝落库：本期行情基准日 {row['date']} 不晚于上期 {last['date']}（重复或数据滞后）。"
              f"确认无误可加 --force 强制写入。")
        return
    row['fwd_pe_ndx'] = fwd_pe_ndx or ''
    row['fwd_pe_spx'] = fwd_pe_spx or ''
    us10y = fnum(snap, 'us10y')
    if fwd_pe_ndx and us10y:
        row['erp_ndx'] = round(100 / fwd_pe_ndx - us10y, 2)
    if fwd_pe_spx and us10y:
        row['erp_spx'] = round(100 / fwd_pe_spx - us10y, 2)
    row['spy_pcr_vol'] = snap.get('spy_pcr_vol', '')
    os.makedirs(os.path.dirname(HISTORY_PATH), exist_ok=True)
    # 按日期 upsert + 排序整表重写：杜绝重复行与乱序（替代原 append）
    existing = {}
    if os.path.exists(HISTORY_PATH):
        with open(HISTORY_PATH, encoding='utf-8-sig', newline='') as f:
            for r in csv.DictReader(f):
                existing[r.get('date')] = r
    existing[row['date']] = row
    ordered = sorted(existing.values(), key=lambda r: r.get('date', ''))
    with open(HISTORY_PATH, 'w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=HISTORY_COLUMNS, extrasaction='ignore')
        w.writeheader()
        w.writerows(ordered)
    print(f"\n📝 本期数据已落库（去重+排序，共{len(ordered)}行）: {HISTORY_PATH} (date={row['date']})")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--fwd-pe-ndx', type=float, default=None)
    ap.add_argument('--fwd-pe-spx', type=float, default=None)
    ap.add_argument('--commit', action='store_true')
    ap.add_argument('--force', action='store_true', help='允许写入与上期同日/更早的行（默认拒绝防重复）')
    args = ap.parse_args()

    snap = load_snapshot()
    if not snap:
        print(f'{FAIL} data/latest_snapshot.json 不存在或为空，请先运行各 fetch 脚本')
        sys.exit(1)
    print(f"快照更新时间: {snap.get('_updated')} | 行情基准日: {snap.get('price_date')}")
    if args.fwd_pe_ndx is None or args.fwd_pe_spx is None:
        report(WARN, '未提供 --fwd-pe-ndx / --fwd-pe-spx，ERP 相关审核将跳过（报告中仍须人工执行同标准）')

    print()
    check_sanity(snap)
    last = load_last_history()
    check_dod(snap, last, args.fwd_pe_ndx, args.fwd_pe_spx)

    print()
    if issues['fail']:
        print(f'⛔ 审核未通过：{issues["fail"]} 项失败 / {issues["warn"]} 项警告 — 禁止出报告，先排查数据源！')
        sys.exit(1)
    print(f'✅ 审核通过（警告 {issues["warn"]} 项）— 可以出报告')
    if args.commit:
        commit(snap, args.fwd_pe_ndx, args.fwd_pe_spx, force=args.force)


if __name__ == '__main__':
    main()
