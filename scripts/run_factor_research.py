# -*- coding: utf-8 -*-
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

from src.analysis.plotting import plot_factor_ic_summary, plot_layered_cumulative_return
from src.backtest.layered import (
    calc_cost_sensitivity,
    calc_layer_returns,
    calc_long_only_returns,
    calc_long_short_returns,
    calc_long_short_turnover,
)
from src.data.storage import read_parquet, save_csv, save_parquet
from src.factors.evaluation import calc_ic_timeseries, summarize_ic_with_overlap_adjustment
from src.factors.library import available_factor_columns, build_price_factors, merge_valuation_factor
from src.factors.preprocess import add_forward_return, factor_columns_from_config, prepare_factor_dataset
from src.factors.report import build_factor_research_report
from src.factors.universe import apply_universe_filters
from src.utils.config import load_yaml


def read_optional_parquet(path: Path) -> pd.DataFrame | None:
    if not path.exists():
        return None
    return read_parquet(path)


def main() -> None:
    config = load_yaml(PROJECT_ROOT / "configs" / "factor.yaml")

    price_path = PROJECT_ROOT / config["input"]["price_path"]
    valuation_path = PROJECT_ROOT / config["input"]["valuation_path"]
    security_master_path = PROJECT_ROOT / config["input"]["security_master_path"]
    trade_status_path = PROJECT_ROOT / config["input"]["trade_status_path"]
    result_root = PROJECT_ROOT / config["result_root"]
    report_root = PROJECT_ROOT / config["report_root"]

    if not price_path.exists():
        raise FileNotFoundError(
            f"Price data not found: {price_path}. Run python scripts/update_data.py first, "
            "and include at least several stocks for cross-sectional factor research."
        )

    raw_prices = read_parquet(price_path)
    security_master = read_optional_parquet(security_master_path)
    trade_status = read_optional_parquet(trade_status_path)
    prices, filter_audit = apply_universe_filters(
        raw_prices,
        symbols=config["universe"].get("symbols"),
        min_history_days=config["universe"].get("min_history_days", 80),
        min_symbols_per_date=config["universe"].get("min_symbols_per_date", 3),
        filters=config["universe"].get("filters", {}),
        security_master=security_master,
        trade_status=trade_status,
    )

    if prices["symbol"].nunique() < config["universe"].get("min_symbols_per_date", 3):
        raise ValueError(
            "Factor research needs a cross-section. Add more symbols to configs/data.yaml, "
            "run scripts/update_data.py, then rerun this script."
        )

    factors = build_price_factors(
        prices,
        momentum_window=config["factors"].get("momentum_window", 20),
        volatility_window=config["factors"].get("volatility_window", 20),
        turnover_window=config["factors"].get("turnover_window", 20),
        value_window=config["factors"].get("value_window", 120),
    )
    factor_columns = factor_columns_from_config(config["factors"])
    valuation = read_optional_parquet(valuation_path)
    factors = merge_valuation_factor(factors, valuation)
    factor_columns = available_factor_columns(factors, factor_columns)
    if not factor_columns:
        raise ValueError("No usable factor columns after valuation and price-factor availability checks.")

    labels = add_forward_return(
        prices,
        horizon=config["label"].get("forward_return_days", 5),
        timing=config["label"].get("timing", "next_open_to_horizon_open"),
    )
    factor_data = prepare_factor_dataset(
        factors,
        labels,
        factor_columns=factor_columns,
        winsorize_quantile=config["preprocess"].get("winsorize_quantile", 0.01),
        zscore=config["preprocess"].get("zscore", True),
        min_symbols_per_date=config["universe"].get("min_symbols_per_date", 3),
    )

    if factor_data.empty:
        raise ValueError("No valid factor rows after preprocessing. Check history length and missing values.")

    ic_ts = calc_ic_timeseries(factor_data, factor_columns)
    ic_summary = summarize_ic_with_overlap_adjustment(
        ic_ts,
        horizon=config["label"].get("forward_return_days", 5),
        non_overlapping=config["label"].get("non_overlapping_ic", True),
    )
    layer_returns = calc_layer_returns(
        factor_data,
        factor_columns,
        quantiles=config["backtest"].get("quantiles", 5),
    )
    long_short = calc_long_short_returns(layer_returns)
    long_only = calc_long_only_returns(long_short)
    turnover = calc_long_short_turnover(
        factor_data,
        factor_columns,
        quantiles=config["backtest"].get("quantiles", 5),
    )
    cost_sensitivity = calc_cost_sensitivity(
        long_short,
        turnover,
        transaction_cost_bps=config["backtest"].get("transaction_cost_bps", [0, 5, 10, 20]),
    )

    save_csv(filter_audit, result_root / "tables" / "universe_filter_audit.csv")
    save_parquet(factor_data, result_root / "tables" / "factor_dataset.parquet")
    save_csv(ic_ts, result_root / "tables" / "factor_ic_timeseries.csv")
    save_csv(ic_summary, result_root / "tables" / "factor_ic_summary.csv")
    save_csv(layer_returns, result_root / "tables" / "factor_layer_returns.csv")
    save_csv(long_short, result_root / "tables" / "factor_long_short_returns.csv")
    save_csv(long_only, result_root / "tables" / "factor_long_only_returns.csv")
    save_csv(turnover, result_root / "tables" / "factor_turnover.csv")
    save_csv(cost_sensitivity, result_root / "tables" / "factor_cost_sensitivity.csv")

    try:
        plot_factor_ic_summary(ic_summary, result_root / "figures" / "factor_ic_summary.png")
        for factor in factor_columns:
            plot_layered_cumulative_return(
                layer_returns,
                factor,
                result_root / "figures" / f"{factor}_layered_cumulative_return.png",
            )
    except ModuleNotFoundError as exc:
        print(f"[Plot Skipped] {exc}")

    report_root.mkdir(parents=True, exist_ok=True)
    value_source = factors["value_factor_source"].dropna().iloc[0] if "value_factor_source" in factors else "unknown"
    (report_root / "03_factor_research.md").write_text(
        build_factor_research_report(
            factor_data=factor_data,
            ic_summary=ic_summary,
            cost_sensitivity=cost_sensitivity,
            audit=filter_audit,
            factor_columns=factor_columns,
            value_source=value_source,
            label_timing=config["label"].get("timing", "next_open_to_horizon_open"),
            horizon=config["label"].get("forward_return_days", 5),
            non_overlapping_ic=config["label"].get("non_overlapping_ic", True),
            long_short_mode=config["backtest"].get("long_short_mode", "research"),
        ),
        encoding="utf-8-sig",
    )

    print("Factor research finished.")
    print(ic_summary)


if __name__ == "__main__":
    main()
