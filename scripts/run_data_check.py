import sys
from pathlib import Path
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

from src.utils.config import load_yaml
from src.data.storage import read_parquet, save_csv
from src.analysis.metrics import summarize_returns, calc_simple_return
from src.analysis.plotting import plot_price_curve, plot_return_distribution


def main() -> None:
    config = load_yaml(PROJECT_ROOT / "configs" / "data.yaml")

    data_root = Path(config["data_root"])
    result_root = PROJECT_ROOT / "results"

    stocks = read_parquet(data_root / "processed" / "stocks_all.parquet")
    indices = read_parquet(data_root / "processed" / "indices_all.parquet")

    summary_stocks = summarize_returns(stocks)
    summary_indices = summarize_returns(indices)

    save_csv(summary_stocks, result_root / "tables" / "stock_risk_summary.csv")
    save_csv(summary_indices, result_root / "tables" / "index_risk_summary.csv")

    plot_price_curve(
        stocks,
        result_root / "figures" / "stock_close_price_curve.png",
    )

    plot_price_curve(
        indices,
        result_root / "figures" / "index_close_price_curve.png",
    )

    # 为每只股票输出收益率分布图
    for symbol, g in stocks.groupby("symbol"):
        g = g.sort_values("date")
        returns = calc_simple_return(g["close"])
        plot_return_distribution(
            returns,
            title=f"{symbol} Daily Return Distribution",
            save_path=result_root / "figures" / f"{symbol}_return_distribution.png",
        )

    print("Data check finished.")
    print(summary_stocks)
    print(summary_indices)


if __name__ == "__main__":
    main()
