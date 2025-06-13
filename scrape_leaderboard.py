import time, tempfile, uuid
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import TimeoutException

def switch_to_all_time(driver):
    dropdown = WebDriverWait(driver, 15).until(
        EC.element_to_be_clickable((By.XPATH, "//div[contains(@class,'variant_black')]"))
    )
    dropdown.click()
    time.sleep(1)
    driver.find_element(By.XPATH, "//div[text()='All-time']").click()
    time.sleep(3)

def parse_top30_with_wallet(driver):
    # 기다렸다가 table rows 로드
    rows = WebDriverWait(driver, 30).until(
        EC.presence_of_all_elements_located((By.XPATH, "//table//tr"))
    )[1:11]

    data = []
    for idx, row in enumerate(rows[:30], start=1):
        cols = row.find_elements(By.TAG_NAME, "td")
        trader = cols[1].text
        # 클릭해서 URL 가져오기
        try:
            cols[1].click()
            time.sleep(1)
            wallet = driver.current_url.rsplit("/",1)[-1]
        except Exception:
            wallet = "N/A"
        driver.back()
        time.sleep(1)
        # 뒷부분 데이터 다시 추출
        refreshed = WebDriverWait(driver, 11).until(
            EC.presence_of_all_elements_located((By.XPATH, "//table//tr"))
        )
        cols2 = refreshed[idx].find_elements(By.TAG_NAME, "td")
        data.append({
            "Trader":         trader,
            "Wallet":         wallet,
            "Account Value":  cols2[2].text,
            "PNL":            cols2[3].text,
            "ROI":            cols2[4].text,
            "Volume":         cols2[5].text,
        })
        print(f"✅ row {idx}: {trader} / {wallet}")
    return pd.DataFrame(data)

def main():
    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    # 고유한 유저 데이터 디렉토리 지정
    tmp_dir = tempfile.gettempdir() + "/selenium_" + uuid.uuid4().hex
    options.add_argument(f"--user-data-dir={tmp_dir}")

    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )
    driver.get("https://app.hyperliquid.xyz/leaderboard")

    try:
        switch_to_all_time(driver)
        df = parse_top30_with_wallet(driver)
        df.to_csv("top30_wallets.csv", index=False)
        print("✅ Saved top30_wallets.csv")
    except TimeoutException as e:
        print(f"❌ Timeout while loading leaderboard: {e}")
    except Exception as e:
        print(f"❌ Failed to parse top30: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
