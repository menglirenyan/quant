import pandas as pd


NUMERIC_COLUMNS = [
    "open",
    "close",
    "high",
    "low",
    "volume",
    "amount",
    "amplitude",
    "pct_change",
    "change",
    "turnover",
]


def clean_ohlcv(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    if "date" not in df.columns:
        raise ValueError("DataFrame must contain date column")

    df["date"] = pd.to_datetime(df["date"])

    for col in NUMERIC_COLUMNS:
        if col in df.columns:
            #如果NUMERIC_COLUMNS中的数据出现在pd中，就将其强制转换为数字，转变不了的用NaN.
            df[col] = pd.to_numeric(df[col], errors="coerce")


    df = df.sort_values(["symbol", "date"])                           #按给定特征排序
    df = df.drop_duplicates(subset=["symbol", "date"], keep="last")   #去重

    # Drop rows that cannot support OHLC return analysis.
    df = df.dropna(subset=["open", "high", "low", "close"])           #如果某行缺少subset中的数据就删除该行数据

    # df = df(常识数据应都>0)  用逻辑与表示  可以看作乘法，全为1时为1.
    df = df[
        (df["open"] > 0)
        & (df["high"] > 0)
        & (df["low"] > 0)
        & (df["close"] > 0)
    ]

    return df.reset_index(drop=True)
