import time
from typing import Callable

import akshare as ak
import pandas as pd


def retry_call(
    func: Callable,
    max_retry: int = 3,
    sleep_seconds: int = 3,
):
    last_error = None

    for i in range(max_retry):
        try:
            return func()
        except Exception as e:
            last_error = e  
            print(f"[Retry {i + 1}/{max_retry}] Error: {repr(e)}")
            time.sleep(sleep_seconds * (i + 1))

    raise last_error


def to_market_symbol(symbol: str) -> str:
    """
    Convert a six-digit A-share code to the market-prefixed code used by
    some AkShare APIs, for example 600519 -> sh600519.
    """
    symbol = str(symbol).zfill(6)

    if symbol.startswith(("6", "5", "9")):
        return f"sh{symbol}"
    return f"sz{symbol}"


def normalize_columns(df: pd.DataFrame, symbol: str) -> pd.DataFrame:
    df = df.copy()

    #将数据类统一映射为同样的关键词
    rename_map = {
        # Eastmoney-style Chinese columns.
        "日期": "date",
        "股票代码": "symbol",
        "开盘": "open",
        "收盘": "close",
        "最高": "high",
        "最低": "low",
        "成交量": "volume",
        "成交额": "amount",
        "振幅": "amplitude",
        "涨跌幅": "pct_change",
        "涨跌额": "change",
        "换手率": "turnover",
        # NetEase-style Chinese columns.
        "收盘价": "close",
        "最高价": "high",
        "最低价": "low",
        "开盘价": "open",
        "前收盘": "pre_close",
        # English columns returned by Sina/Tencent/index endpoints.
        "date": "date",
        "open": "open",
        "close": "close",
        "high": "high",
        "low": "low",
        "volume": "volume",
        "amount": "amount",
        "turnover": "turnover",
        "pct_change": "pct_change",
        "change": "change",
        "amplitude": "amplitude",
        "pre_close": "pre_close",
    }

    #rename(k:v) 将k->v
    df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})

    if "date" not in df.columns:
        raise ValueError(f"date column not found. columns={df.columns.tolist()}")

    df["date"] = pd.to_datetime(df["date"])
    df["symbol"] = str(symbol).zfill(6)

    keep_cols = [
        "date",
        "symbol",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "amount",
        "turnover",
        "pct_change",
        "change",
        "amplitude",
        "pre_close",
    ]

    existing_cols = [c for c in keep_cols if c in df.columns]
    df = df[existing_cols].copy()

    numeric_cols = [
        "open",
        "high",
        "low",
        "close",
        "volume",
        "amount",
        "turnover",
        "pct_change",
        "change",
        "amplitude",
        "pre_close",
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    return df.sort_values("date").reset_index(drop=True)


def get_stock_daily_from_tx(
    symbol: str,
    start_date: str,
    end_date: str,
    adjust: str = "qfq",
) -> pd.DataFrame:
    market_symbol = to_market_symbol(symbol)

    def fetch():
        return ak.stock_zh_a_hist_tx(
            symbol=market_symbol,
            start_date=start_date,
            end_date=end_date,
            adjust=adjust,
            timeout=20,
        )

    df = retry_call(fetch)
    return normalize_columns(df, symbol)


def get_stock_daily_from_sina(
    symbol: str,
    start_date: str,
    end_date: str,
    adjust: str = "qfq",
) -> pd.DataFrame:
    market_symbol = to_market_symbol(symbol)

    def fetch():
        return ak.stock_zh_a_daily(
            symbol=market_symbol,
            start_date=start_date,
            end_date=end_date,
            adjust=adjust,
        )

    df = retry_call(fetch)
    return normalize_columns(df, symbol)


def get_stock_daily_from_163(
    symbol: str,
    start_date: str,
    end_date: str,
) -> pd.DataFrame:
    market_symbol = to_market_symbol(symbol)

    def fetch():
        return ak.stock_zh_a_hist_163(
            symbol=market_symbol,
            start_date=start_date,
            end_date=end_date,
        )

    df = retry_call(fetch)
    return normalize_columns(df, symbol)


def get_stock_daily(
    symbol: str,
    start_date: str,
    end_date: str,
    adjust: str = "qfq",
) -> pd.DataFrame:
    """
    Fetch stock data with a fallback chain:
    1. Tencent adjusted daily data.
    2. Sina adjusted daily data.
    3. NetEase unadjusted daily data as the final fallback.
    """
    errors = []

    for source_name, fetcher in [
        ("tencent", lambda: get_stock_daily_from_tx(symbol, start_date, end_date, adjust)),
        ("sina", lambda: get_stock_daily_from_sina(symbol, start_date, end_date, adjust)),
        ("netease_163_unadjusted", lambda: get_stock_daily_from_163(symbol, start_date, end_date)),
    ]:
        try:
            print(f"[DataSource] {symbol} -> {source_name}")
            df = fetcher()

            if df.empty:
                raise ValueError(f"{source_name} returned empty DataFrame")

            df["source"] = source_name
            return df

        except Exception as e:
            errors.append((source_name, repr(e)))
            print(f"[DataSource Failed] {symbol} {source_name}: {repr(e)}")
            time.sleep(2)

    raise RuntimeError(f"All data sources failed for symbol={symbol}. errors={errors}")


def get_index_daily(
    index_code: str,
    start_date: str,
    end_date: str,
) -> pd.DataFrame:
    """Fetch index daily data from Sina through AkShare."""

    index_code = str(index_code).zfill(6)

    if index_code.startswith(("0", "3")):
        market_symbol = (
            f"sh{index_code}"
            if index_code in {"000300", "000905", "000016"}
            else f"sz{index_code}"
        )
    else:
        market_symbol = to_market_symbol(index_code)

    def fetch():
        return ak.stock_zh_index_daily(symbol=market_symbol)

    df = retry_call(fetch)

    if df.empty:
        raise ValueError(f"No index data returned for index_code={index_code}")

    df = normalize_columns(df, index_code)

    start = pd.to_datetime(start_date)
    end = pd.to_datetime(end_date)
    return df[(df["date"] >= start) & (df["date"] <= end)].copy()
