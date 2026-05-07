# -*- coding: utf-8 -*-
from __future__ import annotations

import pandas as pd


def _fmt_pct(value: float) -> str:
    if pd.isna(value):
        return "nan"
    return f"{value:.2%}"


def build_factor_research_report(
    factor_data: pd.DataFrame,
    ic_summary: pd.DataFrame,
    cost_sensitivity: pd.DataFrame,
    audit: pd.DataFrame,
    factor_columns: list[str],
    value_source: str,
    label_timing: str,
    horizon: int,
    non_overlapping_ic: bool,
    long_short_mode: str,
) -> str:
    start = factor_data["date"].min().date()
    end = factor_data["date"].max().date()

    if ic_summary.empty:
        best_rank_text = "无可用因子"
    else:
        best_rank = ic_summary.sort_values("mean_rank_ic", ascending=False).iloc[0]
        best_rank_text = (
            f'{best_rank["factor"]}，mean RankIC = {best_rank["mean_rank_ic"]:.4f}，'
            f'有效样本日期数 = {int(best_rank["effective_n_dates"])}'
        )

    if cost_sensitivity.empty:
        best_cost_text = "无可用成本敏感性结果"
    else:
        best_cost = cost_sensitivity.sort_values("cumulative_net_return", ascending=False).iloc[0]
        best_cost_text = (
            f'{best_cost["factor"]}，交易成本 {int(best_cost["transaction_cost_bps"])} bps，'
            f'long-short 累计净收益 {_fmt_pct(best_cost["cumulative_net_return"])}'
        )

    skipped = audit[audit["status"] == "skipped"] if not audit.empty else pd.DataFrame()
    skipped_text = "无"
    if not skipped.empty:
        skipped_text = "；".join(
            f'{row["filter_name"]}: {row["message"]}' for _, row in skipped.iterrows()
        )

    value_text = "可用" if value_source != "unavailable" and "value_factor" in factor_columns else "不可用，已跳过价值因子"
    ic_mode = "非重叠抽样 t 检验" if non_overlapping_ic and horizon > 1 else "逐日 t 检验"

    return f"""# 因子研究与横截面回测报告

## 数据与过滤

- 样本区间：{start} 至 {end}
- 截面日期数：{factor_data["date"].nunique()}
- 股票数：{factor_data["symbol"].nunique()}
- 因子列：{", ".join(factor_columns)}
- 过滤降级项：{skipped_text}

## 标签与 IC

- 标签口径：`{label_timing}`，持有期 {horizon} 个交易日。
- 默认含义：t 日收盘后生成因子，t+1 开盘买入，未来第 N 个交易日后开盘卖出。
- IC 检验口径：{ic_mode}；完整逐日 IC 序列仍输出到 `factor_ic_timeseries.csv`。
- RankIC 均值最高的因子：{best_rank_text}

## 分层、换手与成本

- 多空假设：`{long_short_mode}`，这是研究组合假设，不代表 A 股可直接实盘做空。
- 成本模型：long leg 与 short leg 分别计算等权换手，并用 gross turnover 扣减 long-short 收益。
- 成本敏感性最优组合：{best_cost_text}

## 估值因子

- 估值因子状态：{value_text}
- 价值因子只接受真实估值表 `valuation.parquet` 的 PB/PE/PS/股息率，不再使用均线偏离代理作为基本面因子。
"""
