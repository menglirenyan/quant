import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

from src.data.storage import read_parquet, save_csv
from src.analysis.matrix import build_return_matrix, calc_cov_matrix, calc_corr_matrix
from src.analysis.metrics import normality_test
from src.analysis.plotting import plot_corr_heatmap


def main():
    data_root = PROJECT_ROOT / "data"
    result_root = PROJECT_ROOT / "results"

    df = read_parquet(data_root / "processed" / "stocks_all.parquet")

    ret_mat = build_return_matrix(df)

    cov = calc_cov_matrix(ret_mat)
    corr = calc_corr_matrix(ret_mat)

    save_csv(cov, result_root / "tables" / "cov_matrix.csv")
    save_csv(corr, result_root / "tables" / "corr_matrix.csv")

    plot_corr_heatmap(
        corr,
        result_root / "figures" / "corr_heatmap.png"
    )

    print("Covariance Matrix:")
    print(cov)

    print("\nCorrelation Matrix:")
    print(corr)

    print("\nNormality Test:")
    for col in ret_mat.columns:
        res = normality_test(ret_mat[col])
        print(col, res)


if __name__ == "__main__":
    main()