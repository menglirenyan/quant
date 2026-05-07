import sys
from pathlib import Path
from tqdm import tqdm
import pandas as pd
import time

#resolve()取绝对路径
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

from src.utils.config import load_yaml
from src.data.downloader import get_stock_daily, get_index_daily
from src.data.cleaner import clean_ohlcv
from src.data.storage import read_parquet, save_parquet


def read_or_fetch(cache_path: Path, fetcher):
    if cache_path.exists():
        print(f"[Cache Hit] {cache_path}")
        return read_parquet(cache_path)

    df = fetcher()
    save_parquet(df, cache_path)
    return df


def main() -> None:
    config = load_yaml(PROJECT_ROOT / "configs" / "data.yaml")

    #data_root要读到根目录，所以不能直接=config[]
    data_root = PROJECT_ROOT / config["data_root"]
    start_date = config["start_date"]
    end_date = config["end_date"]
    adjust = config.get("adjust", "qfq")

    raw_dir = data_root / "raw"
    processed_dir = data_root / "processed"
    cache_dir = data_root / "cache"

    stock_dfs = []

    print("Downloading stock daily data...")
    #tqdm给循环加进度条 
    for symbol in tqdm(config["symbols"]):
        cache_path = cache_dir / "stocks" / f"{symbol}_{start_date}_{end_date}_{adjust}.parquet"
        df = read_or_fetch(            #read_or_fetch函数判断股票信息是否下载过了，有则读_or_联网下载
            cache_path,
            lambda symbol=symbol: get_stock_daily(         #传参传函数，无论是否执行都会直接调用  如果用lambda，对函数包装了一下，能传本体。
                symbol=symbol,
                start_date=start_date,
                end_date=end_date,
                adjust=adjust,
            ),
        )
        save_parquet(df, raw_dir / "stocks" / f"{symbol}.parquet")

        clean_df = clean_ohlcv(df)
        save_parquet(clean_df, processed_dir / "stocks" / f"{symbol}.parquet")
        stock_dfs.append(clean_df)
        
        #可能要联网下载股票，请求太频繁会被封ip
        time.sleep(2)

    #将单个stock数据合并为一张表
    all_stocks = pd.concat(stock_dfs, ignore_index=True)
    save_parquet(all_stocks, processed_dir / "stocks_all.parquet")

    index_dfs = []

    #类似思路下载大盘指数数据
    print("Downloading index daily data...")
    for name, index_code in tqdm(config["indices"].items()):
        cache_path = cache_dir / "indices" / f"{name}_{index_code}_{start_date}_{end_date}.parquet"
        df = read_or_fetch(
            cache_path,
            lambda index_code=index_code: get_index_daily(
                index_code=index_code,
                start_date=start_date,
                end_date=end_date,
            ),
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
