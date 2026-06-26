# -*- coding: utf-8 -*-
"""
run_inspection.py — 巡检总指挥（一条命令跑完整条数据管线）
解决"换模型就出错"的前半段：把"模型手动跑11个脚本"压成"代码一键跑完"。

流程：
  1) 清空旧快照
  2) 依序运行全部 fetcher（每个独立子进程，单个失败不影响其余）
  3) 读取 data/latest_snapshot.json
  4) 计算派生字段，逐字段打状态标签（OK / MISSING / STALE）
  5) 写出 data/report_data.json（report 的唯一权威数据源）
  6) 打印 PASS/FAIL 摘要，列出所有缺失/陈旧字段

用法：python scripts/run_inspection.py
输出：data/report_data.json + 控制台体检清单
退出码：0=核心字段齐全可出报告；2=核心字段缺失（禁止出报告）
"""
import json
import os
import subprocess
import sys
from datetime import datetime, date

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS_DIR = os.path.join(BASE_DIR, 'scripts')
DATA_DIR = os.path.join(BASE_DIR, 'data')
SNAPSHOT_PATH = os.path.join(DATA_DIR, 'latest_snapshot.json')
REPORT_DATA_PATH = os.path.join(DATA_DIR, 'report_data.json')

# 顺序执行（可靠优先：避免并行同时猛打 Yahoo 被限流导致字段缺失）。
# 提速靠各脚本内部快速失败（尤其 fetch_fred 快速降级），而非并行。
CLEAR = 'clear_snapshot.py'
PIPELINE = [
    'fetch_all.py',
    'fetch_fred.py',
    'fetch_technicals.py',
    'fetch_options_walls.py',
    'fetch_dark_pool.py',
    'fetch_sentiment.py',
    'fetch_fund_flow.py',
    'fetch_valuation.py',
]

# 核心字段：缺失则禁止出报告（脚本本应稳定获取，来自 yfinance/SqueezeMetrics/CNN）
CORE_FIELDS = [
    'ndx_close', 'spx_close', 'qqq_close', 'spy_close',
    'ndx_chg_pct', 'spx_chg_pct', 'qqq_chg_pct', 'spy_chg_pct',
    'vix', 'us10y', 'price_date',
    'ndx_200dma', 'spx_200dma', 'ndx_dev200', 'spx_dev200',
    'ndx_rsi', 'spx_rsi',
    'qqq_put_wall', 'qqq_call_wall', 'spy_put_wall', 'spy_call_wall',
    'dix_pct', 'gex_bn',
    'fear_greed',
]
# 可选字段：FRED 在部分网络环境不可达，缺失只告警不阻断
OPTIONAL_FIELDS = [
    'us2y', 't10y2y_bp', 'hy_oas', 'hyg_ief_chg20', 'm2_yoy',
    'household_equity_pct', 'buffett_ratio', 'vxn', 'cape_spx',
    'qqq_net_gex_bn', 'spy_net_gex_bn', 'qqq_net_dex_bn', 'spy_net_dex_bn',
    'spy_pcr_vol', 'qqq_pcr_vol', 'leading_verdict',
]
# 人工字段：脚本拿不到，必须由模型 WebSearch 后写入 narrative.json 的 manual_fields
MANUAL_FIELDS = ['fwd_pe_ndx', 'fwd_pe_spx', 'top10_qqq', 'top10_spy', 'buffett', 'fedwatch_text']


def run_pipeline():
    """clear 先跑，其余 fetcher 顺序执行（写共享快照，安全无竞态）。"""
    env = os.environ.copy()
    env['PYTHONIOENCODING'] = 'utf-8'   # 血泪教训：防 Emoji 触发 UnicodeEncodeError 掩盖真实结果
    env['PYTHONUTF8'] = '1'
    results = []
    for script in [CLEAR] + PIPELINE:
        path = os.path.join(SCRIPTS_DIR, script)
        if not os.path.exists(path):
            results.append((script, 'SKIP(缺脚本)'))
            continue
        try:
            p = subprocess.run([sys.executable, path], env=env, cwd=SCRIPTS_DIR,
                               capture_output=True, text=True, timeout=120)
            ok = p.returncode == 0
            results.append((script, 'OK' if ok else f'EXIT{p.returncode}'))
            if script == CLEAR:
                continue
            tail = (p.stdout or '').strip().splitlines()[-1:] or ['(无输出)']
            print(f'  [{"OK" if ok else "WARN"}] {script:24s} {tail[0][:64]}')
            if not ok and p.stderr:
                print(f'       stderr: {p.stderr.strip().splitlines()[-1][:80]}')
        except subprocess.TimeoutExpired:
            results.append((script, 'TIMEOUT'))
            print(f'  [WARN] {script:24s} 超时120s（可能网络阻断）')
        except Exception as e:
            results.append((script, f'ERR {e}'))
            print(f'  [WARN] {script:24s} {e}')
    return results


