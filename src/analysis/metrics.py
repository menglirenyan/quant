import numpy as np
import pandas as pd
from scipy.stats import jarque_bera

TRADING_DAYS = 252


def normality_test(returns):
    returns = returns.dropna()

    stat, p_value = jarque_bera(returns)

    return {
        "jb_stat": stat,
        "p_value": p_value,
        "is_normal": p_value > 0.05,
    }

def calc_simple_return(price: pd.Series) -> pd.Series:
    return price.pct_change()


def calc_log_return(price: pd.Series) -> pd.Series:
    return np.log(price / price.shift(1))


def calc_annual_return(returns: pd.Series) -> float:
    returns = returns.dropna()
    if len(returns) == 0:
        return np.nan
    total_return = (1 + returns).prod() - 1
    years = len(returns) / TRADING_DAYS
    return (1 + total_return) ** (1 / years) - 1


def calc_annual_volatility(returns: pd.Series) -> float:
    returns = returns.dropna()
    if len(returns) == 0:
        return np.nan
    return returns.std() * np.sqrt(TRADING_DAYS)


def calc_sharpe(returns: pd.Series, risk_free_rate: float = 0.0) -> float:
    returns = returns.dropna()
    if len(returns) == 0:
        return np.nan

    excess_daily = returns - risk_free_rate / TRADING_DAYS
    std = excess_daily.std()

    if std == 0:
        return np.nan

    return excess_daily.mean() / std * np.sqrt(TRADING_DAYS)


def calc_max_drawdown(price_or_nav: pd.Series) -> float:
    x = price_or_nav.dropna()
    if len(x) == 0:
        return np.nan

    cummax = x.cummax()
    drawdown = x / cummax - 1
    return drawdown.min()


def summarize_returns(df: pd.DataFrame) -> pd.DataFrame:
    """
    输入字段：
    - symbol
    - date
    - close
    """
    results = []

    for symbol, g in df.groupby("symbol"):
        g = g.sort_values("date").copy()
        returns = calc_simple_return(g["close"])

        results.append(
            {
                "symbol": symbol,
                "start_date": g["date"].min(),
                "end_date": g["date"].max(),
                "n_days": len(g),
                "annual_return": calc_annual_return(returns),
                "annual_volatility": calc_annual_volatility(returns),
                "sharpe": calc_sharpe(returns),
                "max_drawdown": calc_max_drawdown(g["close"]),
            }
        )

    return pd.DataFrame(results)