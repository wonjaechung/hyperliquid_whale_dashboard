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
    dropdown = WebDriverWait(driver, 20).until(
        EC.element_to_be_clickable((By.XPATH, "//div[contains(@class, 'variant_black')]"))
    )
    dropdown.click()
    time.sleep(1)
    driver.find_element(By.XPATH, "//div[contains(text(),'All-time')]").click()
    time.sleep(3)

def parse_top30_with_wallet(driver):
    # 테이블 로드 대기
    try:
        # 테이블이 뜰 때까지 최대 60초 대기
        rows = WebDriverWait(driver, 60).until(
            EC.presence_of_all_elements_located((By.XPATH, "//table//tr"))
        )[1:11]
    except TimeoutException as e:
        print("⚠️ 테이블 로드 타임아웃, 페이지 새로고침 후 재시도…", e)
        driver.refresh()
        time.sleep(5)
        rows = WebDriverWait(driver, 60).until(
            EC.presence_of_all_elements_located((By.XPATH, "//table//tr"))
        )[1:11]

    data = []
    for idx, row in enumerate(rows, start=1):
        cols = row.find_elements(By.TAG_NAME, "td")
        trader = cols[1].text if len(cols) > 1 else "N/A"

        # 클릭해서 지갑 주소 캡처
        try:
            cols[1].click()
            time.sleep(2)
            wallet = driver.current_url.split("/")[-1]
        except:
            wallet = "N/A"

        driver.back()
        time.sleep(2)

        # 뒤로왔을 때 다시 테이블 셀 읽기
        fresh_row = WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.XPATH, "//table//tr"))
        )[idx]
        cols2 = fresh_row.find_elements(By.TAG_NAME, "td")

        data.append({
            "Trader":        trader,
            "Wallet":        wallet,
            "Account Value": cols2[2].text if len(cols2) > 2 else "N/A",
            "PNL":           cols2[3].text if len(cols2) > 3 else "N/A",
            "ROI":           cols2[4].text if len(cols2) > 4 else "N/A",
            "Volume":        cols2[5].text if len(cols2) > 5 else "N/A",
        })
        print(f"✅ row {idx}: {trader} / {wallet}")

    return pd.DataFrame(data)

def main():
    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    # 매 세션마다 충돌 방지용 임시 프로필
    tmp_dir = tempfile.gettempdir() + "/selenium_" + uuid.uuid4().hex
    options.add_argument(f"--user-data-dir={tmp_dir}")

    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )
    driver.get("https://app.hyperliquid.xyz/leaderboard")

    switch_to_all_time(driver)

    try:
        df = parse_top30_with_wallet(driver)
        df.to_csv("top30_wallets.csv", index=False)
        print("✅ Saved top30_wallets.csv")
    except Exception as e:
        print(f"❌ Failed to parse top30: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
