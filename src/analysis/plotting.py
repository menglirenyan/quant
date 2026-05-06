from pathlib import Path
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from scipy import stats

def plot_corr_heatmap(corr, save_path):
    save_path = Path(save_path)
    save_path.parent.mkdir(parents=True, exist_ok=True)

    plt.figure(figsize=(8, 6))
    sns.heatmap(corr, annot=True, cmap="coolwarm")
    plt.title("Correlation Matrix Heatmap")
    plt.tight_layout()
    plt.savefig(save_path, dpi=150)
    plt.close()


def plot_density_curve(
    returns: pd.Series,
    title: str,
    save_path: str | Path,
) -> None:
    save_path = Path(save_path)
    save_path.parent.mkdir(parents=True, exist_ok=True)

    returns = pd.to_numeric(returns, errors="coerce").dropna()

    plt.figure(figsize=(10, 6))
    sns.histplot(returns, bins=80, stat="density", alpha=0.35, label="Histogram")
    sns.kdeplot(returns, linewidth=2, label="KDE")
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
    save_path = Path(save_path)
    save_path.parent.mkdir(parents=True, exist_ok=True)

    returns = pd.to_numeric(returns, errors="coerce").dropna()

    plt.figure(figsize=(8, 8))
    stats.probplot(returns, dist="norm", plot=plt)
    plt.title(title)
    plt.tight_layout()
    plt.savefig(save_path, dpi=150)
    plt.close()

def plot_price_curve(df: pd.DataFrame, save_path: str | Path) -> None:
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
