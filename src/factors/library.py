from __future__ import annotations

import numpy as np
import pandas as pd


def _grouped_return(close: pd.Series, symbols: pd.Series, periods: int) -> pd.Series:
    return close.groupby(symbols).pct_change(periods=periods)


def build_price_factors(
    prices: pd.DataFrame,
    momentum_window: int = 20,
    volatility_window: int = 20,
    turnover_window: int = 20,
    value_window: int = 120,
) -> pd.DataFrame:
    """
    Build a minimal A-share cross-sectional factor set from daily OHLCV data.

    Required columns: date, symbol, close. Turnover is optional.
    Higher factor values are interpreted as stronger signals.
    """
    required = {"date", "symbol", "close"}
    missing = required - set(prices.columns)
    if missing:
        raise ValueError(f"prices missing required columns: {sorted(missing)}")

    df = prices.copy()
    df["date"] = pd.to_datetime(df["date"])
    df["symbol"] = df["symbol"].astype(str).str.zfill(6)
    df["close"] = pd.to_numeric(df["close"], errors="coerce")
    if "turnover" in df.columns:
        df["turnover"] = pd.to_numeric(df["turnover"], errors="coerce")
    else:
        df["turnover"] = np.nan

    df = df.sort_values(["symbol", "date"]).reset_index(drop=True)
    grouped = df.groupby("symbol", group_keys=False)
    daily_return = grouped["close"].pct_change()

    momentum_col = f"momentum_{momentum_window}d"
    low_volatility_col = f"low_volatility_{volatility_window}d"
    turnover_col = f"turnover_{turnover_window}d"
    value_proxy_col = f"value_proxy_{value_window}d"

    df[momentum_col] = _grouped_return(df["close"], df["symbol"], momentum_window)
    volatility = grouped["close"].transform(
        lambda s: s.pct_change().rolling(volatility_window, min_periods=max(5, volatility_window // 2)).std()
    )
    df[low_volatility_col] = -volatility
    df[turnover_col] = grouped["turnover"].transform(
        lambda s: s.rolling(turnover_window, min_periods=max(5, turnover_window // 2)).mean()
    )
    moving_average = grouped["close"].transform(
        lambda s: s.rolling(value_window, min_periods=max(20, value_window // 3)).mean()
    )
    df[value_proxy_col] = moving_average / df["close"] - 1
    df["daily_return"] = daily_return

    return df[
        [
            "date",
            "symbol",
            momentum_col,
            low_volatility_col,
            turnover_col,
            value_proxy_col,
            "daily_return",
        ]
    ]


def merge_valuation_factor(factors: pd.DataFrame, valuation: pd.DataFrame | None) -> pd.DataFrame:
    """
    Merge an optional fundamental/valuation table.

    Supported valuation columns: pb, pe, ps, dividend_yield. The preferred value
    factor is book-to-price (1 / pb), then earnings yield (1 / pe), then sales
    yield (1 / ps), then dividend_yield. If no table is supplied, value_factor is
    not created; technical value proxies must not be treated as fundamental data.
    """
    if valuation is None or valuation.empty:
        out = factors.copy()
        out["value_factor_source"] = "unavailable"
        return out

    val = valuation.copy()
    val["date"] = pd.to_datetime(val["date"])
    val["symbol"] = val["symbol"].astype(str).str.zfill(6)

    for col in ["pb", "pe", "ps", "dividend_yield"]:
        if col in val.columns:
            val[col] = pd.to_numeric(val[col], errors="coerce")

    source = None
    if "pb" in val.columns:
        val["value_factor"] = np.where(val["pb"] > 0, 1 / val["pb"], np.nan)
        source = "book_to_price"
    elif "pe" in val.columns:
        val["value_factor"] = np.where(val["pe"] > 0, 1 / val["pe"], np.nan)
        source = "earnings_yield"
    elif "ps" in val.columns:
        val["value_factor"] = np.where(val["ps"] > 0, 1 / val["ps"], np.nan)
        source = "sales_yield"
    elif "dividend_yield" in val.columns:
        val["value_factor"] = val["dividend_yield"]
        source = "dividend_yield"
    else:
        out = factors.copy()
        out["value_factor_source"] = "unavailable"
        return out

    factor_parts = []
    for symbol, factor_group in factors.sort_values(["symbol", "date"]).groupby("symbol"):
        val_group = val[val["symbol"] == symbol].sort_values("date")
        if val_group.empty:
            factor_part = factor_group.copy()
            factor_part["value_factor"] = np.nan
        else:
            factor_part = pd.merge_asof(
                factor_group.sort_values("date"),
                val_group[["date", "value_factor"]].sort_values("date"),
                on="date",
                direction="backward",
            )
        factor_part["symbol"] = symbol
        factor_parts.append(factor_part)

    merged = pd.concat(factor_parts, ignore_index=True) if factor_parts else factors.copy()
    merged["value_factor_source"] = source
    return merged


def available_factor_columns(factors: pd.DataFrame, configured_columns: list[str]) -> list[str]:
    return [col for col in configured_columns if col in factors.columns and factors[col].notna().any()]
