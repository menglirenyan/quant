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
