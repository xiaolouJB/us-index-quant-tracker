# -*- coding: utf-8 -*-
"""
build_report.py — 报告确定性装配器（根治"换模型就出错"的后半段）
数字/水平/影响/五维评级/灯号/天气/操作档位 全部由代码从 report_data.json 规则化算出，
模型只提供 narrative.json 里的纯文字（特别警报、投资逻辑、仲裁等）。
→ 无论哪个模型跑，报告里的事实与判断骨架完全一致。

用法：
  python scripts/build_report.py                 # 用 data/narrative.json
  python scripts/build_report.py --no-narrative  # 不带文字也能出（占位）
输出：分析报告/YYYY-MM-DD_美国宽基指数巡检报告.md
"""
import argparse
import json
import os
import re
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, 'data')
REPORT_DATA_PATH = os.path.join(DATA_DIR, 'report_data.json')
NARRATIVE_PATH = os.path.join(DATA_DIR, 'narrative.json')
CAT_PATH = os.path.join(DATA_DIR, 'cat_levels.json')
OUT_DIR = os.path.join(BASE_DIR, '分析报告')

RED, YEL, GRN, NA = '🔴', '🟡', '🟢', '⚪'
TODO = '⚠️待核实'

# 字段 → (来源, URL)。兜底命中时由 report_data._src_override 覆盖（如腾讯）。
SOURCE_MAP = {
    'price': ('Yahoo Finance', 'finance.yahoo.com'),
    'ma': ('Yahoo Finance（均线为收盘价计算）', 'finance.yahoo.com'),
    'us10y': ('Yahoo ^TNX', 'finance.yahoo.com'),
    'us2y': ('FRED DGS2 / 备源 2YY=F', 'fred.stlouisfed.org'),
    't10y2y': ('FRED T10Y2Y / 备源 ^TNX−2YY=F', 'fred.stlouisfed.org'),
    'cape': ('multpl.com', 'multpl.com/shiller-pe'),
    'dix_gex': ('SqueezeMetrics', 'squeezemetrics.com'),
    'walls': ('Yahoo 期权链（BS近似GEX/DEX）', 'finance.yahoo.com'),
    'fear_greed': ('CNN Fear & Greed', 'cnn.com/markets/fear-and-greed'),
    'pcr': ('Yahoo 期权链计算', 'finance.yahoo.com'),
    'tech': ('Yahoo Finance（RSI/MACD/分型计算）', 'finance.yahoo.com'),
    'fund_flow': ('东方财富', 'eastmoney.com'),
    'manual': ('人工 WebSearch 核实', '见 narrative_schema.md'),
}


# ───────────────────────── 取数与格式化 ─────────────────────────
def g(d, k, default=None):
    v = d.get(k)
    return default if v is None else v


def num(v, fmt='{:.2f}', dash=TODO):
    if v is None:
        return dash
    try:
        return fmt.format(float(v))
    except (TypeError, ValueError):
        return str(v)


def pct(v):
    if v is None:
        return TODO
    return f'{float(v):+.2f}%'


# ───────────────────────── 规则引擎（确定性判定） ─────────────────────────
def erp(fwd_pe, us10y):
    if fwd_pe and us10y:
        return round(100.0 / float(fwd_pe) - float(us10y), 2)
    return None


def light_overall(idx, ep, ps, cape, top10, us10y, manual):
    """总灯号：红/黄/绿。idx in {'ndx','spx'}"""
    base = 2.0 if idx == 'ndx' else 2.5
    ps_red = 5.0 if idx == 'ndx' else 3.0
    top_red = 50.0 if idx == 'ndx' else 30.0
    red = False
    if ep is not None and ep < 0:
        red = True
    if ps is not None and ps > ps_red:
        red = True
    if idx == 'spx' and cape is not None and cape > 30:
        red = True
    if top10 is not None and us10y is not None and top10 > top_red and us10y > 4.35:
        red = True
    if red:
        return RED, '系统熔断 / 高位极度危险'
    if ep is not None and us10y is not None and ep >= base and us10y <= 4.35:
        return GRN, '完美共振 / 击球区'
    return YEL, '估值偏贵 / 震荡防守'


def rate_valuation(ep, ps, cape, buffett, idx, base):
    ps_red = 5.0 if idx == 'ndx' else 3.0
    if (ep is not None and ep < 0) or (ps is not None and ps > ps_red) \
       or (idx == 'spx' and cape is not None and cape > 30) or (buffett is not None and buffett >= 200):
        return RED
    if ep is not None and ep >= base and (buffett is None or buffett < 150):
        return GRN
    return YEL


def rate_macro(us10y, t10y2y, hy_oas):
    if us10y is None:
        return YEL
    if us10y > 4.6 or (t10y2y is not None and t10y2y < -50) or (hy_oas is not None and hy_oas > 5):
        return RED
    if us10y < 4.0 and (t10y2y is None or t10y2y > 0):
        return GRN
    return YEL


