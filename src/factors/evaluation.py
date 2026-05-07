from __future__ import annotations

import numpy as np
import pandas as pd

try:
    from scipy.stats import ttest_1samp
except ModuleNotFoundError:
    ttest_1samp = None


def _corr_or_nan(x: pd.Series, y: pd.Series, method: str) -> float:
    valid = pd.concat([x, y], axis=1).dropna()
    if len(valid) < 3:
        return np.nan
    if valid.iloc[:, 0].nunique() < 2 or valid.iloc[:, 1].nunique() < 2:
        return np.nan
    if method == "spearman":
        return float(valid.iloc[:, 0].rank().corr(valid.iloc[:, 1].rank()))
    return float(valid.iloc[:, 0].corr(valid.iloc[:, 1]))


def calc_ic_timeseries(
    factor_data: pd.DataFrame,
    factor_columns: list[str],
) -> pd.DataFrame:
    rows = []
    for date, group in factor_data.groupby("date"):
        for factor in factor_columns:
            rows.append(
                {
                    "date": date,
                    "factor": factor,
                    "ic": _corr_or_nan(group[factor], group["forward_return"], "pearson"),
                    "rank_ic": _corr_or_nan(group[factor], group["forward_return"], "spearman"),
                    "n_symbols": group["symbol"].nunique(),
                }
            )
    return pd.DataFrame(rows).sort_values(["factor", "date"])


def summarize_ic(ic_ts: pd.DataFrame, periods_per_year: int = 252) -> pd.DataFrame:
    return summarize_ic_with_overlap_adjustment(ic_ts, horizon=1, non_overlapping=False, periods_per_year=periods_per_year)


def _sample_non_overlapping(group: pd.DataFrame, horizon: int, enabled: bool) -> pd.DataFrame:
    clean = group.sort_values("date").reset_index(drop=True)
    if not enabled or horizon <= 1:
        return clean
    return clean.iloc[::horizon].copy()


def summarize_ic_with_overlap_adjustment(
    ic_ts: pd.DataFrame,
    horizon: int,
    non_overlapping: bool = True,
    periods_per_year: int = 252,
) -> pd.DataFrame:
    rows = []
    for factor, group in ic_ts.groupby("factor"):
        sample = _sample_non_overlapping(group, horizon=horizon, enabled=non_overlapping)
        ic = pd.to_numeric(sample["ic"], errors="coerce").dropna()
        rank_ic = pd.to_numeric(sample["rank_ic"], errors="coerce").dropna()

        ic_t = ttest_1samp(ic, popmean=0.0) if ttest_1samp and len(ic) >= 2 else None
        rank_t = ttest_1samp(rank_ic, popmean=0.0) if ttest_1samp and len(rank_ic) >= 2 else None
        sample_mode = "non_overlapping" if non_overlapping and horizon > 1 else "daily"

        rows.append(
            {
                "factor": factor,
                "n_dates": len(group),
                "sample_mode": sample_mode,
                "effective_n_dates": len(sample),
                "mean_ic": ic.mean() if len(ic) else np.nan,
                "std_ic": ic.std() if len(ic) else np.nan,
                "ic_ir": ic.mean() / ic.std() * np.sqrt(periods_per_year) if len(ic) >= 2 and ic.std() != 0 else np.nan,
                "ic_positive_ratio": (ic > 0).mean() if len(ic) else np.nan,
                "ic_t_stat": ic_t.statistic if ic_t else np.nan,
                "ic_p_value": ic_t.pvalue if ic_t else np.nan,
                "overlap_adjusted_t_stat": ic_t.statistic if ic_t else np.nan,
                "overlap_adjusted_p_value": ic_t.pvalue if ic_t else np.nan,
                "mean_rank_ic": rank_ic.mean() if len(rank_ic) else np.nan,
                "std_rank_ic": rank_ic.std() if len(rank_ic) else np.nan,
                "rank_ic_ir": rank_ic.mean() / rank_ic.std() * np.sqrt(periods_per_year)
                if len(rank_ic) >= 2 and rank_ic.std() != 0
                else np.nan,
                "rank_ic_positive_ratio": (rank_ic > 0).mean() if len(rank_ic) else np.nan,
                "rank_ic_t_stat": rank_t.statistic if rank_t else np.nan,
                "rank_ic_p_value": rank_t.pvalue if rank_t else np.nan,
                "rank_ic_overlap_adjusted_t_stat": rank_t.statistic if rank_t else np.nan,
                "rank_ic_overlap_adjusted_p_value": rank_t.pvalue if rank_t else np.nan,
            }
        )
    return pd.DataFrame(rows).sort_values("mean_rank_ic", ascending=False)
