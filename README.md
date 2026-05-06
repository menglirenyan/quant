# quant

xrrg-managed quantitative research project.

## Structure

- `data/`: raw, processed, and cached market data
- `src/`: core source code
- `scripts/`: executable task entrypoints
- `notebooks/`: analysis and visualization
- `configs/`: project configuration
- `logs/`: runtime logs
- `results/`: experiment outputs
- `reports/`: research reports
- `tests/`: unit tests

## Environment

```bash
cd /opt/quant
source .venv/bin/activate
python scripts/health_check.py

```
quant
├─ README.md
├─ configs
│  ├─ config.yaml
│  └─ data.yaml
├─ cpp
├─ data
│  ├─ cache
│  ├─ processed
│  └─ raw
├─ notebooks
├─ reports
├─ requirements.txt
├─ scripts
│  ├─ health_check.py
│  ├─ run_data_check.py
│  └─ update_data.py
├─ src
│  ├─ __init__.py
│  ├─ analysis
│  │  ├─ __init__.py
│  │  ├─ metrics.py
│  │  └─ plotting.py
│  ├─ backtest
│  │  └─ __init__.py
│  ├─ data
│  │  ├─ __init__.py
│  │  ├─ cleaner.py
│  │  ├─ downloader.py
│  │  └─ storage.py
│  ├─ factors
│  │  └─ __init__.py
│  ├─ ml
│  │  └─ __init__.py
│  ├─ portfolio
│  │  └─ __init__.py
│  └─ utils
│     ├─ __init__.py
│     └─ config.py
└─ tests

```