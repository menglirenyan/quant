from __future__ import annotations

import numpy as np
import pandas as pd


AUDIT_COLUMNS = [
    "filter_name",
    "input_rows",
    "output_rows",
    "removed_rows",
    "input_symbols",
    "output_symbols",
    "removed_symbols",
    "status",
    "message",
]


def _empty_audit() -> pd.DataFrame:
    return pd.DataFrame(columns=AUDIT_COLUMNS)


def _audit_row(
    filter_name: str,
    before: pd.DataFrame,
    after: pd.DataFrame,
    status: str = "applied",
    message: str = "",
) -> dict:
    before_symbols = before["symbol"].nunique() if "symbol" in before.columns else 0
    after_symbols = after["symbol"].nunique() if "symbol" in after.columns else 0
    return {
        "filter_name": filter_name,
        "input_rows": len(before),
        "output_rows": len(after),
        "removed_rows": len(before) - len(after),
        "input_symbols": before_symbols,
        "output_symbols": after_symbols,
        "removed_symbols": before_symbols - after_symbols,
        "status": status,
        "message": message,
    }


def _skipped_row(filter_name: str, df: pd.DataFrame, message: str) -> dict:
    return _audit_row(filter_name, df, df, status="skipped", message=message)


def _normalize_price_frame(prices: pd.DataFrame) -> pd.DataFrame:
    out = prices.copy()
    out["date"] = pd.to_datetime(out["date"])
    out["symbol"] = out["symbol"].astype(str).str.zfill(6)
    for col in ["open", "high", "low", "close", "volume", "amount", "turnover", "pct_change"]:
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce")
    return out.sort_values(["symbol", "date"]).reset_index(drop=True)


def _normalize_security_master(security_master: pd.DataFrame | None) -> pd.DataFrame | None:
    if security_master is None or security_master.empty:
        return None

    out = security_master.copy()
    out["symbol"] = out["symbol"].astype(str).str.zfill(6)
    if "list_date" in out.columns:
        out["list_date"] = pd.to_datetime(out["list_date"])
    if "float_market_cap" in out.columns:
        out["float_market_cap"] = pd.to_numeric(out["float_market_cap"], errors="coerce")
    if "is_st" in out.columns:
        out["is_st"] = out["is_st"].fillna(False).astype(bool)
    return out.drop_duplicates(subset=["symbol"], keep="last")


def _normalize_trade_status(trade_status: pd.DataFrame | None) -> pd.DataFrame | None:
    if trade_status is None or trade_status.empty:
        return None

    out = trade_status.copy()
    out["date"] = pd.to_datetime(out["date"])
    out["symbol"] = out["symbol"].astype(str).str.zfill(6)
    for col in ["is_suspended", "is_limit_up", "is_limit_down"]:
        if col in out.columns:
            out[col] = out[col].fillna(False).astype(bool)
    return out.drop_duplicates(subset=["date", "symbol"], keep="last")


#传来的mask其实是一个series过滤条件
def _apply_mask(df: pd.DataFrame, audit_rows: list[dict], name: str, mask: pd.Series, message: str = "") -> pd.DataFrame:
    before = df
    #mask 是一列 True/False     fillna(False)：空值设为 False   astype(bool)：强制转布尔
    mask = mask.fillna(False).astype(bool)
    #只保留mask==true的行
    after = df[mask].copy()
    audit_rows.append(_audit_row(name, before, after, message=message))
    return after


def _infer_suspended_from_prices(df: pd.DataFrame) -> pd.Series:
    if "volume" in df.columns:
        return df["volume"].fillna(0) <= 0
    if "amount" in df.columns:
        return df["amount"].fillna(0) <= 0
    return pd.Series(False, index=df.index)


def _infer_limit_from_prices(df: pd.DataFrame, direction: str) -> pd.Series:
    if "pct_change" in df.columns:
        pct = pd.to_numeric(df["pct_change"], errors="coerce")
        threshold = 9.8 if direction == "up" else -9.8
        return pct >= threshold if direction == "up" else pct <= threshold

    grouped = df.sort_values(["symbol", "date"]).groupby("symbol")
    returns = grouped["close"].pct_change()
    threshold = 0.098 if direction == "up" else -0.098
    return returns >= threshold if direction == "up" else returns <= threshold


