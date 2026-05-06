from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import jarque_bera, ttest_1samp

TRADING_DAYS = 252


def detect_three_sigma_outliers(
    returns: pd.Series,
    symbol: str,
    dates: pd.Series | None = None,
    sigma: float = 3.0,
) -> pd.DataFrame:
    """Find return observations farther than sigma standard deviations."""
    clean_returns = pd.to_numeric(returns, errors="coerce")
    mean = clean_returns.mean()
    std = clean_returns.std()

    columns = ["symbol", "date", "return", "mean", "std", "z_score"]
    if pd.isna(std) or std == 0:
        return pd.DataFrame(columns=columns)

    z_score = (clean_returns - mean) / std
    mask = z_score.abs() > sigma

    if dates is None:
        outlier_dates = pd.Series(clean_returns.index, index=clean_returns.index)
    else:
        outlier_dates = pd.to_datetime(dates)

    return pd.DataFrame(
        {
            "symbol": symbol,
            "date": outlier_dates[mask].to_numpy(),
            "return": clean_returns[mask].to_numpy(),
            "mean": mean,
            "std": std,
            "z_score": z_score[mask].to_numpy(),
        }
    ).sort_values("date")


def t_test_mean_return(returns: pd.Series, popmean: float = 0.0) -> dict:
    """Run a one-sample t test for whether mean daily return differs from popmean."""
    clean_returns = pd.to_numeric(returns, errors="coerce").dropna()
    if len(clean_returns) < 2:
        return {
            "t_stat": np.nan,
            "t_p_value": np.nan,
            "mean_daily_return": clean_returns.mean() if len(clean_returns) else np.nan,
            "is_mean_significant": False,
        }

    stat, p_value = ttest_1samp(clean_returns, popmean=popmean)
    return {
        "t_stat": stat,
        "t_p_value": p_value,
        "mean_daily_return": clean_returns.mean(),
        "is_mean_significant": p_value < 0.05,
    }


def jarque_bera_normality(returns: pd.Series) -> dict:
    clean_returns = pd.to_numeric(returns, errors="coerce").dropna()
    if len(clean_returns) < 2:
        return {
            "jb_stat": np.nan,
            "jb_p_value": np.nan,
            "is_normal": False,
        }

    stat, p_value = jarque_bera(clean_returns)
    return {
        "jb_stat": stat,
        "jb_p_value": p_value,
        "is_normal": p_value > 0.05,
    }


def summarize_distribution_tests(df: pd.DataFrame) -> pd.DataFrame:
    """Summarize 3-sigma, t-test, volatility, and normality by symbol."""
    rows = []

    for symbol, group in df.groupby("symbol"):
        group = group.sort_values("date").copy()
        returns = group["close"].pct_change()
        clean_returns = returns.dropna()
        outliers = detect_three_sigma_outliers(
            returns=returns,
            symbol=symbol,
            dates=group["date"],
        )

        row = {
            "symbol": symbol,
            "start_date": group["date"].min(),
            "end_date": group["date"].max(),
            "n_return_days": len(clean_returns),
            "annual_volatility": clean_returns.std() * np.sqrt(TRADING_DAYS),
            "three_sigma_outlier_count": len(outliers),
            "three_sigma_outlier_ratio": len(outliers) / len(clean_returns)
            if len(clean_returns)
            else np.nan,
        }
        row.update(t_test_mean_return(clean_returns))
        row.update(jarque_bera_normality(clean_returns))
        rows.append(row)

    return pd.DataFrame(rows)


def collect_three_sigma_outliers(df: pd.DataFrame) -> pd.DataFrame:
    outliers = []

    for symbol, group in df.groupby("symbol"):
        group = group.sort_values("date").copy()
        outliers.append(
            detect_three_sigma_outliers(
                returns=group["close"].pct_change(),
                symbol=symbol,
                dates=group["date"],
            )
        )

    if not outliers:
        return pd.DataFrame(columns=["symbol", "date", "return", "mean", "std", "z_score"])

    return pd.concat(outliers, ignore_index=True)
