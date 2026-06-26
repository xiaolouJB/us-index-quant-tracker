# 核心指标可信数据源与字段映射

## 1. 字段 → 获取方式映射表

| 字段 | 获取方式 | 脚本/渠道 |
|------|---------|-----------|
| 指数/ETF 价格、涨跌幅 | **脚本（严禁网页搜索价格）** | `scripts/fetch_all.py`（yfinance） |
| 200/50日均线、斜率、偏离度 | 脚本 | `scripts/fetch_all.py` |
| USD/CNY 及 30/90日变动 | 脚本 | `scripts/fetch_all.py` |
| NDX/SPX 比价、SOX、VUG/VTV、DXY、铜金比 | 脚本 | `scripts/fetch_all.py` |
| 牛市年龄 | 脚本 | `scripts/fetch_all.py`（起点 2022-10-12） |
| US2Y、2s10s 利差 | 脚本 | `scripts/fetch_fred.py`（FRED DGS2 / T10Y2Y） |
| HY 信用利差 | 脚本 | `scripts/fetch_fred.py`（FRED BAMLH0A0HYM2） |
| M2 同比 | 脚本 | `scripts/fetch_fred.py`（FRED M2SL） |
| 居民股票配置比例 | 脚本（季度数据） | `scripts/fetch_fred.py`（FRED BOGZ1FL153064486Q） |
| 巴菲特指标 | 脚本近似 + 人工核实 | `scripts/fetch_fred.py`；以 currentmarketvaluation.com 为准 |
| RSI/MACD/回撤/ATR/周线/分型结构 | 脚本 | `scripts/fetch_technicals.py` |
| Call/Put Wall、净GEX、Gamma翻转位 | 脚本 | `scripts/fetch_options_walls.py` |
| DIX / GEX（SqueezeMetrics） | 脚本 | `scripts/fetch_dark_pool.py` |
| CNN 恐惧贪婪指数、SPY/QQQ PCR | 脚本 | `scripts/fetch_sentiment.py` |
| Forward P/E、P/S、CAPE | **人工 WebSearch** | 标普/纳斯达克官方 Factsheet、FactSet、multpl.com（CAPE）、gurufocus |
| Top10 集中度 | 人工 WebSearch | QQQ / SPY ETF 官方持仓披露 |
| 盈利修正比、Beat Rate | 人工 WebSearch | FactSet Earnings Insight 周报 / Refinitiv I/B/E/S |
| CME FedWatch 概率 | 人工 WebSearch | CME FedWatch Tool |
| 成分股站上200日线比例（宽度） | 人工 WebSearch | macromicro.me / streetstats.finance / StockCharts |
| FOMC/CPI/非农/财报日历 | 人工 WebSearch | 美联储官网、BLS、各公司 IR 日历 |

## 2. 权威渠道清单

- **宏观底座（US10Y/US2Y/利差）**：FRED / 美国财政部。
- **长周期流动性（居民配置）**：FRED Z.1 表（`BOGZ1FL153064486Q`）。
- **估值核心（PE、P/S、CAPE）**：标普/纳斯达克官方 Factsheet / FactSet / 彭博 / multpl.com。
- **微观情绪（PCR、VIX、VXN）**：CBOE；PCR 亦可由脚本从期权链直接计算。
- **结构极值（Top10）**：QQQ / SPY ETF 持仓披露。
- **暗池（DIX/GEX）**：SqueezeMetrics `https://squeezemetrics.com/monitor/static/DIX.csv`（脚本自动获取）。
- **巴菲特指标**：⚠️ FRED `WILL5000IND` 已于 2023年底停更，**禁止引用**。脚本用 Yahoo `^W5000` 点位 / FRED 名义 GDP 近似（1点≈$10亿市值），并必须与 `currentmarketvaluation.com` 或 `longtermtrends.net/market-cap-gdp` 人工交叉核验。
- **季度模块**：L → finra.org Margin Statistics / yardeni.com；M → Barchart / StockCharts `$USHL`；N → FRED `M2SL` / CrossBorder Capital。
- **牛市年龄**：NBER 商业周期 / 彭博历史牛熊统计；本轮起点锚定 2022年10月12日。

## 2.5 国内可用性与"墙"风险（重要）

国内裸网（无代理）时多数海外源不稳定/被墙。各源风险与备选：

| 数据源 | 用途 | 国内无代理风险 | 备选方案 |
|--------|------|--------------|---------|
| Yahoo (yfinance) | 价格/均线/技术/PCR/期权 | 🔴 高（常超时） | ✅ `cn_source.py` 腾讯财经（已验证：us.NDX/us.INX/usQQQ/usSPY/us.VIX，数据与 Yahoo 一致） |
| FRED | 利率/M2/居民配置 | 🔴 已不可达 | Yahoo 2YY=F 备源 + 本地缓存（见 §3） |
| SqueezeMetrics | DIX/GEX 暗池 | 🔴 高 | ❌ 无国内等价源 → 缺失即降级标注 |
| CNN Fear&Greed | 情绪 | 🔴 高（CNN被墙） | ❌ 无理想国内源 → 降级；可人工 |
| multpl | CAPE | 🟠 中 | ❌ → 人工核实 |
| 东方财富 | 资金流 | 🟢 无（国内源） | — |

**腾讯财经接口（cn_source.py，国内兜底核心）**：
- 实时报价：`https://qt.gtimg.cn/q=<code>`（code：`us.NDX` 纳指100 / `us.INX` 标普500 / `usQQQ` / `usSPY` / `us.VIX`）。涨跌幅 = (现价−昨收)/昨收 自算。
- 指数日K线（算均线/RSI）：`https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param=<code>,day,,,300,qfq`（指数有完整历史；ETF的K线稀疏，故均线一律用指数算）。
- `run_inspection.py` 在 Yahoo 核心价格缺失时自动调用；命中后字段在快照打 `_src` 来源标记，并在报告【数据来源附录】注明"腾讯财经"。

## 3. FRED 免 Key 接口说明

脚本使用 `https://fred.stlouisfed.org/graph/fredgraph.csv?id=<SERIES_ID>` 直接下载 CSV，无需 API Key。若接口失效，备用方案：`https://api.stlouisfed.org/fred/series/observations`（需注册免费 Key，存入环境变量 `FRED_API_KEY`）。

## 4. 防错铁律

1. **指数与 ETF 精确点位及涨幅严禁依赖网页搜索**，必须通过 yfinance 脚本获取，避免搜索引擎日期混淆。
2. 期权 Wall 仅在现价 ±15% 内搜索；任何"关键位"距现价 > 20% 必须红色警报二次核验。
3. 人工补充字段必须注明数据日期；引用上一财报季旧数据时必须显式标注。
4. 所有脚本输出统一汇入 `data/latest_snapshot.json`；报告环比一律以 `history/indicators.csv` 为准，不靠记忆。
5. **期权 OI 刷新时点陷阱**：OCC/Yahoo 的持仓量（OI）在美东时间清晨（约5–6点后）才更新前一交易日数据。北京时间**下午及以后**巡检 → OI 已是最新；北京时间**早晨**巡检（=美东前夜）→ 抓到的是再前一日的陈旧 OI，Wall 点位可能已漂移（实例：2026-06-10 SPY Put Wall 早间口径 700，OI 刷新后上移至 720）。报告必须标注 OI 数据时点；关键决策前用 `--expirations 8` 双口径核验，并同时输出 OI 前5名排行（脚本已内置）观察是否存在"双层支撑带"。
