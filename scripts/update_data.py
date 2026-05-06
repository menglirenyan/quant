import sys
from pathlib import Path
from tqdm import tqdm
import pandas as pd
import time

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

from src.utils.config import load_yaml
from src.data.downloader import get_stock_daily, get_index_daily
from src.data.cleaner import clean_ohlcv
from src.data.storage import save_parquet


def main() -> None:
    config = load_yaml(PROJECT_ROOT / "configs" / "data.yaml")

    data_root = PROJECT_ROOT / config["data_root"]
    start_date = config["start_date"]
    end_date = config["end_date"]
    adjust = config.get("adjust", "qfq")

    raw_dir = data_root / "raw"
    processed_dir = data_root / "processed"

    stock_dfs = []

    print("Downloading stock daily data...")
    for symbol in tqdm(config["symbols"]):
        df = get_stock_daily(
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            adjust=adjust,
        )
        save_parquet(df, raw_dir / "stocks" / f"{symbol}.parquet")

        clean_df = clean_ohlcv(df)
        save_parquet(clean_df, processed_dir / "stocks" / f"{symbol}.parquet")
        stock_dfs.append(clean_df)

        time.sleep(2)

    all_stocks = pd.concat(stock_dfs, ignore_index=True)
    save_parquet(all_stocks, processed_dir / "stocks_all.parquet")

    index_dfs = []

    print("Downloading index daily data...")
    for name, index_code in tqdm(config["indices"].items()):
        df = get_index_daily(
            index_code=index_code,
            start_date=start_date,
            end_date=end_date,
        )
        df["index_name"] = name

        save_parquet(df, raw_dir / "indices" / f"{name}_{index_code}.parquet")

        clean_df = clean_ohlcv(df)
        clean_df["index_name"] = name
        save_parquet(clean_df, processed_dir / "indices" / f"{name}_{index_code}.parquet")
        index_dfs.append(clean_df)

        time.sleep(2)

    all_indices = pd.concat(index_dfs, ignore_index=True)
    save_parquet(all_indices, processed_dir / "indices_all.parquet")

    print("Data update finished.")


if __name__ == "__main__":
    main()
