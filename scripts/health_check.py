import sys
import pandas as pd
import numpy as np
import akshare as ak
import sklearn
import statsmodels
import lightgbm
import xgboost

print("Python:", sys.version)
print("pandas:", pd.__version__)
print("numpy:", np.__version__)
print("akshare:", ak.__version__)
print("sklearn:", sklearn.__version__)
print("statsmodels:", statsmodels.__version__)
print("lightgbm:", lightgbm.__version__)
print("xgboost:", xgboost.__version__)

try:
    df = ak.stock_zh_a_hist(
        symbol="000001",
        period="daily",
        start_date="20240101",
        adjust="qfq"
    )
    print(df.head())
    print("AkShare data fetch OK")
except Exception as e:
    print("AkShare data fetch FAILED")
    print(type(e).__name__, e)

print("quant environment OK")
