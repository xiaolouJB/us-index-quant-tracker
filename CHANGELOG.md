# 版本变更记录（CHANGELOG）

> 每个版本在 `_versions/` 下有对应 zip 快照（仅打包 SKILL.md / references / scripts / viewer 等逻辑文件，不含每日报告与数据）。
> **回退方法**：解压对应 `_versions/vX.Y.Z_*.zip`，覆盖当前同名文件即可。

---

## v1.4.0 — 猫姐点位 + 核心看点分享卡（2026-10-11）
**目标：把外部专家点位与社交分享卡纳入确定性管线。展示层扩展，灯号判定口径零改动。**
- 新增 `data/cat_levels.json`：XTrader猫姐美股（@catstocktrading）每周六周复盘的 SPY/QQQ 下周关键点位（防守线/压力位/她的判断/来源视频）。铁律：均为 **ETF 点位、不是 SPX/NDX 指数点位**；该频道视频无字幕轨，点位取自画面内嵌字幕与图表标注，读图价轴的数字须注明精度较低；拿不到不许编造。
- `scripts/build_report.py`：【今日操作速览】新增「🐱 猫姐下周点位」区块——cat_levels.json 存在且视频日与报告数据日相差 −2~+8 天时自动渲染，过期或缺失静默跳过。首期（2026-10-10 视频）：SPY 防守线 770.43／上方压力约 779.75，QQQ 防守线 748.65，双核偏多守线；与本系统 SPY Put Wall 770 几乎重合。
- 新增 `scripts/build_card.py`：每日核心看点 3:4 分享卡（1080×1440，PIL 逐像素精排——不用 AI 生图、本机 Chromium headless 已坏也不走它），与报告同源取数并复用 build_report 的灯号/ERP 函数，五项体检灯号同口径实时计算、禁止写死；输出 `分析报告卡片/<数据日>_核心看点_3x4.png`，涨跌按红涨绿跌。
- 仓库整理：新增 `.gitignore`（`.venv/`、`__pycache__/`、`*.pyc`），`scripts/__pycache__` 退出版本跟踪；归档 2026-09-28~10-09 各期巡检报告。

## v1.3.1 — K线日期逐品种校验（2026-10-02）
**目标：根治 10-02 早盘事故——Yahoo 最后一根 K 线未结算时静默沿用前一日旧价（QQQ/SPY 错发旧收盘）。**
- `scripts/fetch_all.py` 新增 `expected_trading_day()`：按美东(ET)口径推导目标交易日（北京时间 9:30 运行=美东前一日收盘后；周末向前滚到周五；美股节假日由 cron/人工判休市，不维护节假日表）。
- `section_prices()` 逐品种校验最后一根 K 线日期：错位品种价格记 `None`（绝不静默用旧价），快照记 `_stale_symbols`+`_expected_trading_day`；`price_date` 改为校验通过的 `^GSPC` K 线日期（恒等于目标交易日）。
- `scripts/sanity_check.py` 新增错位门禁：错位且未被兜底源补齐 → ⛔阻断出报告；已被腾讯财经兜底补齐 → ⚠️提醒人工复核。
- 下游行为不变：`None` 价格在报告中自动渲染为 `⚠️待核实`；核心字段缺失照常触发腾讯财经兜底，兜底失败则 `run_inspection.py` 以退出码 2 拒绝出报告。

## v1.3.0 — 中文排版三合一（2026-09-30）
**目标：融合 Linear / Stripe / Robinhood 的排版优点，按中文移动端排版规范落地。纯展示层改动，数字、评级、灯号、字段零删减。**
- build_report.py 新增 `pangu()`：全部 narrative 文案自动补"盘古之白鹭"空格（中文与字母/数字间半角空格，如"纳指 100 远期市盈率 21.65 倍"）；`+` 作枚举符转 `、`（数字前的 +/- 不动）；直引号包中文转弯引号（"玩火"）。
- 中文语境括号统一为全角（）：操作速览、仪表盘、环比表里的 `(...)` → `（...）`。
- Robinhood 式数字层级：操作速览、仪表盘、环比表改为数值加粗（小标签+大数字）；解读卡/操作建议保持标签加粗、长句不加粗（Apple 式克制）。
- `references/report_template.md` 规则3追加中文排版规范；写 narrative 时无需手动加空格，由装配器统一处理。

## v1.2.0 — 报告移动端排版重构（2026-09-30）
**目标：手机端/文件面板阅读体验。纯展示层改动，数字、评级、灯号、字段零删减。**
- 删除 GitHub 风格 `<details>/<summary>` 折叠块（手机端不渲染 HTML，会原样显示标签字符）；进阶数据区改为普通二级标题直接展示。
- 删除 `# ═══` 超宽装饰标题，改普通标题+分隔线。
- 含长文本句子的宽表全部改为结构化列表：3秒结论、今日操作速览（双核分卡）、A天气预报、B操作建议、C五项体检、D指标解读卡（每指标"当前/水平/影响"三行）、数据来源附录。
- 纯数字窄表保留 Markdown 表格：双核仪表盘、核心变量环比。
- build_report.py 新增 `strip_prefix`：自动去掉 narrative 文案行首与列表标题重复的"emoji+短标签："前缀（如 `⛈️暴雨预警：`、`💰估值：`）。
- 新增 `paras`：深度解读与维度仲裁的长文案按句号自动切成短段落（每2句一段），小标题分节，人民日报式编辑节奏；模板骨架同步。
- `references/report_template.md` 规则3与相关骨架同步为列表式排版规范；SKILL.md 口径行同步。

