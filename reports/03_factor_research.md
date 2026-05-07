# 因子研究与横截面回测报告

本报告由 `python scripts/run_factor_research.py` 生成。

## 方法说明

- 因子：动量、低波动、换手率、价值。
- 股票池过滤：支持 ST、停牌、新股、涨跌停、行业和市值过滤；缺元数据时按 permissive 策略降级并输出 audit 表。
- 标签：默认 `next_open_to_horizon_open`，即 t 日收盘后生成因子，t+1 开盘买入，未来第 N 个交易日后开盘卖出。
- 预处理：按交易日横截面 winsorize，并做 z-score 标准化。
- 评价：逐日计算 IC 与 RankIC，并用非重叠样本汇总均值、IR、正比例和 t 检验。
- 回测：按因子得分做分层收益，构造最高分层减最低分层的 long-short 研究组合，并对 long/short 双边换手扣成本。

## 运行前检查

横截面因子研究需要多个股票同日比较。若项目甲只配置了单只样本股，请先扩大 `configs/data.yaml` 的 `symbols`，运行 `scripts/update_data.py` 后再运行因子研究脚本。

若存在 `data/processed/valuation.parquet`，脚本会优先使用 PB/PE/PS/股息率生成价值因子；否则跳过 `value_factor`，不再使用价格相对均线的估值代理作为基本面因子。
