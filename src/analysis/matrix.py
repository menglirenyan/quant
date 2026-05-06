import pandas as pd


def build_return_matrix(df: pd.DataFrame) -> pd.DataFrame:
    """
    Input:
        df: [date, symbol, close]

    Output:
        rows: date
        columns: symbol
        values: daily return
    """
    df = df.copy()
    df = df.sort_values(["symbol", "date"])

    df["return"] = df.groupby("symbol")["close"].pct_change()
    return df.pivot(index="date", columns="symbol", values="return")


def calc_cov_matrix(ret_mat: pd.DataFrame) -> pd.DataFrame:
    return ret_mat.cov()


def calc_corr_matrix(ret_mat: pd.DataFrame) -> pd.DataFrame:
    return ret_mat.corr()