SWING_CN = {'up': '上升结构(HH+HL)', 'down': '下降结构(LH+LL)', 'range': '震荡结构'}


def rate_trend(dev200, slope, days_below, swing, divergence):
    if days_below is not None and days_below > 5:
        return RED  # 有效跌破年线=结构破坏
    if dev200 is not None and dev200 > 0 and slope == '向上':
        # 价格在上升年线之上=结构完好；近期分型向下只降到中性，不直接红
        return YEL if swing == 'down' else GRN
    if swing == 'down':
        return RED
    return YEL


def rate_sentiment(fg):
    if fg is None:
        return YEL
    if fg <= 25:
        return GRN  # 极度恐惧=逆向买点
    if fg >= 75:
        return RED  # 极度贪婪=追高风险
    return YEL


def rate_money(gex_bn, dix):
    if (gex_bn is not None and gex_bn < 0) or (dix is not None and dix <= 40):
        return RED
    if (gex_bn is not None and gex_bn > 0) and (dix is not None and dix >= 45):
        return GRN
    return YEL


WEATHER = {RED: '⛈️ 暴雨预警', YEL: '⛅ 多云', GRN: '☀️ 晴天', NA: '❔ 数据待核实'}


def op_tier(light):
    """灯号→操作档位（去金额，纯档位话术）"""
    if light == RED:
        return {'buy': '全面暂停', 'dca': '减半执行', 'grid': '冻结'}
    if light == YEL:
        return {'buy': '小额脉冲', 'dca': '正常执行', 'grid': '待命'}
    if light == NA:
        return {'buy': '观望（数据待核实）', 'dca': '维持原档', 'grid': '待命'}
    return {'buy': '分批建仓', 'dca': '正常执行', 'grid': '激活'}


# ───────────────────────── 指标词典（含义固定 + 水平/影响规则化） ─────────────────────────
def lvl_erp(v):
    if v is None:
        return TODO, ''
    if v < 0:
        return '极差（倒挂）', '冒股票的险却赚得不如存银行，最硬的"别买"信号'
    if v < 2:
        return '偏低', '安全垫薄，性价比一般'
    return '健康', '为风险买单值得，估值有吸引力'


def lvl_pe(v, idx):
    if v is None:
        return TODO, ''
    norm = 20 if idx == 'ndx' else 18
    return ('偏贵' if v > norm else '正常'), '越高，预期落空时跌得越狠'


def lvl_cape(v):
    if v is None:
        return TODO, ''
    return ('泡沫区' if v > 30 else '正常'), '越高，未来10年长期回报通常越低'


def lvl_buffett(v):
    if v is None:
        return TODO, ''
    z = '极端泡沫区' if v > 200 else ('偏贵' if v > 150 else '合理')
    return z, '越高，股市相对实体经济越悬空'


def lvl_us10y(v):
    if v is None:
        return TODO, ''
    return ('偏高（>4.35压制线）' if v > 4.35 else '正常'), '越高=股票的地心引力越强，压制高估值'


def lvl_t10y2y(v):
    if v is None:
        return TODO, ''
    if v < -50:
        return '深度倒挂', '历史上的衰退前兆，需高度警惕'
    if v < 0:
        return '倒挂', '经济放缓信号'
    return '正常（为正）', '暂无衰退预警'


def lvl_dev(v):
    if v is None:
        return TODO, ''
    return ('上方（多头）' if v > 0 else '下方（破位）'), '站上年线=趋势没坏，跌破再便宜也先躲'


def lvl_dd(v):
    if v is None:
        return TODO, ''
    a = abs(v)
    z = '高位区' if a < 5 else ('常规回调' if a < 10 else ('技术性调整' if a < 20 else '技术性熊市'))
    return z, '离高点越近越要防"买在山顶"'


def lvl_rsi(v):
    if v is None:
        return TODO, ''
    z = '超买' if v > 70 else ('超卖' if v < 30 else '中性')
    return z, '超买别追，超卖（趋势没坏）反而是机会'


def lvl_fg(v):
    if v is None:
        return TODO, ''
    if v <= 25:
        z = '极度恐惧'
    elif v <= 45:
        z = '恐惧'
    elif v <= 55:
        z = '中性'
    elif v <= 75:
        z = '贪婪'
    else:
        z = '极度贪婪'
    return z, '极度恐惧常是逆向买点，极度贪婪要警惕回调'


def lvl_vix(v):
    if v is None:
        return TODO, ''
    z = '平静' if v < 15 else ('正常' if v < 25 else ('紧张' if v < 30 else '恐慌'))
    return z, '飙升=避险，长期极低=麻痹大意需警惕'


