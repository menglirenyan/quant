import numpy as np
import pandas as pd

from src.analysis.statistics import jarque_bera_normality

TRADING_DAYS = 252


def normality_test(returns):
    result = jarque_bera_normality(returns)
    return {
        "jb_stat": result["jb_stat"],
        "p_value": result["jb_p_value"],
        "is_normal": result["is_normal"],
    }


def calc_simple_return(price: pd.Series) -> pd.Series:
    return price.pct_change()


def calc_log_return(price: pd.Series) -> pd.Series:
    #pd.shift(x)将数据往下挪x行
    return np.log(price / price.shift(1))

#计算年收益率
def calc_annual_return(returns: pd.Series) -> float:
    returns = returns.dropna()
    if len(returns) == 0:
        return np.nan
    total_return = (1 + returns).prod() - 1    #returns是回报率一般小于1，总收益率需要先加1再累乘 再-1得到总收益率
    years = len(returns) / TRADING_DAYS
    return (1 + total_return) ** (1 / years) - 1   #对-1前的总收益率开N次，得到每年收益率


def calc_annual_volatility(returns: pd.Series) -> float:
    returns = returns.dropna()
    if len(returns) == 0:
        return np.nan
    return returns.std() * np.sqrt(TRADING_DAYS)     #计算年波动率，认为每日股票是独立同分布的，所以方差可加。 用标准差得到波动率


def calc_sharpe(returns: pd.Series, risk_free_rate: float = 0.0) -> float:
    returns = returns.dropna()
    if len(returns) == 0:
        return np.nan

    #risk_free_rate是无风险年化利率，
    excess_daily = returns - risk_free_rate / TRADING_DAYS      #每日超额收益 = 冒险收益 - 无风险日收益
    std = excess_daily.std()

    if std == 0:
        return np.nan

    #夏普率
    #每日超额净值均值*天数 除以 波动率标准差*根号下天数
    return excess_daily.mean() / std  * np.sqrt(TRADING_DAYS)


def calc_max_drawdown(price_or_nav: pd.Series) -> float:
    x = price_or_nav.dropna()
    if len(x) == 0:
        return np.nan
    #注意 x是序列，cummax求距当前位置的最大值
    cummax = x.cummax()
    drawdown = x / cummax - 1    #序列的位置一一对应与当前最大值作比较， - 1 算出回撤率。
    return drawdown.min()


def summarize_returns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Required input columns:
    - symbol
    - date
    - close
    """
    results = []

    for symbol, group in df.groupby("symbol"):
        group = group.sort_values("date").copy()
        returns = calc_simple_return(group["close"])

        results.append(
            {
                "symbol": symbol,
                "start_date": group["date"].min(),
                "end_date": group["date"].max(),
                "n_days": len(group),
                "annual_return": calc_annual_return(returns),
                "annual_volatility": calc_annual_volatility(returns),
                "sharpe": calc_sharpe(returns),
                "max_drawdown": calc_max_drawdown(group["close"]),
            }
        )

    return pd.DataFrame(results)
