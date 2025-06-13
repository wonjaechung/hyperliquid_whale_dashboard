import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# 드라이버 세팅
options = webdriver.ChromeOptions()
# options.add_argument("--headless")
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
driver.get("https://app.hyperliquid.xyz/leaderboard")

# All-time 뷰로 전환
def switch_to_all_time():
    dropdown = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, "//div[contains(@class, 'variant_black')]"))
    )
    dropdown.click()
    time.sleep(1)
    view_button = driver.find_element(By.XPATH, f"//div[contains(text(), 'All-time')]")
    view_button.click()
    time.sleep(3)

# row 30개에서 Wallet 추출 (안정 버전)
def parse_top30_with_wallet():
    data = []

    for i in range(1, 11):
        try:
            # row 재조회
            rows = WebDriverWait(driver, 10).until(
                EC.presence_of_all_elements_located((By.XPATH, "//table//tr"))
            )[1:11]

            if i - 1 >= len(rows):
                raise Exception("row index out of range")

            cols = rows[i - 1].find_elements(By.TAG_NAME, "td")
            trader_name = cols[1].text if len(cols) > 1 else "N/A"

            # 클릭 → URL 추출
            if cols[1].is_displayed() and cols[1].is_enabled():
                cols[1].click()
                time.sleep(2)
                url = driver.current_url
                wallet_address = url.split("/")[-1]
                driver.back()
                time.sleep(2)
            else:
                wallet_address = "N/A"

            # 뒤로 간 뒤 row 다시 가져오기
            rows_after = WebDriverWait(driver, 10).until(
                EC.presence_of_all_elements_located((By.XPATH, "//table//tr"))
            )[1:11]
            cols_after = rows_after[i - 1].find_elements(By.TAG_NAME, "td")

            data.append({
                "Trader": trader_name,
                "Wallet": wallet_address,
                "Account Value": cols_after[2].text if len(cols_after) > 2 else "N/A",
                "PNL": cols_after[3].text if len(cols_after) > 3 else "N/A",
                "ROI": cols_after[4].text if len(cols_after) > 4 else "N/A",
                "Volume": cols_after[5].text if len(cols_after) > 5 else "N/A"
            })

            print(f"✅ row {i} 완료: {trader_name} ({wallet_address})")

        except Exception as e:
            print(f"❌ row {i} 지갑주소 추출 실패: {e}")
            data.append({
                "Trader": f"Row{i}",
                "Wallet": "N/A",
                "Account Value": "N/A",
                "PNL": "N/A",
                "ROI": "N/A",
                "Volume": "N/A"
            })

    return data

# 실행
switch_to_all_time()
data = parse_top30_with_wallet()
driver.quit()

# 저장 및 출력
df = pd.DataFrame(data)
df.to_csv("top30_wallets2.csv", index=False)
print(df)
