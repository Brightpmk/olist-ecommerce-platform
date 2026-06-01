from __future__ import annotations
import pandas as pd
from pathlib import Path
from typing import Dict

def extract_all(raw_dir: str, tables: dict) -> Dict[str, pd.DataFrame]:
    raw_path = Path(raw_dir)
    dfs: Dict[str, pd.DataFrame] = {}

    for key, filename in tables.items():
        fp = raw_path / filename
        if not fp.exists():
            raise FileNotFoundError(f"missing dataset file: {fp}")

        if fp.stat().st_size == 0:
            raise ValueError(f"dataset file is empty: {fp}")

        try:
            df = pd.read_csv(fp)
        except Exception as e:
            raise RuntimeError(f"failed to read csv {filename}: {e}")
            
        dfs[key] = df

    return dfs
