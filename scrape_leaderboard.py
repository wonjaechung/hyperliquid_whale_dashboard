#!/usr/bin/env python3
import time
import tempfile
import uuid
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from webdriver_manager.chrome import ChromeDriverManager

URL = "https://app.hyperliquid.xyz/leaderboard"
CSV_PATH = "top30_wallets.csv"
ROWS = 10  # 크롤링할 상위 N개

def _make_driver():
    opts = webdriver.ChromeOptions()
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")
    # 임시 프로필 디렉토리 지정 (충돌 방지)
    tmpdir = tempfile.mkdtemp(prefix="selenium-")
    opts.add_argument(f"--user-data-dir={tmpdir}")
    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=opts)

def wait_table_rows(driver, timeout=20):
    # tbody 안에 적어도 ROWS 개 이상의 tr 이 뜰 때까지 대기
    return WebDriverWait(driver, timeout).until(
        EC.presence_of_all_elements_located((By.XPATH, "//table//tbody/tr"))
    )

def switch_to_all_time(driver):
    # 우상단 All-time 드롭다운 클릭
    btn = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, "//div[contains(@class,'variant_black')]"))
    )
    btn.click()
    time.sleep(1)
    alltime = driver.find_element(By.XPATH, "//div[text()='All-time']")
    alltime.click()
    time.sleep(2)

def parse_leaderboard(driver):
    rows = wait_table_rows(driver)
    data = []
    for idx, row in enumerate(rows[:ROWS]):
        cols = row.find_elements(By.TAG_NAME, "td")
        # 클릭해서 지갑 URL 획득
        try:
            cols[1].click()
            time.sleep(1)
            wallet = driver.current_url.rsplit("/",1)[-1]
        except:
            wallet = "N/A"
        driver.back()
        time.sleep(1)

        # 다시 컬럼 텍스트 추출
        cols = wait_table_rows(driver)[idx].find_elements(By.TAG_NAME, "td")
        data.append({
            "Rank":         idx+1,
            "Trader":       cols[1].text,
            "Wallet":       wallet,
            "Account Value": cols[2].text,
            "PNL":           cols[3].text,
            "ROI":           cols[4].text,
            "Volume":        cols[5].text,
        })
        print(f"✅ row {idx+1}: {cols[1].text} / {wallet}")
    return pd.DataFrame(data)

def main():
    driver = _make_driver()
    driver.get(URL)
    try:
        switch_to_all_time(driver)
        df = parse_leaderboard(driver)
        df.to_csv(CSV_PATH, index=False)
        print(f"✅ Saved {CSV_PATH} ({len(df)} rows)")
    except TimeoutException as e:
        print(f"❌ Timeout while loading leaderboard: {e}")
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
