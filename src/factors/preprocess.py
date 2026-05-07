from __future__ import annotations

import pandas as pd


FACTOR_COLUMNS = [
    "momentum_20d",
    "low_volatility_20d",
    "turnover_20d",
    "value_factor",
]


def factor_columns_from_config(factor_config: dict) -> list[str]:
    return [
        f"momentum_{factor_config.get('momentum_window', 20)}d",
        f"low_volatility_{factor_config.get('volatility_window', 20)}d",
        f"turnover_{factor_config.get('turnover_window', 20)}d",
        "value_factor",
    ]


def add_forward_return(
    prices: pd.DataFrame,
    horizon: int,
    timing: str = "next_open_to_horizon_open",
) -> pd.DataFrame:
    required = {"date", "symbol", "close"}
    if timing == "next_open_to_horizon_open":
        required.add("open")
    missing = required - set(prices.columns)
    if missing:
        raise ValueError(f"prices missing required columns: {sorted(missing)}")

    df = prices[["date", "symbol", "open", "close"] if "open" in prices.columns else ["date", "symbol", "close"]].copy()
    df["date"] = pd.to_datetime(df["date"])
    df["symbol"] = df["symbol"].astype(str).str.zfill(6)
    df["close"] = pd.to_numeric(df["close"], errors="coerce")
    if "open" in df.columns:
        df["open"] = pd.to_numeric(df["open"], errors="coerce")
    df = df.sort_values(["symbol", "date"])

    grouped = df.groupby("symbol")
    if timing == "next_open_to_horizon_open":
        entry = grouped["open"].shift(-1)
        exit_ = grouped["open"].shift(-(horizon + 1))
    elif timing == "next_open_to_horizon_close":
        entry = grouped["open"].shift(-1)
        exit_ = grouped["close"].shift(-horizon)
    elif timing == "close_to_close":
        entry = df["close"]
        exit_ = grouped["close"].shift(-horizon)
    else:
        raise ValueError(
            "timing must be one of: next_open_to_horizon_open, "
            "next_open_to_horizon_close, close_to_close"
        )

    df["entry_price"] = entry
    df["exit_price"] = exit_
    df["forward_return"] = df["exit_price"] / df["entry_price"] - 1
    df["label_timing"] = timing
    return df[["date", "symbol", "entry_price", "exit_price", "forward_return", "label_timing"]]


def filter_universe(
    df: pd.DataFrame,
    symbols: list[str] | None = None,
    min_history_days: int = 80,
) -> pd.DataFrame:
    out = df.copy()
    out["symbol"] = out["symbol"].astype(str).str.zfill(6)

    if symbols:
        keep = {str(symbol).zfill(6) for symbol in symbols}
        out = out[out["symbol"].isin(keep)]

    counts = out.groupby("symbol")["date"].transform("count")
    return out[counts >= min_history_days].copy()


def winsorize_by_date(df: pd.DataFrame, columns: list[str], quantile: float = 0.01) -> pd.DataFrame:
    if quantile <= 0:
        return df.copy()

    out = df.copy()
    grouped = out.groupby("date")
    for col in columns:
        lower = grouped[col].transform(lambda s: s.quantile(quantile))
        upper = grouped[col].transform(lambda s: s.quantile(1 - quantile))
        out[col] = out[col].clip(lower=lower, upper=upper)
    return out


def zscore_by_date(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    out = df.copy()
    grouped = out.groupby("date")
    for col in columns:
        mean = grouped[col].transform("mean")
        std = grouped[col].transform("std")
        out[col] = (out[col] - mean) / std.replace(0, pd.NA)
    return out


def prepare_factor_dataset(
    factor_frame: pd.DataFrame,
    labels: pd.DataFrame,
    factor_columns: list[str] | None = None,
    winsorize_quantile: float = 0.01,
    zscore: bool = True,
    min_symbols_per_date: int = 3,
) -> pd.DataFrame:
    factor_columns = factor_columns or FACTOR_COLUMNS

    df = factor_frame.merge(labels, on=["date", "symbol"], how="inner")
    df = df.dropna(subset=[*factor_columns, "forward_return"]).copy()

    counts = df.groupby("date")["symbol"].transform("nunique")
    df = df[counts >= min_symbols_per_date].copy()

    df = winsorize_by_date(df, factor_columns, winsorize_quantile)
    if zscore:
        df = zscore_by_date(df, factor_columns)

    return df.dropna(subset=[*factor_columns, "forward_return"]).sort_values(["date", "symbol"])
