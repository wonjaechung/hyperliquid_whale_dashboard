#!/usr/bin/env python3
import requests
import pandas as pd
from hyperliquid.utils import constants

# ── Configuration ──────────────────────────────────────────────────────────
BASE_URL    = constants.MAINNET_API_URL
CSV_PATH    = "top30_wallets.csv"
LIMIT       = 10

# ── Fetch top-30 All-Time leaderboard via REST API ─────────────────────────
def fetch_top30_all_time():
    # API 엔드포인트 예: GET /leaderboard/allTime?limit=30
    url = f"{BASE_URL}/leaderboard/allTime"
    params = {"limit": LIMIT}
    resp = requests.get(url, params=params)
    resp.raise_for_status()
    data = resp.json()  # 리스트 of dicts
    
    # 필요한 필드만 뽑아서 DataFrame으로
    df = pd.DataFrame(data)
    df = df.rename(columns={
        "trader":         "Trader",
        "wallet":         "Wallet",
        "accountValue":   "Account Value",
        "pnl":            "PNL",
        "roi":            "ROI",
        "volume":         "Volume"
    })
    # 혹시 순위 컬럼이 없으면 생성
    df.insert(0, "Rank", range(1, len(df)+1))
    return df[["Rank","Trader","Wallet","Account Value","PNL","ROI","Volume"]]

def main():
    df = fetch_top30_all_time()
    df.to_csv(CSV_PATH, index=False)
    print(f"✅ Saved {CSV_PATH} (fetched {len(df)} rows)")

if __name__ == "__main__":
    main()
