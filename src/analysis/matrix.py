import pandas as pd


def build_return_matrix(df: pd.DataFrame) -> pd.DataFrame:
    """
    输入：
        df: [date, symbol, close]

    输出：
        行：date
        列：symbol
        值：日收益率
    """
    df = df.copy()
    df = df.sort_values(["symbol", "date"])

    df["return"] = df.groupby("symbol")["close"].pct_change()

    pivot = df.pivot(index="date", columns="symbol", values="return")

    return pivot

def calc_cov_matrix(ret_mat: pd.DataFrame) -> pd.DataFrame:
    return ret_mat.cov()


def calc_corr_matrix(ret_mat: pd.DataFrame) -> pd.DataFrame:
    return ret_mat.corr()