def lvl_pcr(v):
    if v is None:
        return TODO, ''
    z = '偏贪婪' if v < 0.7 else ('中性' if v <= 1.0 else '偏避险')
    return z, '极端值往往是反向信号'


def lvl_dix(v):
    if v is None:
        return TODO, ''
    z = '吸筹（偏多）' if v > 45 else ('常态' if v >= 40 else '派发（偏空）')
    return z, '高DIX是底部的看多旁证'


def lvl_gex(v):
    if v is None:
        return TODO, ''
    return ('正（减震器）' if v > 0 else '负（加速器）'), '正GEX下跌有缓冲，负GEX一跌就容易踩踏'


# ───────────────────────── 装配 ─────────────────────────
def row(*cells):
    return '| ' + ' | '.join(str(c) for c in cells) + ' |'


def strip_prefix(text, prefix):
    """去掉文案行首与给定标签重复的 'emoji+短标签：' 前缀。
    （表格时代遗留：单元格里自带标签；改成列表标题后标题里已有，再留就重复。）"""
    if not text or not prefix:
        return text
    m = re.match(r'^\s*(\S{1,12}?)\s*[：:]\s*(.*)$', text, re.S)
    if m:
        lab = m.group(1).replace(' ', '').replace('　', '')
        pre = prefix.replace(' ', '').replace('　', '')
        if lab == pre:
            return m.group(2)
    return text


def paras(text, per=2):
    """把长文案按中文句号/问号/感叹号切成短段落（每 per 句一段），适配手机阅读节奏。
    注意：分号不切——分号连接的是紧耦合分句，断开会留下悬空半句。"""
    if not text:
        return []
    sents = [s for s in re.split(r'(?<=[。！？])', text) if s.strip()]
    return [''.join(sents[i:i + per]) for i in range(0, len(sents), per)]


_CJK = '\u4e00-\u9fff'


def pangu(text):
    """盘古之白鹭：中文与拉丁字母/数字相邻时补一个半角空格。
    中文排版基本功；Markdown 渲染器不会自动做，只能在装配时 baked in。
    全角标点两侧不加空格；emoji 不受影响；`+` 作枚举符时转 `、`（数字前的 +/- 不动）；
    直引号 '...' 包中文时转弯引号 "..."（大陆简体规范）。"""
    if not text:
        return text
    text = re.sub(f'(?<=[{_CJK}])(?=[A-Za-z0-9])', ' ', text)
    text = re.sub(f'(?<=[A-Za-z0-9])(?=[{_CJK}])', ' ', text)
    text = re.sub(f'(?<=[A-Za-z{_CJK}])\\+(?=[A-Za-z{_CJK}])', '、', text)
    text = re.sub(f"'([{_CJK}][^']*?)'", r'"\1"', text)
    return text


