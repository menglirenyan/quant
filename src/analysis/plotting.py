from pathlib import Path
import pandas as pd

try:
    import matplotlib.pyplot as plt
except ModuleNotFoundError:
    plt = None

try:
    import seaborn as sns
except ModuleNotFoundError:
    sns = None

try:
    from scipy import stats
except ModuleNotFoundError:
    stats = None


def _require_matplotlib() -> None:
    if plt is None:
        raise ModuleNotFoundError("matplotlib is required for plotting")


def plot_corr_heatmap(corr, save_path):
    _require_matplotlib()

    save_path = Path(save_path)
    save_path.parent.mkdir(parents=True, exist_ok=True)

    plt.figure(figsize=(8, 6))
    if sns is not None:
        sns.heatmap(corr, annot=True, cmap="coolwarm")
    else:
        plt.imshow(corr, cmap="coolwarm", aspect="auto")
        plt.colorbar()
        plt.xticks(range(len(corr.columns)), corr.columns, rotation=45)
        plt.yticks(range(len(corr.index)), corr.index)
    plt.title("Correlation Matrix Heatmap")
    plt.tight_layout()
    plt.savefig(save_path, dpi=150)
    plt.close()


def plot_density_curve(
    returns: pd.Series,
    title: str,
    save_path: str | Path,
) -> None:
    _require_matplotlib()

    save_path = Path(save_path)
    save_path.parent.mkdir(parents=True, exist_ok=True)

    returns = pd.to_numeric(returns, errors="coerce").dropna()

    plt.figure(figsize=(10, 6))
    if sns is not None:
        sns.histplot(returns, bins=80, stat="density", alpha=0.35, label="Histogram")
        sns.kdeplot(returns, linewidth=2, label="KDE")
    else:
        plt.hist(returns, bins=80, density=True, alpha=0.45, label="Histogram")
    plt.title(title)
    plt.xlabel("Daily Return")
    plt.ylabel("Density")
    plt.legend()
    plt.tight_layout()
    plt.savefig(save_path, dpi=150)
    plt.close()


def plot_qq(
    returns: pd.Series,
    title: str,
    save_path: str | Path,
) -> None:
    _require_matplotlib()

    save_path = Path(save_path)
    save_path.parent.mkdir(parents=True, exist_ok=True)

    returns = pd.to_numeric(returns, errors="coerce").dropna()
    if stats is None:
        raise ModuleNotFoundError("scipy is required for QQ plots")

    plt.figure(figsize=(8, 8))
    stats.probplot(returns, dist="norm", plot=plt)
    plt.title(title)
    plt.tight_layout()
    plt.savefig(save_path, dpi=150)
    plt.close()

def plot_price_curve(df: pd.DataFrame, save_path: str | Path) -> None:
    _require_matplotlib()

    save_path = Path(save_path)
    save_path.parent.mkdir(parents=True, exist_ok=True)

    plt.figure(figsize=(12, 6))

    for symbol, g in df.groupby("symbol"):
        g = g.sort_values("date")
        plt.plot(g["date"], g["close"], label=symbol)

    plt.title("Close Price Curve")
    plt.xlabel("Date")
    plt.ylabel("Close Price")
    plt.legend()
    plt.tight_layout()
    plt.savefig(save_path, dpi=150)
    plt.close()


def plot_return_distribution(
    returns: pd.Series,
    title: str,
    save_path: str | Path,
) -> None:
    _require_matplotlib()

    save_path = Path(save_path)
    save_path.parent.mkdir(parents=True, exist_ok=True)

    returns = returns.dropna()

    plt.figure(figsize=(10, 6))
    plt.hist(returns, bins=80)
    plt.title(title)
    plt.xlabel("Daily Return")
    plt.ylabel("Frequency")
    plt.tight_layout()
    plt.savefig(save_path, dpi=150)
    plt.close()


def plot_factor_ic_summary(summary: pd.DataFrame, save_path: str | Path) -> None:
    _require_matplotlib()

    save_path = Path(save_path)
    save_path.parent.mkdir(parents=True, exist_ok=True)

    plot_df = summary.sort_values("mean_rank_ic", ascending=True)

    plt.figure(figsize=(10, 6))
    plt.barh(plot_df["factor"], plot_df["mean_ic"], alpha=0.7, label="IC")
    plt.barh(plot_df["factor"], plot_df["mean_rank_ic"], alpha=0.7, label="RankIC")
    plt.axvline(0, color="black", linewidth=1)
    plt.title("Factor IC and RankIC Summary")
    plt.xlabel("Average Correlation")
    plt.legend()
    plt.tight_layout()
    plt.savefig(save_path, dpi=150)
    plt.close()


def plot_layered_cumulative_return(
    layer_returns: pd.DataFrame,
    factor: str,
    save_path: str | Path,
) -> None:
    _require_matplotlib()

    save_path = Path(save_path)
    save_path.parent.mkdir(parents=True, exist_ok=True)

    data = layer_returns[layer_returns["factor"] == factor].copy()
    if data.empty:
        return

    pivot = data.pivot(index="date", columns="quantile", values="mean_forward_return").sort_index()
    cumulative = (1 + pivot.fillna(0)).cumprod() - 1

    plt.figure(figsize=(11, 6))
    for col in cumulative.columns:
        plt.plot(cumulative.index, cumulative[col], label=f"Q{col}")
    plt.axhline(0, color="black", linewidth=1)
    plt.title(f"{factor} Layered Cumulative Forward Return")
    plt.xlabel("Date")
    plt.ylabel("Cumulative Return")
    plt.legend()
    plt.tight_layout()
    plt.savefig(save_path, dpi=150)
    plt.close()