def apply_universe_filters(
    prices: pd.DataFrame,
    symbols: list[str] | None = None,
    min_history_days: int = 80,
    min_symbols_per_date: int = 3,
    filters: dict | None = None,
    security_master: pd.DataFrame | None = None,
    trade_status: pd.DataFrame | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:                   #返回两个DataFrame元组
    filters = filters or {}
    policy = filters.get("missing_metadata_policy", "permissive")
    if policy != "permissive":
        raise ValueError("Only missing_metadata_policy='permissive' is supported by this workflow")

    df = _normalize_price_frame(prices)
    master = _normalize_security_master(security_master)
    status = _normalize_trade_status(trade_status)
    audit_rows: list[dict] = []

    if symbols:
        keep = {str(symbol).zfill(6) for symbol in symbols}
        df = _apply_mask(df, audit_rows, "symbol_whitelist", df["symbol"].isin(keep))

    #groupby("symbol") 按股票分组         transform("count") 算每只股票总天数       counts >= N → mask
    counts = df.groupby("symbol")["date"].transform("count")
    df = _apply_mask(df, audit_rows, "min_history_days", counts >= min_history_days, f"min_history_days={min_history_days}")

    #停牌 = 不能买也不能卖 → 直接删掉如果没有停牌数据，就用成交量 = 0自动推断。
    if filters.get("exclude_suspended", True):
        if status is not None and "is_suspended" in status.columns:
            df = df.merge(status[["date", "symbol", "is_suspended"]], on=["date", "symbol"], how="left")
            df["is_suspended"] = df["is_suspended"].fillna(False).astype(bool)
            df = _apply_mask(df, audit_rows, "exclude_suspended", ~df["is_suspended"])         #~取反，即保留未停牌的
            df = df.drop(columns=["is_suspended"])
        else:
            suspended = _infer_suspended_from_prices(df)
            df = _apply_mask(
                df,
                audit_rows,
                "exclude_suspended",
                ~suspended,
                "trade_status missing; inferred suspended rows from zero volume/amount when available",
            )

    #涨停买不进，跌停卖不出 → 删掉回测必须剔除，否则收益造假。
    if filters.get("exclude_limit_up_down", True):
        if status is not None and {"is_limit_up", "is_limit_down"}.issubset(status.columns):
            df = df.merge(status[["date", "symbol", "is_limit_up", "is_limit_down"]], on=["date", "symbol"], how="left")
            df[["is_limit_up", "is_limit_down"]] = df[["is_limit_up", "is_limit_down"]].fillna(False).astype(bool)
            df = _apply_mask(df, audit_rows, "exclude_limit_up_down", ~(df["is_limit_up"] | df["is_limit_down"]))   #保留未涨停或跌停的
            df = df.drop(columns=["is_limit_up", "is_limit_down"])
        else:
            limit_up = _infer_limit_from_prices(df, "up")
            limit_down = _infer_limit_from_prices(df, "down")
            df = _apply_mask(
                df,
                audit_rows,
                "exclude_limit_up_down",
                ~(limit_up | limit_down),
                "trade_status missing; inferred limit rows from pct_change or close returns",
            )

    if master is None:
        for name in [
            "exclude_st",
            "exclude_new_stock_days",
            "industry_include",
            "industry_exclude",
            "min_float_market_cap",
            "max_float_market_cap",
        ]:
            audit_rows.append(_skipped_row(name, df, "security_master missing; permissive mode kept rows"))
    else:
        df = df.merge(master, on="symbol", how="left")
        if filters.get("exclude_st", True) and "is_st" in df.columns:
            df = _apply_mask(df, audit_rows, "exclude_st", ~df["is_st"].fillna(False))
        elif filters.get("exclude_st", True):
            audit_rows.append(_skipped_row("exclude_st", df, "is_st column missing; permissive mode kept rows"))

        new_stock_days = filters.get("exclude_new_stock_days")
        if new_stock_days and "list_date" in df.columns:
            age_days = (df["date"] - df["list_date"]).dt.days
            df = _apply_mask(df, audit_rows, "exclude_new_stock_days", age_days >= int(new_stock_days))
        elif new_stock_days:
            audit_rows.append(_skipped_row("exclude_new_stock_days", df, "list_date column missing; permissive mode kept rows"))

        include = filters.get("industry_include") or []
        exclude = filters.get("industry_exclude") or []
        if include and "industry" in df.columns:
            df = _apply_mask(df, audit_rows, "industry_include", df["industry"].isin(include))
        elif include:
            audit_rows.append(_skipped_row("industry_include", df, "industry column missing; permissive mode kept rows"))

        if exclude and "industry" in df.columns:
            df = _apply_mask(df, audit_rows, "industry_exclude", ~df["industry"].isin(exclude))
        elif exclude:
            audit_rows.append(_skipped_row("industry_exclude", df, "industry column missing; permissive mode kept rows"))

        min_cap = filters.get("min_float_market_cap")
        max_cap = filters.get("max_float_market_cap")
        if min_cap is not None and "float_market_cap" in df.columns:
            df = _apply_mask(df, audit_rows, "min_float_market_cap", df["float_market_cap"] >= float(min_cap))
        elif min_cap is not None:
            audit_rows.append(_skipped_row("min_float_market_cap", df, "float_market_cap column missing; permissive mode kept rows"))

        if max_cap is not None and "float_market_cap" in df.columns:
            df = _apply_mask(df, audit_rows, "max_float_market_cap", df["float_market_cap"] <= float(max_cap))
        elif max_cap is not None:
            audit_rows.append(_skipped_row("max_float_market_cap", df, "float_market_cap column missing; permissive mode kept rows"))

        metadata_cols = ["list_date", "is_st", "industry", "float_market_cap"]
        df = df.drop(columns=[col for col in metadata_cols if col in df.columns])

    date_counts = df.groupby("date")["symbol"].transform("nunique")
    df = _apply_mask(
        df,
        audit_rows,
        "min_symbols_per_date",
        date_counts >= min_symbols_per_date,
        f"min_symbols_per_date={min_symbols_per_date}",
    )

    audit = pd.DataFrame(audit_rows, columns=AUDIT_COLUMNS) if audit_rows else _empty_audit()
    return df.sort_values(["symbol", "date"]).reset_index(drop=True), audit