def days_old(price_date_str):
    try:
        d = datetime.strptime(price_date_str, '%Y-%m-%d').date()
        return (date.today() - d).days
    except Exception:
        return None


def main():
    print('=' * 60)
    print('巡检总指挥 run_inspection.py — 一键跑完数据管线')
    print('=' * 60)
    print('\n[1/3] 运行数据管线...')
    pipe = run_pipeline()

    print('\n[2/3] 读取快照并体检...')
    if not os.path.exists(SNAPSHOT_PATH):
        print('  ⛔ latest_snapshot.json 不存在，管线全军覆没，禁止出报告')
        sys.exit(2)
    with open(SNAPSHOT_PATH, encoding='utf-8') as f:
        snap = json.load(f)

    # —— 国内兜底：若 Yahoo 核心价格/RSI 缺失（疑似被墙或瞬时失败），自动调用腾讯源补齐 ——
    core_cn = ['ndx_close', 'spx_close', 'qqq_close', 'spy_close', 'ndx_rsi', 'spx_rsi', 'ndx_200dma', 'spx_200dma']
    if any(snap.get(f) is None for f in core_cn):
        print('  ⚠️ Yahoo 核心价格缺失，启用国内兜底源（腾讯财经）...')
        env = os.environ.copy()
        env['PYTHONIOENCODING'] = 'utf-8'
        env['PYTHONUTF8'] = '1'
        cnp = os.path.join(SCRIPTS_DIR, 'fetch_prices_cn.py')
        if os.path.exists(cnp):
            subprocess.run([sys.executable, cnp], env=env, cwd=SCRIPTS_DIR,
                           capture_output=True, text=True, timeout=60)
            with open(SNAPSHOT_PATH, encoding='utf-8') as f:
                snap = json.load(f)

    status = {}
    for fld in CORE_FIELDS:
        status[fld] = 'OK' if snap.get(fld) is not None else 'MISSING'
    for fld in OPTIONAL_FIELDS:
        status[fld] = 'OK' if snap.get(fld) is not None else 'MISSING(可选)'
    for fld in MANUAL_FIELDS:
        status[fld] = 'PENDING(待模型WebSearch填入narrative.json)'

    # 新鲜度
    age = days_old(snap.get('price_date', ''))
    freshness = 'OK'
    if age is None:
        freshness = 'UNKNOWN'
    elif age > 5:
        freshness = f'STALE(行情已{age}天前)'

    core_missing = [f for f in CORE_FIELDS if status[f] == 'MISSING']

    report_data = {
        '_generated': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        '_price_date': snap.get('price_date'),
        '_freshness': freshness,
        '_field_status': status,
        '_core_missing': core_missing,
        '_src_override': snap.get('_src', {}),   # 兜底源命中时的来源覆盖（如腾讯）
        '_pipeline': dict(pipe),
        'data': snap,
    }
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(REPORT_DATA_PATH, 'w', encoding='utf-8') as f:
        json.dump(report_data, f, ensure_ascii=False, indent=2)

    print('\n[3/3] 体检结论：')
    print(f'  行情基准日: {snap.get("price_date")}  新鲜度: {freshness}')
    opt_missing = [f for f in OPTIONAL_FIELDS if status[f].startswith('MISSING')]
    if opt_missing:
        print(f'  ⚠️ 可选字段缺失（多为FRED不可达，需人工核或降级）: {", ".join(opt_missing)}')
    print(f'  📝 人工字段（必须WebSearch填入 narrative.json）: {", ".join(MANUAL_FIELDS)}')
    print(f'\n  → 权威数据已写入: {REPORT_DATA_PATH}')

    if core_missing:
        print(f'\n⛔ 核心字段缺失，禁止出报告: {", ".join(core_missing)}')
        print('   请排查对应脚本/网络后重跑 run_inspection.py')
        sys.exit(2)
    if freshness.startswith('STALE'):
        print(f'\n⚠️ 行情数据偏旧（{freshness}）：确认今天是否休市；如非休市需排查数据源')
    print('\n✅ 核心字段齐全 — 下一步：模型写 data/narrative.json，再运行 build_report.py')


if __name__ == '__main__':
    main()
