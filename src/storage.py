import pandas as pd
from pathlib import Path

def save_parquet(df: pd.DataFrame, path: str):
    print("inside save_parquet ",path)
    p = Path(path)
    print("Path p: ",p)
    p.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(p, index=False)
    # print("parquet df: ", len(df))
