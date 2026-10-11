# -*- coding: utf-8 -*-
"""
build_card.py — 每日核心看点 3:4 社交分享卡
从 data/report_data.json + data/narrative.json 取数（与 build_report.py 同源），
用 PIL 逐像素精排 1080x1440 卡片，保证中文与数字精准清晰。
不用 AI 生图（写中文数字必糊）；本机 Chromium headless 已坏，改走 PIL。

用法：
  python scripts/build_card.py
输出：分析报告卡片/YYYY-MM-DD_核心看点_3x4.png
"""
import json
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE_DIR, 'scripts'))
from build_report import (g, num, erp, light_overall, WEATHER, lvl_fg,  # noqa: E402
    rate_valuation, rate_macro, rate_trend, rate_sentiment, rate_money,
    RED as _R, YEL as _Y, GRN as _G, NA as _N)
from PIL import Image, ImageDraw, ImageFont, ImageFilter  # noqa: E402

W, H = 1080, 1440
FONT_DIR_CJK = '/usr/share/fonts/opentype/noto'
EMOJI_TTF = '/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf'

BG = (7, 11, 20)
T1 = (244, 246, 251)
T2 = (154, 164, 182)
T3 = (92, 102, 120)
RED = (246, 70, 93)
PINK = (255, 107, 126)
PINK_SOFT = (255, 179, 190)
GRN = (14, 203, 129)
YEL = (240, 185, 11)


def cjk(size, bold=False):
    name = 'NotoSansCJK-Bold.ttc' if bold else 'NotoSansCJK-Regular.ttc'
    return ImageFont.truetype(os.path.join(FONT_DIR_CJK, name), size,
                              index=2, layout_engine=ImageFont.Layout.RAQM)


def emoji(size):
    return ImageFont.truetype(EMOJI_TTF, size)


def draw_emoji(img, xy, char, target_h):
    """NotoColorEmoji 是位图字体，只支持 109px strike：先按 109 渲染再缩放到目标高度。"""
    base = 109
    tmp = Image.new('RGBA', (220, 220), (0, 0, 0, 0))
    d = ImageDraw.Draw(tmp)
    d.text((20, 20), char, font=emoji(base), embedded_color=True)
    bbox = tmp.getbbox()
    if not bbox:
        return
    crop = tmp.crop(bbox)
    w0, h0 = crop.size
    w1 = max(1, round(w0 * target_h / h0))
    crop = crop.resize((w1, target_h), Image.LANCZOS)
    img.alpha_composite(crop, (int(xy[0]), int(xy[1])))


def fmt_pct(v):
    if v is None:
        return '待核实'
    return f'{float(v):+.2f}%'.replace('-', '\u2212')


def wrap(text, font, max_w, draw):
    """按字符宽折行（中文按字切即可）"""
    lines, cur = [], ''
    for ch in text:
        if draw.textlength(cur + ch, font=font) <= max_w:
            cur += ch
        else:
            lines.append(cur)
            cur = ch
    if cur:
        lines.append(cur)
    return lines