## v1.0.0 — 基线（2026-06-26）
进化重构前的存档基线。此版本已包含：
- 双核路由 + 灯号系统 + 模块 A–R / L-M-N / Q
- 数据脚本：fetch_all / fetch_fred / fetch_technicals / fetch_options_walls / fetch_dark_pool / fetch_sentiment / fetch_fund_flow / sanity_check / clear_snapshot
- 报告模板：今日操作速览 + 📚小白必读(五维体检) + 进阶数据区 + 大白话深度解读
- 教学层 references/beginner_layer.md
- 已知待改进项：数字靠模型手抄（跨模型易错）、indicators.csv 有重复行、第4节灯号含金额、部分估值字段靠人工 WebSearch。

## v1.1.0 — 数据确定性重构（2026-06-26 ✅已完成）
**目标达成：换任何模型，报告里的数字/评级/灯号/天气/操作档位完全一致，根治跨模型数据错乱。**
- 新增 `scripts/run_inspection.py`：一条命令跑完整条管线（清空→8个fetcher→体检），输出唯一权威数据源 `data/report_data.json`，每字段带状态(OK/MISSING/STALE)，核心缺失以退出码2阻断。
- 新增 `scripts/build_report.py`：**确定性装配器**。数字从 report_data.json 代码注入；指标"水平/影响"、5维评级、总灯号、天气、操作档位全部规则引擎自动算；模型只写 `data/narrative.json` 的人工字段+文字。报告自带"数据可信度水印"，缺失字段显示 `⚠️待核实`。
- 新增 `references/narrative_schema.md`：模型唯一需手写文件的填写指南。
- fetch_all.py 增加当日涨跌幅入快照（ndx/spx/qqq/spy_chg_pct），价格行不再靠模型手算。
- SKILL.md 流程改为极简3步：run_inspection → 写 narrative.json → build_report。
- run_pipeline.bat 升级为调用 run_inspection.py。
- 注：viewer/ 已由用户移除，报告改为直接阅读 Markdown。

新工作流：
```
python scripts/run_inspection.py        # 1. 一键取数+体检
# 2. 模型按 narrative_schema.md 写 data/narrative.json（WebSearch人工字段+文字判断）
python scripts/build_report.py          # 3. 确定性装配报告
```

## v1.3.0 — 国内可用性 + 数据全溯源（2026-06-26 ✅已完成）
**解决"墙"风险 + "每个数字有据可查" + "计算前确保数据准确"。**
- 新增 `scripts/cn_source.py`：腾讯财经国内源（us.NDX/us.INX/usQQQ/usSPY/us.VIX 报价 + 指数日K线），数据与 Yahoo 一致、更快、国内可达。
- 新增 `scripts/fetch_prices_cn.py`：国内价格兜底层，填核心价格/涨跌幅/VIX/指数均线，打 `_src` 来源标记。
- `run_inspection.py`：检测到 Yahoo 核心价格缺失（疑似被墙）时**自动切换国内兜底源**。
- **P4-B 降级标注**：海外专属数据（DIX/GEX、CNN F&G、CAPE，无国内等价源）缺失时，报告显著提示"本期网络降级缺失X项"，绝不静默/编造。
- **P4-C 全溯源**：报告新增【📋 数据来源附录】，每个关键数字标注 来源+URL+数据时间；兜底命中时显示"腾讯财经"。
- **P4-D 计算保护**：参与计算(ERP/5维/灯号)的字段缺失→评级标 ⚪(待核实)、操作降为"观望"，绝不用脏数据算。
- `data_sources.md` 增"国内可用性与墙风险"对照表。
- 新增 `README.md`：中英双语（默认中文）、产品运营视角，一眼看懂核心价值与使用场景。

## v1.2.0 — 完整性修复 + 提速 + 可读性升级（2026-06-26 ✅已完成）
> P2 与 P3 一并实现，合为一个版本。

**数据完整性（P2）**
- `indicators.csv` 去重+排序：清掉历史重复行（19→12行）；`sanity_check.py` 落库改为"按日期 upsert + 整表排序重写"，杜绝重复/乱序复发。
- SKILL.md 第4节灯号**去金额、改档位话术**（火力全开/小额脉冲/全面暂停 等），金额只留第1节参数矩阵，杜绝私人金额泄露进报告。
- 新增 `scripts/fetch_valuation.py`：CAPE（multpl.com）脚本化抓取，减少人工字段（CAPE 从"人工"降为"脚本可选"）。

**提速（P2）**
- `run_inspection.py` 顺序执行（曾试并行，因 Yahoo 限流导致字段缺失，回退到可靠优先的顺序版）。
- `fetch_fred.py` 快速失败：首探超时 (4,7)s + `_FRED_DOWN` 短路，FRED 不可达时该步从 ~30s 降到 ~8s。
- 最大提速来自 v1.1 的"一条命令替代11步手动操作"（agent 工作流层面）。

**可读性（P3）**
- 报告新增 **⚡3秒结论卡**（置顶）：每个指数一行"天气→动作→大白话"，外加一行 **五维体检 emoji 记分卡**。
- **进阶数据区用 `<details>` 折叠**，默认收起，小白只看小白层。
- 注：viewer 已被用户移除，可视化仪表盘改为 Markdown 内的 emoji 记分卡（无需额外渲染依赖）。
