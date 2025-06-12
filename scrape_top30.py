import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

def switch_to_all_time(driver):
    dropdown = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, "//div[contains(@class, 'variant_black')]"))
    )
    dropdown.click()
    time.sleep(1)
    driver.find_element(By.XPATH, "//div[contains(text(), 'All-time')]").click()
    time.sleep(3)

def parse_top30_with_wallet(driver):
    rows = WebDriverWait(driver, 10).until(
        EC.presence_of_all_elements_located((By.XPATH, "//table//tr"))
    )[1:31]
    data = []
    for i, row in enumerate(rows, start=1):
        cols = row.find_elements(By.TAG_NAME, "td")
        name = cols[1].text
        cols[1].click(); time.sleep(2)
        wallet = driver.current_url.split("/")[-1]
        driver.back(); time.sleep(2)
        cols2 = WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.XPATH, "//table//tr"))
        )[i].find_elements(By.TAG_NAME, "td")
        data.append({
            "Trader":      name,
            "Wallet":      wallet,
            "Account Value": cols2[2].text,
            "PNL":         cols2[3].text,
            "ROI":         cols2[4].text,
            "Volume":      cols2[5].text
        })
    return data

def main():
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    driver.get("https://app.hyperliquid.xyz/leaderboard")
    switch_to_all_time(driver)
    data = parse_top30_with_wallet(driver)
    driver.quit()

    df = pd.DataFrame(data)
    df.to_csv("top30_wallets.csv", index=False)

if __name__ == "__main__":
    main()
