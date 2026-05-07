# quant

一个面向 A 股日频行情的量化研究小项目，用于完成数据选型、字段设计、缓存、收益风险矩阵、分布检验和结论写作。

## 项目结构

- `configs/`: 数据范围、股票池、指数池和通用路径配置。
- `src/data/`: 行情下载、字段标准化、清洗和本地存储。
- `src/analysis/`: 收益率、年化指标、协方差、相关矩阵、统计检验和绘图函数。
- `scripts/`: 可直接运行的流程脚本。
- `reports/`: 研究结论文档。
- `data/`: 本地行情数据目录，包含 `raw`、`processed`、`cache`。
- `results/`: 表格和图片输出目录。

## 三周任务对应关系

### 第 1 周：数据选型、字段设计与本地缓存

配置入口：`configs/data.yaml`

运行：

```bash
python scripts/update_data.py
```

输出：

- `data/cache/`: 按股票、指数、日期区间和复权方式缓存原始下载结果。
- `data/raw/`: 原始标准化数据。
- `data/processed/`: 清洗后的股票和指数数据。

### 第 2 周：收益率、年化波动率、协方差矩阵与相关矩阵

运行：

```bash
python scripts/run_data_check.py
python scripts/run_matrix_analysis.py
```

输出：

- `results/tables/stock_risk_summary.csv`
- `results/tables/index_risk_summary.csv`
- `results/tables/return_matrix.csv`
- `results/tables/cov_matrix.csv`
- `results/tables/corr_matrix.csv`
- `results/figures/corr_heatmap.png`

### 第 3 周：3σ 异常值、t 检验、QQ 图/密度图与结论写作

运行：

```bash
python scripts/run_statistical_analysis.py
```

输出：

- `results/tables/distribution_test_summary.csv`
- `results/tables/three_sigma_outliers.csv`
- `results/figures/*_return_density.png`
- `results/figures/*_qq_plot.png`
- `reports/02_distribution_tests.md`

## 环境检查

```bash
python scripts/health_check.py
```

## 项目乙：因子研究与横截面回测

配置入口：`configs/factor.yaml`

前置条件：`data/processed/stocks_all.parquet` 至少包含多个股票的日线数据。项目甲默认样本只有 1 只股票，做横截面因子研究前需要先在 `configs/data.yaml` 增加股票池并运行：

```bash
python scripts/update_data.py
```

运行因子研究：

```bash
python scripts/run_factor_research.py
```

当前最小因子集：

- `momentum_{window}d`: N 日动量，窗口见 `configs/factor.yaml`。
- `low_volatility_{window}d`: N 日低波动因子，波动率取负后作为得分。
- `turnover_{window}d`: N 日平均换手率。
- `value_factor`: 优先使用 `data/processed/valuation.parquet` 中的 PB/PE/PS/股息率；若没有基本面表，则退化为 `value_proxy_{window}d`。

可选估值表字段：

- 必需：`date`, `symbol`
- 至少一个：`pb`, `pe`, `ps`, `dividend_yield`

可选股票池元数据：

- `data/processed/security_master.parquet`: `symbol`, `list_date`, `is_st`, `industry`, `float_market_cap`
- `data/processed/trade_status.parquet`: `date`, `symbol`, `is_suspended`, `is_limit_up`, `is_limit_down`
- 缺失元数据时默认按 `missing_metadata_policy: permissive` 降级运行，并在 `universe_filter_audit.csv` 与报告中标注。

标签与回测口径：

- 默认标签为 `next_open_to_horizon_open`: t 日收盘后生成因子，t+1 开盘买入，未来第 N 个交易日后开盘卖出。
- IC 汇总默认使用非重叠样本做 t 检验，完整逐日 IC 仍保存在明细表。
- long-short 是研究组合假设，long leg 与 short leg 分别计算换手并按 gross turnover 扣成本。
- 价值因子只使用真实估值表；估值表不可用时跳过 `value_factor`，不再用均线偏离代理冒充基本面。

输出：

- `results/tables/factor_dataset.parquet`
- `results/tables/universe_filter_audit.csv`
- `results/tables/factor_ic_timeseries.csv`
- `results/tables/factor_ic_summary.csv`
- `results/tables/factor_layer_returns.csv`
- `results/tables/factor_long_short_returns.csv`
- `results/tables/factor_long_only_returns.csv`
- `results/tables/factor_turnover.csv`
- `results/tables/factor_cost_sensitivity.csv`
- `results/figures/factor_ic_summary.png`
- `results/figures/*_layered_cumulative_return.png`
- `reports/03_factor_research.md`
