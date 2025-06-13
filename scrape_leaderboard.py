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
    dropdown = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, "//div[contains(@class, 'variant_black')]"))
    )
    dropdown.click()
    time.sleep(1)
    driver.find_element(By.XPATH, "//div[contains(text(),'All-time')]").click()
    time.sleep(3)

def parse_top10_with_wallet(driver):
    # 최대 10행 기다리기 (30초)
    try:
        rows = WebDriverWait(driver, 30).until(
            EC.presence_of_all_elements_located((By.XPATH, "//table//tr"))
        )[1:11]
    except TimeoutException:
        driver.refresh()
        time.sleep(2)
        rows = WebDriverWait(driver, 30).until(
            EC.presence_of_all_elements_located((By.XPATH, "//table//tr"))
        )[1:31]

    data = []
    for i, row in enumerate(rows, start=1):
        cols = row.find_elements(By.TAG_NAME, "td")
        trader = cols[1].text if len(cols)>1 else "N/A"
        # 클릭 → 주소 추출
        try:
            cols[1].click()
            time.sleep(2)
            wallet = driver.current_url.split("/")[-1]
        except:
            wallet = "N/A"
        driver.back()
        time.sleep(2)
        # 뒤로왔을 때 다시 row elements 얻기
        all_rows = WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.XPATH, "//table//tr"))
        )
        cols2 = all_rows[i].find_elements(By.TAG_NAME, "td")
        data.append({
            "Trader":         trader,
            "Wallet":         wallet,
            "Account Value":  cols2[2].text if len(cols2)>2 else "N/A",
            "PNL":            cols2[3].text if len(cols2)>3 else "N/A",
            "ROI":            cols2[4].text if len(cols2)>4 else "N/A",
            "Volume":         cols2[5].text if len(cols2)>5 else "N/A"
        })
        print(f"✅ row {i}: {trader} / {wallet}")
    return pd.DataFrame(data)

def main():
    # 크롬 옵션: 헤드리스 + 샌드박스 off + 임시 유저데이터
    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
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
