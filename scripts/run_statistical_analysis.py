import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

from src.analysis.plotting import plot_density_curve, plot_qq
from src.analysis.statistics import (
    collect_three_sigma_outliers,
    summarize_distribution_tests,
)
from src.data.storage import read_parquet, save_csv


def build_conclusion(summary):
    non_normal_count = int((~summary["is_normal"]).sum())
    significant_count = int(summary["is_mean_significant"].sum())
    highest_vol = summary.sort_values("annual_volatility", ascending=False).iloc[0]
    most_outliers = summary.sort_values("three_sigma_outlier_count", ascending=False).iloc[0]

    return f"""# 收益率分布与统计检验报告

## 数据范围

本报告使用 `data/processed/stocks_all.parquet` 中的清洗后股票收盘价。

## 主要结果

- JB 检验下不服从正态分布的收益率序列：{non_normal_count} / {len(summary)}
- 单样本 t 检验在 5% 水平下均值显著不为 0 的序列：{significant_count} / {len(summary)}
- 年化波动率最高的标的：{highest_vol["symbol"]} ({highest_vol["annual_volatility"]:.2%})
- 3σ 异常值最多的标的：{most_outliers["symbol"]} ({int(most_outliers["three_sigma_outlier_count"])})

## 结论

A 股日收益率不应默认按完全正态分布处理。3σ 表格用于定位需要进一步解释的尾部事件，t 检验用于判断平均日收益是否显著偏离 0，QQ 图和密度图则提供偏态、肥尾和分布断点的可视化证据。
"""


def main() -> None:
    data_root = PROJECT_ROOT / "data"
    result_root = PROJECT_ROOT / "results"
    report_root = PROJECT_ROOT / "reports"

    stocks = read_parquet(data_root / "processed" / "stocks_all.parquet")

    summary = summarize_distribution_tests(stocks)
    outliers = collect_three_sigma_outliers(stocks)

    save_csv(summary, result_root / "tables" / "distribution_test_summary.csv")
    save_csv(outliers, result_root / "tables" / "three_sigma_outliers.csv")

    for symbol, group in stocks.groupby("symbol"):
        group = group.sort_values("date")
        returns = group["close"].pct_change()

        plot_density_curve(
            returns,
            title=f"{symbol} Daily Return Density",
            save_path=result_root / "figures" / f"{symbol}_return_density.png",
        )
        plot_qq(
            returns,
            title=f"{symbol} Daily Return QQ Plot",
            save_path=result_root / "figures" / f"{symbol}_qq_plot.png",
        )

    report_root.mkdir(parents=True, exist_ok=True)
    (report_root / "02_distribution_tests.md").write_text(
        build_conclusion(summary),
        encoding="utf-8",
    )

    print("Statistical analysis finished.")
    print(summary)


if __name__ == "__main__":
    main()