def build(data, nar):
    d = data.get('data', {})
    mf = nar.get('manual_fields', {})
    price_date = data.get('_price_date') or d.get('price_date') or TODO
    today = datetime.now().strftime('%Y年%m月%d日')

    us10y = g(d, 'us10y')
    # 估值核心（CAPE 优先用脚本抓取值，无则取人工）
    fpe_n, fpe_s = mf.get('fwd_pe_ndx'), mf.get('fwd_pe_spx')
    cape = g(d, 'cape_spx') if g(d, 'cape_spx') is not None else mf.get('cape_spx')
    buf = mf.get('buffett')
    top_n, top_s = mf.get('top10_qqq'), mf.get('top10_spy')
    ep_n = round(100.0 / fpe_n, 2) if fpe_n else None
    ep_s = round(100.0 / fpe_s, 2) if fpe_s else None
    erp_n = erp(fpe_n, us10y)
    erp_s = erp(fpe_s, us10y)
    ps_n, ps_s = mf.get('ps_ndx'), mf.get('ps_spx')
    hy = mf.get('hy_oas') if mf.get('hy_oas') is not None else None

    # 总灯号
    ln, lnname = light_overall('ndx', erp_n, ps_n, None, top_n, us10y, mf)
    ls, lsname = light_overall('spx', erp_s, ps_s, cape, top_s, us10y, mf)

    # 五维评级（取双核较保守者作为大盘整体口径；估值/趋势分核展示）
    t10y2y = g(d, 't10y2y_bp')
    val_n = rate_valuation(erp_n, ps_n, None, buf, 'ndx', 2.0)
    val_s = rate_valuation(erp_s, ps_s, cape, buf, 'spx', 2.5)
    val = RED if RED in (val_n, val_s) else (YEL if YEL in (val_n, val_s) else GRN)
    macro = rate_macro(us10y, t10y2y, hy)
    tr_n = rate_trend(g(d, 'ndx_dev200'), g(d, 'ndx_ma200_slope'), g(d, 'ndx_days_below_ma200'), g(d, 'ndx_swing_structure'), g(d, 'ndx_divergence'))
    tr_s = rate_trend(g(d, 'spx_dev200'), g(d, 'spx_ma200_slope'), g(d, 'spx_days_below_ma200'), g(d, 'spx_swing_structure'), g(d, 'spx_divergence'))
    trend = RED if RED in (tr_n, tr_s) else (GRN if tr_n == GRN and tr_s == GRN else YEL)
    senti = rate_sentiment(g(d, 'fear_greed'))
    money = rate_money(g(d, 'gex_bn'), g(d, 'dix_pct'))

    # P4-D 计算缺数据保护：关键输入缺失 → 评级标 ⚪（待核实），不给误导性颜色
    if erp_n is None and erp_s is None:
        val = NA
    if us10y is None:
        macro = NA
    if g(d, 'ndx_dev200') is None and g(d, 'spx_dev200') is None:
        trend = NA
    if g(d, 'fear_greed') is None:
        senti = NA
    if g(d, 'gex_bn') is None and g(d, 'dix_pct') is None:
        money = NA
    # 总灯号缺核心估值输入时不臆造
    if erp_n is None and ps_n is None:
        ln, lnname = NA, '数据待核实（估值字段缺失）'
    if erp_s is None and ps_s is None and cape is None:
        ls, lsname = NA, '数据待核实（估值字段缺失）'

    opn, ops = op_tier(ln), op_tier(ls)

    def nf(key, default='（待模型在 narrative.json 填写）'):
        return pangu(nar.get(key) or default)

    # 3秒结论用：把灯号翻译成动作短语
    act3 = {RED: '别买/守住', YEL: '观望/小步', GRN: '可买/加码', NA: '待核实'}

    L = []
    A = L.append
    A(f'# 🇺🇸 美国宽基指数双核巡检报告')
    A(f'**巡检日期：{today}（基于 {price_date} 美股收盘数据 · build_report 确定性装配）**')
    A(f'> ⚡ **本期特别警报：{nf("special_alert")}**\n')
    A('---\n')

    # ⚡ 3秒结论卡（最顶层，小白扫一眼就走）
    A('## ⚡ 3秒结论')
    A('')
    A(f'🟣 **纳斯达克100（QQQ）**： {WEATHER[ln]} → **{act3[ln]}**')
    A(f'{strip_prefix(nf("plain_ndx",""), WEATHER[ln])}')
    A('')
    A(f'🔵 **标普500（SPY）**： {WEATHER[ls]} → **{act3[ls]}**')
    A(f'{strip_prefix(nf("plain_spx",""), WEATHER[ls])}')
    A('')
    A(f'🧾 **体检记分卡**：估值 {val}　宏观 {macro}　趋势 {trend}　情绪 {senti}　资金 {money}　（🟢好 🟡中性 🔴差）')
    A('')
    A('---\n')

    # 今日操作速览
    A('## 🎯 今日操作速览与执行摘要')
    A('')
    A('### 🟣 纳斯达克100')
    A('')
    A(f'- 最新收盘：**{num(g(d,"ndx_close"),"{:,.2f}")}（{pct(g(d,"ndx_chg_pct"))}）**、QQQ **{num(g(d,"qqq_close"))}（{pct(g(d,"qqq_chg_pct"))}）**')
    A(f'- 今日灯号：**{ln} {lnname}**')
    A(f'- 申购/加仓：**{opn["buy"]}**')
    A(f'- 定投：**{"不适用" if nar.get("ndx_no_dca", True) else opn["dca"]}**')
    A(f'- 最重要支撑：QQQ **{num(g(d,"qqq_put_wall"),"{:.0f}")}**（期权护城河）→ 年线 **{num(g(d,"ndx_200dma"),"{:,.0f}")}**')
    A('')
    A('### 🔵 标普500')
    A('')
    A(f'- 最新收盘：**{num(g(d,"spx_close"),"{:,.2f}")}（{pct(g(d,"spx_chg_pct"))}）**、SPY **{num(g(d,"spy_close"))}（{pct(g(d,"spy_chg_pct"))}）**')
    A(f'- 今日灯号：**{ls} {lsname}**')
    A(f'- 申购/加仓：**{ops["buy"]}**')
    A(f'- 定投：**{ops["dca"]}**')
    A(f'- 最重要支撑：SPY **{num(g(d,"spy_put_wall"),"{:.0f}")}**（期权护城河）→ 年线 **{num(g(d,"spx_200dma"),"{:,.0f}")}**')
    A('')
    A(f'> 🚨 **行动指令：{nf("exec_action")}**')
    A(f'> 🎭 **主力暗牌**：{nf("dark_cards")}')
    A(f'> 📅 **本周注意：** {nf("weekly_note")}\n')

    # 🐱 猫姐下周点位（每周六周复盘存 data/cat_levels.json；视频日距报告数据日 9 天内才展示，过期/缺失静默跳过）
    cat = None
    if os.path.exists(CAT_PATH):
        try:
            with open(CAT_PATH, encoding='utf-8') as f:
                cat = json.load(f)
        except Exception:
            cat = None
    if cat:
        try:
            _vd = datetime.strptime(cat.get('video_date', ''), '%Y-%m-%d').date()
            _pd = datetime.strptime(price_date, '%Y-%m-%d').date()
            _fresh = -2 <= (_pd - _vd).days <= 8
        except Exception:
            _fresh = False
        if _fresh:
            _s, _q = cat.get('spy') or {}, cat.get('qqq') or {}
            _parts = []
            if _s.get('defense') is not None:
                _seg = f'SPY 防守线 **{_s["defense"]:.2f}**'
                if _s.get('resistance') is not None:
                    _seg += f'／上方压力约 **{_s["resistance"]:.2f}**'
                _parts.append(_seg)
            if _q.get('defense') is not None:
                _parts.append(f'QQQ 防守线 **{_q["defense"]:.2f}**')
            if _parts:
                _stance = '；'.join(x for x in [cat.get('stance_spy'), cat.get('stance_qqq')] if x)
                _line = (f'> 🐱 **猫姐下周点位**（{cat.get("video_date", "")} 周复盘 · ETF 点位）：'
                         + '；'.join(_parts))
                if _stance:
                    _line += f'。{_stance}'
                A(_line)
                A(f'> 📺 来源：猫姐周复盘 {cat.get("video_url", "")}\n')
    A('---\n')

    # 小白必读
    A('# 📚 小白必读：5分钟看懂今天该不该买\n')

    A('## A. 现在大盘是什么状态？（天气预报）')
    A('')
    A(f'- 🟣 **纳斯达克100**：{WEATHER[ln]}')
    A(f'  - {strip_prefix(nf("plain_ndx"), WEATHER[ln])}')
    A(f'- 🔵 **标普500**：{WEATHER[ls]}')
    A(f'  - {strip_prefix(nf("plain_spx"), WEATHER[ls])}')
    A(f'\n> **总结：** {nf("summary_take")}\n')

    A('## B. 那你该怎么操作？')
    A('')
    hold_n = '拿住别慌，守住护城河' if ln != GRN else '可继续持有'
    hold_s = '拿住别慌，守住护城河' if ls != GRN else '可继续持有'
    A(f'- **已经在定投**：纳指（无定投计划，跳过）／标普{ops["dca"]}')
    A(f'- **想加仓/新买入**：纳指{opn["buy"]}／标普{ops["buy"]}')
    A(f'- **手里已有仓位**：{hold_n if hold_n == hold_s else "纳指" + hold_n + "／标普" + hold_s}')
    A(f'\n> 💡 **大白话理由：** {nf("operation_reason")}\n')

    A('## C. 凭什么这么判断？我们给大盘做了5项体检')
    A('')
    for icon, name, short, job, grade, say in [
        ('💰', '估值', '估值', '贵不贵、划不划算', val, nf('dim_valuation_say', '见下方估值科')),
        ('🌊', '宏观环境', '宏观', '大环境顺不顺风', macro, nf('dim_macro_say', '见下方宏观科')),
        ('📈', '趋势', '趋势', '现在是上坡还是下坡', trend, nf('dim_trend_say', '见下方趋势科')),
        ('😱', '情绪', '情绪', '大家太贪婪还是太恐惧', senti, nf('dim_sentiment_say', '见下方情绪科')),
        ('🐳', '资金筹码', '资金', '大资金在偷偷买还是卖', money, nf('dim_money_say', '见下方资金科'))]:
        A(f'- {icon} **{name}**（{job}）： {grade}')
        A(f'  - {strip_prefix(say, icon + short)}')
    A('\n> **为什么偏看这5个方面？** 它们正好覆盖决定股价的全部力量：估值定长期能赚多少、宏观定资金潮水方向、趋势定是不是好时机、情绪是反向温度计、资金是大钱真实动作。少看任何一个都有盲区。\n')

    # D 指标卡
    A('## D. 看懂背后的每个数字（指标解读卡）')
    A('')

    def card(title, rows):
        A(f'#### {title}')
        A('')
        for name, what, val_s, lvl, imp in rows:
            A(f'**{name}** · {what}')
            A(f'- 当前：{val_s}')
            A(f'- 水平：{lvl}')
            A(f'- 影响：{imp}')
            A('')

    lz, li = lvl_erp(erp_n if erp_n is not None else erp_s)
    card('💰 估值科', [
        ['ERP 股债性价比', '买股票比存国债多赚的部分', f'纳指 {pct(erp_n)} / 标普 {pct(erp_s)}', lz, li],
        ['Forward P/E', '花多少钱买未来1块钱利润', f'纳指 {num(fpe_n)}倍 / 标普 {num(fpe_s)}倍', lvl_pe(fpe_n, 'ndx')[0], lvl_pe(fpe_n, 'ndx')[1]],
        ['CAPE（标普）', '熨平10年的长期市盈率', num(cape), lvl_cape(cape)[0], lvl_cape(cape)[1]],
        ['巴菲特指标', '股市相对整个经济涨过头没', f'{num(buf,"{:.0f}")}%', lvl_buffett(buf)[0], lvl_buffett(buf)[1]],
    ])
    card('🌊 宏观科', [
        ['US10Y 10年美债', '无风险收益、股票的地心引力', f'{num(us10y)}%', lvl_us10y(us10y)[0], lvl_us10y(us10y)[1]],
        ['2s10s 利差', '经济前景晴雨表', f'{num(t10y2y,"{:+.1f}")}bp', lvl_t10y2y(t10y2y)[0], lvl_t10y2y(t10y2y)[1]],
        ['Fed 路径', '接下来放水还是收水', nf('fedwatch_short', mf.get('fedwatch_text', TODO)), '—', '决定未来几个月钱变多还是变少'],
    ])
    card('📈 趋势科', [
        ['年线（200日）', '牛熊分界线', f'纳指 {pct(g(d,"ndx_dev200"))} / 标普 {pct(g(d,"spx_dev200"))}', lvl_dev(g(d, 'ndx_dev200'))[0], lvl_dev(g(d, 'ndx_dev200'))[1]],
        ['距历史高点', '离山顶多远', f'纳指 {pct(g(d,"ndx_drawdown_pct"))} / 标普 {pct(g(d,"spx_drawdown_pct"))}', lvl_dd(g(d, 'ndx_drawdown_pct'))[0], lvl_dd(g(d, 'ndx_drawdown_pct'))[1]],
        ['分型结构', '波段走势形态', SWING_CN.get(g(d, 'ndx_swing_structure'), g(d, 'ndx_swing_structure', TODO)), '见背离提示', g(d, 'ndx_divergence', '无背离')],
        ['RSI', '涨跌过头温度计', f'纳指 {num(g(d,"ndx_rsi"),"{:.0f}")} / 标普 {num(g(d,"spx_rsi"),"{:.0f}")}', lvl_rsi(g(d, 'ndx_rsi'))[0], lvl_rsi(g(d, 'ndx_rsi'))[1]],
    ])
    card('😱 情绪科', [
        ['恐惧贪婪指数', '市场情绪打分（0-100）', num(g(d, 'fear_greed'), '{:.0f}'), lvl_fg(g(d, 'fear_greed'))[0], lvl_fg(g(d, 'fear_greed'))[1]],
        ['VIX 恐慌指数', '预期波动大不大', num(g(d, 'vix')), lvl_vix(g(d, 'vix'))[0], lvl_vix(g(d, 'vix'))[1]],
        ['PCR 期权比', '买保险vs买彩票的人', f'SPY {num(g(d,"spy_pcr_vol"))} / QQQ {num(g(d,"qqq_pcr_vol"))}', lvl_pcr(g(d, 'spy_pcr_vol'))[0], lvl_pcr(g(d, 'spy_pcr_vol'))[1]],
    ])
    card('🐳 资金科', [
        ['DIX 暗池', '机构偷偷买还是卖', f'{num(g(d,"dix_pct"))}%', lvl_dix(g(d, 'dix_pct'))[0], lvl_dix(g(d, 'dix_pct'))[1]],
        ['GEX 减震器', '做市商压波动还是放大波动', f'{num(g(d,"gex_bn"),"{:+.2f}")}B', lvl_gex(g(d, 'gex_bn'))[0], lvl_gex(g(d, 'gex_bn'))[1]],
        ['期权护城河', '下方强支撑价位', f'QQQ {num(g(d,"qqq_put_wall"),"{:.0f}")} / SPY {num(g(d,"spy_put_wall"),"{:.0f}")}', '距现价见防线表', '守住=减震器有效，跌破=变加速器'],
    ])

    A('## E. 这几项打架了，最终听谁的？')
    A('')
    for p in paras(nf("arbitration")):
        A(p)
        A('')

    A('---\n')
    A('## 📂 进阶数据区（仪表盘 / 环比 / 深度解读 —— 小白可跳过）')
    A('')

    # 进阶：双核仪表盘（数字全来自JSON）
    for idx, name, fpe, ep, erpv, ps, cape_v, top, light, lname in [
        ('ndx', '纳斯达克100（NDX）', fpe_n, ep_n, erp_n, ps_n, None, top_n, ln, lnname),
        ('spx', '标普500（SPX）', fpe_s, ep_s, erp_s, ps_s, cape, top_s, ls, lsname)]:
        etf = 'QQQ' if idx == 'ndx' else 'SPY'
        A(f'## 📊 {name} — 仪表盘')
        A(row('指标', '当前值', '状态'))
        A(row('---', '---', '---'))
        A(row(f'{name.split("（")[0]}/{etf} 收盘',
              f'**{num(g(d, idx+"_close"),"{:,.2f}")}（{pct(g(d, idx+"_chg_pct"))}）** / **{num(g(d, etf.lower()+"_close"))}（{pct(g(d, etf.lower()+"_chg_pct"))}）**', light))
        A(row('Forward P/E', f'**{num(fpe)}x**', f'E/P ≈ {num(ep)}%'))
        A(row('US10Y', f'**{num(us10y)}%**', lvl_us10y(us10y)[0]))
        A(row('**ERP（核心）**', f'**{num(ep)}% − {num(us10y)}% = {pct(erpv)}**', lvl_erp(erpv)[0]))
        if idx == 'spx':
            A(row('CAPE 席勒市盈率', f'**{num(cape_v)}**', lvl_cape(cape_v)[0]))
        A(row('P/S 市销率', f'**{num(ps)}x**', '红线 >{}x'.format(5.0 if idx == 'ndx' else 3.0)))
        A(row(f'{etf} Top10集中度', f'**{num(top)}%**', '红线 >{}%'.format(50 if idx == 'ndx' else 30)))
        A(row('RSI(14)', f'**{num(g(d, idx+"_rsi"), "{:.0f}")}**', lvl_rsi(g(d, idx+'_rsi'))[0]))
        A(row('50日均线 / 年线', f'**{num(g(d, idx+"_50dma"),"{:,.0f}")}** / **{num(g(d, idx+"_200dma"),"{:,.0f}")}**',
              f'年线偏离 {pct(g(d, idx+"_dev200"))}'))
        A(row('期权 Put/Call Wall', f'**{num(g(d, etf.lower()+"_put_wall"),"{:.0f}")}** / **{num(g(d, etf.lower()+"_call_wall"),"{:.0f}")}**',
              f'净GEX {num(g(d, etf.lower()+"_net_gex_bn"),"{:+.2f}")}B / 净DEX {num(g(d, etf.lower()+"_net_dex_bn"),"{:+.2f}")}B'))
        A('')

    # 环比表
    A('## 📌 核心变量环比（同 history/indicators.csv）')
    A(row('变量', '本期值'))
    A(row('---', '---'))
    A(row('NDX / SPX 收盘', f'**{num(g(d,"ndx_close"),"{:,.0f}")}** / **{num(g(d,"spx_close"),"{:,.0f}")}**'))
    A(row('US10Y / US2Y', f'**{num(us10y)}%** / **{num(g(d,"us2y"))}%**'))
    A(row('VIX / VXN', f'**{num(g(d,"vix"))}** / **{num(g(d,"vxn"))}**'))
    A(row('ERP（NDX/SPX）', f'**{pct(erp_n)}** / **{pct(erp_s)}**'))
    A(row('DIX / GEX', f'**{num(g(d,"dix_pct"))}%** / **{num(g(d,"gex_bn"),"{:+.2f}")}B**'))
    A('')

    # 深度解读（人民日报式：小标题分节 + 短段落，手机阅读节奏）
    A('## 📖 本期行情大白话深度解读')
    A('')
    A(f'**{nf("thesis_title")}**')
    A('')
    for i, (sub, key) in enumerate(
            [('估值陷阱', 'thesis_valuation'),
             ('流动性与做市商', 'thesis_liquidity'),
             ('给你的忠告', 'thesis_advice')], 1):
        A(f'### {i}. {sub}')
        A('')
        for p in paras(nf(key)):
            A(p)
            A('')

    # 📋 数据来源附录（P4-C：每个数字有据可查）
    src_ov = data.get('_src_override', {})

    def src_of(field, cat):
        if field in src_ov:
            return src_ov[field]
        return SOURCE_MAP.get(cat, ('—', ''))[0]

    def url_of(field, cat):
        if field in src_ov:
            return ''
        return SOURCE_MAP.get(cat, ('', ''))[1]

    A('## 📋 数据来源附录（每个数字有据可查）')
    A('')
    appendix = [
        ('指数收盘 NDX/SPX', f'{num(g(d,"ndx_close"),"{:,.0f}")} / {num(g(d,"spx_close"),"{:,.0f}")}', 'ndx_close', 'price', price_date),
        ('ETF收盘 QQQ/SPY', f'{num(g(d,"qqq_close"))} / {num(g(d,"spy_close"))}', 'qqq_close', 'price', price_date),
        ('年线 200日MA', f'{num(g(d,"ndx_200dma"),"{:,.0f}")} / {num(g(d,"spx_200dma"),"{:,.0f}")}', 'ndx_200dma', 'ma', price_date),
        ('US10Y / US2Y', f'{num(us10y)}% / {num(g(d,"us2y"))}%', 'us2y', 'us2y', price_date),
        ('CAPE 席勒市盈率', num(cape), 'cape_spx', 'cape', price_date),
        ('Forward P/E (NDX/SPX)', f'{num(fpe_n)} / {num(fpe_s)}', 'fwd_pe_ndx', 'manual', '人工核实'),
        ('巴菲特指标', f'{num(buf,"{:.0f}")}%', 'buffett', 'manual', '人工核实'),
        ('Top10 (QQQ/SPY)', f'{num(top_n)}% / {num(top_s)}%', 'top10_qqq', 'manual', '人工核实'),
        ('恐惧贪婪指数', num(g(d, 'fear_greed'), '{:.0f}'), 'fear_greed', 'fear_greed', price_date),
        ('VIX', num(g(d, 'vix')), 'vix', 'price', price_date),
        ('DIX / GEX', f'{num(g(d,"dix_pct"))}% / {num(g(d,"gex_bn"),"{:+.2f}")}B', 'dix_pct', 'dix_gex', g(d, 'dix_date', price_date)),
        ('期权墙 QQQ/SPY', f'P{num(g(d,"qqq_put_wall"),"{:.0f}")} / P{num(g(d,"spy_put_wall"),"{:.0f}")}', 'qqq_put_wall', 'walls', price_date),
        ('主力资金流', f'SPY {num(g(d,"spy_main_flow"),"{:,.0f}")}', 'spy_main_flow', 'fund_flow', price_date),
    ]
    for label, val_s, fld, cat, asof in appendix:
        s = src_of(fld, cat)
        u = url_of(fld, cat)
        A(f'- **{label}**：{val_s} · {s} · {(u or "—")} · {(asof or "—")}')
    A('')

    # 数据可信度水印 + P4-B 降级标注
    A('---')
    fresh = data.get('_freshness', '?')
    miss = data.get('_core_missing', [])
    manual_missing = [k for k in ('fwd_pe_ndx', 'fwd_pe_spx') if not mf.get(k)]
    # 海外专属数据若缺失，多为网络/墙导致的降级（这些项无国内等价源）
    overseas = {'dix_pct': '暗池DIX', 'gex_bn': 'GEX', 'fear_greed': '恐惧贪婪指数',
                'cape_spx': 'CAPE', 'spy_pcr_vol': 'PCR', 'qqq_net_gex_bn': 'QQQ期权GEX'}
    degraded = [name for f, name in overseas.items() if g(d, f) is None]
    using_cn = bool(src_ov)
    A(f'> 🔎 **数据可信度**：行情基准日 {price_date}，新鲜度 {fresh}。'
      + ('核心字段齐全。' if not miss else f'⚠️核心缺失：{miss}。')
      + (f' 🇨🇳已启用国内兜底源（{list(set(src_ov.values()))}）。' if using_cn else '')
      + ('' if not manual_missing else f' ⚠️人工字段未填：{manual_missing}（显示为{TODO}）。'))
    if degraded:
        A(f'> ⚠️ **本期网络降级**：以下海外专属数据未取到（无国内等价源），已按缺失处理、未参与计算：{"、".join(degraded)}。')
    A('> ⚠️ **免责声明**：本报告由量化系统自动装配，数字由代码从快照注入（非模型手填），来源见上方附录，仅为个人投资流程工具，不构成投资建议。')
    A(f'\n*📌 装配时间：{datetime.now().strftime("%Y-%m-%d %H:%M")} | build_report.py 确定性装配*')
    return '\n'.join(L)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--no-narrative', action='store_true')
    args = ap.parse_args()

    if not os.path.exists(REPORT_DATA_PATH):
        print(f'⛔ 缺少 {REPORT_DATA_PATH}，请先运行 run_inspection.py')
        raise SystemExit(2)
    with open(REPORT_DATA_PATH, encoding='utf-8') as f:
        data = json.load(f)

    nar = {}
    if not args.no_narrative and os.path.exists(NARRATIVE_PATH):
        with open(NARRATIVE_PATH, encoding='utf-8') as f:
            nar = json.load(f)
    elif not args.no_narrative:
        print(f'⚠️ 未找到 {NARRATIVE_PATH}，将用占位文字生成（数字仍真实）。')

    md = build(data, nar)
    os.makedirs(OUT_DIR, exist_ok=True)
    pd = data.get('_price_date') or datetime.now().strftime('%Y-%m-%d')
    out = os.path.join(OUT_DIR, f'{pd}_美国宽基指数巡检报告.md')
    with open(out, 'w', encoding='utf-8') as f:
        f.write(md)
    print(f'✅ 报告已装配: {out}')
    if data.get('_core_missing'):
        print(f'⚠️ 注意核心字段缺失: {data["_core_missing"]}')


if __name__ == '__main__':
    main()
