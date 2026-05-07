from __future__ import annotations

import numpy as np
import pandas as pd


def assign_quantiles(group: pd.DataFrame, factor: str, quantiles: int) -> pd.Series:
    ranks = group[factor].rank(method="first")
    unique_count = ranks.nunique()
    if unique_count < 2:
        return pd.Series(pd.NA, index=group.index, dtype="Int64")

    bins = min(quantiles, unique_count)
    labels = range(1, bins + 1)
    return pd.qcut(ranks, q=bins, labels=labels, duplicates="drop").astype("Int64")


def calc_layer_returns(
    factor_data: pd.DataFrame,
    factor_columns: list[str],
    quantiles: int = 5,
) -> pd.DataFrame:
    rows = []
    for factor in factor_columns:
        temp = factor_data[["date", "symbol", factor, "forward_return"]].dropna().copy()
        temp["quantile"] = temp.groupby("date", group_keys=False).apply(
            lambda g: assign_quantiles(g, factor, quantiles),
            include_groups=False,
        )
        temp = temp.dropna(subset=["quantile"])

        layer = (
            temp.groupby(["date", "quantile"], observed=True)["forward_return"]
            .mean()
            .reset_index()
            .rename(columns={"forward_return": "mean_forward_return"})
        )
        layer["factor"] = factor
        rows.append(layer)

    if not rows:
        return pd.DataFrame(columns=["date", "quantile", "mean_forward_return", "factor"])
    return pd.concat(rows, ignore_index=True).sort_values(["factor", "date", "quantile"])


def calc_long_short_returns(layer_returns: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for factor, group in layer_returns.groupby("factor"):
        pivot = group.pivot(index="date", columns="quantile", values="mean_forward_return")
        if pivot.empty:
            continue
        low = pivot.columns.min()
        high = pivot.columns.max()
        rows.append(
            pd.DataFrame(
                {
                    "date": pivot.index,
                    "factor": factor,
                    "long_return": pivot[high].to_numpy(),
                    "short_return": pivot[low].to_numpy(),
                    "long_short_return": (pivot[high] - pivot[low]).to_numpy(),
                }
            )
        )
    if not rows:
        return pd.DataFrame(columns=["date", "factor", "long_return", "short_return", "long_short_return"])
    return pd.concat(rows, ignore_index=True).sort_values(["factor", "date"])


def calc_long_only_returns(long_short_returns: pd.DataFrame) -> pd.DataFrame:
    if long_short_returns.empty:
        return pd.DataFrame(columns=["date", "factor", "long_return"])
    return long_short_returns[["date", "factor", "long_return"]].copy()


def _equal_weights(symbols: list[str]) -> dict[str, float]:
    if not symbols:
        return {}
    weight = 1.0 / len(symbols)
    return {symbol: weight for symbol in symbols}


def _turnover(previous: dict[str, float], current: dict[str, float]) -> float:
    all_symbols = set(previous) | set(current)
    return 0.5 * sum(abs(current.get(symbol, 0.0) - previous.get(symbol, 0.0)) for symbol in all_symbols)


def calc_long_short_turnover(
    factor_data: pd.DataFrame,
    factor_columns: list[str],
    quantiles: int = 5,
) -> pd.DataFrame:
    rows = []
    for factor in factor_columns:
        previous_long: dict[str, float] = {}
        previous_short: dict[str, float] = {}
        temp = factor_data[["date", "symbol", factor]].dropna().copy()

        for date, group in temp.groupby("date"):
            group = group.copy()
            group["quantile"] = assign_quantiles(group, factor, quantiles)
            group = group.dropna(subset=["quantile"])
            if group.empty:
                continue

            top = group[group["quantile"] == group["quantile"].max()]
            bottom = group[group["quantile"] == group["quantile"].min()]
            current_long = _equal_weights(top["symbol"].tolist())
            current_short = _equal_weights(bottom["symbol"].tolist())
            long_turnover = _turnover(previous_long, current_long)
            short_turnover = _turnover(previous_short, current_short)

            rows.append(
                {
                    "date": date,
                    "factor": factor,
                    "long_turnover": long_turnover,
                    "short_turnover": short_turnover,
                    "gross_turnover": long_turnover + short_turnover,
                }
            )
            previous_long = current_long
            previous_short = current_short

    if not rows:
        return pd.DataFrame(columns=["date", "factor", "long_turnover", "short_turnover", "gross_turnover"])
    return pd.DataFrame(rows).sort_values(["factor", "date"])


def calc_top_quantile_turnover(
    factor_data: pd.DataFrame,
    factor_columns: list[str],
    quantiles: int = 5,
) -> pd.DataFrame:
    turnover = calc_long_short_turnover(factor_data, factor_columns, quantiles)
    if turnover.empty:
        return pd.DataFrame(columns=["date", "factor", "top_quantile_turnover"])
    return turnover[["date", "factor", "long_turnover"]].rename(columns={"long_turnover": "top_quantile_turnover"})


def calc_cost_sensitivity(
    long_short_returns: pd.DataFrame,
    turnover: pd.DataFrame,
    transaction_cost_bps: list[int],
) -> pd.DataFrame:
    base = long_short_returns.merge(turnover, on=["date", "factor"], how="left")
    for col in ["long_turnover", "short_turnover", "gross_turnover"]:
        if col not in base.columns:
            base[col] = 0.0
    base[["long_turnover", "short_turnover", "gross_turnover"]] = base[
        ["long_turnover", "short_turnover", "gross_turnover"]
    ].fillna(0.0)

    rows = []
    for cost_bps in transaction_cost_bps:
        cost_rate = cost_bps / 10000
        temp = base.copy()
        temp["net_long_return"] = temp["long_return"] - temp["long_turnover"] * cost_rate
        temp["net_long_short_return"] = temp["long_short_return"] - temp["gross_turnover"] * cost_rate
        for factor, group in temp.groupby("factor"):
            returns = pd.to_numeric(group["net_long_short_return"], errors="coerce").dropna()
            long_returns = pd.to_numeric(group["net_long_return"], errors="coerce").dropna()
            rows.append(
                {
                    "factor": factor,
                    "transaction_cost_bps": cost_bps,
                    "mean_net_long_return": long_returns.mean() if len(long_returns) else np.nan,
                    "mean_net_return": returns.mean() if len(returns) else np.nan,
                    "cumulative_net_long_return": (1 + long_returns).prod() - 1 if len(long_returns) else np.nan,
                    "cumulative_net_return": (1 + returns).prod() - 1 if len(returns) else np.nan,
                    "net_return_std": returns.std() if len(returns) else np.nan,
                    "average_long_turnover": group["long_turnover"].mean(),
                    "average_short_turnover": group["short_turnover"].mean(),
                    "average_turnover": group["gross_turnover"].mean(),
                }
            )
    return pd.DataFrame(rows).sort_values(["factor", "transaction_cost_bps"])
