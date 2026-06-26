# narrative.json 填写指南（模型唯一需要手写的文件）

> 数据确定性重构后，**模型不再手抄任何数字、不再手动拼装报告**。模型只做两件事：
> ① WebSearch 几个脚本拿不到的估值字段；② 写几段纯文字判断。
> 两者都写进 `data/narrative.json`，再由 `build_report.py` 与 `data/report_data.json`（脚本数字）合并成报告。
> **报告里所有数字、5维评级、灯号、天气、操作档位都是代码算的，与模型无关** —— 这是消灭"换模型就数据错乱"的关键。

## 工作流（每次巡检）
1. `python scripts/run_inspection.py` —— 一键跑完管线，生成 `data/report_data.json`（含字段状态体检）。
2. 看体检结论里的"人工字段"清单 → **WebSearch 核实最新值**（严禁凭记忆/旧值）。
3. 读 `references/modules.md` + `references/beginner_layer.md`，对照 `report_data.json` 的真实数字做判断。
4. 写 `data/narrative.json`（见下方 schema）。
5. `python scripts/build_report.py` → 生成 Markdown 报告（可直接阅读）。
6. （可选）`python scripts/sanity_check.py --fwd-pe-ndx <值> --fwd-pe-spx <值> --commit` → 环比校验并落库。

## narrative.json 字段 schema

```jsonc
{
  "manual_fields": {            // ← 必须 WebSearch 核实，禁止编造；拿不到就删掉该键，报告会显示"待核实"
    "fwd_pe_ndx": 24.5,         // 纳指100 远期市盈率（gurufocus / macromicro）
    "fwd_pe_spx": 21.1,         // 标普500 远期市盈率（FactSet Earnings Insight）
    "cape_spx": 39.5,           // 标普 席勒CAPE（multpl.com）
    "top10_qqq": 47.5,          // QQQ 前十大权重%（invesco / slickcharts）
    "top10_spy": 38.4,          // SPY 前十大权重%（slickcharts）
    "buffett": 228,             // 巴菲特指标%（currentmarketvaluation.com）
    "ps_ndx": 6.7,              // 纳指 市销率（可选）
    "ps_spx": 3.5,              // 标普 市销率（可选）
    "hy_oas": 2.8,              // HY信用利差%（FRED 不可达时人工核，gurufocus）
    "fedwatch_text": "..."      // CME FedWatch 一句话路径
  },
  "ndx_no_dca": true,           // 纳指是否无定投计划（true=报告定投栏显示"不适用"）

  // —— 以下全是纯文字判断，写给普通人看，遵守 beginner_layer.md 的写作铁律 ——
  "special_alert": "本期最致命风险或最强信号，一句话，禁空话",
  "exec_action": "一句话强结论行动指令（如：维持观望/越跌越买）",
  "dark_cards": "把 GEX/DEX/DIX 翻译成大白话博弈局势（减震器/炸药包/护城河）",
  "weekly_note": "未来一周最重要1-2个事件+日期，大白话",

  "plain_ndx": "纳指天气一句话状态（≤20字）",
  "plain_spx": "标普天气一句话状态（≤20字）",
  "summary_take": "小白A区总结，2-3句把核心矛盾讲清",
  "operation_reason": "B区操作建议的大白话理由",

  "dim_valuation_say": "估值维度一句话",
  "dim_macro_say": "宏观维度一句话",
  "dim_trend_say": "趋势维度一句话",
  "dim_sentiment_say": "情绪维度一句话",
  "dim_money_say": "资金维度一句话",

  "arbitration": "5维打架时的仲裁说明：最终听谁的、为什么（按beginner_layer.md第三节）",

  "thesis_title": "深度解读的吸睛标题",
  "thesis_valuation": "估值陷阱段（结合ERP/US10Y）",
  "thesis_liquidity": "流动性与做市商段（结合GEX/DIX/DEX/期权墙）",
  "thesis_advice": "忠告与底线纪律段（给防守/进攻底线）"
}
```

## 重要约束
- **manual_fields 必须 WebSearch**：这些是报告里仅存的、脚本拿不到的数字。拿不到宁可不填（显示"待核实"），**绝不能编**。
- **文字判断必须基于 report_data.json 的真实数字**：先看代码算出的真实值，再写判断，禁止脱离数据空谈。
- **评级/灯号/天气不用你写**：build_report.py 会按规则自动算。你的文字只是"解释"这些评级，不要在文字里给出和系统不一致的结论。
- **遵守 beginner_layer.md 写作铁律**：结论先行、称呼用"你"、专业词配比喻、禁止"注意风险"类废话。