def glow(base, center, radius, color, alpha):
    layer = Image.new('RGBA', base.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    x, y = center
    d.ellipse([x - radius, y - radius, x + radius, y + radius],
              fill=color + (alpha,))
    layer = layer.filter(ImageFilter.GaussianBlur(radius // 3))
    return Image.alpha_composite(base, layer)


def main():
    with open(os.path.join(BASE_DIR, 'data', 'report_data.json'), encoding='utf-8') as f:
        data = json.load(f)
    nar = {}
    np_ = os.path.join(BASE_DIR, 'data', 'narrative.json')
    if os.path.exists(np_):
        with open(np_, encoding='utf-8') as f:
            nar = json.load(f)
    mf = nar.get('manual_fields', {})
    d = data.get('data', {})
    price_date = data.get('_price_date') or d.get('price_date') or ''
    from datetime import datetime
    today = datetime.now().strftime('%Y年%-m月%-d日')

    us10y = g(d, 'us10y')
    fpe_n, fpe_s = mf.get('fwd_pe_ndx'), mf.get('fwd_pe_spx')
    cape = g(d, 'cape_spx') if g(d, 'cape_spx') is not None else mf.get('cape_spx')
    buf = mf.get('buffett')
    top_n, top_s = mf.get('top10_qqq'), mf.get('top10_spy')
    erp_n, erp_s = erp(fpe_n, us10y), erp(fpe_s, us10y)
    ps_n, ps_s = mf.get('ps_ndx'), mf.get('ps_spx')
    ln, _ = light_overall('ndx', erp_n, ps_n, None, top_n, us10y, mf)
    ls, _ = light_overall('spx', erp_s, ps_s, cape, top_s, us10y, mf)

    # 五维灯号：与 build_report.build() 同口径（取双核较保守者），缺数据 → ⚪
    hy = mf.get('hy_oas') if mf.get('hy_oas') is not None else None
    t10y2y = g(d, 't10y2y_bp')
    val_n = rate_valuation(erp_n, ps_n, None, buf, 'ndx', 2.0)
    val_s = rate_valuation(erp_s, ps_s, cape, buf, 'spx', 2.5)
    val_g = _R if _R in (val_n, val_s) else (_Y if _Y in (val_n, val_s) else _G)
    macro_g = rate_macro(us10y, t10y2y, hy)
    tr_n = rate_trend(g(d, 'ndx_dev200'), g(d, 'ndx_ma200_slope'),
                      g(d, 'ndx_days_below_ma200'), g(d, 'ndx_swing_structure'), g(d, 'ndx_divergence'))
    tr_s = rate_trend(g(d, 'spx_dev200'), g(d, 'spx_ma200_slope'),
                      g(d, 'spx_days_below_ma200'), g(d, 'spx_swing_structure'), g(d, 'spx_divergence'))
    trend_g = _R if _R in (tr_n, tr_s) else (_G if tr_n == _G and tr_s == _G else _Y)
    senti_g = rate_sentiment(g(d, 'fear_greed'))
    money_g = rate_money(g(d, 'gex_bn'), g(d, 'dix_pct'))
    if erp_n is None and erp_s is None:
        val_g = _N
    if us10y is None:
        macro_g = _N
    if g(d, 'ndx_dev200') is None and g(d, 'spx_dev200') is None:
        trend_g = _N
    if g(d, 'fear_greed') is None:
        senti_g = _N
    if g(d, 'gex_bn') is None and g(d, 'dix_pct') is None:
        money_g = _N
    DIM_COLOR = {_R: RED, _Y: YEL, _G: GRN, _N: (154, 164, 182)}
    five_dims = [('估值', val_g), ('宏观', macro_g), ('趋势', trend_g), ('情绪', senti_g), ('资金', money_g)]

    act = {'🔴': '别买 · 守住', '🟡': '观望 · 小步', '🟢': '可买 · 加码', '⚪': '待核实'}
    fg = g(d, 'fear_greed')
    fg_word = lvl_fg(fg)[0] if fg is not None else '待核实'
    takeaway = ('买股票不如存银行：ERP 双双倒挂，估值、利率、事件三重红灯叠满，收伞不动。'
                if ln == '🔴' and ls == '🔴'
                else (nar.get('summary_take') or '按灯号行事，纪律大于预测。').strip())

    img = Image.new('RGBA', (W, H), BG + (255,))
    img = glow(img, (130, -40), 480, RED, 26)
    img = glow(img, (W + 60, H + 80), 520, (64, 110, 255), 24)
    dr = ImageDraw.Draw(img)
    PX = 56
    CW = W - PX * 2

    def composite_layer(draw_fn):
        """半透明图形必须画在独立图层再 alpha_composite——直接画在 RGBA 上会被替换而非混合。"""
        nonlocal img, dr
        layer = Image.new('RGBA', img.size, (0, 0, 0, 0))
        d = ImageDraw.Draw(layer)
        draw_fn(d)
        img = Image.alpha_composite(img, layer)
        dr = ImageDraw.Draw(img)

    def card(x, y, w, h, r, fill, outline, width=1):
        composite_layer(lambda d: d.rounded_rectangle(
            [x, y, x + w, y + h], radius=r, fill=fill, outline=outline, width=width))

    # ── 顶栏 ──
    draw_emoji(img, (PX, 52), '🇺🇸', 44)
    # 用固定 advance 估算旗标宽度（双区域指示符约 1.5 倍行高）
    dr.text((PX + 78, 62), '美国宽基指数 · 每日核心看点', font=cjk(30, True), fill=T1)
    dr.text((PX, 122), f'{today} ｜ 基于 {price_date} 美股收盘', font=cjk(24), fill=T3)

    # ── 双核 verdict ──
    y0, ch, gap = 184, 320, 20
    cw = (CW - gap) // 2
    for i, (name, wx, a) in enumerate(
            [('纳斯达克 100', WEATHER[ln], act.get(ln, '')),
             ('标普 500', WEATHER[ls], act.get(ls, ''))]):
        x = PX + i * (cw + gap)
        wx_text = wx.split(' ', 1)[1] if ' ' in wx else wx  # 天气 emoji 已单独绘制，文字只留中文
        card(x, y0, cw, ch, 30, (246, 70, 93, 20), (246, 70, 93, 80), 2)
        draw_emoji(img, (x + 34, y0 + 22), '⛈️', 92)
        dr.text((x + 34, y0 + 128), name, font=cjk(26), fill=T2)
        dr.text((x + 32, y0 + 160), wx_text, font=cjk(56, True), fill=PINK)
        # 行动 pill
        pt = a
        pf = cjk(25, True)
        tw = dr.textlength(pt, font=pf)
        pw, ph = tw + 64, 54
        px, py = x + 34, y0 + ch - 30 - ph
        composite_layer(lambda d: d.rounded_rectangle(
            [px, py, px + pw, py + ph], radius=ph // 2,
            outline=(246, 70, 93, 130), width=2))
        dr.text((px + (pw - tw) / 2, py + 11), pt, font=pf, fill=PINK_SOFT)

    # ── 指数大数字 ──
    y0, ch = 524, 240
    for i, (name, close, pctv) in enumerate(
            [('纳斯达克 100', num(g(d, 'ndx_close'), '{:,.2f}'), g(d, 'ndx_chg_pct')),
             ('标普 500', num(g(d, 'spx_close'), '{:,.2f}'), g(d, 'spx_chg_pct'))]):
        x = PX + i * (cw + gap)
        card(x, y0, cw, ch, 30, (255, 255, 255, 10), (255, 255, 255, 22))
        dr.text((x + 34, y0 + 28), name, font=cjk(24), fill=T2)
        dr.text((x + 32, y0 + 62), close, font=cjk(64, True), fill=T1)
        pc = RED if (pctv or 0) >= 0 else GRN
        dr.text((x + 34, y0 + 152), fmt_pct(pctv), font=cjk(34, True), fill=pc)

    # ── 六宫格 ──
    y0, gh, gap = 784, 150, 16
    gw = (CW - gap * 2) // 3
    cells = [
        ('10年美债', f'{num(us10y)}%', T1, '股票地心引力'),
        ('ERP · 纳指', fmt_pct(erp_n), RED, '股债性价比倒挂'),
        ('CAPE', num(cape), T1, '泡沫区 > 30'),
        ('巴菲特指标', f'{num(buf, "{:.0f}")}%', T1, '极端泡沫区'),
        ('VIX 恐慌指数', num(g(d, 'vix')), T1, '正常区间'),
        ('恐惧贪婪', num(fg, '{:.0f}'), T1, fg_word),
    ]
    for i, (t, val, color, sub) in enumerate(cells):
        x = PX + (i % 3) * (gw + gap)
        y = y0 + (i // 3) * (gh + gap)
        card(x, y, gw, gh, 24, (255, 255, 255, 8), (255, 255, 255, 18))
        f1, f2, f3 = cjk(22), cjk(42, True), cjk(20)
        tw = dr.textlength(t, font=f1)
        dr.text((x + (gw - tw) / 2, y + 20), t, font=f1, fill=T2)
        vw = dr.textlength(val, font=f2)
        dr.text((x + (gw - vw) / 2, y + 50), val, font=f2, fill=color)
        sw = dr.textlength(sub, font=f3)
        dr.text((x + (gw - sw) / 2, y + 106), sub, font=f3, fill=T3)

    # ── 五项体检 ──
    y0, ch = 1116, 100
    card(PX, y0, CW, ch, 24, (255, 255, 255, 8), (255, 255, 255, 18))
    dr.text((PX + 34, y0 + 32), '五项体检', font=cjk(24), fill=T2)
    items = [(n, DIM_COLOR[gg]) for n, gg in five_dims]  # 灯号来自报告同源计算，禁止写死
    fi = cjk(25)
    total_w = sum(dr.textlength(n, font=fi) + 30 + 26 for n, _ in items) - 26
    ix = PX + CW - 34 - total_w
    iy = y0 + ch // 2
    for n, color in items:
        dr.ellipse([ix, iy - 9, ix + 18, iy + 9], fill=color)
        dr.text((ix + 30, iy - 19), n, font=fi, fill=(198, 205, 219))
        ix += dr.textlength(n, font=fi) + 30 + 26

    # ── 一句话 ──
    y0, ch = 1236, 118
    card(PX, y0, CW, ch, 24, (255, 255, 255, 10), (255, 255, 255, 22))
    dr.rectangle([PX, y0 + 22, PX + 6, y0 + ch - 22], fill=RED)
    fq = cjk(29)
    lines = wrap(takeaway, fq, CW - 110, dr)
    ly = y0 + (ch - len(lines) * 50) / 2 - 4
    for ln_ in lines:
        dr.text((PX + 44, ly), ln_, font=fq, fill=(232, 236, 244))
        ly += 50

    # ── 页脚 ──
    dr.text((PX, H - 62), '美国宽基指数 · 每日巡检', font=cjk(20), fill=T3)
    rf = cjk(20)
    rt = '个人投资流程工具 · 不构成投资建议'
    dr.text((W - PX - dr.textlength(rt, font=rf), H - 62), rt, font=rf, fill=T3)

    out = Image.alpha_composite(Image.new('RGBA', img.size, BG + (255,)), img).convert('RGB')
    os.makedirs(os.path.join(BASE_DIR, '分析报告卡片'), exist_ok=True)
    pd = data.get('_price_date') or datetime.now().strftime('%Y-%m-%d')
    pp = os.path.join(BASE_DIR, '分析报告卡片', f'{pd}_核心看点_3x4.png')
    out.save(pp)
    print(f'✅ 分享卡已生成: {pp} ({out.size[0]}x{out.size[1]})')


if __name__ == '__main__':
    main()
