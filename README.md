<div align="center">

# 🇺🇸 美国宽基指数双核巡检 · AI 量化助手
### US Broad-Index Dual-Core Inspector — An AI Quant Copilot

**一句话：每天 1 分钟，用机构级的方法，告诉你纳指100和标普500"现在该不该买"——并且说人话。**

`纳斯达克100` · `标普500` · `估值-宏观-趋势-情绪-资金 五维体检` · `小白也能看懂` · `数据可溯源` · `国内可用`

[中文](#中文) ｜ [English](#english)

</div>

---

<a name="中文"></a>
## 中文（默认）

### 🎯 它解决什么问题？

普通人投美股宽基（纳指100 / 标普500）最大的痛点不是"没数据"，而是：
- **数据看不懂**：市盈率、ERP、暗池、Gamma……一堆黑话，不知道现在算高还是低；
- **不知道该不该动手**：涨了怕追高、跌了怕接飞刀，没有一套纪律；
- **AI 报告不可信**：不同模型、不同时间，数字对不上，甚至凭空编造。

**这个 Skill 把"华尔街级的多因子分析"自动化，并翻译成大白话的操作建议——结论先行、有据可查、换谁来跑数字都一样。**

### 💡 核心价值（一眼看懂）

| 你想要的 | 我们给的 |
|---------|---------|
| 🟢 **一眼知道该不该买** | 报告顶部【⚡3秒结论】：天气预报式图标 + "别买/观望/可买" + 一句话 |
| 🧭 **知道为什么** | 【五维体检记分卡】：估值/宏观/趋势/情绪/资金，每项一个红黄绿灯 |
| 📖 **看懂每个数字** | 每个指标都配"是什么 + 现在算高还是低 + 对你有啥影响"三件套 |
| 🤖 **数字绝对可信** | 数字由代码注入、判断由规则引擎算，**换任何大模型结果一致**，绝不编造 |
| 🔍 **每个数都能查** | 报告附【数据来源附录】：来源 + 链接 + 数据时间，逐项可溯源 |
| 🧱 **国内也能跑** | Yahoo 被墙时自动切换腾讯财经等国内源，核心数据不断供 |

### 👥 适合谁

- **定投 / QDII 场外基金的普通投资者**：想要一个"今天定投正常 / 减半 / 暂停"的明确指令；
- **想入门美股但被术语劝退的小白**：用大白话+体检比喻快速建立认知；
- **有一定基础、想要纪律化的进阶用户**：报告下半部分有完整的专业数据区（期权墙、GEX/DEX、分型结构、巴菲特指标等）。

### 📋 一份报告长什么样

```
⚡ 3秒结论
  纳斯达克100（QQQ）：⛈️ 暴雨预警 → 别买/守住 | 跌出了恐慌，但价格还不够便宜
  体检记分卡：估值🔴 宏观🟡 趋势🟡 情绪🟢 资金🟡

🎯 今日操作速览   —— 收盘价+涨跌幅、灯号、申购/定投档位、关键支撑位
📚 小白必读       —— 现在啥状态 → 怎么操作 → 凭啥判断(五维) → 每个指标解读 → 打架听谁的
📂 进阶数据区(折叠) —— 双核仪表盘 / 环比 / 期权博弈 / 大白话深度解读
📋 数据来源附录   —— 每个数字的来源+链接+时间
```

> 操作建议一律用**档位话术**（火力全开 / 小额脉冲 / 观望 / 全面暂停；定投：加倍 / 正常 / 减半 / 暂停），**不出现任何个人金额**，保护隐私。

### 🚀 三步上手

```bash
# 1) 一键取数 + 自动体检（含国内兜底）
python scripts/run_inspection.py

# 2) AI 按 references/narrative_schema.md 补人工字段(WebSearch) + 写大白话判断
#    → 生成 data/narrative.json

# 3) 确定性装配报告（数字由代码注入）
python scripts/build_report.py
# 报告输出到 分析报告/YYYY-MM-DD_美国宽基指数巡检报告.md
```

整条流程约 **1 分钟**，输出一份 Markdown 报告，直接阅读即可。

### 🛡️ 数据可信度与抗墙设计

- **确定性架构**：所有数字与评级由 Python 脚本/规则引擎产出，AI 只写文字判断 → **跨模型零漂移**。
- **三重门禁**：常识校验（如 Put Wall 不能高于 Call Wall）+ 环比熔断（异常波动暂停）+ 核心字段缺失直接阻断出报告。
- **国内兜底**：Yahoo / FRED / CNN 等海外源被墙时，自动切换腾讯财经（实测数据一致）；无国内等价源的数据（暗池/CAPE 等）则**明确降级标注**，绝不静默或编造。
- **全程溯源**：每个关键数字标注来源、链接、数据时间。

### 🗂️ 目录结构

| 路径 | 作用 |
|------|------|
| `SKILL.md` | 主控：参数矩阵、流程、灯号规则、SLA |
| `scripts/` | 数据管线：`run_inspection`(总指挥) / `build_report`(装配器) / 各 fetcher / `cn_source`(国内源) |
| `references/` | 规则与口径：`modules`(模块A–R) / `beginner_layer`(说人话大脑) / `report_template` / `data_sources` / `narrative_schema` |
| `分析报告/` | 历次巡检报告输出 |
| `history/indicators.csv` | 环比基线（去重+排序） |
| `_versions/` + `CHANGELOG.md` | 版本快照（可一键回退）与变更记录 |

### ⚠️ 免责声明

本工具为**个人投资流程管理与学习用途**，所有输出为量化信号的客观呈现，**不构成任何投资建议**。数据存在延迟与误差可能，实盘操作前请自行核实关键数值，盈亏自负。

---

<a name="english"></a>
## English

### 🎯 What problem does it solve?

For everyday investors in US broad indices (Nasdaq-100 / S&P 500), the real pain isn't a lack of data — it's that **the data is unreadable, the "should I buy?" call is unclear, and AI-generated reports can't be trusted** (numbers drift across models or get hallucinated).

**This Skill automates Wall-Street-grade multi-factor analysis and translates it into plain-language, conclusion-first action calls — fully sourced, and identical no matter which LLM runs it.**

### 💡 Core value

| You want | We deliver |
|----------|-----------|
| 🟢 Instant verdict | A top **"3-Second Verdict"**: weather icon + Buy / Watch / Avoid + one line |
| 🧭 The "why" | A **5-Dimension Scorecard**: Valuation / Macro / Trend / Sentiment / Capital, each a traffic light |
| 📖 Understand every number | Each metric ships with "what it is + is it high/low now + what it means for you" |
| 🤖 Trustworthy numbers | Numbers injected by code, ratings by a rules engine → **model-independent, never fabricated** |
| 🔍 Fully traceable | A **Data-Source Appendix**: source + link + timestamp per metric |
| 🧱 Works in mainland China | Auto-fallback to domestic sources (Tencent) when Yahoo/FRED/CNN are blocked |

### 👥 Who it's for

- **DCA / fund investors** wanting a clear "continue / halve / pause" instruction;
- **Beginners** put off by jargon — learn via plain language and a "health check-up" metaphor;
- **Advanced users** wanting discipline — a full pro data section (option walls, GEX/DEX, swing structure, Buffett indicator) sits below.

### 🚀 Quick start

```bash
python scripts/run_inspection.py     # 1) fetch + auto health-check (with domestic fallback)
# 2) AI fills manual fields (WebSearch) + plain-language calls → data/narrative.json
python scripts/build_report.py       # 3) deterministic report assembly
# → 分析报告/YYYY-MM-DD_*.md
```

About **1 minute** end-to-end; outputs a ready-to-read Markdown report.

### 🛡️ Reliability & censorship resilience

- **Deterministic core**: numbers & ratings from code, not the model → zero cross-model drift.
- **Triple gate**: sanity checks + day-over-day circuit breakers + hard block on missing core fields.
- **Domestic fallback**: switches to Tencent Finance when overseas sources are blocked; overseas-only data (dark pool / CAPE) is explicitly marked as degraded, never silently faked.
- **Full provenance**: source, link, and timestamp for every key number.

### ⚠️ Disclaimer

This tool is for **personal investment-workflow management and educational use only**. All output is an objective presentation of quantitative signals and **does not constitute investment advice**. Verify critical figures before any real trade; you bear all risk.

---

<div align="center">

*🤖 由 AI 量化巡检系统驱动 · Powered by an AI quant-inspection pipeline*
*版本管理见 [CHANGELOG.md](CHANGELOG.md) ｜ 当前 v1.3.0*

</div>
