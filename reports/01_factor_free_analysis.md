# A 股收益与风险基础分析

## 数据

样本股票来自 `configs/data.yaml`，覆盖银行、保险、白酒、新能源等行业代表标的。行情字段在下载后统一为 `date`、`symbol`、`open`、`high`、`low`、`close`、`volume`、`amount` 等标准列。

## 分析流程

1. 使用 `scripts/update_data.py` 下载并缓存日频行情。
2. 使用 `scripts/run_data_check.py` 生成收益、波动、夏普比率和最大回撤概览。
3. 使用 `scripts/run_matrix_analysis.py` 生成收益率矩阵、协方差矩阵、相关矩阵和相关性热力图。
4. 使用 `scripts/run_statistical_analysis.py` 生成 3σ 异常值、t 检验、QQ 图、密度图和分布检验报告。

## 主要结论写作框架

### 1. 收益与风险

先比较 `stock_risk_summary.csv` 中的年化收益率、年化波动率、夏普比率和最大回撤，判断哪些标的收益更高、哪些标的风险更高。

### 2. 相关性

再结合 `corr_matrix.csv` 和 `corr_heatmap.png` 判断行业内部相关性和跨行业分散效果。相关性越低，组合分散化价值通常越强。

### 3. 分布与极端风险

最后结合 `distribution_test_summary.csv`、`three_sigma_outliers.csv`、QQ 图和密度图判断收益率是否接近正态分布、是否存在肥尾、偏态和极端波动。

## 结论

本项目不依赖因子模型，而是先完成基础收益风险画像。合理的结论应同时引用表格指标和图形证据，避免只凭单一收益率排序判断标的优劣。
